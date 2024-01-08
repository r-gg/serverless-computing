#!/bin/bash


docker run --name p11runtime -d --rm -v "$PWD:/mounty" rggg1/python11action

echo "Starting container"
sleep 5


echo "Installing requirements"
docker exec -it p11runtime bash -c "cd mounty && virtualenv virtualenv && source virtualenv/bin/activate && pip install -r requirements.txt"


echo "Zipping (everything except this script)"
zip -r pythonaction.zip . -x \*.sh

echo "deleting container"
docker rm -f $(docker container ls --all --quiet --filter "name=p11runtime")

rm -rf virtualenv