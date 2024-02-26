# AI Command Line Tools

Welcome to the `susi_shell` repository, which is part of the susi_api project aimed at providing AI capabilities in a command-line based environment. This suite of tools enables users to interact with AI services directly from their terminal.

Some of these tools currently require a working connection to the OpenAI API.
Future versions of this command line tool collection should use local self-hosted services.
We implement those function in the susi_api project.

## Available Commands (all to be implemented)

- `run <model-name>` - Run a model with the given name and chat.
- `ask <model-name>` - Provides an answer to a submitted question.
- `context` - Select, view or create a context for the ask command.
- `complete` - Takes a piece of text and uses AI to generate a contextually relevant completion.
- `listen` - record audio and optionally pass it to the transscript command
- `transscript` - Listens to audio input and transcribes it into text.
- `translate` - Translates a block of text from one language to another.
- `say` - Converts text to speech. (Note: This command is currently available on macOS. by default)

## Usage

You can use `susi_shell` in one of two ways:

- interactive: run `./susi_shell.sh run <model-name>` to use the susi_shell in a similar way as ollama
- batch: run `echo "hello world" | ./susi_shell.sh ask <model-name>` to use stdin as input for a prompt to the `<model-name>`

