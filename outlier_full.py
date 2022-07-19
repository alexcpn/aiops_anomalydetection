#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" 
 Objective - Use facebook Prophet to find outliers of 
 Env - A kubernetes cluster with Prometheus, Grafana and Node Exporter 
 0. Use Grafana data exploer feature to get the PromQL queries for the graphs we need; test using Pormetheus GUI
 1. Read some metrics for a data range from Prometheus using PromQL via Prometheus REST API
 2. Convert data to dataframe 
 3. Use the data to train the prohet and fit its prediction on existing data
 4. Prophet will ignore outliers that go beyond its tolerance; and fit the line and trend it base on existing data
 5. Those outliers that prohet rejects will usually be the range outliers
 6. Generate the plot and compare with Grafana
 Convert to Pandas dataframe - convert timestamps
 Tuning Prophet hyper-parameters https://towardsdatascience.com/time-series-analysis-with-facebook-prophet-how-it-works-and-how-to-use-it-f15ecf2c0e3a
""" 

from prophet import Prophet
from prophet.plot import add_changepoints_to_plot
import numpy as np
import requests
import urllib
import pandas as pd
from matplotlib import pyplot as plt

__author__ = "alex.punnen@nokia.com"
__status__ = "Prototype"

def get_promql_data(promqlquery:str,prometheus_url:str) -> pd.DataFrame:
    """Qureies the prometheus server and returns the dataframe or None if not successful"""

     # PromQL
    #org_query ='rate(node_disk_read_bytes_total{job="node-exporter",+instance="172.18.0.2:9100",+device=~"nvme.+"}[1m])[1h:1m]'
    # note that PromQL wants the + in original query "nvme.+" to be encoded ; and rest as unencoded; This however does not work with request lib
    
    params = {'query':promqlquery}   
    url_encoded_query = urllib.parse.urlencode(params,safe='+')
    print("url_encoded_query",url_encoded_query)
    response = requests.get(prometheus_url,params=url_encoded_query)
    print("response.url",response.url)
    out = response.json()
    #print("response.json",out)
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
    df["ds"] =  pd.to_datetime(df["ds"],utc=False,unit='s')
    return df

if __name__ == "__main__":

    promqlquery ='rate(node_disk_read_bytes_total{job="node-exporter",+instance="172.18.0.2:9100",+device=~"nvme.*"}[20m])[7d:20m]'
    #promqlquery ='rate(node_disk_read_bytes_total{job="node-exporter",instance="172.18.0.2:9100",device=~"nvme.*"}[20m] @ 1648473649)[7d:20m]'
    promqlquery = 'sum by(pod)(node_namespace_pod_container:container_memory_working_set_bytes {cluster="", node=~"kubeflow-control-plane", container!=""} )[12h:10m]'
    promqlquery = 'sum by(pod)(node_namespace_pod_container:container_memory_working_set_bytes {cluster="", node=~"kubeflow-control-plane",\
         container!="",pod=~"kube-proxy-.*"} )[7d:20m]' # 1 mt interval is too many data points- sweet spot is between 10m to 20m
    prometheus_url= "http://localhost:9090/api/v1/query"
    df =get_promql_data(promqlquery,prometheus_url) 

    # Prophet works well with very minimal hyper-parameter changes
    #m = Prophet(changepoint_prior_scale=0.05,changepoint_range=1)
    # Set the hyper parameters for test
    m = Prophet(changepoint_prior_scale=0.05,
    changepoint_range=1, # By default changepoints are only inferred for the first 80% of the time series; In our case we are not forecasting \
    # but fitting so we need to give 100 percent here
    daily_seasonality=True,weekly_seasonality=False,yearly_seasonality=False, # we do not need to explicity set this; it takes from the data
    seasonality_mode='additive', # this is the default - other option is 'multiplicative'
    holidays_prior_scale=0.001  # default is 10, we set it to .001 to dampen holidays 
    )
    m.fit(df) # change this to trained model
    
    future = m.make_future_dataframe(periods =20,freq='20min') 
    forecast = m.predict(future)
    print(" -- model predict-- ")
    print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail())
    print("forecast all columns")
    print(forecast.columns.values.tolist())
    print(forecast.shape[0],df.shape[0])
    #values =m.history['y'] > forecast['yhat_upper']
    
    # find the dataframes having same indices
    forecast_truncated_index =forecast.index.intersection(df.index)
    forecast_truncated = forecast.loc[forecast_truncated_index]
    print(forecast_truncated.shape[0],df.shape[0],df.shape[0],df.shape[0])

    # Identify the thresholds with some buffer
    # For Prometheus type data no need to take the np.max as fit is already tight
    #buffer_max = np.max( forecast_truncated['yhat_upper'])
    buffer_max =  forecast_truncated['yhat_upper']
    #print("Buffer Max=",buffer_max)
    #buffer_min = np.min( forecast_truncated['yhat_lower'])
    buffer_min = forecast_truncated['yhat_lower']
    #print("Buffer Min=",buffer_min)
    
    # compare to dataframes having different lengths
    indices_max =m.history[m.history['y'] > buffer_max].index
    indices_min =m.history[m.history['y'] < buffer_min].index
    #indices_max =m.history[m.history['y'] > buffer_max.reset_index(drop=True)].index
    #indices_min =m.history[m.history['y'] < buffer_min.reset_index(drop=True)].index

    indices =indices_min.union(indices_max)
    
    # Get those points that have crossed the threshold
    thresholded_df  = m.history.iloc[indices] # ------> This has the thresholded values and more important timestamp
        
    figsize=(10, 6)
    fig = plt.figure(facecolor='w', figsize=figsize)
    ax = fig.add_subplot(111)
    fig = m.plot(forecast,ax=ax)

    # plot the threhsolded points as red
    ax.plot(thresholded_df['ds'].dt.to_pydatetime(), thresholded_df['y'], 'r.',
            label='Thresholded data points')
    fig.savefig('./out/outlier_forecast.png')
    

    # Uncomment the below, if you need to see the changepoints
    # these are points where prophet curve fitting senses the trends and updates as per the trend

    #threshold=0.01
    #signif_changepoints = m.changepoints[
    #        np.abs(np.nanmean(m.params['delta'], axis=0)) >= threshold]
    #print("changepoints=\n",m.changepoints) # these are the changepoints 

    #outliers = add_changepoints_to_plot(fig.gca(), m, forecast)
    #print("Outliers",outliers) # these are the outliers as matplolib 2D lines - need to refine
    #fig.savefig('forecastwithchange.png')
    

