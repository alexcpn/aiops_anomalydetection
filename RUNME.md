
# Running Prometheus Outlier detection

## Port forward in Kind cluster

```
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090
kubectl port-forward svc/prometheus-grafana 8080:80
```

## Running in Docker

```
docker run --rm -it --net=host -v /home/alex:/home alexcpn/fb_prophet_python:1
anomalydetection# python ./python/prom_analysis/outlier_full.py 
```

