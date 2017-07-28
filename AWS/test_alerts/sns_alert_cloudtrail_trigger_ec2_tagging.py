#!/usr/bin/env python
''' cloudwatch event-pattern trigger:
{
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com"
    ],
    "eventName": [
      "RunInstances"
    ]
  }
}
'''
#  -----------------------------------------------------------------------------
# tools needed
import json, boto3, logging, time, datetime
from time import mktime
# Program meta -----------------------------------------------------------------
vers = "1.0"
ProgramName = "sns_alert_cloudtrail_trigger"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
#  -----------------------------------------------------------------------------
# make connections to services
EC2RegionName = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=EC2RegionName)
EC2Client = boto3.client('ec2')
# IAM
AWSAccountName = ''
IAMClient = boto3.client('iam')
paginator = IAMClient.get_paginator('list_account_aliases')
for response in paginator.paginate():
    AccountAliases = response['AccountAliases']
AWSAccountName = str(AccountAliases)
# SNS
SNSClient = boto3.client('sns')
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
#  -----------------------------------------------------------------------------
class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)
#  -----------------------------------------------------------------------------
# Main function
def lambda_handler(event, context):
    print(json.dumps(event, cls=Render))
    AllEventItems = event['detail']['responseElements']['instancesSet']['items']
    InstanceOwner = event['detail']['userIdentity']['userName']
    InstanceType = event['detail']['requestParameters']['instanceType']
    InstanceIDs = []
    count = 0
    for items in AllEventItems:
        if "instanceId" in items:
            InstanceIDs.append(items['instanceId'])
            count += 1
    SNSMessage =  "\n\nUser [ " + InstanceOwner + " ] created [ " + str(count) + " x " + InstanceType + " ] instance(s): "
    for ids in InstanceIDs:
        SNSMessage += "\n" + ids
    SNSClient.publish(TopicArn=SNSARN, Message=SNSMessage, Subject=AWSAccountName+' - EC2 Instances Created' )
    for instance in InstanceIDs:
        EC2Client.create_tags(Resources=[instance],Tags=[{'Key': 'Created-By', 'Value': InstanceOwner },])
