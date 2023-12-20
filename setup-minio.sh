#!/bin/bash

SESSION="Minio"

bold=$(tput bold)
normal=$(tput sgr0)

tmux new-session -d -s $SESSION

tmux rename-window -t 0 'Main'

echo "deploying minio"

tmux send-keys -t $SESSION:Main 'cd ~/Desktop/openwhisk-test/minio' C-m 'kubectl apply -f minio-dev.yaml' C-m

sleep 8

tmux new-window -t $SESSION:1 -n 'svc'

tmux send-keys -t $SESSION:svc 'kubectl expose pod minio --port=9000 --name=minio-operator9000 -n minio-dev' C-m

tmux send-keys -t $SESSION:Main 'kubectl port-forward pod/minio 9000:9090 -n minio-dev' C-m

echo "Minio Reachable on http://localhost:9000 the username and password are : ${bold}minioadmin"
echo "If it is unreachable try running the setup again (it might take a while to set the pod up)"

