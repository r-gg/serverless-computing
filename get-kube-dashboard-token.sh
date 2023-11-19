#!/bin/bash

echo "------   Kubernetes dashboard token   -------"

kubectl get secret admin-user -n kubernetes-dashboard -o jsonpath={".data.token"} | base64 -d

echo " "
echo "---------------------------------------------"