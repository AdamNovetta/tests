#!/usr/bin/env python
# tools needed
import json, boto3, logging, time, datetime
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# output spacer
ls = " - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - "
# Program meta -----------------------------------------------------------------
vers = "2.0"
ProgramName = "AutoOrc"
#  -----------------------------------------------------------------------------
# define the connection, replace region if your instances aren't in this region
region = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region)
cw = boto3.client('cloudwatch')
UnNamedLabel = "no name?"
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
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
# function to return name of instances for an instance ID
def get_instance_name(ec2id):
    EC2Instance = ec2.Instance(ec2id)
    InstanceName = ''
    if EC2Instance.tags is not None:
        for tags in EC2Instance.tags:
            if tags["Key"] == 'Name':
                InstanceName = tags["Value"]
    else:
        InstanceName = UnNamedLabel
    return InstanceName
# main function, that lambda 'calls'
def lambda_handler(event, context):
    # set variable to figure out what day of the week it is
    d = datetime.datetime.now()
    # define timer, used to gague shutdown time
    timer = time.strftime("%H:%M")
    print ls
    print "[ Orc routine start time : " + timer + " ]"
    # set base filters for running/stopped instances, and matching orc tags
    FilterRunning = [
        {'Name': 'instance-state-name','Values': ['running']},
        {'Name': 'tag:autoOrc-down','Values': [timer]}
        ]
    FilterStopped = [
        {'Name': 'instance-state-name','Values': ['stopped']},
        {'Name': 'tag:autoOrc-up','Values': [timer]}
        ]
    # collect all running instances and filter for orc down tag
    OrcInstances = ec2.instances.filter(Filters=FilterRunning)
    counter = 0
    ErrorCounter = 0
    for instance in OrcInstances:
        counter += 1
        StateCode = 0
        name = get_instance_name(instance.id)
        # Print the instances stopping for logging purposes
        print "---> Shutting down instance: "
        print(instance.id) + " [ Name : " + name + " ] "
        response = instance.stop()
        StateCode = response['StoppingInstances'][0]['CurrentState']['Code']
        #print "Instance " + name + " status code: " + str(StateCode)
        if  StateCode == 16:
            ErrorCounter += 1
            print "error stopping " + name + ", error code: " + str(StateCode)
    if (counter > 0):
        putCloudWatchMetric(MyAWSID, counter, 'autoOrc-down', 'Success')
    if (ErrorCounter > 0):
        putCloudWatchMetric(MyAWSID, ErrorCounter, 'autoOrc-down', 'Error')
    # determine all stopped instances and filter for the  orc up tag
    OrcInstancesUp = ec2.instances.filter(Filters=FilterStopped)
    counter = 0
    ErrorCounter = 0
    BadStartCodes = ['32', '48', '64', '80']
    # check to make sure we're only starting stuff on weekdays
    if d.isoweekday() in range(1, 6):
        for instance in OrcInstancesUp:
            counter += 1
            StateCode = 0
            name = get_instance_name(instance.id)
            # Print the instances starting for logging purposes
            print "---> Starting instance: "
            print(instance.id) + " [ Name : " + name + " ] "
            response = instance.start()
            StateCode = response['StartingInstances'][0]['CurrentState']['Code']
            #print "Instance " + name + " status code: " + str(StateCode)
            if StateCode in BadStartCodes:
                ErrorCounter += 1
                print "error starting " + name + ", error code: " + str(StateCode)
        if (counter > 0):
            putCloudWatchMetric(MyAWSID, counter, 'autoOrc-up', 'Success')
        if (ErrorCounter > 0):
            putCloudWatchMetric(MyAWSID, ErrorCounter, 'autoOrc-up', 'Error')
    print "[ Orc routine finished ]"
    print ls
