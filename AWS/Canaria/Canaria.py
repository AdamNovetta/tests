#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime
import inspect
from time import mktime


# Program meta
vers = "3.2"
ProgramName = "Canaria"


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
logger = logging.getLogger()
logger.setLevel(logging.WARNING)


# Define boto3 connections/variables
EC2RegionName = "us-east-1"
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


# Render JSON with datestamps correctly
class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)


# Check the permissions of a bucket and its contents
def scan_bucket(bucket):
    BucketOutput = {}
    ParsedData = ''
    ProblemFiles = ProblemBuckets = 0
    bucket_check = LR("get_open_s3_bucket_permissions", {'BucketName': bucket})
    if bucket_check != "null":
        BucketCheck = str(bucket_check[1:-1])
        ParsedData += "\n- " + str(BucketCheck) + " can access whole bucket!"
        BucketOutput['ProblemBuckets'] = 1
    bucket_data = LR("get_open_s3_object_permissions", {'BucketName': bucket})
    if bucket_data != "null":
        BucketData = json.loads(bucket_data)
        for Issue in BucketData:
            ParsedData += "\n- " + Issue + " - "
            ParsedData += str(BucketData[Issue]['Issue']['User'])
            ParsedData += " can "
            ParsedData += str(BucketData[Issue]['Issue']['Permission'])
            ProblemFiles += 1
        if ProblemFiles > 0:
            BucketOutput['ProblemFiles'] = ProblemFiles
        BucketOutput['Issues'] = ParsedData
    return BucketOutput


# Main function
def lambda_handler(event, context):
    SNSMessage = ''
    ReportedBuckets = {}
    ProblemBuckets = ProblemFiles = Errors = 0
    MyAWSID = LR("get_account_ID")[1:-1]
    AccountName = LR("get_account_name")[1:-1]
    SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
    print("Running report on account: " + AccountName + " - ID# " + MyAWSID)
    MyBuckets = json.loads(LR("get_all_s3_bucket_names"))
    for BucketName in MyBuckets:
        result = LR("connect_to_s3_bucket", {'BucketName': BucketName})
        if result == "true":
            ScanResults = scan_bucket(BucketName)
            if ScanResults:
                if 'ProblemBuckets' in ScanResults:
                    ProblemBuckets += ScanResults['ProblemBuckets']
                if 'ProblemFiles' in ScanResults:
                    ProblemFiles += ScanResults['ProblemFiles']
                if 'Issues' in ScanResults:
                    ReportedBuckets[BucketName] = ScanResults['Issues']
        if result == "false":
            ReportedBuckets[BucketName] = "\n- Not scannable via Lambda checks"
            Errors += 1
    SNSSubject = "AWS Account: " + AccountName + " - S3 Permissions Report"
    if ProblemBuckets or ProblemFiles or Errors > 0:
        print(json.dumps(ReportedBuckets))
        for rp in ReportedBuckets:
            SNSMessage += "\nBucket:  [ " + rp + " ]  \nIssues: "
            SNSMessage += str(ReportedBuckets[rp]) + "\n"
        SNSMessage += "\nTotal files with suspect permissions: "
        SNSMessage += str(ProblemFiles) + "\n"
        SNSMessage += "\nTotal buckets with suspect permissions: "
        SNSMessage += str(ProblemBuckets) + "\n"
        SNSMessage += "\nTotal errors: "
        SNSMessage += str(Errors) + "\n"
        LR("send_sns_message", {
                                    'SNSARN': SNSARN,
                                    'SNSMessage': SNSMessage,
                                    'SNSSubject': SNSSubject
                                })
    else:
        print("[ No buckets with open permissions! ]")
