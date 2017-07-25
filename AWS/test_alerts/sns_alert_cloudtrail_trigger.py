#!/usr/bin/env python
# tools needed
import json, boto3, logging, time, datetime
from pprint import pprint
from time import mktime
# Program meta -----------------------------------------------------------------
vers = "1.0"
ProgramName = "sns_alert_cloudtrail_trigger"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#  -----------------------------------------------------------------------------
# Class to render JSON outputs (with dates) successfully
class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)
#  -----------------------------------------------------------------------------
# make connections to services
EC2RegionName = "us-east-1"
# SNS
SNSClient = boto3.client('sns')
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
# Main function
def lambda_handler(event, context):
    print "SNS ARN: " + SNSARN
    print "EVENT: " + str(event)
    print "\nCONTEXT: " + str(context)
    SNSMessage =  "Cloudtrail log \n [ " + json.dumps(event, cls=Render) + " ]\n"
    SNSClient.publish(TopicArn=SNSARN, Message=SNSMessage, Subject='Alert! Cloudtrail triggered')
