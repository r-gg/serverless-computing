#!/bin/bash

# Define MinIO pod and namespace
MINIO_POD_NAME="minio"
MINIO_NAMESPACE="minio-dev"

# Define MinIO root credentials
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD="minioadmin"

# Define new user credentials
ACCESS_KEY="minioadmin1"
SECRET_KEY="minioadmin1"

tmux new-window -t Minio:3 -n 'akg'

# Execute commands inside the MinIO pod
tmux send-keys -t Minio:akg "kubectl exec -i -n $MINIO_NAMESPACE $MINIO_POD_NAME -- /bin/sh" C-m
tmux send-keys -t Minio:akg "mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD" C-m
tmux send-keys -t Minio:akg "mc admin user svcacct add local minioadmin --access-key "$ACCESS_KEY" --secret-key "$SECRET_KEY"" C-m

