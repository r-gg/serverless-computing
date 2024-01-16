#!/bin/bash

SESSION="Minio"

bold=$(tput bold)
normal=$(tput sgr0)

tmux new-session -d -s $SESSION

tmux rename-window -t 0 'Main'

echo "deploying minio"

tmux send-keys -t $SESSION:Main 'cd ./minio' C-m 'kubectl apply -f minio-dev.yaml' C-m

sleep 8

tmux new-window -t $SESSION:1 -n 'svc'

tmux send-keys -t $SESSION:svc 'kubectl expose pod minio --port=9000 --name=minio-operator9000 -n minio-dev' C-m

# Name of the pod to check
POD_NAME="minio"

# Namespace where the pod is located, change if necessary
NAMESPACE="minio-dev"

# Interval in seconds between checks
INTERVAL=10

echo "Waiting for pod $POD_NAME to be running..."

# Loop until the pod status is 'Running'
while true; do
    # Get the status of the pod
    STATUS=$(kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.status.phase}')

    # Check if the status is 'Running'
    if [ "$STATUS" == "Running" ]; then
        echo "Pod $POD_NAME is running."
        break
    else
        echo "Pod $POD_NAME status: $STATUS. Waiting..."
    fi

    # Wait for the specified interval before checking again
    sleep $INTERVAL
done

tmux send-keys -t $SESSION:Main 'kubectl port-forward pod/minio 9000:9090 -n minio-dev' C-m

echo "Minio Reachable on http://localhost:9000 the username and password are : ${bold}minioadmin"
echo "If it is unreachable try running the setup again (it might take a while to set the pod up)"

echo "Creating service account for minio"
./minio/add-service-account.sh

