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

# Execute commands inside the MinIO pod
kubectl exec -n $MINIO_NAMESPACE $MINIO_POD_NAME -- /bin/sh <<EOF

    # Set alias for MinIO server
    mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

    mc admin user svcacct add local minioadmin --access-key "$ACCESS_KEY" --secret-key "$SECRET_KEY"

EOF
