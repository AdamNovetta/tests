#!/usr/bin/env python3
import boto3
import calendar
import json
import time
import sys
import logging
from datetime import datetime


# Program meta
vers = "1.3"
program_name = "Effingo"
desc = "Takes Daily/Weekly/Monthly snapshots of EBS volumes"


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
def logging_output():
    logging.basicConfig(level=logging.INFO)
    start_message = 'Started taking %(period)s snapshots at %(date)s' % {
        'period': period,
        'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S')
    }
    message += start_message + "\n\n"
    logging.info(start_message)


# Define boto3 connections/variables
region_name = "us-east-1"
lambda_client = boto3.client('lambda')
ec2 = boto3.resource("ec2", region_name=region_name)
EC2_client = boto3.client('ec2')


# Function to relay calls to other Lambda functions
def lambda_relay(function_name, payload=None):

    if payload is not None:
        pload = {"FunctionName": function_name, "FunctionPayload": payload}
    else:
        pload = {"FunctionName": function_name}

    lambda_output = lambda_client.invoke(
            FunctionName='lambda_function_relay',
            InvocationType='RequestResponse',
            Payload=json.dumps(pload)
            )
    data = lambda_output['Payload'].read().decode()
    return(data)


# Main function of the script
def lambda_handler(event, context):
    AWS_ID = lambda_relay("get_account_ID")[1:-1]
    account_name = lambda_relay("get_account_name")[1:-1]
    topic_name = "auto-snapshots"
    SNS_ARN = "arn:aws:sns:" + region_name + ":" + AWS_ID + ":" + topic_name
    del_list = []
    v_tags = ['DailySnapshot', 'WeeklySnapshot', 'MonthlySnapshot']
    message = errmsg = ""
    t_created = t_deleted = count_err = count_success = count_total = 0
    # Number of days to keep snapshot types
    keep_week = 3
    keep_day = 5
    keep_month = 2
    today = datetime.today()
    day = today.strftime('%-d')
    month = today.strftime('%-m')
    now = datetime.weekday(today)
    days_in_month = calendar.mdays[int(month)]
    tasks = v_tags

    # get the 'Name' tag out of the batch of tags sent
    def get_tag_name(TAGS):
        name_tag = ''
        if TAGS is not None:
            for tags in TAGS:
                if tags["Key"] == 'Name':
                    name_tag = tags["Value"]
        else:
            name_tag = "[ no name ]"
        return name_tag

    # Get the tags of a reouse that's passed to the func
    def get_resource_tags(resources):
        resource_ID = resources.id
        resource_tags = {}
        if resource_ID:
            tag_filter = [{
                'Name': 'resource-id',
                'Values': [resource_ID]
            }]
            tags = EC2_client.describe_tags(Filters=tag_filter)
            for tag in tags['Tags']:
                key = tag['Key']
                value = tag['Value']
                # Tags starting with 'aws:' are reserved for internal use
                # also don't double-tag snapshots with the scripts v_tags
                if not key.startswith("aws:") and str(key) not in str(v_tags):
                    resource_tags[key] = value
        return(resource_tags)

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
    if int(day) != days_in_month:
        tasks.remove('MonthlySnapshot')
    # run applicable tasks after filtering
    for task in tasks:
        period = ''
        tag_type = task
        if tag_type == 'DailySnapshot':
            period = 'day'
            date_suffix = today.strftime('%a')
        elif tag_type == 'WeeklySnapshot':
            period = 'week'
            date_suffix = today.strftime('%U')
        elif tag_type == 'MonthlySnapshot':
            period = 'month'
            date_suffix = month
        print("\nMaking snapshots for [ "+period+" ] tagged: " + tag_type+"\n")
        vols = ec2.volumes.filter(Filters=[{
                                            'Name': 'tag:' + tag_type,
                                            'Values': ["True"]
                                            }])
        for vol in vols:
            v_name = get_tag_name(vol.tags)
            print("Taking snapshot of: " + v_name + "   ID: " + vol.id + "\n")
            try:
                count_total += 1
                logging.info(vol)
                tags_volume = get_resource_tags(vol)

                description = str(period) + '_snapshot ' + str(vol.id)
                description += '_' + str(period) + '_' + str(date_suffix)
                description += ' by Lambda Effingo script at '
                description += str(today.strftime('%d-%m-%Y %H:%M:%S'))
                try:
                    current_snap = vol.create_snapshot(Description=description)
                    set_resource_tags(current_snap, tags_volume)

                    success_msg = "Snapshot created with description: "
                    success_msg += str(description) + " and tags: "
                    success_msg += str(tags_volume)

                    print(str(success_msg))
                    logging.info(str(success_msg))
                    t_created += 1

                except Exception:
                    print("Unexpected error:", sys.exc_info()[0])
                    logging.error(e)
                    pass

                print(
                    "\n Deleting the old snapshots for volume " + vol.id + "\n"
                    )

                snapshots = vol.snapshots.all()
                del_list = []
                for snap in snapshots:
                    sdesc = str(snap.description)
                    if (sdesc.startswith('week_snapshot') and period == 'week'):
                        del_list.append(snap)
                    elif (sdesc.startswith('day_snapshot') and period == 'day'):
                        del_list.append(snap)
                    elif (sdesc.startswith('month_snapshot') and period == 'month'):
                        del_list.append(snap)
                    else:
                        logging.info(
                            ' Skipping, not added to delete list: ' + sdesc
                            )
                for snap in del_list:
                    logging.info(snap)
                    logging.info(snap.start_time)

                def date_compare(snap1):
                    return snap1.start_time

                del_list.sort(key=date_compare)

                if period == 'day':
                    keep = keep_day
                elif period == 'week':
                    keep = keep_week
                elif period == 'month':
                    keep = keep_month
                delta = len(del_list) - keep
                for i in range(delta):
                    del_message = ' Deleting snapshot '
                    del_message += str(del_list[i].description)
                    logging.info(del_message)
                    del_list[i].delete()
                    t_deleted += 1
                time.sleep(3)
            except Exception:
                print("[LATE STAGE] Unexpected error: ", sys.exc_info())
                logging.error('Error in processing volume with id: ' + vol.id)
                errmsg += 'Error in processing volume with id: ' + vol.id
                count_err += 1
            else:
                count_success += 1

    result = '\nFinished making snapshots at '
    result += str(datetime.today().strftime('%d-%m-%Y %H:%M:%S'))
    result += ' with ' + str(count_success) + ' snapshots of '
    result += str(count_total) + ' possible.\n\n'

    message += result

    message += "\nTotal snapshots created: " + str(t_created)
    message += "\nTotal snapshots errors: " + str(count_err)
    message += "\nTotal snapshots deleted: " + str(t_deleted) + "\n"

    print('\n' + message + '\n')

    if SNS_ARN:
        if errmsg:
            err_SNS_subj = account_name + ' - Error with AWS Snapshots'
            err_msg = 'Error in processing volumes: ' + errmsg,
            lambda_relay("send_sns_message", {
                                                'SNS_ARN': SNS_ARN,
                                                'SNSMessage': err_msg,
                                                'sns_subj': err_SNS_subj
                                                })
        sns_subj = account_name + ' - Finished AWS snapshotting'
        lambda_relay("send_sns_message", {
                                            'SNS_ARN': SNS_ARN,
                                            'SNSMessage': message,
                                            'sns_subj': sns_subj
                                            })
    logging.info(result)
