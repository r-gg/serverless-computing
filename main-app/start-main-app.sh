#!/bin/bash

SESSION=main-app


SESSIONEXISTS=$(tmux list-sessions | grep $SESSION)

# Only create tmux SESSION if it doesn't already exist
if [ -n "$SESSIONEXISTS" ]
then
    tmux kill-session -t $SESSION
fi

tmux new-session -d -s $SESSION

tmux new-window -t $SESSION:1 -n 'App'

echo "Applying the deployment"


tmux send-keys -t $SESSION:App 'kubectl create namespace main-app' C-m

tmux send-keys -t $SESSION:App 'kubectl delete deployment main-app -n main-app' C-m

tmux send-keys -t $SESSION:App 'kubectl apply -f deployment.yml -n main-app' C-m


tmux send-keys -t $SESSION:App 'kubectl rollout status deployment main-app -n main-app' C-m

echo "Deployment attempt finished, forwarding pod port 5000 to localhost:5000"

tmux send-keys -t $SESSION:App 'kubectl port-forward -n main-app $(kubectl get pods -n main-app | tail -n +2 | awk '\''{print $1; exit}'\'') 5000:5000' C-m

tmux new-window -t $SESSION:2 -n 'Test'

tmux send-keys -t $SESSION:Test 'kubectl port-forward -n main-app $(kubectl get pods -n main-app | tail -n +2 | awk '\''{print $1; exit}'\'') 5001:5001' C-m


tmux attach-session -t $SESSION:0