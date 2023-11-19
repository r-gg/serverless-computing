#!/bin/bash

SESSION="OpenWhisk"

bold=$(tput bold)
normal=$(tput sgr0)

tmux new-window -t $SESSION:4 -n 'MinIO'

echo "deploying minio"

tmux send-keys -t $SESSION:MinIO 'cd ~/Desktop/openwhisk-test/minio' C-m 'kubectl apply -f minio-dev.yaml' C-m

sleep 8

tmux send-keys -t $SESSION:MinIO 'kubectl port-forward pod/minio 9000:9090 -n minio-dev' C-m

echo "Minio Reachable on http://localhost:9000 the username and password are : ${bold}minioadmin"
echo "If it is unreachable try running the setup again (it might take a while to set the pod up)

