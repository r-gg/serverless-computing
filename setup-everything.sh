#!/bin/bash

./setup-kind-openwhisk.sh && \

./setup-minio.sh && \

./setup-kafka.sh

cd main-app && \

./build-and-start-main-app.sh

cd ../python && \

./deploy-python-action.sh learner && \

# Prewarming the action
wsk -i action invoke learner --result 

curl http://localhost:5000/build-everything && \

sleep 60

echo "Everything is set up. You can start the FL process by visiting http://localhost:5000/learn?nclients=3&nrounds=5&nselected=3"
