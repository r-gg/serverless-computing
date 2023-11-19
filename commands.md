kubectl label node kind-worker openwhisk-role=invoker && kubectl label node kind-worker2 openwhisk-role=invoker && kubectl label node kind-control-plane openwhisk-role=core  



# For the dashboard we need a bearer token, so we create a service account and get its bearer token

kubectl apply -f dashboard-adminuser.yaml && kubectl apply -f dashboard-cluster-role-binding.yaml && kubectl apply -f dashboard-admin-secret.yaml && kubectl get secret admin-user -n kubernetes-dashboard -o jsonpath={".data.token"} | base64 -d

#&& kubectl -n kubernetes-dashboard create token admin-user


# Deploy from git with:

arrow@rg-vm:~/Desktop/openwhisk-test/openwhisk-deploy-kube/deploy/kind$ helm install owdev ../../helm/openwhisk -n openwhisk --create-namespace -f mycluster.yaml


# get system credentials to access whisk.system namespace
kubectl -n openwhisk get secret owdev-whisk.auth -o jsonpath='{.data.system}' | base64 --decode

from [https://github.com/apache/openwhisk-deploy-kube/issues/253#issuecomment-404533474]


