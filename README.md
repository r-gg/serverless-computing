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

Access Keys > create access key

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

## Creating the action .zip (where the python requirements will be downloaded)

Start the container where the action will be placed
```
docker run --name p11runtime --rm -v "$PWD:/tmp" python11action
```

Exec the command to create the venv
```
docker exec -it p11runtime bash -c "cd tmp && virtualenv virtualenv && source virtualenv/bin/activate && pip install -r requirements.txt"
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
```


# Misc

## get admin user credentials to access whisk.system namespace
kubectl -n openwhisk get secret owdev-whisk.auth -o jsonpath='{.data.system}' | base64 --decode

from [https://github.com/apache/openwhisk-deploy-kube/issues/253#issuecomment-404533474]

## NOTE: Persistent volume host refers to the node running the pod (not the Ubuntu system hosting docker and kubernetes on it!)

So in order to have that, bind the volume from ubunto to (each) one of the nodes in the simulated k8s cluster (kind-workers)

# Questions

1. Can you add and remove nodes to/from kind cluster after deployment? (maybe it goes over kubernetes?)



# Issues:

Either or:
  - Use latest MinIO but try to build a python 3.7 or higher runtime for the action
  - Use minio:7.1.8 and use python 3.6