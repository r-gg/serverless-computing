#!/bin/bash

kubectl apply -f jupyter-pod.yaml

# Pod name
pod_name="my-jupyter-notebook"

# Wait for the pod to be in the "Running" state
echo "Waiting for pod $pod_name to be in the 'Running' state..."
while true; do
    # Get the pod's status
    pod_status=$(kubectl get pod $pod_name --template="{{.status.phase}}")

    # Check if the pod is running
    if [ "$pod_status" == "Running" ]; then
        echo "Pod $pod_name is running."
        break
    else
        echo "Pod $pod_name is not running yet. Current status: $pod_status"
        sleep 5
    fi
done

# Retrieve logs from the specific pod
log_output=$(kubectl logs $pod_name)

# Extract the first occurrence of the token using grep
token=$(echo "$log_output" | grep -oP 'token=\K[^ ]+' | head -n 1)

# Print the extracted token
echo "Use the following token to access the dashboard on http://localhost:10000:$token"

kubectl port-forward pod/my-jupyter-notebook 10000:8888
