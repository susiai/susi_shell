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

def request_response_base(method, api_url, body=None, key=None):
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
    response = conn.getresponse()
    return response, conn

def request_response(method, api_url, body=None, key=None):
    response, conn = request_response_base(method, api_url, body, key)
    status_code = response.status

    # handle redirect
    if status_code == 301:
        new_path = response.getheader('Location')
        conn.close()
        api_url_parsed = urlparse(api_url)
        new_url = new_path if new_path.startswith("http") else f"{api_url_parsed.scheme}://{api_url_parsed.netloc}{new_path}"
        response, conn = request_response("GET", f"{new_url}", body, key)
        status_code = response.status
    
    return response, conn

list_cache = {}

def ollama_list(endpoint):
    # try to get list from cache
    host = endpoint['api_base']
    cache = entry = list_cache.get(host)
    if cache:
        last_updated = cache.get('last_updated')
        if last_updated and time.time() - last_updated < 3600:
            data = cache.get('data')
            if data:
                return data

    # make connection
    t0 = time.time()
    response, conn = request_response("GET", f"{endpoint['api_base']}/api/tags", None, endpoint.get("key"))
    status_code = response.status
    if status_code != 200:
        raise Exception(f"Unexpected status code: {status_code}")
    data = json.loads(response.read())
    conn.close()
    models_dict = {
        entry['model']: {
            'parameter_size': float(entry['details']['parameter_size'][:-1]),
            'quantization_level': entry['details']['quantization_level'][1:2]
        }
        for entry in data['models']
    }

    # update cache
    list_cache[host] = {
        'last_updated': t0,
        'data': models_dict
    }

    #t1 = time.time()
    #print(f"Time taken for host {host} : {t1 - t0}")
    return models_dict

def ollama_ps(endpoint):
    response, conn = request_response("GET", f"{endpoint['api_base']}/api/ps", None, endpoint.get("key"))
    data = json.loads(response.read())
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
    response, conn = request_response("POST", f"{endpoint['api_base']}/api/pull", {"model": model, "stream": False}, endpoint.get("key"))
    data = json.loads(response.read())
    conn.close()
    return not data.get("error", False)

def ollama_delete(endpoint, model):
    #curl -X DELETE http://localhost:11434/api/delete -d '{"model": "llama3.2"}'
    response, conn = request_response("DELETE", f"{endpoint['api_base']}/api/delete", {"model": model}, endpoint.get("key"))
    response_code = response.status
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
    response, conn = request_response("POST", endpoint["api_base"] + "/v1/chat/completions", body, endpoint.get("key", None))
    POISON_PILL = "data: [DONE]"
    if stream:
        total_tokens = 0
        for line in response:
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
        data = response.read()
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
