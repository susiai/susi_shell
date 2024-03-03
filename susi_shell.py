import sys
import time
import queue
import argparse
import threading
from src.persona import PERSONA, DEFAULT_PERSONA
from src.ollama_client import get_endpoint, chat
from src.console import initialize_status, select_endpoint, queue_printer, console, POISON_OUTPUT_TOKEN

# process commands line by line, handles multi-line inputs
def terminal(status, command_line):
    if command_line == '"""':
        if status["multi_line"]:
            status["multi_line"] = False
            console(status, "\n".join(status["input_lines"]))
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
    parser.add_argument('command', nargs='?', default=None, help='The command (run, batch, ask, ls)')
    parser.add_argument('model', nargs='?', default='llama3.2:latest', help='An additional parameter for the command')
    parser.add_argument('--api', action='append', help="Specify backend OpenAI API endpoints (i.e. ollama); can be used multiple times")

    args = parser.parse_args()
    command = args.command
    
    # initialize output queue and status
    output_queue = queue.Queue()
    output_queue_thread = threading.Thread(target=queue_printer, args=(output_queue,), daemon=True)
    output_queue_thread.start()
    api_endpoints = args.api if args.api else ["http://localhost:11434"]
    cleaned_endpoints = [api.rstrip('/') for api in api_endpoints]
    endpoints = [get_endpoint(api_base=("http://" + api if not api.startswith("http") else api), model_name=args.model) for api in cleaned_endpoints]
    status = initialize_status(endpoints, args.model, DEFAULT_PERSONA, output_queue)

    # parse command line commands
    if command == None or command == 'run':
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
        endpoint = select_endpoint(endpoints, args.model)
        chat(endpoint, output_queue, context, prompt=user_input, stream=False)

    if command == 'ls':
        # list available models; this is operated as console command
        console(status, "/model ls")

    if command == 'ps':
        # list available models; this is operated as console command
        console(status, "/model ps")

    if command == 'pull':
        # pull a model
        console(status, "/model pull " + args.model)

    if command == 'rm':
        # dele a model
        console(status, "/model rm " + args.model)

    # wait for output queue to finish
    output_queue.put(POISON_OUTPUT_TOKEN)
    output_queue_thread.join()

if __name__ == "__main__":
    main()
