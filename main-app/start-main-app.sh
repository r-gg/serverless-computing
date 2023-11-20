#!/bin/bash

SESSION=main-app


SESSIONEXISTS=$(tmux list-sessions | grep $SESSION)

# Only create tmux SESSION if it doesn't already exist
if [ "$SESSIONEXISTS" = "" ]
then

    tmux new-session -d -s $SESSION

    tmux rename-window -t 0 'Main'

    tmux send-keys -t 'Main' 'cd ~/Desktop/openwhisk-test/main-app' C-m 'echo "~~~Setting up Kubernetes cluster with openwhisk ~~~"' C-m

    tmux new-window -t $SESSION:1 -n 'App'

    echo "Building docker image"

    tmux send-keys -t $SESSION:App 'cd ~/Desktop/openwhisk-test/main-app' C-m 'docker build -t main-app .' C-m

    echo "Applying the deployment"

    tmux send-keys -t $SESSION:App 'kubectl apply -f deployment.yml' C-m


fi

tmux attach-session -t $SESSION:0