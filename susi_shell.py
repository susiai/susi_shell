import os
import sys
import json
import time
import queue
import urllib3
import requests
import argparse
import threading
from src.persona import PERSONA, DEFAULT_PERSONA
from src.ollama_client import get_endpoint, ollama_list, chat
from src.console import initialize_status, queue_printer, console, POISON_OUTPUT_TOKEN

# process commands line by line, handles multi-line inputs
def terminal(status, command_line):
    if command_line == '"""':
        if status["multi_line"]:
            status["multi_line"] = False
            console(context, "\n".join(status["input_lines"]))
            return

        status["multi_line"] = True
        status["input_lines"] = []
        return
    
    if status["multi_line"]:
        status["input_lines"].append(command_line)
        return

    console(status, command_line)

def main():
    parser = argparse.ArgumentParser(description='AI Command Line Tools')
    parser.add_argument('command', type=str, help='The command (run, batch, ask, ls)')
    parser.add_argument('model', nargs='?', default='llama3.2:latest', help='An additional parameter for the command')

    args = parser.parse_args()
    command = args.command

    # initialize output queue and status
    output_queue = queue.Queue()
    output_queue_thread = threading.Thread(target=queue_printer, args=(output_queue,), daemon=True)
    output_queue_thread.start()
    endpoint = get_endpoint(model_name = args.model)
    status = initialize_status(endpoint, DEFAULT_PERSONA, output_queue)

    # parse command line commands
    if command == 'run':
        # run the shell
        while True:
            # read user input
            while not output_queue.empty(): time.sleep(0.1) # wait until the output queue is empty
            print("... " if status["multi_line"] else ">>> ", end="") # the prompt is not placed in the output_queue!
            sys.stdout.flush()
            user_input = input()
            user_input = user_input.replace('\\', '/') # fix mistakes in input
            
            # handle termination
            if user_input == '/bye': break

            # pass user input to terminal
            terminal(status, user_input)

    if command == 'batch':
        # read user input and process it line by line as batch
        user_input = input()
        commands = user_input.split('\n')
        for command in commands:
            terminal(status, command)

    if command == 'ask':
        # read user input and process it at once as prompt
        user_input = input()
        context = PERSONA[DEFAULT_PERSONA]["context"].copy()
        chat(endpoint, output_queue, context, prompt=user_input, stream=True)

    if command == 'ls':
        # list available models; this is operated as console command
        console(status, "/model ls")

    # wait for output queue to finish
    output_queue.put(POISON_OUTPUT_TOKEN)
    output_queue_thread.join()

if __name__ == "__main__":
    main()
