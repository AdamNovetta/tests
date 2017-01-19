#!/usr/bin/env python
'''
   Onynmer - Lambda Function - V 1.0
--------------------------------------------------------------------------------
Copyright 2016 Novetta, Inc.
P&T Infrastructure or its affiliates. All Rights Reserved.

  This file is distributed on an AS IS BASIS, WITHOUT WARRANTIES OR CONDITIONS
  OF ANY KIND, express or implied.

Support: PT-INFRASTRUCTURE@novetta.com
--------------------------------------------------------------------------------
Purpose:
    This will rename all EBS volume in the 'region = '
    to: [intance-name-tag]-/mount/point
    and renames all unattached volumes to "- UNATTACHED -previousEBSname"

Usage:
   - Run manually in Lambda or (recommended) on a triggered cron
   (suggeted hourly or sooner)
   - Update region and UnattachedLabel vars to suit your setup

p.s. - comment out (or uncomment) print lines to alter logging output
'''
import json, boto3, logging, time, datetime

region = "us-east-1"
ec2 = boto3.resource("ec2", region_name=region)
UnattachedLabel = "- UNATTACHED - "

def get_instance_name(ec2id):
    EC2Instance = ec2.Instance(ec2id)
    InstanceName = ''
    for tags in EC2Instance.tags:
        if tags["Key"] == 'Name':
            InstanceName = tags["Value"]
    return InstanceName

def lambda_handler(event, context):
    for volume in ec2.volumes.all():
        if volume.tags is not None:
            for tags in volume.tags:
                if tags["Key"] == 'Name':
                    VolumeName = tags["Value"]
        else:
            VolumeName = ''
        if volume.state == 'in-use':
            InstanceID = volume.attachments[0]['InstanceId']
            InstanceMount = volume.attachments[0]['Device']
            InstanceName =  get_instance_name(InstanceID)
            NewVolumeName = "[ " + InstanceName + " ]-" + InstanceMount
            volume_new_name = [{'Key': 'Name','Value': NewVolumeName}]
            if VolumeName != NewVolumeName:
                print "-- [ Attached volume (" + volume.id + ") re-named: " + NewVolumeName + " ] --"
                volume.create_tags(Tags=volume_new_name)
            else:
                print "--> Attached volume (" + volume.id + ") named correctly, ('" + VolumeName + "') "
            # Diagnostic output check:
            #print "[ Volume ID: " + volume.id + " -- Volume Name: " + VolumeName +" -- is attached to: " + InstanceID + " -- Named: " + InstanceName + " -- Mounted: " + InstanceMount + " ] "
        if volume.state == 'available':
            NewVolumeName = UnattachedLabel + VolumeName
            volume_new_name = [{'Key': 'Name','Value': NewVolumeName}]
            if not VolumeName.startswith('- UNATTACHED -'):
                print "---- [ Unattached volume re-named: " + NewVolumeName + " ] ----"
                volume.create_tags(Tags=volume_new_name)
            else:
                print "----> Unttached volume (" + volume.id + ") named correctly, ('" + VolumeName + "') "
        print " "
