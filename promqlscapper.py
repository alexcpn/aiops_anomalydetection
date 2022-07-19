# objective -
# Read a set of data range from Prometheus using PromQL
# Convert to Pandas dataframe - convert timestamps
# 

import requests
import urllib
import pandas as pd

def get_promql_data(promqlquery:str,prometheus_url:str) -> pd.DataFrame:
    """Qureies the prometheus server and returns the dataframe or None if not successful"""

     # PromQL
    #org_query ='rate(node_disk_read_bytes_total{job="node-exporter",+instance="172.18.0.2:9100",+device=~"nvme.+"}[1m])[1h:1m]'
    # note that PromQL wants the + in original query "nvme.+" to be encoded ; and rest as unencoded; This however does not work
    
    params = {'query':promqlquery}   
    url_encoded_query = urllib.parse.urlencode(params,safe='+')
    print("url_encoded_query",url_encoded_query)
    response = requests.get(prometheus_url,params=url_encoded_query)
    print("response.url",response.url)
    out = response.json()
    print("response.json",out)
    results = out['data']['result']
    valueslist = []
    for result in results:
        valueslist.append(result['values'])
    if not valueslist:
        print("No results received; check range or Errors")
        return None

    flattened = [val for sublist in valueslist for val in sublist]
    df = pd.DataFrame(flattened)
    df.columns=["ds","y"]
    print(df.head())
    df["ds"] =  pd.to_datetime(df["ds"],utc=False,unit='s')
    return df


if __name__ == "__main__":
    #promqlquery ='rate(node_disk_read_bytes_total{job="node-exporter",+instance="172.18.0.2:9100",+device=~"nvme.*"}[1m])[1h:1m]'
    promqlquery ='rate(node_disk_read_bytes_total{job="node-exporter",+instance="172.18.0.2:9100",+device=~"nvme.*"}[10m])[1h:10m]'
    #'node_load1{job="node-exporter", instance="172.18.0.2:9100"}[7d:05m]' 1648506840 1648510380
    
    # For queries like below we need to parse throguh each pod and run the fit
    promqlquery = 'sum by(pod)(node_namespace_pod_container:container_memory_working_set_bytes {cluster="", node=~"kubeflow-control-plane", container!=""} )[1h:10m]'
    
    # let use the query like below to see an incrasing trend in memory
    promqlquery ='sum by(pod)(node_namespace_pod_container:container_memory_working_set_bytes {cluster="", node=~"kubeflow-control-plane", container!="",pod=~"kube-proxy-.*"} )[1h:10m]'
    #promqlquery ='node_namespace_pod:kube_pod_info:'

    prometheus_url= "http://localhost:9090/api/v1/query"
    df =get_promql_data(promqlquery,prometheus_url) 
    print(df.head())
    print(df.tail())

