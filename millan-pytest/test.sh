#!/bin/bash

# If no file passed, run on all files
if [ "$#" -ne 1 ]; then
    echo "Running tests on all files..."
    pytest --cache-clear --no-header -v
else
    echo "Running tests on $1..."
    pytest --cache-clear --no-header -v "$1"
fi