# TODOs for serverless computing

- parallel training (multiple openwhisk invocations at once)
- after these invocations are done, merge them and save as new global model

# Order at setup

1. setup-kind-openwhisk
2. setup-minio (added a little update to the setup script and did not test it, so it might not work) + add minioadmin1 access key in the dashboard 
3. setup-kafka
4. start-main-app
5. goto localhost:5000/build-everything ~ creates a bucket, splits and uploads MNIST dataset to the bucket. creates a dedicated kafka topic called 'federated'
6. prepare the action: `......./python$ ./deploy-python-action.sh learner`
7. to start learning goto localhost:5000/learn

# After changing the action code

- Delete action `wski action delete learner`
- Redeploy action `......./python$ ./deploy-python-action.sh learner`

# After changing the main-app code

- Delete deployment `kubectl delete deployment main-app -n main-app`
- Kill tmux session `tmux kill-session -t main-app`
- rebuild and deploy `...../main-app$ ./build-and-start-main-app.sh`

# Available services to all pods

- kafka at : `kafkica.openwhisk.svc.cluster.local`
- minio at : `minio-operator9000.minio-dev.svc.cluster.local` (port 9000)
- openwhisk API (for wsk CLI) : `owdev-nginx.openwhisk.svc.cluster.local`

# Openwhisk setup

## Deploy the kubernetes cluster with kind

```
arrow@rg-vm:~/Desktop/openwhisk-test/openwhisk-deploy-kube/deploy/kind$ ./start-kind.sh 
```

## Deploy openwhisk on that k8s cluster

### Label the nodes as invoker and core

```
kubectl label node kind-worker openwhisk-role=invoker && kubectl label node kind-worker2 openwhisk-role=invoker && kubectl label node kind-control-plane openwhisk-role=core 
```

### Deploy openwhisk
```
arrow@rg-vm:~/Desktop/openwhisk-test/openwhisk-deploy-kube/deploy/kind$ helm install owdev ../../helm/openwhisk/ -n openwhisk --create-namespace -f mycluster.yaml
```

#### Check status with

```
kubectl get pods -n openwhisk --watch
```

install-packages should be completed.

### Adding a new Openwhisk user (Optional) ~ Currently the guest account is used with predefined credentials.

Guest credentials: "--auth 23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"

```
kubectl -n openwhisk  -ti exec owdev-wskadmin -- /bin/sh

wskadmin user create fedUser
```


## Set up kubernetes dashboard and start serving it

```
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml && kubectl proxy
```

## In order to log in to the dashboard create service account role and assign bindings to get the token

```
kubectl apply -f dashboard-adminuser.yaml && kubectl apply -f dashboard-cluster-role-binding.yaml && kubectl apply -f dashboard-admin-secret.yaml && kubectl get secret admin-user -n kubernetes-dashboard -o jsonpath={".data.token"} | base64 -d
```

the AUTH data and API_URL is stored in `~/.wskprop` (also queryable via `wski property get --all`) (`wski` is an alias for `wsk -i`)



## Prometheus and Grafana

Mix from https://dev.to/aws-builders/your-guide-to-prometheus-monitoring-on-kubernetes-with-grafana-gi8
and https://semaphoreci.com/blog/prometheus-grafana-kubernetes-helm and https://medium.com/@giorgiodevops/kind-install-prometheus-operator-and-fix-missing-targets-b4e57bcbcb1f


```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
```

```
kubectl create namespace prometheus
```

```
helm install stable prometheus-community/kube-prometheus-stack -n prometheus
```

Expose prometheus to localhost (it was only available to the nodes in the cluster)
```
kubectl port-forward -n prometheus svc/stable-kube-prometheus-sta-prometheus 9090:9090
```

- Note: Port-forward usually goes with pods and not services , hence `svc/` was added

Grafana comes in the helm chart as well so we expose grafana on localhost with port-forwarding as well
```
kubectl -n prometheus port-forward svc/stable-grafana 3000:80   
```

### get admin password for grafana service (username is admin)
```
kubectl get secret --namespace prometheus stable-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```

- The prometheus is already added as a data source in grafana :) !

# MinIO

Following https://min.io/docs/minio/kubernetes/upstream/

In minio-dev.yaml changed (deleted the following lines):
```
nodeSelector:
    kubernetes.io/hostname: kind-control-plane # Specify a node label associated to the Worker Node on which you want to deploy the pod.
```

(address 9090 was already in use  so `kubectl port-forward pod/minio 9000:9090 -n minio-dev`)

## Install MinIO client

```
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs \
  -o $HOME/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

## Expose Minio pod as a service so it is reachable within the cluster

https://kubernetes.io/docs/tutorials/services/connect-applications-service/
https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/

```
kubectl expose pod minio --port=9000 --name=minio-operator9000 -n minio-dev

```

Testing if it is reachable from another pod
```
kubectl run curl --image=radial/busyboxplus:curl -i --tty --rm
[ root@curl:/ ]$ curl -k minio-operator9000.minio-dev.svc.cluster.local:9000
```

## Create access key in minio dashboard

Access Keys > create access key (not easy to automate 💀)

# Installing `requirements.txt` when deploying python actions

https://github.com/apache/openwhisk/blob/master/docs/actions-python.md#packaging-python-actions-with-a-virtual-environment-in-zip-files


## Since minio needs python version >3.7 and the default python runtime of OpenWhisk actions is 3.6, we use another runtime 3.11 by following the setup steps in https://github.com/apache/openwhisk-runtime-python/blob/master/tutorials/local_build.md and https://github.com/apache/openwhisk-runtime-python/tree/master respectively

# Debugging the containers : https://medium.com/openwhisk/advanced-debugging-of-openwhisk-actions-518414636932

using the `invoker.py`

running the new runtime on 8080 instead of classic http 80:

```
docker run -p 127.0.0.1:8080:8080/tcp --name=bloom_whisker --rm -it action-python-v3.11:1.0-SNAPSHOT
```

```
docker tag <image-id-of action-python-v3.11:1.0-SNAPSHOT> python11action
```

# Debugging 


## Debugging ML and Action code with a jupyter notebook pod?

```
./start-jupyter.sh
```

Runs the jupyter pod as root so that further packages can be installed for debugging. It forwards the localhost:10000 to the pod port where the dashboard is served (8888). Note: No root privileges are available in dashboard. If you want to add packages or generally have sudo access, you have to exec into the pod.

The script also prints out the token needed for logging into the dashboard.

## Debugging network in kubernetes 

```
kubectl run tmp-shell --rm -i --tty --image nicolaka/netshoot
```

## Creating the action .zip (where the python requirements will be downloaded) ~ Not needed anymore because the zip gets too big for openwhisk and cannot be deployed (See new `deploy-python-action.sh`)

Start the container where the action will be placed
```
docker run --name p11runtime --rm -v "$PWD:/mounty" rggg1/python11action
```

Exec the command to create the venv
```
docker exec -it p11runtime bash -c "cd mounty && virtualenv virtualenv && source virtualenv/bin/activate && pip install -r requirements.txt"
```

Stop the test container used for creating the venv.

Also testing if action works
```
zip -r helloPython.zip virtualenv check.py __main__.py requirements.txt 
ls
invoke.py init helloPython.zip 
../debugging/invoke.py init helloPython.zip 
../debugging/invoke.py run ''
../debugging/invoke.py run '{"id":"1"}'
```

```
wski action create hello --docker rggg1/python11action helloPython.zip
```

**The above steps are automated in  `create-zip.sh` and `deploy-python-action`** 

**it might take a while on the first start**
```
wski action invoke hello --result
```

# Kafka

In a kafka pod by openwhisk:
```
root@owdev-kafka-0:/opt/kafka/bin# ./kafka-topics.sh --zookeper=localhost:9092 --list

root@owdev-kafka-0:/# ./kafka-topics.sh --zookeeper=owdev-zookeeper.openwhisk:2181 --list
```


## Label pod so that it can be exposed as a service

```
kubectl label pod -n openwhisk owdev-kafka-0 application=kafka
```

Then use following yaml to create a service:
```
apiVersion: v1
kind: Service
metadata:
  name: kafkica
  labels:
    application: kafka
spec:
  ports:
  - port: 9092
    protocol: TCP
  selector:
    application: kafka
```

it will expose the pod port 9092 

## In a main-app pod

get the kafka tar and extract it

```
wget "https://dlcdn.apache.org/kafka/3.6.0/kafka_2.13-3.6.0.tgz"

tar -xzf kafka_2.13-3.6.0.tgz

cd kafka_2.13-3.6.0
```

Access zookeeper

```
root@main-app-84c55f5ffd-gjvvr:/app/kafka_2.13-3.6.0/bin# ./zookeeper-shell.sh owdev-zookeeper.openwhisk:2181
```

(Maybe needed to install java and gradle with)
```
apt install default-jre
apt install gradle
```


# Main-App

The main app image now contains `wsk` and its apihost and auth are already set to `owdev-nginx.openwhisk.svc.cluster.local` and guest credentials (`23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP`) respectively

To download datasets to minio firstly log into minio dashboard, create access key where access key is `minioadmin1` and secret key is `minioadmin1` as well.

Call `/setup-minio` endpoint of main-app

Call `/download-dataset` ~ This downloads the entire MNIST dataset into the main-app pod and splits it into 50 pieces.

Call `/upload-splits` ~ This uploads the 50 pieces into MinIO

# Misc

## get admin user credentials to access whisk.system namespace
kubectl -n openwhisk get secret owdev-whisk.auth -o jsonpath='{.data.system}' | base64 --decode

from [https://github.com/apache/openwhisk-deploy-kube/issues/253#issuecomment-404533474]

## NOTE: Persistent volume host refers to the node running the pod (not the Ubuntu system hosting docker and kubernetes on it!)

So in order to have that, bind the volume from ubunto to (each) one of the nodes in the simulated k8s cluster (kind-workers)



# Issues:

Training data cannot be stored locally but pulled from minio because an activation container cannot have access to the underlying pod's files. (possible with apache.openwhisk.Invoker modification but not sure how to do it with helm)

Kafka messages might not be consumed due to unclosed consumers. If it happens, just change the consumer's `group_id`.