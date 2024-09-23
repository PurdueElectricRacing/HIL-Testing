#!/bin/bash

# Check if a Python file was passed as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: ./test <file.py>"
    exit 1
fi

pytest --cache-clear --no-header -v "$1"