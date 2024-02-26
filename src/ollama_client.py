import os
import json
import time
import urllib3
import requests
import argparse

def get_endpoint(api_base='http://localhost:11434', model_name='llama3.2:latest'):
    return {
        "name": model_name,
        "model": model_name,
        "key": "",
        "endpoint": f"{api_base}/v1/chat/completions"
    }

def ollama_list(api_base='http://localhost:11434'):
    # call api http://localhost:11434/api/tags with http get request
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    endpoint = f"{api_base}/api/tags"
    response = requests.get(endpoint, verify=False)
    response.raise_for_status()
    data = response.json()
    models_list = data['models']
    models_dict = {}
    for entry in models_list:
        # get parameter_size and quantization_level from data
        model = entry['model']
        details = entry['details']
        attr = {}
        parameter_size = details['parameter_size']
        quantization_level = details['quantization_level']
        parameter_size = parameter_size[:-1]
        try:
            parameter_size = float(parameter_size)
            attr['parameter_size'] = parameter_size
        except ValueError:
            pass
        quantization_level_char = quantization_level[1:2]
        try:
            quantization_level = int(quantization_level_char)
            attr['quantization_level'] = quantization_level
        except ValueError:
            pass
        models_dict[model] = attr
    return models_dict

def chat(endpoint, output_queue, context, prompt='Hello World', temperature=0.0, max_tokens=8192):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    stoptokens = ["[/INST]", "<|im_end|>", "<|end_of_turn|>", "<|eot_id|>", "<|end_header_id|>", "<EOS_TOKEN>", "</s>", "<|end|>"]
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if endpoint.get("key", ""): headers['Authorization'] = 'Bearer ' + endpoint["key"]
    modelname = endpoint["model"]
    context.append({"role": "user", "content": prompt})
    payload = {
        "model": modelname,
        "messages": context,
        "temperature": temperature,
        "response_format": { "type": "text" },
        "stream": False,
        "stop": stoptokens,
        "max_tokens": max_tokens
    }
    t0 = time.time()
    try:
        response = requests.post(endpoint["endpoint"], headers=headers, json=payload, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if response:
            try:
                data = response.json()
                message = data.get('message', {})
                content = message.get('content', '')
                raise Exception(f"API request failed: {content}")
            except json.JSONDecodeError:
                raise Exception(f"API request failed: {e}")
    t1 = time.time()
    try:
        data = response.json()
        usage = data.get('usage', {})
        total_tokens = usage.get('total_tokens', 0)
        token_per_second = total_tokens / (t1 - t0)
        choices = data.get('choices', [])
        if len(choices) == 0: raise Exception("No response from the API: " + str(data))
        message = choices[0].get('message', {})
        answer = message.get('content', '')
        answer_lines = answer.split('\n')
        if output_queue:
            for line in answer_lines:
                output_queue.put(f"{line}\n")
            output_queue.put("\n")
        context.append({"role": "assistant", "content": answer})
        return total_tokens, token_per_second
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response from the API: {e}")
