# AI Command Line Tools

Welcome to the `susi_shell` repository, which is part of the susi_api project aimed at providing AI capabilities in a command-line based environment. This suite of tools enables users to interact with AI services directly from their terminal.

Some of these tools currently require a working connection to the OpenAI API.
Future versions of this command line tool collection should use local self-hosted services.
We implement those function in the susi_api project.

## Available Commands (all to be implemented)

- `ask` - Provides an answer to a submitted question.
- `context` - Select, view or create a context for the ask command.
- `complete` - Takes a piece of text and uses AI to generate a contextually relevant completion.
- `listen` - record audio and optionally pass it to the transscript command
- `transscript` - Listens to audio input and transcribes it into text.
- `translate` - Translates a block of text from one language to another.
- `say` - Converts text to speech. (Note: This command is currently available on macOS. by default)

## Prerequisites

Before installing, ensure that you have the following:
- Git installed on your machine.
- An active OpenAI account to obtain an API key.

## Installation

To install these scripts, we must store a secret key outside of this repository and we must append a path to the `$PATH` variable to execute scripts inside the `bin` path of this repository. Follow these steps:

1. Clone the repository to your local machine using:
    ```sh
    cd [/path/to/git/]
    ```
    Replace `[/path/to/git/]` with the name of your git repositories.
    ```sh
    git clone https://github.com/susiai/susi_shell.git
    ```

2. Navigate to the cloned repository's directory:
    ```sh
    cd [/path/to/git/susi_shell]
    ```
    Replace `[/path/to/git/susi_shell]` with the name of the repository.

3. Add the `bin/` subdirectory to your system's PATH variable:
    - For a temporary assignment (resets after terminal is closed), use:
        ```sh
        export PATH=$PATH:/path/to/git/susi_shell/bin
        ```
        Replace `/path/to/git/susi_shell/bin` with the actual path to the `bin/` subdirectory in the repository.

    - For a permanent assignment, add the export command to your shell's initialization script, such as `.bashrc` or `.zshrc`:
       ```sh
       echo 'export PATH=$PATH:/path/to/git/susi_shell/bin' >> ~/.bashrc
       ```
       or
       ```sh
       echo 'export PATH=$PATH:/path/to/git/susi_shell/bin' >> ~/.zshrc
       ```
       Remember to replace `/path/to/git/susi_shell/bin` with the actual path to the `bin/` subdirectory and use the appropriate file for your shell.

4. Source your shell's initialization script to apply the changes, or you can restart your terminal:
    ```sh
    source ~/.bashrc
    ```
    or
    ```sh
    source ~/.zshrc
    ```

5. Verify that the installation was successful by typing one of the commands, for example:
    ```sh
    transscript --help
    ```

## API Key Storage

The AI tools in this repository require an API key for the OpenAI services. To set this up, follow these steps:

1. Create a file named `keys.sh` inside your `~/.ssh/` directory with the following command:
    ```sh
    touch ~/.ssh/keys.sh
    ```

2. Open `keys.sh` in a text editor and add the following line:
    ```sh
    export OPENAI_API_KEY=<your-openai-api-key>
    ```
    Replace `<your-openai-api-key>` with your actual OpenAI API key.

3. To ensure that your API key is loaded in each new terminal session, you will need to call this `keys.sh` script from your shell's initialization script. If you're using Zsh, you can add the following line to your `~/.zshrc` file:
    ```sh
    source ~/.ssh/keys.sh
    ```

4. After updating your `~/.zshrc` file, apply the changes by either restarting your terminal or sourcing your `~/.zshrc`:
    ```sh
    source ~/.zshrc
    ```

5. To verify that the API key is set correctly, open a new terminal session and echo the `OPENAI_API_KEY`:
    ```sh
    echo $OPENAI_API_KEY
    ```
    This should print your OpenAI API key. If it doesn't, ensure you've followed the steps above correctly.

**Note:** Storing API keys in plain text is not recommended for production environments. This method is suitable for development purposes only. For production, consider using more secure methods like environment managers or secret management services.

## Contributing
We welcome contributions from the community. Please send us a pull request.

