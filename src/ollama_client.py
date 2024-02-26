import os
import json
import time
import urllib3
import requests
import argparse
from urllib.parse import urlparse
import http.client

def get_endpoint(api_base='http://localhost:11434', model_name='llama3.2:latest'):
    return {
        "key": "",
        "name": model_name,
        "model": model_name,
        "api_base": api_base
    }

def ollama_list(endpoint):
    # call api http://localhost:11434/api/tags with http get request
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    api_url = f"{endpoint["api_base"]}/api/tags"
    response = requests.get(api_url, verify=False)
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

POISON_PILL = "data: [DONE]"

def chat(endpoint, output_queue, context, prompt='Hello World', stream = False, temperature=0.0, max_tokens=8192):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    stoptokens = ["[/INST]", "<|im_end|>", "<|end_of_turn|>", "<|eot_id|>", "<|end_header_id|>", "<EOS_TOKEN>", "</s>", "<|end|>"]
    modelname = endpoint["model"]
    context.append({"role": "user", "content": prompt})
    body = {
        "top_p": 0.7,
        "stream": stream,
        "stop": stoptokens,
        "model": modelname,
        "messages": context,
        "presence_penalty": 0.3,
        "frequency_penalty": 0.7,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_format": { "type": "text" }
    }
    encoded_body = json.dumps(body).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Content-Length': str(len(encoded_body))}
    if endpoint.get("key", ""): headers['Authorization'] = 'Bearer ' + endpoint["key"]
    t_0 = time.time()
    api_url = urlparse(endpoint["api_base"] + "/v1/chat/completions")
    if api_url.scheme == "https":
        conn = http.client.HTTPSConnection(api_url.netloc)
    else:
        conn = http.client.HTTPConnection(api_url.netloc)
    conn.request("POST", api_url.path, encoded_body, headers)
    resp = conn.getresponse()
    if stream:
        t_1 = time.time()
        while True:
            line = resp.readline()
            if not line:
                break
            # pass line to the queue
            t = line.decode('utf-8').strip()
            # cut away the first six characters
            if not t or len(t) < 6: continue

            if POISON_PILL in t or '"finish_reason":"stop"' in t:
                output_queue.put("\n")
                output_queue.put("\n")
                return 0.0, 0.0
            t = t[6:]
            if not t: continue
            # parse t as json
            try:
                t = json.loads(t)
                choices = t.get('choices', [])
                token = choices[0].get('delta', {}).get('content', '')
                output_queue.put(token)
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response from the API: {e}, t: {t}")

    else:
        data = resp.read()
        conn.close()
        t_1 = time.time()

        try:
            data = json.loads(data)
            usage = data.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            token_per_second = total_tokens / (t_1 - t_0)
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
