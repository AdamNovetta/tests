#!/usr/bin/env python3
import boto3
import logged

# TODO
# setup tools for:
#
# better error reporting for:
# - aws_client
# - aws_resource


#  old connections
# ec2_client = boto3.client('ec2')
# iam_client = boto3.client('iam')
# s3_client = boto3.client('s3')


# connect to aws client
def aws_client(resource, region_name=''):

    try:
        obj = boto3.client(resource)
    except:
        obj = print("Unable to attach to " + resource)

    return(obj)


# connect to aws resource
def aws_resource(resource, region_name=''):

    try:
        obj = boto3.resource(resource)
    except:
        obj = print("Unable to attach to " + resource)

    return(obj)


# get AWS account alias(s)/name(s)
def get_account_name():
    api_call = aws_client('iam')
    paginator = api_call.get_paginator('list_account_aliases')
    for response in paginator.paginate():
        acct_alias = response['AccountAliases']
    if len(acct_alias) > 1:
        aws_acct_name = str("-".join(acct_alias))
    else:
        aws_acct_name = str("".join(acct_alias))

    return aws_acct_name


# get AWS account ID
def get_account_id():
    api_call = aws_client('sts')
    my_aws_id = api_call.get_caller_identity()['Account']

    return(my_aws_id)


# Get all S3 bucket names
def all_s3_bucket_names():
    api_call = aws_client('s3')
    s3_buckets = api_call.list_buckets()
    all_bucket_names = []
    for bucket in s3_buckets['Buckets']:
        all_bucket_names.append(bucket['Name'])

    return all_bucket_names


# get the name tag of an instance
def get_ec2_instance_name(id, region=''):
    instance_name = ''
    unamed_label = "(no name)"
    ec2 = aws_client('ec2', region_name=region)
    ec2_instance = ec2.Instance(id)
    if ec2_instance.tags is not None:
        for tags in ec2_instance.tags:
            if tags["Key"] == 'Name':
                instance_name = tags["Value"]
    else:
        instance_name = unamed_label
    return(InstanceName)


# send out SNS message to a given topic, provided the message/sub
def send_sns(event):
    sns_client = aws_client('sns')
    sns_arn = event['sns_arn']
    sns_message = event['sns_message']
    sns_subject = event['sns_subject']
    sns_client.publish(
                        TopicArn=sns_arn,
                        Message=sns_message,
                        Subject=sns_subject
                    )


# Create cloudwatch metrics for instance start/stop/failure
def put_cloudwatch_metric(namespace, metricName, value, process, outcome):
    cw = aws_client('cloudwatchw')
    cw.put_metric_data(
        Namespace=namespace,
        MetricData=[{
            'MetricName': metricName,
            'Value': value,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'Process', 'Value': process},
                {'Name': 'Outcome', 'Value': outcome}
            ]
        }]
    )
