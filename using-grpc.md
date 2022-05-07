[//]: # (Copyright, Michael Vittrup Larsen)
[//]: # (Origin: https://github.com/MichaelVL/istio-katas)
[//]: # (Tags: #grpc #blue-green-deployment #http-header-routing #VirtualService #kiali)

# Blue/green deployments using gRPC

First, deploy version `v1` of the test application, using the gRPC variant:

```console
kubectl apply -f deploy/v1-grpc
```


# Cleanup

```console
kubectl delete -f deploy/v1-grpc
```
