#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime
from time import mktime
from pprint import pprint


# Program meta
vers = "1.0"
ProgramName = "Clamor"
Desc = "Managing alerting and notifications  "

# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# make connections to services
EC2RegionName = "us-east-1"
# SNS configuration
#  Set this first variable to the SNS topic desired/created name ####
SNSTopicVar = "AWS-Alerts"
# Forming the rest of the SNS ARN
SNSClient = boto3.client('sns')
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':' + SNSTopicVar


class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)


# Check SNS Topic exists, if not create it
def check_sns_topic_exists(NameOfTopic):
    topics = SNSClient.list_topics()
    TopicList = topics['Topics']
    TopicNames = [t['TopicArn'].split(':')[5] for t in TopicList]
    if NameOfTopic in TopicNames:
        print("FOUND :" + NameOfTopic)
    else:
        print("NOT FOUND : " + NameOfTopic)
        SNSClient.create_topic(Name=SNSTopicVar)
        SNSClient.set_topic_attributes(
                                        TopicArn=SNSARN,
                                        AttributeName='DisplayName',
                                        AttributeValue=SNSTopicVar
                                    )


# IAM client to get the name of this account
def get_account_name():
    IAMClient = boto3.client('iam')
    paginator = IAMClient.get_paginator('list_account_aliases')
    for response in paginator.paginate():
        AccountAliases = response['AccountAliases']
    if len(AccountAliases) > 1:
        AWSAccountName = str("-".join(AccountAliases))
    else:
        AWSAccountName = str("".join(AccountAliases))
    return AWSAccountName


# Main function
def lambda_handler(event, context):
    check_sns_topic_exists(SNSTopicVar)
    # TODO - Setup notification process
