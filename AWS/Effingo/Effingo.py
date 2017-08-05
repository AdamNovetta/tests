#!/usr/bin/env python
# tools needed
import boto3, calendar, tiime, sys, logging
from datetime import datetime
# Program meta -----------------------------------------------------------------
vers = "1.0"
ProgramName = "Effingo"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# List witch snapshots to delete
deletelist = []
#run daily, if sat then run weekly, if last day of the month run monthly
# Setup logging TODO: send to S3!!!!
def logging_output():
    logging.basicConfig(level=logging.WARNING)
    StartMessage = 'Started taking %(period)s snapshots at %(date)s' % {
        'period': period,
        'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S')
    }
    message += StartMessage + "\n\n"
    logging.info(StartMessage)

# AWS assumptions --------------------------------------------------------------
EC2RegionName = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=EC2RegionName)
EC2Client = boto3.client('ec2')
# ------------------------------------------------------------------------------
# The volumes tags we're looking for to establish the backup intervals
VolumeTags = ['DailySnapshot', 'WeeklySnapshot', 'MonthlySnapshot']
# ------------------------------------------------------------------------------
# the Account ID for the AWS account this script is running in
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
SNSClient = boto3.client('sns')
# Make sure the SNS topic below exists in your account, it enables script emails
SNSTopicName = "auto-snapshots"
SNSARN = "arn:aws:sns:" + EC2RegionName +":" + MyAWSID + ":" + SNSTopicName
# IAM check_acl_status
IAMClient = boto3.client('iam')
# ------------------------------------------------------------------------------
# Get the tags of a reouse that's passed to the func
def get_resource_tags(resources):
    ResourceID = resources.id
    ResourceTags = {}
    if ResourceID:
        TagFilter = [{
            'Name': 'resource-id',
            'Values': [ResourceID]
        }]
        tags = EC2Client.describe_tags(Filters=TagFilter)
        for tag in tags['Tags']:
            key = tag['Key']
            value = tag['Value']
            # Tags starting with 'aws:' are reserved for internal use
            # also don't double-tag snapshots with the scripts VolumeTags
            if not key.startswith('aws:') and key not in VolumeTags:
                ResourceTags[key] = value
    return ResourceTags

# Set the tags of the resource from the tags passed to the func
def set_resource_tags(resource, tags):
    for TagKey, TagValue in tags.iteritems():
        if resource.tags is None:
            print 'Tagging %(ResourceID)s with [%(TagKey)s: %(TagValue)s]' % {
                'ResourceID': resource.id,
                'TagKey': TagKey,
                'TagValue': TagValue
            }
            resource.create_tags(Tags=[{'Key':TagKey, 'Value':TagValue}])
        elif TagKey not in resource.tags or resource.tags[TagKey] != TagValue:
            print 'Tagging %(ResourceID)s with [%(TagKey)s: %(TagValue)s]' % {
                'ResourceID': resource.id,
                'TagKey': TagKey,
                'TagValue': TagValue
            }
            resource.create_tags(Tags=[{'Key':TagKey, 'Value':TagValue}])

# get the 'Name' tag out of the batch of tags sent
def get_tag_name(TAGS):
    # returns the Name|tag:value given an instanceID
    NameTag = ''
    if TAGS is not None:
        for tags in TAGS:
            if tags["Key"] == 'Name':
                NameTag = tags["Value"]
    else:
        NameTag = UnNamedLabel
    return NameTag
# ------------------------------------------------------------------------------
# Main function of the script
def lambda_handler(event, context):
    # Message to return result via SNS
    message = ""
    errmsg = ""
    # Counters
    TotalCreates = 0
    TotalDeletes = 0
    CountErrors = 0
    CountSuccess = 0
    CountTotal = 0
    passes = 0
    # Number of snapshots to keep (the older ones are going to be deleted)
    KeepWeek = 5
    KeepDay = 5
    KeepMonth = 2
    # time variables
    today = datetime.today()
    day = today.strftime('%-d')
    year = today.strftime('%Y')
    month = today.strftime('%-m')
    now = datetime.weekday(today)
    DaysInMonth = calendar.mdays[int(month)]
    # Test
    paginator = IAMClient.get_paginator('list_account_aliases')
    for response in paginator.paginate():
            AccountAliases = response['AccountAliases']
    AccountAliases = str(AccountAliases)
    # all of the VolumeTags are now tasks to be done (daily/weekly/monthly)
    tasks = VolumeTags
    # deciding if we're running WeeklySnapshot / MonthlySnapshot
    # if it's day 5 (sat), we'll run a weekly backup
    if 5 != now:
        tasks.remove('WeeklySnapshot')
    # if it's the last day of the month, run monthly backups for tagged volumes too
    if int(day) != DaysInMonth:
        tasks.remove('MonthlySnapshot')
    # run the snapshot task(s)
    for task in tasks:
        period = ''
        TagType = task
        if TagType == 'DailySnapshot':
            period = 'day'
            DateSuffix = today.strftime('%a')
        elif TagType == 'WeeklySnapshot':
            period = 'week'
            DateSuffix = today.strftime('%U')
        elif TagType == 'MonthlySnapshot':
            period = 'month'
            DateSuffix = month
        print "\n Running snapshots for [ " + period + " ] that match tag type: " + TagType + "\n"
        vols = ec2.volumes.filter(Filters=[{'Name': 'tag:'+TagType ,'Values': ["True"]}])
        for vol in vols:
            VolumeName = get_tag_name(vol.tags)
            print "Taking snapshot of: " + VolumeName + "   ID: " +vol.id + "\n"
            try:
                CountTotal += 1
                logging.info(vol)
                TagsVolume = get_resource_tags(vol)
                description = '%(period)s_snapshot %(vol_id)s_%(period)s_%(DateSuffix)s by Lambda Effingo script at %(date)s' % {
                    'period': period,
                    'vol_id': vol.id,
                    'DateSuffix': DateSuffix,
                    'date': today.strftime('%d-%m-%Y %H:%M:%S')
                }
                try:
                    CurrentSnap = vol.create_snapshot(Description=description)
                    set_resource_tags(CurrentSnap, TagsVolume)
                    SuccessMessage = 'Snapshot created with description: %s and tags: %s' % (str(description), str(TagsVolume))
                    print(str(SuccessMessage))
                    logging.info(str(SuccessMessage))
                    TotalCreates += 1
                except Exception, e:
                    print "Unexpected error:", sys.exc_info()[0]
                    logging.error(e)
                    pass
                print "\n Deleting the old snapshots for this volume... \n"
                snapshots = vol.snapshots.all()
                deletelist = []
                for snap in snapshots:
                    sndesc = snap.description
                    if (sndesc.startswith('week_snapshot') and period == 'week'):
                        deletelist.append(snap)
                    elif (sndesc.startswith('day_snapshot') and period == 'day'):
                        deletelist.append(snap)
                    elif (sndesc.startswith('month_snapshot') and period == 'month'):
                        deletelist.append(snap)
                    else:
                        logging.info('     Skipping, not added to deletelist: ' + sndesc)
                for snap in deletelist:
                    logging.info(snap)
                    logging.info(snap.start_time)

                def date_compare(snap1, snap2):
                    if snap1.start_time < snap2.start_time:
                        return -1
                    elif snap1.start_time == snap2.start_time:
                        return 0
                    return 1

                deletelist.sort(date_compare)
                if period == 'day':
                    keep = KeepDay
                elif period == 'week':
                    keep = KeepWeek
                elif period == 'month':
                    keep = KeepMonth
                delta = len(deletelist) - keep
                for i in range(delta):
                    DeleteMessage = '     Deleting snapshot ' + deletelist[i].description
                    logging.info(DeleteMessage)
                    deletelist[i].delete()
                    TotalDeletes += 1
                time.sleep(3)
            except:
                print "[LATE STAGE] Unexpected error:", sys.exc_info()[0]
                logging.error('Error in processing volume with id: ' + vol.id)
                errmsg += 'Error in processing volume with id: ' + vol.id
                CountErrors += 1
            else:
                CountSuccess += 1
    result = '\nFinished making snapshots at %(date)s with %(CountSuccess)s snapshots of %(CountTotal)s possible.\n\n' % {
                'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S'),
                'CountSuccess': CountSuccess,
                'CountTotal': CountTotal
    }
    message += result
    message += "\nTotal snapshots created: " + str(TotalCreates)
    message += "\nTotal snapshots errors: " + str(CountErrors)
    message += "\nTotal snapshots deleted: " + str(TotalDeletes) + "\n"

    print '\n' + message + '\n'
    print result

    # SNS reporting
    if SNSARN:
        if errmsg:
            SNSClient.publish(TopicArn=SNSARN, Message='Error in processing volumes: ' + errmsg, Subject=AccountAliases+' - Error with AWS Snapshots')
        SNSClient.publish(TopicArn=SNSARN, Message=message, Subject=AccountAliases+' - Finished AWS snapshotting')

    logging.info(result)
