#!/bin/bash

cd setup-scripts && \

./setup-kind-openwhisk.sh && \

./setup-minio.sh && \

./setup-kafka.sh && \

cd ../main-app && \

./start-main-app.sh && \

cd ../python && \

./deploy-python-action.sh learner --memory 256 && \

# Prewarming the action

echo "Prewarming the action" && \

wsk -i action invoke learner --result
wsk -i action invoke learner --result

echo "Prewarming done, setting up resources needed for FL" && \

curl http://localhost:5000/build-everything && \

sleep 60 && \

echo "Everything is set up. You can start the FL process by visiting http://localhost:5000/learn?nclients=3&nrounds=5&nselected=3"
