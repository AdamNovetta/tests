# tools needed
import json, boto3, logging, time, datetime
from pprint import pprint
# make connections to services
# S3
ec2_region_name = "us-east-1"
s3_client = boto3.client('s3')
s3_buckets = s3_client.list_buckets()
s3_object = boto3.resource('s3')
# SNS
sns_client = boto3.client('sns')
My_AWS_ID = boto3.client('sts').get_caller_identity().get('Account')
sns_arn = 'arn:aws:sns:' + ec2_region_name + ':' + My_AWS_ID + ':AWS_Alerts'
#
# Get all bucket names
def get_all_bucket_names():
    all_bucket_names = []
    for buckets in s3_buckets:
        if "Buckets" in buckets:
            all_buckets = s3_buckets[buckets]
            for bucket in all_buckets:
                for bucket_data in bucket:
                    if "Name" in bucket_data:
                        all_bucket_names.append(bucket[bucket_data])
    return all_bucket_names
# check acl of an object
def check_acl_status(target, object_type, parent_bucket):
    ACL_data = ''
    if "bucket" in object_type:
        bucket_acl = s3_object.BucketAcl(target)
        ACL_data = bucket_acl.grants
    if "object" in object_type:
        object_acl = s3_object.ObjectAcl(parent_bucket, target)
        ACL_data = object_acl
    return ACL_data
# print contents of bucket
def bucket_contents(target_bucket):
    output = ''
    available_resources = s3_client.list_objects(Bucket=target_bucket)
    output = "\n[ " + target_bucket + " ]"
    for item in available_resources['Contents']:
        output +=  "\n|- " + item['Key']
    return output
# 'Main' function
def lambda_handler(event, context):
    reported_buckets  = []
    problem_buckets = 0
    sns_message = ''
    MyBuckets = get_all_bucket_names()
    #print(MyBuckets)
    for BucketName in MyBuckets:
        ACL_output = ''
        try:
            s3_client.head_bucket(Bucket=BucketName)
            viewable = True
            #print "[ Bucket " + BucketName + " has viewable permissions! ]"
        except:
            #print "[ Bucket " + BucketName + " is NOT viewable ]"
            viewable = False
        if viewable == True:
            #print "[ can view " + BucketName + "'s permissions ]"
            ACL_output = check_acl_status(BucketName, 'bucket', '')
            for i in ACL_output:
                for  grants in i:
                    if "Grantee" in grants:
                        all_types = i[grants]
                        for grant in all_types:
                            #print all_types[grant] + i['Permission']
                            if "AllUsers" in all_types[grant] :
                                #print ">>> ALL USER ( "+ i['Permission'] + " ) PERMISSION FOUND!!!!!!!! <<<"
                                #print " And here's what is exposed: "
                                #bucket_contents(BucketName)
                                if BucketName not in reported_buckets:
                                    reported_buckets.append(BucketName)
                                    problem_buckets += 1
                            if "AuthenticatedUsers" in all_types[grant]:
                                #print ">>> ALL Authenticated USERS ( "+ i['Permission'] + " ) PERMISSION FOUND!!!!!!!! <<<"
                                #print " And here's what is exposed: "
                                #bucket_contents(BucketName)
                                if BucketName not in reported_buckets:
                                    reported_buckets.append(BucketName)
                                    problem_buckets += 1
        #print "_______________________________________________________________________________________"
    print "reported buckets: "
    print reported_buckets
    for rp in reported_buckets:
        #print "rp is : " + rp
        sns_message += "\nBucket: " + rp + " has open permissions!"
        sns_message += "\nContents: "
        sns_message += "\n"
        sns_message += bucket_contents(rp)
        sns_message += "\n"
    number_problem_buckets = str(problem_buckets)
    sns_message +=  "\n [ Total buckets with permissions issues: " + number_problem_buckets + " ]\n"
    sns_client.publish(TopicArn=sns_arn, Message=sns_message, Subject='A
