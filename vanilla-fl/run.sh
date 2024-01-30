#!/bin/bash

# Function to kill server and client processes
cleanup() {
    echo "Cleaning up..."
    kill $SERVER_PID
    for PID in "${CLIENT_PIDS[@]}"; do
        kill $PID
    done
}

# Trap SIGINT and SIGTERM to ensure cleanup function is called when script exits
trap cleanup SIGINT SIGTERM EXIT

# Set your variables here
NUM_CLIENTS=12
N_ROUNDS=20
N_SELECTED=10

# Install dependencies
pip install -r requirements.txt

# Start the server in the background and save its PID
python3 ./server.py &
SERVER_PID=$!

# Initialize an array to keep track of client PIDs
declare -a CLIENT_PIDS

# Check server readiness by polling the health check endpoint
until $(curl --output /dev/null --silent --head --fail http://localhost:8080/healthcheck); do
    printf '.'
    sleep 5
done

# Start client.py specified number of times in a loop and save their PIDs
for i in $(seq 1 $NUM_CLIENTS); do
    python3 ./client.py &
    CLIENT_PIDS+=($!)
done

# Wait a bit to ensure the server is up before making the HTTP request
sleep 5

# Making the HTTP request
curl "http://localhost:8080/start_training?n_rounds=$N_ROUNDS&n_selected=$N_SELECTED"

# Wait for user input before closing
read -p "Press any key to continue..."

# Cleanup
cleanup