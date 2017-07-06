#!/usr/bin/env python
# tools needed
import boto3, calendar, tiime, sys, logging
from datetime import datetime
# Program meta -----------------------------------------------------------------
vers = "1.0"
prog_name = "Effingo"
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
    start_message = 'Started taking %(period)s snapshots at %(date)s' % {
        'period': period,
        'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S')
    }
    message += start_message + "\n\n"
    logging.info(start_message)

# AWS assumptions --------------------------------------------------------------
ec2_region_name = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=ec2_region_name)
ec2_client = boto3.client('ec2')
# ------------------------------------------------------------------------------
# The volumes tags we're looking for to establish the backup intervals
volume_tags = ['DailySnapshot', 'WeeklySnapshot', 'MonthlySnapshot']
# ------------------------------------------------------------------------------
# the Account ID for the AWS account this script is running in
My_AWS_ID = boto3.client('sts').get_caller_identity().get('Account')
sns_client = boto3.client('sns')
# Make sure the SNS topic below exists in your account, it enables script emails
SNS_topic_name = "auto-snapshots"
sns_arn = "arn:aws:sns:" + ec2_region_name +":" + My_AWS_ID + ":" + SNS_topic_name
# IAM check_acl_status
iam_client = boto3.client('iam')
# ------------------------------------------------------------------------------
# Get the tags of a reouse that's passed to the func
def get_resource_tags(resources):
    resource_id = resources.id
    resource_tags = {}
    if resource_id:
        tag_filter = [{
            'Name': 'resource-id',
            'Values': [resource_id]
        }]
        tags = ec2_client.describe_tags(Filters=tag_filter)
        for tag in tags['Tags']:
            key = tag['Key']
            value = tag['Value']
            # Tags starting with 'aws:' are reserved for internal use
            # also don't double-tag snapshots with the scripts volume_tags
            if not key.startswith('aws:') and key not in volume_tags:
                resource_tags[key] = value
    return resource_tags

# Set the tags of the resource from the tags passed to the func
def set_resource_tags(resource, tags):
    for tag_key, tag_value in tags.iteritems():
        if resource.tags is None:
            print 'Tagging %(resource_id)s with [%(tag_key)s: %(tag_value)s]' % {
                'resource_id': resource.id,
                'tag_key': tag_key,
                'tag_value': tag_value
            }
            resource.create_tags(Tags=[{'Key':tag_key, 'Value':tag_value}])
        elif tag_key not in resource.tags or resource.tags[tag_key] != tag_value:
            print 'Tagging %(resource_id)s with [%(tag_key)s: %(tag_value)s]' % {
                'resource_id': resource.id,
                'tag_key': tag_key,
                'tag_value': tag_value
            }
            resource.create_tags(Tags=[{'Key':tag_key, 'Value':tag_value}])

# get the 'Name' tag out of the batch of tags sent
def get_tag_name(TAGS):
    # returns the Name|tag:value given an instanceID
    Name_Tag = ''
    if TAGS is not None:
        for tags in TAGS:
            if tags["Key"] == 'Name':
                Name_Tag = tags["Value"]
    else:
        Name_Tag = UnNamedLabel
    return Name_Tag
# ------------------------------------------------------------------------------
# Main function of the script
def lambda_handler(event, context):
    # Message to return result via SNS
    message = ""
    errmsg = ""
    # Counters
    total_creates = 0
    total_deletes = 0
    count_errors = 0
    count_success = 0
    count_total = 0
    passes = 0
    # Number of snapshots to keep (the older ones are going to be deleted)
    keep_week = 5
    keep_day = 5
    keep_month = 2
    # time variables
    today = datetime.today()
    day = today.strftime('%-d')
    year = today.strftime('%Y')
    month = today.strftime('%-m')
    now = datetime.weekday(today)
    days_in_month = calendar.mdays[int(month)]
    # Test
    paginator = iam_client.get_paginator('list_account_aliases')
    for response in paginator.paginate():
            AccountAliases = response['AccountAliases']
    AccountAliases = str(AccountAliases)
    # all of the volume_tags are now tasks to be done (daily/weekly/monthly)
    tasks = volume_tags
    # deciding if we're running WeeklySnapshot / MonthlySnapshot
    # if it's day 5 (sat), we'll run a weekly backup
    if 5 != now:
        tasks.remove('WeeklySnapshot')
    # if it's the last day of the month, run monthly backups for tagged volumes too
    if int(day) != days_in_month:
        tasks.remove('MonthlySnapshot')
    # run the snapshot task(s)
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
        print "\n Running snapshots for [ " + period + " ] that match tag type: " + tag_type + "\n"
        vols = ec2.volumes.filter(Filters=[{'Name': 'tag:'+tag_type ,'Values': ["True"]}])
        for vol in vols:
            VolumeName = get_tag_name(vol.tags)
            print "Taking snapshot of: " + VolumeName + "   ID: " +vol.id + "\n"
            try:
                count_total += 1
                logging.info(vol)
                tags_volume = get_resource_tags(vol)
                description = '%(period)s_snapshot %(vol_id)s_%(period)s_%(date_suffix)s by Lambda Effingo script at %(date)s' % {
                    'period': period,
                    'vol_id': vol.id,
                    'date_suffix': date_suffix,
                    'date': today.strftime('%d-%m-%Y %H:%M:%S')
                }
                try:
                    current_snap = vol.create_snapshot(Description=description)
                    set_resource_tags(current_snap, tags_volume)
                    suc_message = 'Snapshot created with description: %s and tags: %s' % (str(description), str(tags_volume))
                    print(str(suc_message))
                    logging.info(str(suc_message))
                    total_creates += 1
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
                    keep = keep_day
                elif period == 'week':
                    keep = keep_week
                elif period == 'month':
                    keep = keep_month
                delta = len(deletelist) - keep
                for i in range(delta):
                    del_message = '     Deleting snapshot ' + deletelist[i].description
                    logging.info(del_message)
                    deletelist[i].delete()
                    total_deletes += 1
                time.sleep(3)
            except:
                print "[LATE STAGE] Unexpected error:", sys.exc_info()[0]
                logging.error('Error in processing volume with id: ' + vol.id)
                errmsg += 'Error in processing volume with id: ' + vol.id
                count_errors += 1
            else:
                count_success += 1
    result = '\nFinished making snapshots at %(date)s with %(count_success)s snapshots of %(count_total)s possible.\n\n' % {
                'date': datetime.today().strftime('%d-%m-%Y %H:%M:%S'),
                'count_success': count_success,
                'count_total': count_total
    }
    message += result
    message += "\nTotal snapshots created: " + str(total_creates)
    message += "\nTotal snapshots errors: " + str(count_errors)
    message += "\nTotal snapshots deleted: " + str(total_deletes) + "\n"

    print '\n' + message + '\n'
    print result

    # SNS reporting
    if sns_arn:
        if errmsg:
            sns_client.publish(TopicArn=sns_arn, Message='Error in processing volumes: ' + errmsg, Subject=AccountAliases+' - Error with AWS Snapshots')
        sns_client.publish(TopicArn=sns_arn, Message=message, Subject=AccountAliases+' - Finished AWS snapshotting')

    logging.info(result)
