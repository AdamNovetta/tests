#!/usr/bin/env python
# tools needed
import json
import boto3
import logging
import time
import datetime
from pprint import pprint
# Program meta -----------------------------------------------------------------
vers = "1.0"
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
# SNS
SNSClient = boto3.client('sns')
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
SNSARN = 'arn:aws:sns:' + EC2RegionName + ':' + MyAWSID + ':AWS_Alerts'
# IAM client to get the name of this account
IAMClient = boto3.client('iam')
paginator = IAMClient.get_paginator('list_account_aliases')
for response in paginator.paginate():
    AccountAliases = response['AccountAliases']
AWSAccountName = str(AccountAliases)
print "Running report on account: " + AWSAccountName
#  -----------------------------------------------------------------------------
# Get all bucket names
def get_all_bucket_names():
    AllBucketNames = []
    for buckets in S3Buckets:
        if "Buckets" in buckets:
            AllBuckets = S3Buckets[buckets]
            for bucket in AllBuckets:
                for BucketData in bucket:
                    if "Name" in BucketData:
                        AllBucketNames.append(bucket[BucketData])
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
    ReportedBuckets  = {}
    ProblemBuckets = 0
    SNSMessage = ''
    MyBuckets = get_all_bucket_names()
    SNSSubject = "AWS Account - " + str(AWSAccountName) + " - S3 Bucket permission report"
    #print(MyBuckets)
    for BucketName in MyBuckets:
        ACLOutput = ''
        try:
            S3Client.head_bucket(Bucket=BucketName)
            viewable = True
        except:
            viewable = False
        if viewable == True:
            ACLOutput = check_acl_status(BucketName, 'bucket', '')
            for i in ACLOutput:
                for  grants in i:
                    if "Grantee" in grants:
                        AllTypes = i[grants]
                        for grant in AllTypes:
                            if "AllUsers" in AllTypes[grant] :
                                if BucketName not in ReportedBuckets:
                                    ReportedBuckets[BucketName] = "Everyone / Public Access"
                                    ProblemBuckets += 1
                            if "AuthenticatedUsers" in AllTypes[grant]:
                                if BucketName not in ReportedBuckets:
                                    ReportedBuckets[BucketName] = "Any AWS user (not just on your account) "
                                    ProblemBuckets += 1
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
        SNSMessage +=  "Found no buckets with open permissions."
        SNSClient.publish(TopicArn=SNSARN, Message=SNSMessage, Subject=SNSSubject)
