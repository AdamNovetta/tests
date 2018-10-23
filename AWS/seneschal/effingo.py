#!/usr/bin/env python3
import boto3
import calendar
import json
import time
import sys
import logged
import aws_tools
from datetime import datetime


# program meta
vers = "1.3"
program_name = "Effingo"
desc = "Takes Daily/Weekly/Monthly snapshots of EBS volumes"


# boto3 connections/variables
ec2 = aws_tools.aws_resource('ec2')
ec2_client = aws_tools.aws_client('ec2')


# Main function of the script
def lambda_handler(event, context):

    if event['logging']:
        log = logged.log_data(program_name, vers, event['logging'])
    else:
        log = logged.log_data(program_name, vers, False)

    aws_id = aws_tools.get_account_id()
    account_name = aws_tools.get_account_name()
    region_name = "us-east-1"
    topic_name = "auto-snapshots"
    sns_arn = "arn:aws:sns:" + region_name + ":" + aws_id + ":" + topic_name
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

    # Get the tags of a resource
    def get_resource_tags(resources):
        resource_ID = resources.id
        resource_tags = {}
        if resource_ID:
            tag_filter = [{
                'Name': 'resource-id',
                'Values': [resource_ID]
            }]
            tags = ec2_client.describe_tags(Filters=tag_filter)
            for tag in tags['Tags']:
                key = tag['Key']
                value = tag['Value']
                if not key.startswith("aws:") and str(key) not in str(v_tags):
                    resource_tags[key] = value
        return(resource_tags)

    # Set the tags of the resource from the tags passed to the func
    def set_resource_tags(resource, tags):
        for k, v in tags.items():
            if resource.tags is None:
                resource.create_tags(Tags=[{'Key': k, 'Value': v}])

            elif tag_key not in resource.tags or resource.tags[k] != v:
                resource.create_tags(Tags=[{'Key': k, 'Value': v}])

    # Only run 'WeeklySnapshot' on day 5 - Saturday
    if 5 != now:
        tasks.remove('WeeklySnapshot')

    # Only run the 'MonthlySnapshot' on the last day of the month
    if int(day) != days_in_month:
        tasks.remove('MonthlySnapshot')

    # run applicable snapshot-tasks after filtering for todays date
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
        process_message = "Snapshots for " + period + " tagged: " + tag_type
        log.starting(process_message)
        vols = ec2.volumes.filter(Filters=[{
                                            'Name': 'tag:' + tag_type,
                                            'Values': ["True"]
                                            }])
        # cycle volumes and snapshot them, delete their old copies
        for vol in vols:
            v_name = aws_tools.get_tag_name(vol.tags)
            log.subroutine(" EBS Volume: " + v_name + " snapping...")
            #try:
            count_total += 1
            tags_volume = get_resource_tags(vol)

            description = str(period) + '_snapshot ' + str(vol.id)
            description += '_' + str(period) + '_' + str(date_suffix)
            description += ' by Lambda ' + program_name + ' script at '
            description += str(today.strftime('%d-%m-%Y %H:%M:%S'))
            try:
                current_snap = vol.create_snapshot(Description=description)
                set_resource_tags(current_snap, tags_volume)

                success_msg = "Snapshot created with description: "
                success_msg += str(description) + " and tags: "
                success_msg += str(tags_volume)

                log.info("1", success_msg)
                t_created += 1

            except Exception:
                log.info("0", sys.exc_info()[0])
                pass

            # Collect and sort all snapshots to remove the old ones
            log.info("info", "Removing old snapshots for volume " + v_name)
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
                    log.info("info", "Skipping " + sdesc)
            for snap in del_list:
                log.info("info", str(snap) + str(snap.start_time))

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
                log.info("info", del_message)
                del_list[i].delete()
                t_deleted += 1
            time.sleep(4)
            #except Exception:
            #    error_details = 'Error in processing volume id: ' + vol.id + "\n"
            #    log.info("0", error_details)
            #    errmsg += error_details
            #    count_err += 1
            #else:
            count_success += 1

    log.ending(process_message)

    result = '\nFinished making snapshots at '
    result += str(datetime.today().strftime('%d-%m-%Y %H:%M:%S'))
    result += ' with ' + str(count_success) + ' snapshots of '
    result += str(count_total) + ' possible.\n\n'

    message += result

    message += "\nTotal snapshots created: " + str(t_created)
    message += "\nTotal snapshots errors: " + str(count_err)
    message += "\nTotal snapshots deleted: " + str(t_deleted) + "\n"


    if sns_arn:
        if errmsg:
            err_sns_subj = account_name + ' - Error with AWS Snapshots'
            err_msg = 'Error in processing volumes: \n' + errmsg
            aws_tools.send_sns({
                                'sns_arn': sns_arn,
                                'sns_message': err_msg,
                                'sns_subject': err_sns_subj
                            })
        sns_subj = account_name + ' - Finished AWS snapshotting'
        aws_tools.send_sns({
                        'sns_arn': sns_arn,
                        'sns_message': message,
                        'sns_subject': sns_subj
                    })
    log.info("info", result)
    log.finished()
