import os
import json
import time
import urllib3
import requests
import argparse
from src.persona import PERSONA, DEFAULT_PERSONA
from src.ollama_client import get_endpoint, chat

def console_command(endpoint):
    status = {"context": PERSONA[DEFAULT_PERSONA]["context"].copy(), "input_lines": [], "multi_line": False, "persona": DEFAULT_PERSONA}
    while True:
        # read user input
        print("... " if status["multi_line"] else ">>> ", end="")
        user_input = input()
        user_input = user_input.replace('\\', '/') # fix mistakes in input
        
        # parse and execute command
        if user_input == '/?' or user_input == '/help':
            print("Commands:")
            print("  /bye: Exit")
            print("  /clear: Clear session context")
            print("  /persona ls: List available personas")
            print("  /persona <name>: Switch to persona with given name")
            print("  /?, /help: Show help")
            print("")
            continue

        if user_input == '/clear':
            status["context"] = PERSONA[status["persona"]]["context"].copy()
            print("Cleared session context\n")
            continue

        if user_input == '/persona':
            print(f"Current persona is '{status['persona']}'\n")
            continue

        if user_input == '/persona ls':
            print("Available personas:")
            for name, data in PERSONA.items():
                print(f"  {name}: {data['description']}")
            print("")
            continue

        if user_input.startswith('/persona '):
            try:
                persona_name = user_input.split(' ')[1]
                persona = PERSONA.get(persona_name, None)
                if persona is None:
                    print(f"A persona with name '{persona_name}' does not exist\n")
                    continue
                status["persona"] = persona_name
                status["context"] = persona["context"].copy()
                print(f"Switched to persona '{persona_name}'\n")
            except Exception as e:
                print(f"Error switching persona: {e}\n")
            continue

        if user_input == '/bye':
            break

        # compute LLM response
        if user_input == '"""':
            if status["multi_line"]:
                status["multi_line"] = False
                chat(endpoint, status["context"], prompt="\n".join(status["input_lines"]), printout=True)
                continue

            status["multi_line"] = True
            status["input_lines"] = []
            continue
        
        if status["multi_line"]:
            status["input_lines"].append(user_input)
            continue
        
        chat(endpoint, status["context"], prompt=user_input, printout=True)

def main():
    parser = argparse.ArgumentParser(description='AI Command Line Tools')
    parser.add_argument('command', type=str, help='The command to run (ask)')
    parser.add_argument('model', nargs='?', default='llama3.2:latest', help='An additional parameter for the command')

    args = parser.parse_args()
    command = args.command
    model = args.model
    endpoint = get_endpoint(model_name = model)
    
    if command == 'run':
        console_command(endpoint)

    if command == 'ask':
        user_input = input()
        context = PERSONA[DEFAULT_PERSONA]["context"].copy()
        chat(endpoint, context, prompt=user_input, printout=True)

if __name__ == "__main__":
    main()
