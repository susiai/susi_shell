import json
import time
import urllib3
import http.client
from urllib.parse import urlparse

def get_endpoint(api_base='http://localhost:11434', model_name='llama3.2:latest'):
    return {
        "key": "",
        "name": model_name,
        "model": model_name,
        "api_base": api_base
    }

def request(method, api_url, body=None, key=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    encoded_body = json.dumps(body).encode('utf-8') if body else None
    headers = {'Accept': 'application/json'}
    if encoded_body:
        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(encoded_body))
    if key: headers['Authorization'] = 'Bearer ' + key
    api_url = urlparse(api_url)
    if api_url.scheme == "https":
        conn = http.client.HTTPSConnection(api_url.netloc)
    else:
        conn = http.client.HTTPConnection(api_url.netloc)
    conn.request(method, api_url.path, body=encoded_body, headers=headers)
    return conn

def ollama_list(endpoint):
    conn = request("GET", f"{endpoint['api_base']}/api/tags", None, endpoint.get("key"))
    data = json.loads(conn.getresponse().read())
    conn.close()
    models_dict = {
        entry['model']: {
            'parameter_size': float(entry['details']['parameter_size'][:-1]),
            'quantization_level': entry['details']['quantization_level'][1:2]
        }
        for entry in data['models']
    }
    return models_dict

def ollama_ps(endpoint):
    conn = request("GET", f"{endpoint['api_base']}/api/ps", None, endpoint.get("key"))
    data = json.loads(conn.getresponse().read())
    conn.close()
    models_dict = {
        entry['model']: {
            'parameter_size': float(entry['details']['parameter_size'][:-1]),
            'quantization_level': entry['details']['quantization_level'][1:2]
        }
        for entry in data['models']
    }
    return models_dict

def ollama_pull(endpoint, model):
    # curl http://localhost:11434/api/pull -d '{"model": "llama3.2"}'
    conn = request("POST", f"{endpoint['api_base']}/api/pull", {"model": model, "stream": False}, endpoint.get("key"))
    data = json.loads(conn.getresponse().read())
    conn.close()
    return not data.get("error", False)

def ollama_delete(endpoint, model):
    #curl -X DELETE http://localhost:11434/api/delete -d '{"model": "llama3.2"}'
    conn = request("DELETE", f"{endpoint['api_base']}/api/delete", {"model": model}, endpoint.get("key"))
    # check http response
    response_code = conn.getresponse().status
    conn.close()
    return response_code == 200

def chat(endpoint, output_queue, context, prompt='Hello World', stream = False, temperature=0.0, max_tokens=8192):
    context.append({"role": "user", "content": prompt})
    body = {
        "top_p": 0.7,
        "stream": stream,
        "messages": context,
        "presence_penalty": 0.3,
        "frequency_penalty": 0.7,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "model": endpoint["model"],
        "response_format": { "type": "text" },
        "stop": ["[/INST]", "<|im_end|>", "<|end_of_turn|>", "<|eot_id|>", "<|end_header_id|>", "<EOS_TOKEN>", "</s>", "<|end|>"]
    }
    t_0 = time.time()
    conn = request("POST", endpoint["api_base"] + "/v1/chat/completions", body, endpoint.get("key", None))
    resp = conn.getresponse()
    POISON_PILL = "data: [DONE]"
    if stream:
        total_tokens = 0
        for line in resp:
            t = line.decode('utf-8').strip()
            if not t or len(t) < 6: continue
            if POISON_PILL in t or '"finish_reason":"stop"' in t:
                conn.close()
                output_queue.put("\n\n")
                t_1 = time.time()
                token_per_second = total_tokens / (t_1 - t_0)
                return total_tokens, token_per_second

            t = t[6:]
            if not t: continue

            try:
                t = json.loads(t)
                token = t.get('choices', [{}])[0].get('delta', {}).get('content', '')
                output_queue.put(token)
                total_tokens += 1
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response from the API: {e}, t: {t}")
    else:
        data = resp.read()
        conn.close()

        try:
            data = json.loads(data)
            usage = data.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            t_1 = time.time()
            token_per_second = total_tokens / (t_1 - t_0)
            choices = data.get('choices', [])
            if not choices: raise Exception("No response from the API: " + str(data))
            message = choices[0].get('message', {})
            answer = message.get('content', '')
            if output_queue:
                for line in answer.split('\n'):
                    output_queue.put(f"{line}\n")
                output_queue.put("\n")
            context.append({"role": "assistant", "content": answer})
            return total_tokens, token_per_second
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from the API: {e}")
