#!/bin/bash

SESSION="Kafka"

bold=$(tput bold)
normal=$(tput sgr0)

tmux new-session -d -s $SESSION

tmux rename-window -t 0 'Main'

echo "Exposing Kafka"

tmux send-keys -t $SESSION:Main 'cd ./kafka' C-m 'kubectl label pod -n openwhisk owdev-kafka-0 application=kafka' C-m 'kubectl apply -f kafka-svc.yaml' C-m

echo "${bold}done"
