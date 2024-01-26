# TODOs

- currently the actions need to be manually warmed up before starting training.
- EMNIST instead of MNIST

# Order at setup

1. setup-kind-openwhisk
2. setup-minio (added a little update to the setup script and did not test it, so it might not work) + add minioadmin1 access key in the dashboard 
3. setup-kafka
4. start-main-app
5. goto localhost:5000/build-everything ~ creates a bucket, splits and uploads MNIST dataset to the bucket. creates a dedicated kafka topic called 'federated'
6. prepare the action: `......./python$ ./deploy-python-action.sh learner`
7. to start learning goto localhost:5000/learn

# To start learning

After staring the main-app, it gets served on localhost:5000. After navigating to `/build-everything` the training can start.

To start training navigate to `/learn`. Pass the arguments with url params: `/learn?nclients=10&nrounds=10&nselected=5`

Default values are:
- nclients=3
- nselected=3
- nrounds=5

Each round starts nclients and each client gets one split. As soon as the 50 splits get used the splits start getting re-used.

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


# Developing the main app

- Ports 5000 and 5001 of the main-app pod are open. The default app is served on 5000 and 5001 is left for experimentation.
- If you want to add custom code to the main flask app, modify the app.py in the pod and start serving the flask app on localhost:5001

# Openwhisk setup (automated with `./setup-kind-openwhisk.sh`)

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


## Set up kubernetes dashboard and start serving it (automated in `./setup-kind-openwhisk.sh` and `./get-kube-dashboard-token.sh`)

```
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml && kubectl proxy
```

In order to log in to the dashboard create service account role and assign bindings to get the token

```
kubectl apply -f dashboard-adminuser.yaml && kubectl apply -f dashboard-cluster-role-binding.yaml && kubectl apply -f dashboard-admin-secret.yaml && kubectl get secret admin-user -n kubernetes-dashboard -o jsonpath={".data.token"} | base64 -d
```

the AUTH data and API_URL is stored in `~/.wskprop` (also queryable via `wski property get --all`) (`wski` is an alias for `wsk -i`)



# MinIO

Following https://min.io/docs/minio/kubernetes/upstream/

In default minio-dev.yaml changed (deleted the following lines):
```
nodeSelector:
    kubernetes.io/hostname: kind-control-plane # Specify a node label associated to the Worker Node on which you want to deploy the pod.
```

(address 9090 was already in use  so `kubectl port-forward pod/minio 9000:9090 -n minio-dev`)

## Expose Minio pod as a service so it is reachable within the cluster (Automated in `./setup-minio.sh`)

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

Automated in `./setup-minio.sh` (at the end).


## New python runtime

 
Since minio needs python version >3.7 and the default python runtime of OpenWhisk actions is 3.6, we use another runtime 3.11 by following the setup steps in https://github.com/apache/openwhisk-runtime-python/blob/master/tutorials/local_build.md and https://github.com/apache/openwhisk-runtime-python/tree/master respectively

To build the runtime and push it to dockerhub run the script `./rebuild-image-and-push-to-hub.sh` in `new_python_runtime_setup/openwhisk-runtime-python` (from that directory).


# Debugging 


## Debugging ML and Action code with a jupyter notebook pod

```
./start-jupyter.sh
```

Runs the jupyter pod as root so that further packages can be installed for debugging. It forwards the localhost:10000 to the pod port where the dashboard is served (8888). Note: No root privileges are available in dashboard. If you want to add packages or generally have sudo access, you have to exec into the pod.

The script also prints out the token needed for logging into the dashboard.

## Debugging network in kubernetes 

```
kubectl run tmp-shell --rm -i --tty --image nicolaka/netshoot
```

# Main-App

The main app image now contains `wsk` and its apihost and auth are already set to `owdev-nginx.openwhisk.svc.cluster.local` and guest credentials (`23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP`) respectively

To download datasets to minio firstly log into minio dashboard, create access key where access key is `minioadmin1` and secret key is `minioadmin1` as well.

Call `/setup-minio` endpoint of main-app

Call `/download-and-split-dataset` ~ This downloads the entire MNIST dataset into the main-app pod and splits it into 50 pieces.

Call `/upload-splits` ~ This uploads the 50 pieces into MinIO



# Issues:

Training data cannot be stored locally but pulled from minio because an activation container cannot have access to the underlying pod's files. (possible with apache.openwhisk.Invoker modification but not sure how to do it with helm)

Kafka messages might not be consumed due to unclosed consumers. If it happens, just change the consumer's `group_id`.



# Misc

## get admin user credentials to access whisk.system namespace
kubectl -n openwhisk get secret owdev-whisk.auth -o jsonpath='{.data.system}' | base64 --decode

from [https://github.com/apache/openwhisk-deploy-kube/issues/253#issuecomment-404533474]

## NOTE: Persistent volume host refers to the node running the pod (not the Ubuntu system hosting docker and kubernetes on it!)

So in order to have that, bind the volume from ubunto to (each) one of the nodes in the simulated k8s cluster (kind-workers)


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


### Adding a new Openwhisk user (Optional) ~ Currently the guest account is used with predefined credentials.

Guest credentials: "--auth 23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"

```
kubectl -n openwhisk  -ti exec owdev-wskadmin -- /bin/sh

wskadmin user create fedUser
```