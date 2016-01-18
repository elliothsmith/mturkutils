# Getting started with MTurk for DiCarlo Lab

## Before you begin

We use Amazon Mechanical Turk (MTurk) for high-throughput web-based human psychophysics. Before you begin launching any task, make sure you have contacted the lab manager and have taken the appropriate [Collaborative Institutional Training Initiative](http://couhes.mit.edu/training-research-involving-human-subjects) (CITI) courses. 

You will also need credentials separately for amazon s3 and MTurk. Someone from the lab will help you get those credentials. Once you get them go to the home folder of [mh17](http://mindhive.mit.edu/intro) (simply ssh username@mh17.mit.edu) and create a file named '.boto' The contents of the file should look like:

    [Credentials]
    aws_access_key_id=AKEYOUWILLGET
    aws_secret_access_key=thesecretkeyuwillget
    [MTurkCredentials]
    AWS_ACCESS_KEY_ID = AKEYOUWILLGET
    AWS_SECRET_ACCESS_KEY = thesecretkeyuwillget

The other _username_ and _password_ you will need is for the Amazon Mechanical Turk Requester account. This is where you can check how many **HITs** (_Human Intelligence Tasks_) you have launched and how many subjects have responded so far etc. You can also directly download the results and work off it. But it is suggested that you use the existing lab tools ([mturkutils](https://github.com/dicarlolab/mturkutils)) to organize the process and make it more efficient and the data easily shareable.

## General workflow

![General Workflow] (https://raw.githubusercontent.com/dicarlolab/dicarlolab101/master/mturk_files/general_workflow.png?token=AKMnBtRqank3HDI1px-2e8-bk3fvTEFKks5WfG7XwA%3D%3D)

Ha (hahong@mit.edu) has provided a tutorial that deals with each of the steps. Click the tutorial link below to see it. ([Tutorial](https://github.com/dicarlolab/mturkutils/blob/master/tutorials/Hands-on%20tutorial.pdf))

Briefly, here are the steps to get your experiment going on MTurk:

### Getting started

1. Copy an existing experiment from "experiments" folder. `hvm_2_way` or `objectome_64objs_v2` might be a good way to start.
2. Template html file (usually inside the `web` subfolder) defines how each HIT looks like.
3. The `driver.py` file specifies how to generate html files that will be uploaded to S3 for each HIT from the template.
4. Running `python driver.py` will generate HITs in a sandbox. You should always test them to make sure they work before making production HITs. HIT IDs will be printed and also saved in a pickle file for later use when you want to download data.
5. Running `python driver.py production` will generate the actual HITs that MTurkers can complete.

### Create HITs

```python
exp = get_exp()[0]
exp.prepHTMLs()
exp.testHTMLs()
exp.uploadHTMLs()
exp.createHIT(secure=True)
```

### Store data in dicarlo5

```python
import cPickle
from driver_basic import get_exp 
exp = get_exp(sandbox=False)[0]
hitids = cPickle.load(open(‘PICKLEFILE.pkl’))
exp.updateDBwithHITs(hitids)
```

### Retrieve data stored in dicarlo5

1. Open terminal locally and tunnel into dicarlo5:
   `ssh -f -N -L 22334:localhost:22334 <username>@dicarlo5.mit.edu`
2. Type `ipython`
3. Within ipython:
```
import pymongo as pm
import numpy as np

mongo_conn = pm.Connection(host='localhost',port=22334)
db = mongo_conn['mturk']
coll = db['your_collection_name']

#To look inside collection
for doc in coll.find():
  imData = doc['ImgData’]
  ...
```
