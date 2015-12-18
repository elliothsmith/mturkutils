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

