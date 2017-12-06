#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
logger = logging.getLogger()
logger.setLevel(logging.WARNING)


# Program meta
vers = "3.1"
ProgramName = "AutoOrc"
Desc = "Auto stops and starts EC2 Instances/RDS instances bass on tags"
ls = " - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"


# define boto3 connections/variables
region = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region)
cw = boto3.client('cloudwatch')
rds = boto3.client('rds')
UnNamedLabel = "no name?"
LClient = boto3.client('lambda')


def LR(function_name, payload=None):

    if payload is not None:
        pload = {"FunctionName": function_name, "FunctionPayload": payload}
    else:
        pload = {"FunctionName": function_name}

    LambdaRelayOutput = LClient.invoke(
            FunctionName='lambda_function_relay',
            InvocationType='RequestResponse',
            Payload=json.dumps(pload)
            )
    data = LambdaRelayOutput['Payload'].read().decode()
    return(data)


# Setup cloudwatch alerts for instances
def putCloudWatchMetric(metricName, value, process, outcome):
    cw.put_metric_data(
        Namespace='ORC-Results',
        MetricData=[{
            'MetricName': metricName,
            'Value': value,
            'Unit': 'Count',
            'Dimensions': [{
                'Name': 'Process',
                'Value': process
                },
                {
                'Name': 'Outcome',
                'Value': outcome
                }]
            }]
    )


# function to get AutoOrc-down / AutoOrc-up tags
def get_rds_orc_tags(ARN, phase):
    OrcTimer = ''
    tags = rds.list_tags_for_resource(ResourceName=ARN)
    for tag in tags['TagList']:
        if tag['Key'] == phase:
            OrcTimer = tag['Value']
    return OrcTimer


# Main function, that lambda calls
def lambda_handler(event, context):
    MyAWSID = LR("get_account_ID")[1:-1]
    # set variable to figure out what day of the week it is
    d = datetime.datetime.now()
    # define timer, used to gague shutdown time
    timer = time.strftime("%H:%M")
    print(ls + "\n[ AutoOrc routine start time : " + timer + region + " ]")
    # set base filters for running/stopped instances, and matching orc tags
    FilterRunning = [
        {'Name': 'instance-state-name', 'Values': ['running']},
        {'Name': 'tag:autoOrc-down', 'Values': [timer]}
        ]

    FilterStopped = [
        {'Name': 'instance-state-name', 'Values': ['stopped']},
        {'Name': 'tag:autoOrc-up', 'Values': [timer]}
        ]
    # determine all running instances and filter for the orc up tag
    OrcInstances = ec2.instances.filter(Filters=FilterRunning)
    OrcDBs = rds.describe_db_instances()
    counter = ErrorCounter = 0
    # AutoOrc down EC2 Instances
    for instance in OrcInstances:
        counter += 1
        StateCode = 0
        name = LR("get_ec2_instance_name", {
                                                "Region": region,
                                                "EC2ID": instance.id
                                            })
        # Print the instances stopping for logging purposes
        print("---> Shutting down instance: ")
        print(instance.id + " [ Name : " + name + " ] ")
        response = instance.stop()
        StateCode = response['StoppingInstances'][0]['CurrentState']['Code']
        # print "Instance " + name + " status code: " + str(StateCode)
        if StateCode == 16:
            ErrorCounter += 1
            print("Error stopping " + name + ", error code: " + str(StateCode))
    if (counter > 0):
        putCloudWatchMetric(MyAWSID, counter, 'autoOrc-down', 'Success')
    if (ErrorCounter > 0):
        putCloudWatchMetric(MyAWSID, ErrorCounter, 'autoOrc-down', 'Error')
        print(" x - Errored while stopping " + str(counter) + " instances")
    print(" - Stopped " + str(counter) + " instances")
    # determine all stopped instances and filter for the orc up tag
    OrcInstancesUp = ec2.instances.filter(Filters=FilterStopped)
    counter = ErrorCounter = 0
    BadStartCodes = ['32', '48', '64', '80']
    # check to make sure we're only starting stuff on weekdays
    if d.isoweekday() in range(1, 6):
        for instance in OrcInstancesUp:
            counter += 1
            StateCode = 0
            name = LR("get_ec2_instance_name", {
                                                    "Region": region,
                                                    "EC2ID": instance.id
                                                })
            # Print the instances starting for logging purposes
            print("---> Starting instance: ")
            print(instance.id + " [ Name : " + name + " ] ")
            response = instance.start()
            StateCode = response['StartingInstances'][0]['CurrentState']['Code']
            # print "Instance " + name + " status code: " + str(StateCode)
            if StateCode in BadStartCodes:
                ErrorCounter += 1
                print(" Error starting " + name + ", code: " + str(StateCode))
        if (counter > 0):
            putCloudWatchMetric(MyAWSID, counter, 'autoOrc-up', 'Success')
        if (ErrorCounter > 0):
            putCloudWatchMetric(MyAWSID, ErrorCounter, 'autoOrc-up', 'Error')
            print(" x - Errored while starting " + str(counter) + " instances")
    print(" - Started " + str(counter) + " instances")
    # Cycle through all RDS instaces, starting Orc tagged ones on weekdays
    # stopping all instances if timer tag is (now)
    for RDSInstance in OrcDBs['DBInstances']:
        RDSName = str(RDSInstance['DBInstanceIdentifier'])
        RDSARN = str(RDSInstance['DBInstanceArn'])
        RDSStatus = str(RDSInstance['DBInstanceStatus'])
        RDSAZState = str(RDSInstance['MultiAZ'])
        if d.isoweekday() in range(1, 6):
            if RDSAZState == 'False' and RDSStatus == 'stopped':
                orc_up = get_rds_orc_tags(RDSARN, "autoOrc-up")
                if orc_up == timer:
                    print("RDS : " + RDSName + " database is starting up")
                    rds.start_db_instance(DBInstanceIdentifier=RDSName)
        if RDSAZState == 'False' and RDSStatus == 'available':
            orc_down = get_rds_orc_tags(RDSARN, "autoOrc-down")
            if orc_down == timer:
                print("RDS : " + RDSName + " database is shutting down now")
                rds.stop_db_instance(DBInstanceIdentifier=RDSName)

    print("[ AutoOrc routine finished " + region + " ]\n" + ls)
