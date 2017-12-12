#!/usr/bin/env python
import boto3
import calendar
import json
import time
import sys
import logging
from datetime import datetime


# Program meta
vers = "1.2"
ProgramName = "Effingo"
Desc = "Takes Daily/Weekly/Monthly snapshots of EBS volumes"


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
def logging_output():
    logging.basicConfig(level=logging.INFO)
    StartMessage = 'Started taking %(period)s snapshots at %(date)s' % {
        'period': period,
        'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S')
    }
    message += StartMessage + "\n\n"
    logging.info(StartMessage)


# Define boto3 connections/variables
EC2RegionName = "us-east-1"
LClient = boto3.client('lambda')
ec2 = boto3.resource("ec2", region_name=EC2RegionName)
EC2Client = boto3.client('ec2')


# Function to relay calls to other Lambda functions
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


# Main function of the script
def lambda_handler(event, context):
    MyAWSID = LR("get_account_ID")[1:-1]
    AccountName = LR("get_account_name")[1:-1]
    SNSTopicName = "auto-snapshots"
    SNSARN = "arn:aws:sns:" + EC2RegionName + ":" + MyAWSID + ":" + SNSTopicName
    deletelist = []
    VolumeTags = ['DailySnapshot', 'WeeklySnapshot', 'MonthlySnapshot']
    message = errmsg = ""
    TotalCreates = TotalDeletes = CountErrors = CountSuccess = CountTotal = 0
    # Number of days to keep snapshot types
    KeepWeek = 3
    KeepDay = 5
    KeepMonth = 2
    today = datetime.today()
    day = today.strftime('%-d')
    month = today.strftime('%-m')
    now = datetime.weekday(today)
    DaysInMonth = calendar.mdays[int(month)]
    tasks = VolumeTags

    # get the 'Name' tag out of the batch of tags sent
    def get_tag_name(TAGS):
        NameTag = ''
        if TAGS is not None:
            for tags in TAGS:
                if tags["Key"] == 'Name':
                    NameTag = tags["Value"]
        else:
            NameTag = UnNamedLabel
        return NameTag

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
                if not key.startswith("aws:") and str(key) not in str(VolumeTags):
                    ResourceTags[key] = value
        return(ResourceTags)

    # Set the tags of the resource from the tags passed to the func
    def set_resource_tags(resource, tags):
        for TKey, TValue in tags.items():
            if resource.tags is None:
                print(
                        'Tagging ' + resource.id +
                        ' with [' + TKey + ': ' + TValue + ']'
                    )
                resource.create_tags(Tags=[{
                                            'Key': TKey,
                                            'Value': TValue
                                            }])
            elif TKey not in resource.tags or resource.tags[TKey] != TValue:
                print(
                        'Tagging ' + resource.id +
                        ' with [' + TKey + ': ' + TValue + ']'
                    )
                resource.create_tags(Tags=[{'Key': TKey, 'Value': TValue}])

    # Only run 'WeeklySnapshot' on day 5 - Saturday
    if 5 != now:
        tasks.remove('WeeklySnapshot')
    # Only run the 'MonthlySnapshot' on the last day of the month
    if int(day) != DaysInMonth:
        tasks.remove('MonthlySnapshot')
    # run applicable tasks after filtering
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
        print("\nRunning snapshots job [ "+period+" ] tagged: "+TagType+"\n")
        vols = ec2.volumes.filter(Filters=[{
                                            'Name': 'tag:' + TagType,
                                            'Values': ["True"]
                                            }])
        for vol in vols:
            VolumeName = get_tag_name(vol.tags)
            print("Taking snapshot of: "+VolumeName+"   ID: "+vol.id + "\n")
            try:
                CountTotal += 1
                logging.info(vol)
                TagsVolume = get_resource_tags(vol)

                description = str(period) + '_snapshot ' + str(vol.id)
                description += '_' + str(period) + '_' + str(DateSuffix)
                description += ' by Lambda Effingo script at '
                description += str(today.strftime('%d-%m-%Y %H:%M:%S'))
                try:
                    CurrentSnap = vol.create_snapshot(Description=description)
                    set_resource_tags(CurrentSnap, TagsVolume)

                    SuccessMessage = "Snapshot created with description: "
                    SuccessMessage += str(description) + " and tags: "
                    SuccessMessage += str(TagsVolume)

                    print(str(SuccessMessage))
                    logging.info(str(SuccessMessage))
                    TotalCreates += 1

                except BaseException as e:
                    print("Unexpected error:", sys.exc_info()[0])
                    logging.error(e)
                    pass

                print(
                    "\n Deleting the old snapshots for volume" + vol.id + "\n"
                    )

                snapshots = vol.snapshots.all()
                deletelist = []
                for snap in snapshots:
                    sdesc = str(snap.description)
                    if (sdesc.startswith('week_snapshot') and period == 'week'):
                        deletelist.append(snap)
                    elif (sdesc.startswith('day_snapshot') and period == 'day'):
                        deletelist.append(snap)
                    elif (sdesc.startswith('month_snapshot') and period == 'month'):
                        deletelist.append(snap)
                    else:
                        logging.info(
                            ' Skipping, not added to deletelist: ' + sdesc
                            )
                for snap in deletelist:
                    logging.info(snap)
                    logging.info(snap.start_time)

                def date_compare(snap1):
                    return snap1.start_time

                deletelist.sort(key=date_compare)

                if period == 'day':
                    keep = KeepDay
                elif period == 'week':
                    keep = KeepWeek
                elif period == 'month':
                    keep = KeepMonth
                delta = len(deletelist) - keep
                for i in range(delta):
                    DeleteMessage = ' Deleting snapshot '
                    DeleteMessage += str(deletelist[i].description)
                    logging.info(DeleteMessage)
                    deletelist[i].delete()
                    TotalDeletes += 1
                time.sleep(3)
            except:
                print("[LATE STAGE] Unexpected error:", sys.exc_info())
                logging.error('Error in processing volume with id: ' + vol.id)
                errmsg += 'Error in processing volume with id: ' + vol.id
                CountErrors += 1
            else:
                CountSuccess += 1

    result = '\nFinished making snapshots at '
    result += str(datetime.today().strftime('%d-%m-%Y %H:%M:%S'))
    result += ' with ' + str(CountSuccess) + ' snapshots of ' + str(CountTotal)
    result += ' possible.\n\n'

    message += result

    message += "\nTotal snapshots created: " + str(TotalCreates)
    message += "\nTotal snapshots errors: " + str(CountErrors)
    message += "\nTotal snapshots deleted: " + str(TotalDeletes) + "\n"

    print('\n' + message + '\n')

    if SNSARN:
        if errmsg:
            ErrorSNSSubject = AccountName + ' - Error with AWS Snapshots'
            ErrorMessage = 'Error in processing volumes: ' + errmsg,
            LR("send_sns_message", {
                                'SNSARN': SNSARN,
                                'SNSMessage': ErrorMessage,
                                'SNSSubject': ErrorSNSSubject
                            })
        SNSSubject = AccountName + ' - Finished AWS snapshotting'
        LR("send_sns_message", {
                            'SNSARN': SNSARN,
                            'SNSMessage': message,
                            'SNSSubject': SNSSubject
                        })
    logging.info(result)
