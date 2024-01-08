#!/bin/bash

echo "Usage ./deploy-python-action.sh <action-name>"

echo "Creating the python (Python3.11) action on openwhisk with the name $1"

if [ -z "$1" ]
  then
    echo "No action_name supplied"
    exit 1
fi

zip $1.zip __main__.py

wsk -i action create $1 --docker rggg1/python11action $1.zip