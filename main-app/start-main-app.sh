#!/bin/bash

SESSION=main-app


SESSIONEXISTS=$(tmux list-sessions | grep $SESSION)

# Only create tmux SESSION if it doesn't already exist
if [ -n "$SESSIONEXISTS" ]
then
    tmux kill-session -t $SESSION
fi

tmux new-session -d -s $SESSION

tmux rename-window -t 0 'Main'

tmux send-keys -t 'Main' 'cd ~/Desktop/openwhisk-test/main-app' C-m 'echo "~~~Setting up Kubernetes cluster with openwhisk ~~~"' C-m

tmux new-window -t $SESSION:1 -n 'App'

echo "Building docker image and pushing it to hub"

tmux send-keys -t $SESSION:App 'cd ~/Desktop/openwhisk-test/main-app' C-m 'docker build -t main-app .' C-m

tmux send-keys -t $SESSION:App 'docker tag main-app rggg1/main-app' C-m

tmux send-keys -t $SESSION:App 'docker push rggg1/main-app' C-m

echo "Applying the deployment"


tmux send-keys -t $SESSION:App 'kubectl create namespace main-app' C-m

tmux send-keys -t $SESSION:App 'kubectl delete deployment main-app -n main-app' C-m

tmux send-keys -t $SESSION:App 'kubectl apply -f deployment.yml -n main-app' C-m


tmux send-keys -t $SESSION:App 'kubectl rollout status deployment main-app -n main-app' C-m

echo "Deployment attempt finished, forwarding pod port 5000 to localhost:5000"

tmux send-keys -t $SESSION:App 'kubectl port-forward -n main-app main-app-84c55f5ffd-kdfvg 5000:5000' C-m


tmux attach-session -t $SESSION:0