#!/bin/bash

./tutorials/local_build.sh -r python311Action -t python11action

docker tag python11action rggg1/python11action

docker push rggg1/python11action
