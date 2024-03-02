import sys
import random
from src.persona import PERSONA, DEFAULT_PERSONA
from src.ollama_client import ollama_list, ollama_ps, ollama_pull, ollama_delete, chat

POISON_OUTPUT_TOKEN = "***POISON_OUTPUT_TOKEN***" # token to indicate end of output in output_queue

# initialize status: this is a dictionary that holds the current state of the console
def initialize_status(endpoints, preferred_model, persona, output_queue):
    return {
        "endpoints": endpoints, # list of endpoint url stubs
        "preferred_model": preferred_model,
        "context": PERSONA[persona]["context"].copy(),
        "persona": persona,
        "multi_line": False,
        "input_lines": [],
        "output_queue": output_queue
    }

# queue printer which prints all items in the queue until the poison token is found
def queue_printer(output_queue):
    while True:
        item = output_queue.get()
        if item == POISON_OUTPUT_TOKEN:
            break
        print(item, end="")
        sys.stdout.flush()

def select_endpoint4status(status):
    endpoints = status["endpoints"]
    preferred_model = status["preferred_model"]
    return select_endpoint(endpoints, preferred_model)

def select_endpoint(endpoints, preferred_model):
    if len(endpoints) == 0:
        return None
    if len(endpoints) == 1:
        endpoints[0]["model"] = preferred_model
        return endpoints[0]
    else:
        # get models for each endpoint
        potential_endpoints = []
        for ep in endpoints:
            models_dict = ollama_list(ep)
            if models_dict.get(preferred_model, None) is not None or models_dict.get(preferred_model + ":latest", None) is not None:
                potential_endpoints.append(ep)
        return potential_endpoints[random.randint(0, len(potential_endpoints)-1)]

# compute responses
def console(status, prompt):
    output_queue = status["output_queue"]

    # parse and execute the prompt
    if prompt == '': # ignore empty lines / respond with empty lines (gives batch outputs a better structure)
        output_queue.put("\n")
        return

    if prompt == '/?' or prompt == '/help':
        output_queue.put("Commands:\n")
        output_queue.put("  /bye: Exit\n")
        output_queue.put("  /clear: Clear session context\n")
        output_queue.put("  /api ls Print defined endpoints\n")
        output_queue.put("  /api add <urlstub>: Add endpoint stub\n")
        output_queue.put("  /api rm <urlstub>: Remove endpoint stub\n")
        output_queue.put("  /persona: Print current persona\n")
        output_queue.put("  /persona ls: List available personas\n")
        output_queue.put("  /persona <name>: Switch to persona with given name\n")
        output_queue.put("  /model: Print current model\n")
        output_queue.put("  /model ls: List available models\n")
        output_queue.put("  /model ps: List running models\n")
        output_queue.put("  /model rm <name>: delete a model from all api endpoints\n")
        output_queue.put("  /model rmr <name>: delete a model from a random api endpoint\n")
        output_queue.put("  /model pull <name>: pull a model into all api endpoints\n")
        output_queue.put("  /model pull0 <name>: pull a model into first api endpoint\n")
        output_queue.put("  /model pulln <name>: pull a model into last api endpoint\n")
        output_queue.put("  /model <name>: Switch to model with given name\n")
        #output_queue.put("  /council on: Switch on a council of random models (at least 3 or number of APIs)\n")
        #output_queue.put("  /council on <n>: Switch on a council of <n> random models\n")
        #output_queue.put("  /council ls: List models used in the council\n")
        #output_queue.put("  /council off: Switch off council\n")
        #output_queue.put("  /council <name-1>, <name-2>, ..., <name-n>: Use given models for council\n")
        output_queue.put("  /?, /help: Show help\n")
        output_queue.put("\n")
        return

    if prompt == '/clear':
        status["context"] = PERSONA[status["persona"]]["context"].copy()
        output_queue.put("Cleared session context\n")
        output_queue.put("\n")
        return

    if prompt == '/api ls':
        output_queue.put("Defined endpoints:\n")
        for endpoint in status["endpoints"]:
            output_queue.put(f"  {endpoint['api_base']}\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/api add '):
        api_base = prompt.split(' ')[2].strip()
        status["endpoints"].append({"api_base": api_base, "model": status["preferred_model"]})
        output_queue.put(f"Added endpoint '{api_base}'\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/api rm '):
        model = prompt.split(' ')[2].strip()
        status["endpoints"] = [endpoint for endpoint in status["endpoints"] if endpoint["api_base"] != api_base]
        output_queue.put(f"Removed endpoint '{api_base}'\n")
        output_queue.put("\n")
        return

    if prompt == '/persona':
        output_queue.put(f"Current persona is '{status['persona']}'\n")
        output_queue.put("\n")
        return

    if prompt == '/persona ls' or prompt == '/persona list':
        output_queue.put("Available personas:\n")
        for name, data in PERSONA.items():
            output_queue.put(f"  {name}: {data['description']}\n")
        output_queue.put("\n")
        return

    if prompt.startswith('/persona '):
        try:
            persona_name = prompt.split(' ')[1]
            persona = PERSONA.get(persona_name, None)
            if persona is None:
                output_queue.put(f"A persona with name '{persona_name}' does not exist\n")
                output_queue.put("\n")
                return
            status["persona"] = persona_name
            status["context"] = persona["context"].copy()
            output_queue.put(f"Switched to persona '{persona_name}'\n")
            output_queue.put("\n")
        except Exception as e:
            output_queue.put(f"Error switching persona: {e}\n")
            output_queue.put("\n")
        return

    if prompt == '/model':
        output_queue.put(f"Current model is '{status['endpoints'][0]['model']}'\n")
        output_queue.put("\n")
        return

    if prompt == '/model ls' or prompt == '/model list':
        output_queue.put("Available models:\n")
        models_acc_dict = {}
        model_max_len = 0
        for endpoint in status["endpoints"]:
            models_dict = ollama_list(endpoint)
            for (model, attr) in models_dict.items():
                model_max_len = max(model_max_len, len(model))
                if model not in models_acc_dict:
                    models_acc_dict[model] = 1
                else:
                    models_acc_dict[model] += 1
        output_queue.put(f"Model Name {' '*(model_max_len-22)} # of Endpoints\n")
        output_queue.put(f"{'-'*(model_max_len+4)}\n")
        for (model, count) in models_acc_dict.items():
            output_queue.put(f"{model} {' '*(model_max_len-len(model))} {count}\n")
        output_queue.put("\n")
        return
    
    if prompt == '/model ps':
        output_queue.put("Running models:\n")
        models_acc_dict = {}
        for endpoint in status["endpoints"]:
            models_dict = ollama_ps(endpoint)
            for (model, attr) in models_dict.items():
                if model not in models_acc_dict:
                    models_acc_dict[model] = [endpoint["api_base"]]
                else:
                    models_acc_dict[model].append(endpoint["api_base"])
        for (model, endpoints) in models_acc_dict.items():
            output_queue.put(f"{model} {endpoints}\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/model pull0 '):
        model_name = prompt.split(' ')[2].strip()
        output_queue.put("Pulling model:\n")
        endpoint = status['endpoints'][0]
        success = ollama_pull(endpoint, model_name)
        output_queue.put(("Successfully pulled model " if success else "Failed to pull model ") + model_name + " in endpoint " + endpoint["api_base"] + "\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/model pulln '):
        model_name = prompt.split(' ')[2].strip()
        output_queue.put("Pulling model:\n")
        endpoint = status['endpoints'][-1]
        success = ollama_pull(endpoint, model_name)
        output_queue.put(("Successfully pulled model " if success else "Failed to pull model ") + model_name + " in endpoint " + endpoint["api_base"] + "\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/model pull '):
        model_name = prompt.split(' ')[2].strip()
        output_queue.put("Pulling models:\n")
        for endpoint in status['endpoints']:
            success = ollama_pull(endpoint, model_name)
            output_queue.put(("Successfully pulled model " if success else "Failed to pull model ") + model_name + " in endpoint " + endpoint["api_base"] + "\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/model rm ') or prompt.startswith('/model delete '):
        model_name = prompt.split(' ')[2].strip()
        output_queue.put(f"Deleting model {model_name} in all endpoints:\n")
        for endpoint in status['endpoints']:
            success = ollama_delete(endpoint, model_name)
            output_queue.put(("Successfully deleted model " if success else "Failed to delete model ") + model_name + " in endpoint " + endpoint["api_base"] + "\n")
        output_queue.put("\n")
        return
    
    if prompt.startswith('/model rmr '):
        model_name = prompt.split(' ')[2].strip()
        output_queue.put(f"Deleting model {model_name} in one random endpoint:\n")
        endpoint_candidates = []
        for endpoint in status['endpoints']:
            model_dict = ollama_list(endpoint)
            if model_name in model_dict or model_name + ":latest" in model_dict:
                endpoint_candidates.append(endpoint)
        if len(endpoint_candidates) == 0:
            output_queue.put(f"Model {model_name} not found in any endpoint\n")
            output_queue.put("\n")
            return
        else:
            endpoint = endpoint_candidates[random.randint(0, len(endpoint_candidates)-1)]
            success = ollama_delete(endpoint, model_name)
            output_queue.put(("Successfully deleted model " if success else "Failed to delete model ") + model_name + " in endpoint " + endpoint["api_base"] + "\n")
            output_queue.put("\n")
            return

    if prompt.startswith('/model '):
        try:
            token = prompt.split(' ')
            if len(token) < 3:
                model_name = token[1].strip()
            elif token[1].strip() == "run":
                model_name = token[2].strip()
            else:
                output_queue.put(f"Error switching to a model: wrong syntax")
                output_queue.put("\n")
                return
            
            for endpoint in status["endpoints"]:
                models_dict = ollama_list(endpoint)
                if model_name in models_dict:
                    endpoint["model"] = model_name
                    status["preferred_model"] = model_name
                    output_queue.put(f"Switched to model '{model_name}'\n")
                    output_queue.put("\n")
                    return
            
            output_queue.put(f"A model with name '{model_name}' does not exist\n")
            output_queue.put("\n")
            return
        except Exception as e:
            output_queue.put(f"Error switching model: {e}\n")
            output_queue.put("\n")
            return

    endpoint = select_endpoint4status(status)
    chat(endpoint, output_queue, status["context"], prompt=prompt, stream=True)