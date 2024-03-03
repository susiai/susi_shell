#!/bin/bash

cd "$(dirname "$0")"

# Use python3 to run susi_shell.py with all passed arguments and piped input.
python3 susi_shell.py "$@"
