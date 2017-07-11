#!/usr/bin/env python
# tools needed
import json, boto3, logging, time, datetime
from pprint import pprint
# Program meta -----------------------------------------------------------------
vers = "1.0"
prog_name = "sns_alert_cloudtrail_trigger"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#  -----------------------------------------------------------------------------
# make connections to services
ec2_region_name = "us-east-1"
s3_client = boto3.client('s3')
s3_buckets = s3_client.list_buckets()
s3_object = boto3.resource('s3')
# SNS
sns_client = boto3.client('sns')
My_AWS_ID = boto3.client('sts').get_caller_identity().get('Account')
sns_arn = 'arn:aws:sns:' + ec2_region_name + ':' + My_AWS_ID + ':AWS_Alerts'
# Main function
def lambda_handler(event, context):
    print "SNS ARN: " + sns_arn
    print "EVENT: " + str(event)
    print "\nCONTEXT: " + str(context)
    sns_message =  "Cloudtrail log \n [ " + str(event) + " ]\n"
    sns_client.publish(TopicArn=sns_arn, Message=sns_message, Subject='Alert! Cloudtrail triggered')
