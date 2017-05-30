#!/usr/bin/env python
'''
   AutoOrc - Lambda Function - V 1.2
--------------------------------------------------------------------------------
Copyright 2017 Novetta, Inc.
P&T Infrastructure or its affiliates. All Rights Reserved.

  This file is distributed on an AS IS BASIS, WITHOUT WARRANTIES OR CONDITIONS
  OF ANY KIND, express or implied.

Support: PT-INFRASTRUCTURE@novetta.com
--------------------------------------------------------------------------------
Purpose:
    Shuts down or starts up instances based on the ec2 instance tags:
    autoOrc-down and autoOrc-up, and the UTC time value in those tags (ie 13:00)

Usage:
   - Setup a 1 minute interval cloudwatch event (cron trigger) and create the
   above tags, specifying times for on/off in 24-hour UTC
   - Update region and filter_running.append/filter_stopped.append statements, if
     you want to use other tags to hold the up and down times
'''
import json, boto3, logging, time, datetime
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
# output spacer
ls = " - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - "
# define the connection, replace region if your instances aren't in this region
region = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region) 
# main function, that lambda 'calls'
def lambda_handler(event, context):
    # set variable to figure out what day of the week it is
    d = datetime.datetime.now()
    # define timer, used to gague shutdown time
    timer = time.strftime("%H:%M")
    print ls
    print "[ Orc routine start time : " + timer + " ]"
    # set base filters for running/stopped instances, and matching orc tags    
    filter_running = [
        {'Name': 'instance-state-name','Values': ['running']},
        {'Name': 'tag:autoOrc-down','Values': [timer]}
        ]
    filter_stopped = [
        {'Name': 'instance-state-name','Values': ['stopped']},
        {'Name': 'tag:autoOrc-up','Values': [timer]}
        ]
    # collect all running instances and filter for orc down tag
    orc_instances = ec2.instances.filter(Filters=filter_running)   
    for instance in orc_instances:
        name = "no name?"
        for tag in instance.tags:
            if 'Name'in tag['Key']:
                name = tag['Value']
        # Print the instances stopping for logging purposes
        print "Shutting down instance: "
        print(instance.id) + " [ Name : " + name + " ] "
        instance.stop()
    # determine all stopped instances and filter for the  orc up tag
    orc_instances_up = ec2.instances.filter(Filters=filter_stopped) 
    # check to make sure we're only starting stuff on weekdays  
    if d.isoweekday() in range(1, 6):
        for instance in orc_instances_up:
            name = "no name?"
            for tag in instance.tags:
                if 'Name'in tag['Key']:
                    name = tag['Value']
            # Print the instances starting for logging purposes
            print "---> Starting instance: "
            print(instance.id) + " [ Name : " + name + " ] "
            instance.start()    
    print "[ Orc routine finished ]"        
    print ls
