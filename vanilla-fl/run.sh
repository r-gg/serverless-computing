#!/bin/bash

# Set your variables here
NUM_CLIENTS=6
N_ROUNDS=50
N_SELECTED=4

# Install dependencies
pip install -r requirements.txt

# Start the server in the background
python ./server.py &

# Check server readiness by polling the health check endpoint
until $(curl --output /dev/null --silent --head --fail http://localhost:8080/healthcheck); do
    printf '.'
    sleep 5
done

# Start client.py specified number of times in a loop
for i in $(seq 1 $NUM_CLIENTS); do
    python ./client.py &
done

# Wait a bit to ensure the server is up before making the HTTP request
sleep 5

# Making the HTTP request
curl "http://localhost:8080/start_training?n_rounds=$N_ROUNDS&n_selected=$N_SELECTED"

# Wait for user input before closing
read -p "Press any key to continue..."
