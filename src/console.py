import sys
import requests
import argparse
import threading
from src.persona import PERSONA, DEFAULT_PERSONA
from src.ollama_client import get_endpoint, ollama_list, chat

POISON_OUTPUT_TOKEN = "***POISON_OUTPUT_TOKEN***" # token to indicate end of output in output_queue

# initialize status: this is a dictionary that holds the current state of the console
def initialize_status(endpoint, persona, output_queue):
    return {
        "endpoints": [endpoint],
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
        output_queue.put("  /persona: Print current persona\n")
        output_queue.put("  /persona ls: List available personas\n")
        output_queue.put("  /persona <name>: Switch to persona with given name\n")
        output_queue.put("  /model: Print current model\n")
        output_queue.put("  /model ls: List available models\n")
        output_queue.put("  /model <name>: Switch to model with given name\n")
        output_queue.put("  /?, /help: Show help\n")
        output_queue.put("\n")
        return

    if prompt == '/clear':
        status["context"] = PERSONA[status["persona"]]["context"].copy()
        output_queue.put("Cleared session context\n")
        output_queue.put("\n")
        return

    if prompt == '/persona':
        output_queue.put(f"Current persona is '{status['persona']}'\n")
        output_queue.put("\n")
        return

    if prompt == '/persona ls':
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

    if prompt == '/model ls':
        output_queue.put("Available models:\n")
        models_dict = ollama_list(status['endpoints'][0])
        for (model, attr) in models_dict.items():
            output_queue.put(f"- {model}\n")
        output_queue.put("\n")
        return

    if prompt.startswith('/model '):
        try:
            model_name = prompt.split(' ')[1].strip()
            # check if model_name exists in list of models
            models_dict = ollama_list(status['endpoints'][0])
            if model_name not in models_dict:
                output_queue.put(f"A model with name '{model_name}' does not exist\n")
                output_queue.put("\n")
                return
            status['endpoints'][0]["model"] = model_name
            output_queue.put(f"Switched to model '{model_name}'\n")
            output_queue.put("\n")
            return
        except Exception as e:
            output_queue.put(f"Error switching model: {e}\n")
            output_queue.put("\n")
            return

    endpoint = status["endpoints"][0]
    chat(endpoint, output_queue, status["context"], prompt=prompt, stream=True)