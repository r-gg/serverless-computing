#!/bin/bash

SESSION=OpenWhisk


tmux new-window -t $SESSION:5 -n 'Python'

echo "Creating Python 11 runtime"

tmux send-keys -t $SESSION:Python 'cd ./new_python_runtime_setup/openwhisk-runtime-python' C-m 'cd tutorials; chmod 755 local_build.sh; cd ..; ./tutorials/local_build.sh -r python311Action -t action-python-v3.11:1.0-SNAPSHOT' C-m


