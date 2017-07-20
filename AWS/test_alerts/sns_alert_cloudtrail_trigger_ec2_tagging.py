#!/usr/bin/env python
''' cloudwatch rule/trigger event-pattern:
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
import json, boto3, logging, time, datetime,pprint
pp = pprint.PrettyPrinter(indent=4)
# Program meta -----------------------------------------------------------------
vers = "1.0"
prog_name = "sns_alert_cloudtrail_trigger"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#  -----------------------------------------------------------------------------
# make connections to services
# S3
ec2_region_name = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=ec2_region_name)
ec2_client = boto3.client('ec2')
s3_client = boto3.client('s3')
s3_buckets = s3_client.list_buckets()
s3_object = boto3.resource('s3')
# SNS
sns_client = boto3.client('sns')
My_AWS_ID = boto3.client('sts').get_caller_identity().get('Account')
sns_arn = 'arn:aws:sns:' + ec2_region_name + ':' + My_AWS_ID + ':AWS_Alerts'
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
    all_event_items = event['detail']['responseElements']['instancesSet']['items']
    instance_owner = event['detail']['userIdentity']['userName']
    instance_ids = []
    #ec2_instance_id = event['detail']['responseElements']['instancesSet']['items'][0]['instanceId']
    for items in all_event_items:
        if "instanceId" in items:
            instance_ids.aapend(all_event_items[items]['instanceId'])

    sns_message =  "(THIS IS A TEST)\n\n The user [ "
    sns_message +=  instance_owner
    sns_message += " ] requested instance, "
    sns_message += ami_ids
    sns_message += " be created in this aws account"
    sns_client.publish(TopicArn=sns_arn, Message=sns_message, Subject='Alert! Cloudtrail triggered')
    ec2_client.create_tags(Resources=[instance_ids],Tags=[{'Key': 'Admin', 'Value': instance_owner },])
