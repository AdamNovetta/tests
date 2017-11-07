#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime
import inspect
from time import mktime


# Program meta
vers = "2.0"
ProgramName = "Canaria"


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
logger = logging.getLogger()
logger.setLevel(logging.WARNING)


# Define boto3 connections/variables
EC2RegionName = "us-east-1"
S3Client = boto3.client('s3')
S3Buckets = S3Client.list_buckets()


class call_lambda:

    lambda_client = boto3.client('lambda')

    # Defines Lambda call that doesn't have a payload attached
    def no_input(self, function_name):
        invoke_response = call_lambda().lambda_client.invoke(
                                            FunctionName=function_name,
                                            InvocationType='RequestResponse',
                                            )
        data = invoke_response['Payload'].read().decode()[1:-1]
        return(data)


    # Defines Lambda call that includes a payload
    def payloaded_input(self, function_name, payload):
        invoke_response = call_lambda().lambda_client.invoke(
                                            FunctionName=function_name,
                                            InvocationType='RequestResponse',
                                            Payload=json.dumps(payload)
                                            )
        data = invoke_response['Payload'].read().decode()
        return(data)


    # Call Lambda to get the account ID
    def get_account_ID(self):
        fname = inspect.stack()[0][3]
        data = call_lambda().no_input(function_name=fname)
        return data


    # Call Lambda to get the name of the account
    def get_account_name(self):
        fname = inspect.stack()[0][3]
        data = call_lambda().no_input(function_name=fname)
        return data


    # Call lambda to get buckets with open permissions
    def get_open_s3_bucket_permissions(self, bucket):
        pload = { 'BucketName' : bucket }
        fname = inspect.stack()[0][3]
        data = call_lambda().payloaded_input(
                                function_name=fname,
                                payload=pload
                                )
        return data


    # Call Lambda to get objects in 'bucket' that have open permissions
    def get_open_s3_object_permissions(self, bucket):
        pload = { 'BucketName' : bucket }
        fname = inspect.stack()[0][3]
        data = call_lambda().payloaded_input(
                                function_name=fname,
                                payload=pload
                                )
        return data


    # Call lambda to send an SNS message
    def send_sns_message(self, ARN, Message, Subject):
        pload = {
                'SNSARN' : ARN,
                'SNSMessage' : Message,
                'SNSSubject' : Subject
                }
        fname = inspect.stack()[0][3]
        data = call_lambda().payloaded_input(
                                function_name=fname,
                                payload=pload
                                )
        return data


# Render JSON with datestamps correctly
class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)


# Get all bucket names
def get_all_bucket_names():
    AllBucketNames = []
    for bucket in S3Buckets['Buckets']:
        AllBucketNames.append(bucket['Name'])
    return AllBucketNames


# Attempt to connect to S3 bucket
def connect_to_bucket(target):
    try:
        S3Client.head_bucket(Bucket=target)
        viewable = True
    except:
        viewable = False
    return viewable


# Check the permissions of a bucket and its contents
def scan_bucket(bucket):
    BucketOutput= {}
    ParsedData = ''
    ProblemFiles=ProblemBuckets= 0

    bucket_check = call_lambda().get_open_s3_bucket_permissions(bucket)
    if bucket_check != "null":
        BucketCheck = json.loads(bucket_check)
        ParsedData += "\n- " + str(BucketCheck) + " can access whole bucket!"
        BucketOutput['ProblemBuckets'] = 1
    bucket_data = call_lambda().get_open_s3_object_permissions(bucket)
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
    ProblemBuckets=ProblemFiles=Errors= 0
    MyAWSID = call_lambda().get_account_ID()
    AccountName = call_lambda().get_account_name()
    SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
    print("Running report on account: " + AccountName + " - ID# " + MyAWSID)
    MyBuckets = get_all_bucket_names()
    for BucketName in MyBuckets:
        result = connect_to_bucket(BucketName)
        if result == True:
            ScanResults = scan_bucket(BucketName)
            if ScanResults:
                if 'ProblemBuckets' in ScanResults:
                    ProblemBuckets += ScanResults['ProblemBuckets']
                if 'ProblemFiles' in ScanResults:
                    ProblemFiles += ScanResults['ProblemFiles']
                if 'Issues' in ScanResults:
                    ReportedBuckets[BucketName] = ScanResults['Issues']
        if result == False:
            ReportedBuckets[BucketName] = "\n- Not scannable via Lambda checks"
            Errors += 1
    SNSSubject = "AWS Account: " + AccountName + " - S3 Permissions Report"
    if ProblemBuckets or ProblemFiles or Errors > 0:
        print(ReportedBuckets)
        for rp in ReportedBuckets:
            SNSMessage += "\nBucket:  [ " + rp + " ]  \nIssues: "
            SNSMessage += str(ReportedBuckets[rp]) + "\n"
        SNSMessage +=  "\nTotal files with suspect permissions: "
        SNSMessage += str(ProblemFiles) + "\n"
        SNSMessage +=  "\nTotal buckets with suspect permissions: "
        SNSMessage += str(ProblemBuckets) + "\n"
        SNSMessage +=  "\nTotal errors: "
        SNSMessage += str(Errors) + "\n"
        call_lambda().send_sns_message(
                        ARN=SNSARN,
                        Message=SNSMessage,
                        Subject=SNSSubject
                        )
    else:
        print("[ No buckets with open permissions! ]")
