#!/usr/bin/env python
# tools needed
import json
import boto3
import logging
import time
import datetime
from time import mktime
from pprint import pprint
# Program meta -----------------------------------------------------------------
vers = "1.4"
ProgramName = "Canaria"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
#  -----------------------------------------------------------------------------
# make connections to services
# S3
EC2RegionName = "us-east-1"
S3Client = boto3.client('s3')
S3Buckets = S3Client.list_buckets()
S3Object = boto3.resource('s3')
#  -----------------------------------------------------------------------------
def call_lambda(lambdaName):
    lambda_client = boto3.client('lambda')
    invoke_response = lambda_client.invoke(FunctionName=lambdaName,
                                           InvocationType='RequestResponse'
                                           )
    data = invoke_response['Payload'].read().decode()
    data = data[1:-1]
    return(data)


# call_lambda function to get the ID of this account
def get_account_ID():
    return(call_lambda(get_account_ID.__name__))


# call_lambda function to get the name of this account
def get_account_name():
    return(call_lambda(get_account_name.__name__))
    

# Render JSON with datestamps correctly
class Render(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))

        return json.JSONEncoder.default(self, obj)


# Get all bucket names
def get_all_bucket_names():
    #print(json.dumps(S3Buckets, cls=Render)
    AllBucketNames = []
    for bucket in S3Buckets['Buckets']:
        AllBucketNames.append(bucket['Name'])
    return AllBucketNames


# check acl of an object
def check_acl_status(target, ObjectType, ParentBucket):
    ACLData = ''
    if "bucket" in ObjectType:
        bucket_acl = S3Object.BucketAcl(target)
        ACLData = bucket_acl.grants
    if "object" in ObjectType:
        object_acl = S3Object.ObjectAcl(ParentBucket, target)
        ACLData = object_acl
    return ACLData


# print contents of bucket
def bucket_contents(TargetBucket):
    output = ''
    AvailableResources = S3Client.list_objects(Bucket=TargetBucket)
    output = "\n[ " + TargetBucket + " ]"
    if 'Contents' in AvailableResources:
        for item in AvailableResources['Contents']:
            output +=  "\n|- " + item['Key']
    else:
        output = "(Bucket is currently empty)"
    return output


# 'Main' function
def lambda_handler(event, context):
    MyAWSID = get_account_ID()
    SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
    AccountName = get_account_name()
    print "Running report on account: " + AccountName + " - ID# " + MyAWSID
    ReportedBuckets  = {}
    ProblemBuckets = 0
    SNSMessage = ''
    MyBuckets = get_all_bucket_names()
    for BucketName in MyBuckets:
        ACLOutput = ''
        try:
            S3Client.head_bucket(Bucket=BucketName)
            viewable = True
        except:
            viewable = False
        if viewable == True:
            ACLOutput = check_acl_status(BucketName, 'bucket', '')
            for grants in ACLOutput:
                for grantee in grants['Grantee']:
                    if "AllUsers" in grants['Grantee'][grantee]:
                        if BucketName not in ReportedBuckets:
                            ReportedBuckets[BucketName] = "Everyone / Public Access"
                            ProblemBuckets += 1
                    if "AuthenticatedUsers" in grants['Grantee'][grantee]:
                        if BucketName not in ReportedBuckets:
                            ReportedBuckets[BucketName] = "Any AWS user (not just your account) "
                            ProblemBuckets += 1
    SNSSubject = "AWS Account - " + AccountName + " - S3 Bucket permission report"
    if ProblemBuckets > 0:
        print "Reported buckets: "
        print pprint(ReportedBuckets)
        for rp in ReportedBuckets:
            SNSMessage += "\nBucket:  [ " + rp + " ]  \n  Has open permissions to: " + ReportedBuckets[rp]
            SNSMessage += "\n"
        NumberOfProblemBuckets = str(ProblemBuckets)
        SNSMessage +=  "\n [ Total buckets with suspect permissions: " + NumberOfProblemBuckets + " ]\n"
        SNSClient.publish(TopicArn=SNSARN, Message=SNSMessage, Subject=SNSSubject)

    else:
        print "[ No buckeets with open permissions! ]"
