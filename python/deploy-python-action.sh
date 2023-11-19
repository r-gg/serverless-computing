#!/bin/bash

echo "Usage ./deploy-python-action.sh <action-name> <zip_file>"

echo "Creating the python (Python3.11) action on openwhisk with the name $1 and from the zip file $2"

if [ -z "$1" ]
  then
    echo "No action_name supplied"
    exit 1
fi

if [ -z "$2" ]
  then
    echo "No zip_file supplied"
    exit 1
fi

wsk -i action create $1 --docker rggg1/python11action $2