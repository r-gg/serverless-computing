#!/bin/bash

# Function to show usage
usage() {
    echo "Usage: $0 action_name [--memory <value>] [--timeout <value>]"
    echo "Default --memory is 256MB if not provided."
    echo "Default --timeout is 300000ms if not provided."
    exit 1
}

# Check if at least one argument is provided
if [ $# -eq 0 ]; then
    usage
fi

# First argument is the action name
action_name=$1
shift  # Shift past the first argument

# Initialize variables
memory='256'  # Default memory value in MB
timeout='300000'  # Default timeout value in ms

# Parse options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --memory) 
            memory="$2"; 
            if ! [[ "${memory}" =~ ^[0-9]+$ ]]; then
                echo "Error: --memory option requires an integer value."
                usage
            fi
            shift ;;  # Shift past the value
        --timeout)
            timeout="$2";
            if ! [[ "${timeout}" =~ ^[0-9]+$ ]]; then
                echo "Error: --timeout option requires an integer value."
                usage
            fi
            shift ;;
        *) usage ;;
    esac
    shift  # Shift past the current argument
done

echo "Creating the python (Python3.11) action on openwhisk with the name $action_name"
echo "Memory is set to ${memory}MB."
echo "Timeout is set to ${timeout}ms."

# Check if action_name is not empty
if [ -z "$action_name" ]; then
    echo "No action_name supplied"
    usage
fi

# Create zip file for the action
zip $action_name.zip __main__.py

# Create the action
wsk -i action create $action_name --docker rggg1/python11action $action_name.zip --timeout $timeout --memory $memory

# Remove the zip file
rm $action_name.zip
