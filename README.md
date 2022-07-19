# Using Time Series Forecasting Library Prophet for Anomaly detection

***For Running the code please see [RUNME.md](RUNME.md)***

## Using Prophet to look at the Past to find anomalies

Prophet from Facebook Research is an open-source time-series forecasting library
Prophet is a procedure for forecasting time series data based on an additive model where non-linear trends are fit with yearly, weekly, and daily seasonality.

Prophet is open source software released by Facebook’s Core Data Science team around 2017–18 and is very widely used. https://facebook.github.io/prophet/

It follows the concept of change points; that is it changes the curve fitting based on the inflection points it identifies in the time series data. We can plot the change points to see visually the inflection points it identities. Hence it fits the trend data very nicely.

We can use this property to fit in the time-series data from Prometheus or Grafana and use it to find out the outliers, which are the anomaly points.

Let’s use this open-source Grafana dashboards from Wikipedia, that show various Edit parameters. In this Edit dashboard, we will check this History of Saves chart in particular and see if there were any anomalies in that.

Since we don’t have the access to the backend Prometheus or similar scrapper they are using, we can use the Grafana data export option for now. Else we can write a PromQL, and query directly the data.

Wikipedia History of Saves Public Grafana Board (live here 
https://grafana.wikimedia.org/d/000000208/edit-count?orgId=1&refresh=5m)

Snapshot we took for processing below

![wikimedia_dashboard]

Here is the processed data, where the anomalies are put as red dots

![wiki_edit_save_outlier]

Prophet is good in that it requires minimal hyperparameter tuning; especially for system metrics data.
The only hyperparameter tuning done for this is changepoint_range, which we put here as 1 since we want to fit the entire historical data. (We are not in here for predicting the future, but to check the past!!)

I increase the interval width from the default .80 (80% ) to 95% for this particular chart; to increase the yhat_upper and yhat_lower band; so that only true outliers are exposed out

```
m = Prophet(changepoint_prior_scale=0.05,changepoint_range=1,interval_width=.95)
```

With more data processing, automation and threshold analysis, this can become the base for AIOps.

Minimal code and data here https://gist.github.com/alexcpn/ae733768af4e6ec55ae3863602d5146c
Some other interesting Charts
Prophet Inflection point Example

How Prophet fits the Trends
Note that with the above, if there is an increasing memory consumption like a memory leak, there won’t be an outlier as such, but still, it won’t be too difficult to automatically find that out.
Using Prophet to find outliers of Prometheus data
In a test Kubernetes cluster, I have put the Prometheus monitoring stack and the Node exporters and other standard scrappers, to get the monitoring data. Computer system-generated data is seasonal to the extent that CPU cycles are affected by periodic tasks like corn jobs and traffic trends, memory cycles -growth and garbage collection.
Prophet by default uses the data points to identify the seasonality aspect. There is no need to tweak the hyper-parameters.
To demonstrate, here are two graphs of the following Prometheus Query

```
promqlquery = 'sum by(pod)(node_namespace_pod_container:container_memory_working_set_bytes {cluster="", node=~"kubeflow-control-plane",container!="",pod=~"kube-proxy-.*"} )[7d:20m]'
Prometheus Container Memory for a Pod (Kubernetes)
```

Prometheus GUI Graph of PromQL for a container memory


![promgui]

Note that I have been using a Kind based cluster for the above experiments on my laptop, and there are periods of no data when I have set the laptop to Sleep mode. Prophet is able to fill the missing data points

Here is the output processed with only one setting change point_range changed

By default change points are only inferred for the first 80% of the time series; In our case, we are not forecasting but fitting so we need to give 100 per cent here and thereby the value of 1 is given.

```
m = Prophet(changepoint_prior_scale=0.05,changepoint_range=1)
```

![default_seasonality]

With default Prophet settings
Here is the same output with various seasonality related hyperparameters given

```
m = Prophet(changepoint_prior_scale=0.05,
changepoint_range=1, # By default changepoints are only inferred for the first 80% of the time series; In our case we are not forecasting # but fitting so we need to give 100 percent here
daily_seasonality=True,weekly_seasonality=False,yearly_seasonality=False, # we do not need to explicity set this; it takes from the data
seasonality_mode='additive', # this is the default - other option is 'multiplicative'
holidays_prior_scale=0.001  # default is 10, we set it to .001 to dampen holidays
)
```
![explicit_seasonality]

With Seasonality explicitly Set and holidays regularized off
We can see that Prophet deduces the trends correctly by default.


If we explicitly set the *daily_seasonality* also as *False*, then we can see that it does not fit properly; which is to be expected

![daily_set_off]
With daily_seasonality off

[wikimedia_dashboard]: https://i.imgur.com/myrkVEn.png
[wiki_edit_save_outlier]: https://i.imgur.com/FGQn7lh.png
[promgui]: https://i.imgur.com/U0RnezS.png
[default_seasonality]: https://i.imgur.com/qZdhAB8.png
[explicit_seasonality]: https://i.imgur.com/eoHlEaC.png
[daily_set_off]: https://i.imgur.com/R4Xyk7g.png