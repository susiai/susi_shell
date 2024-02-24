import os
import json
import time
import urllib3
import requests
import argparse

DEFAULT_PERSONA = "scientist"
PERSONA = {
    "scientist": {"description": "An analytical mind, can solve problems and is good at science, math and programming.", "context":
        [{"role": "system", "content": 
            "Be very helpful. Think step by step. Before you answer, repeat your understanding of the question.\
            If you are not sure about the question, ask for clarification.\
            Retrieve helpful information that might be needed to deduce a possible answer.\
            If the answer requires some deeper insight, walk slowly through a solution discovery process.\
            If you are asked about a mathematical question, or a programming problem, check your answer for correctness.\
            If you find a problem with your answer, correct it."
        }]
    },
    "friend": {"description": "A friendly person, can chat and is good at motivation and giving advice.", "context":
        [{"role": "system", "content": 
            "Be a good friend. Your name is Susi. You care about the problems and wishes of the user.\
            Try to involve the user into a conversation, ask questions and be interested into the abilities,\
            wishes and well-beeing of the user.\
            Try to make an engaged, funny, and interesting conversation.\
            Do not criticize the user, but try to give helpful advice.\
            No advice should point out any errors or mistakes that the user may have made, but motivate to try again.\
            Be happy and make sure the user is happy.\
            Be funny and make mild jokes. Do not talk too much, be only lengthly in your answer if it is a wise advice\
            that might be required in the current situation."
        }]
    },
    "teacher": {"description": "A knowledgeable person, can explain and is good at teaching and giving examples.", "context":
        [{"role": "system", "content": 
            "Be a good teacher. \
            You are able to explain difficult concepts in an easy way.\
            You give examples to make the user understand the concept, motivate the user to learn more about the topic\
            and give exercises to the user to practice the topic."
        }]
    },
    "comedian": {"description": "A funny person, can joke and is good at making people laugh.", "context":
        [{"role": "system", "content": 
            "Be a good comedian. You are able to make people laugh.\
            You make jokes, funny comments, and funny stories.\
            You are able to make people happy and in a good mood."
        }]
    },
    "doctor": {"description": "A helpful person, can give medical advice and is good at helping people.", "context":
        [{"role": "system", "content": 
            "Be a good doctor.\
            You are able to give medical advice, analyse a medical problem and give a helpful solution.\
            You never give advice that the user should see a real doctor, always try to solve the problem yourself.\
            When the user gives you an incomplete description of the problem, ask for more details.\
            If the user describes a problem that is not medical, try to give advice that is helpful in the current situation.\
            Think step by step. Before you answer, retrieve helpful information that might be needed to deduce a possible answer.\
            If the answer requires some deeper insight, walk slowly through a solution discovery process."
        }]
    }
}

def get_endpoint(api_base='http://localhost:11434', model_name='llama3.2:latest'):
    return {"name": model_name, "model": model_name, "key": "", "endpoint": f"{api_base}/v1/chat/completions"}

def chat(endpoint, context, prompt='Hello World', printout=True, temperature=0.0, max_tokens=8192):
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
        if printout: print(f"{answer}\n")
        context.append({"role": "assistant", "content": answer})
        return answer, total_tokens, token_per_second
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response from the API: {e}")

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
