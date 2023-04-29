import os
import argparse
import openai
from openai import OpenAI

client = OpenAI()
model="gpt-3.5-turbo"

# Function to initialize the chat session
def start_chat_session():
    api_key=os.getenv("OPENAI_API_KEY")
    session = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a helpful assistant."}]
    )
    return session['id']

# Function to get a response from the API
def get_response(session_id, user_input):
    response = client.chat.completions.create(model=model,
    messages=[
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": ""}
    ],
    session_id=session_id)
    return response['choices'][0]['message']['content']

# Main function to handle the chat command
def ask_command(session_id):
    print("Welcome to the chat! Ask me anything, or type 'exit' to end the chat.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["end", "quit", "exit"]:
            print("Goodbye!")
            break
        else:
            ai_message = get_response(session_id, user_input)
            print(f"AI: {ai_message}")

# Setup argparse to handle command-line arguments
def setup_argparse():
    parser = argparse.ArgumentParser(description='AI Command Line Tools')
    parser.add_argument('command', type=str, help='The command to run (ask)')
    return parser

def main():
    parser = setup_argparse()
    args = parser.parse_args()
    
    if args.command == 'ask':
        session_id = start_chat_session()
        ask_command(session_id)

if __name__ == "__main__":
    main()
