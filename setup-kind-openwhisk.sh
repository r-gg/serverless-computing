#!/bin/bash

SESSION="OpenWhisk"


echo "Prerequisites: docker, kubernetes, helm, wsk"

SESSIONEXISTS=$(tmux list-sessions | grep $SESSION)

# Only create tmux SESSION if it doesn't already exist
if [ "$SESSIONEXISTS" = "" ]
then

    echo "to see the windows use\n\ttmux attach-SESSION -t OpenWhisk"

    tmux new-session -d -s $SESSION

    tmux rename-window -t 0 'Main'

    tmux send-keys -t 'Main' 'echo "Setting up Kubernetes cluster with openwhisk"' C-m

    tmux new-window -t $SESSION:1 -n 'Kind'

    echo "creating cluster with kind"

    tmux send-keys -t 'Kind' 'cd ./openwhisk-deploy-kube/deploy/kind' C-m './start-kind.sh; tmux wait -S kind-done' C-m

    echo "waiting for kind to finish setup"

    tmux wait kind-done

    echo "kind cluster created"

    tmux send-keys -t $SESSION:Kind 'kubectl label node kind-worker openwhisk-role=invoker && kubectl label node kind-worker2 openwhisk-role=invoker && kubectl label node kind-control-plane openwhisk-role=core' C-m

    sleep 1

    tmux new-window -t $SESSION:2 -n 'Kubernetes-dashboard'

    echo "Starting kubernetes dashboard"

    tmux send-keys -t $SESSION:Kubernetes-dashboard 'kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml' C-m

    tmux send-keys -t $SESSION:Kubernetes-dashboard 'kubectl apply -f dashboard-adminuser.yaml && kubectl apply -f dashboard-cluster-role-binding.yaml && kubectl apply -f dashboard-admin-secret.yaml' C-m

    tmux send-keys -t $SESSION:Kubernetes-dashboard 'kubectl proxy -p 8001' C-m

    sleep 1 

    echo "To access the dashboard use the token\n" $(kubectl get secret admin-user -n kubernetes-dashboard -o jsonpath={".data.token"} | base64 -d) "\n"

    sleep 1

    echo "Starting openwhisk. Monitor status with: kubectl get pods -n openwhisk --watch\n make sure that install-packages is completed"

    tmux new-window -t $SESSION:3 -n 'Openwhisk'

    tmux send-keys -t $SESSION:Openwhisk 'cd ./openwhisk-deploy-kube/deploy/kind' C-m

    tmux send-keys -t $SESSION:Openwhisk 'helm install owdev ./../../helm/openwhisk/ -n openwhisk --create-namespace -f mycluster.yaml' C-m

fi

echo "Waiting for openwhisk to deploy"

INSTALLFINISHED=$(kubectl get pods -n openwhisk | grep "install-packages.*Completed")

while [ "$INSTALLFINISHED" = "" ]
do
    echo "."
    sleep 30
    INSTALLFINISHED=$(kubectl get pods -n openwhisk | grep "install-packages.*Completed")
done

echo "openwhisk install finished"
echo -en "\007"
# Attach session, on the Main window
tmux attach-session -t $SESSION:0
