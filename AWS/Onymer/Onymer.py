#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime


# Meta
vers = "4.2"
ProgramName = "Onymer"
Desc = "Tags EC2 assests (AMIs/EBSs/IFs/Snaps) based on EC2 Instance name tag"

# Define boto3 connections/variables
region = "us-east-1"
ec2 = boto3.resource("ec2", region_name=region)
EC2Client = boto3.client('ec2')
LClient = boto3.client('lambda')


# Lambda Relay function
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


# Getting the Account ID needed to filter snapshots/AMIs
MyAWSID = LR("get_account_ID")[1:-1]
OIDS = [str(MyAWSID)]


# Label applied to anything not named and un-attached
UnattachedLabel = "- UNATTACHED - "
# Used as a temp variable to identify things without names
UnNamedLabel = "(no name)"
# Don't touch this unless AWS changes their labeling on marketplace snapshots!
GenericSnapshot = "Created"


# debug helper, has nothing to do with actual renaming process
def log_output(data):
    # Set below to false to disable logging output
    ENABLE_LOGGING = True
    output = d = moreData = ''
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)

    state = data['state']
    proc = data['proc']
    count = str(data['count'])
    if data['data']:
        moreData = str(data['data'])

    d = str(datetime.datetime.now())

    if "starting" in state:
        output = "[ " + ProgramName + " - " + vers + " | " + state + " " + proc
        output += " process @ " + d + " ]"

    if "success" in state:
        output = "+ - " + proc + " - " + moreData

    if "problem" in state:
        output = "x - " + proc + " - " + moreData

    if "ending" in state:
        output = "[ <!> ____ Processed: " + count
        output += " objects while running " + proc + " tasks _____ <!> ]"

    if "error" in state:
        output = " X ERROR X " + proc + " - " + moreData
    if ENABLE_LOGGING:
        print(output)


# Iteration counter for naming passes / debugging
class name_counter:
        def __init__(self):
                self.number = 0
                self.total = 0

        def add(self):
                self.number += 1
                self.total += 1

        def reset(self):
                self.number = 0


# Main function
def lambda_handler(event, context):
    # Logging and counting objects tracking vars
    logData = {}
    counter = name_counter()
    logData['proc'] = logData['state'] = logData['data'] = ''
    logData['count'] = counter
    # EBS renaming process
    logData['state'] = "starting"
    logData['proc'] = "volume rename"
    log_output(logData)
    for Volume in ec2.volumes.all():
        VolumeName = LR("get_name_tag", {"Tags": Volume.tags})[1:-1]
        if Volume.state == 'in-use':
            InstanceID = Volume.attachments[0]['InstanceId']
            InstanceMount = Volume.attachments[0]['Device']
            InstanceName = LR("get_ec2_instance_name", {
                                                    "Region": region,
                                                    "EC2ID": InstanceID
                                                        })[1:-1]
            NewVolumeName = "[ " + InstanceName + " ]-" + InstanceMount
            VolumesNewName = [{'Key': 'Name', 'Value': NewVolumeName}]
            if VolumeName != NewVolumeName:
                logData['proc'] = "volumeID " + Volume.id + " renamed"
                logData['data'] = NewVolumeName
                Volume.create_tags(Tags=VolumesNewName)
            else:
                logData['proc'] = " volumeID " + Volume.id + " named correctly"
                logData['data'] = NewVolumeName
        if Volume.state == 'available':
            NewVolumeName = UnattachedLabel + VolumeName
            VolumesNewName = [{'Key': 'Name', 'Value': NewVolumeName}]
            if not VolumeName.startswith('- UNATTACHED -'):
                logData['proc'] = "unattached EBS " + Volume.id + " renamed"
                logData['data'] = "to:  " + NewVolumeName
                Volume.create_tags(Tags=VolumesNewName)
            else:
                logData['proc'] = "unattached EBS " + Volume.id
                logData['data'] = "is correctly named  " + NewVolumeName
        logData['state'] = "success"
        log_output(logData)
        counter.add()
    logData['state'] = "ending"
    logData['proc'] = "volume rename"
    logData['count'] = counter.number
    log_output(logData)
    # Network Interface rename process
    logData['state'] = "starting"
    logData['proc'] = "interface rename"
    log_output(logData)
    NetworkInterfaces = EC2Client.describe_network_interfaces()
    counter.reset()
    for Interface in NetworkInterfaces['NetworkInterfaces']:
        attached = ThisInterface = ''
        InterfaceID = Interface['NetworkInterfaceId']
        named = "[ no attachment status? ]"
        ThisInterface = ec2.NetworkInterface(InterfaceID)
        attached = ThisInterface.status
        if attached == "in-use":
            if 'InstanceId' in ThisInterface.attachment:
                EC2ID = ThisInterface.attachment['InstanceId']
                if EC2ID is not None:
                    named = LR("get_ec2_instance_name", {
                                                            "Region": region,
                                                            "EC2ID": EC2ID
                                                        })[1:-1]
                else:
                    named = "No-Instance-ID"
            else:
                try:
                    named = Interface['Description']
                except:
                    named = "non-ec2-network-interface"
        if attached == "available":
            named = UnattachedLabel
        InterfacesNewName = [{'Key': 'Name', 'Value': named}]
        ThisInterface.create_tags(Tags=InterfacesNewName)
        logData['proc'] = ThisInterface.network_interface_id + " now labeled "
        logData['data'] = named
        logData['state'] = "success"
        log_output(logData)
        counter.add()
    logData['state'] = "ending"
    logData['proc'] = "interface rename"
    logData['count'] = counter.number
    log_output(logData)
    # Snapshot labeling process
    logData['state'] = "starting"
    logData['proc'] = "snapshot labeling"
    log_output(logData)
    DescribeAllSnapshots = EC2Client.describe_snapshots(OwnerIds=OIDS)
    counter.reset()
    for Snapshot in DescribeAllSnapshots['Snapshots']:
        ThisSnapshot = NewSnapN = ''
        SnapID = Snapshot['SnapshotId']
        ThisSnapshot = ec2.Snapshot(SnapID)
        SnapshotOwner = ThisSnapshot.owner_id
        Desc = ThisSnapshot.description
        SnapshotTags = ThisSnapshot.tags
        Dob = ThisSnapshot.start_time
        Dob = Dob.strftime("%m/%d/%y")
        SnapshotName = LR("get_name_tag", {"Tags": SnapshotTags})[1:-1]
        SnapVolume = ThisSnapshot.volume_id
        if SnapshotName.startswith(UnNamedLabel):
            if Desc.startswith(GenericSnapshot):
                if SnapVolume is not None:
                    OriginalVolume = ec2.Volume(SnapVolume).id
                    if OriginalVolume is not None:
                        try:
                            vts = ec2.Volume(SnapVolume).tags
                            NewSnapN = LR("get_name_tag", {"Tags": vts})[1:-1]
                            logData['proc'] = " Labeling SnapID: " + SnapID
                            logData['data'] = " as  " + NewSnapN
                            logData['state'] = "success"

                        except:
                            logData['proc'] = "no volume with ID " + SnapVolume
                            logData['data'] = "exists"
                            logData['state'] = "error"
                            NewSnapN = "Old-" + SnapVolume + "-Snapshot-" + Dob

                else:
                    NewSnapN = "CreateImage" + SnapVolume + "-Snapshot-" + Dob
                    logData['proc'] = "Labeling SnapID: " + SnapID
                    logData['data'] = "as  " + NewSnapN
                    logData['state'] = "success"

            else:
                NewSnapN = Desc
                logData['proc'] = "Labeling Snapashot: " + SnapID + " : " + Desc
                logData['data'] = "as " + NewSnapN
                logData['state'] = "success"

            Snapshot_new_name = [{'Key': 'Name', 'Value': NewSnapN}]
            ThisSnapshot.create_tags(Tags=Snapshot_new_name)

        else:
            logData['proc'] = "Snapshot: " + SnapID
            logData['data'] = "already tagged as  " + SnapshotName
            logData['state'] = "success"

        log_output(logData)
        counter.add()
    logData['state'] = "ending"
    logData['proc'] = "snapshot labeling"
    logData['count'] = counter.number
    log_output(logData)
    # AMI labeling process
    logData['state'] = "starting"
    logData['proc'] = "Labeling owned AMIs"
    log_output(logData)
    DescribeAllImages = EC2Client.describe_images(Owners=OIDS)
    counter.reset()
    for Image in DescribeAllImages['Images']:
        ThisImage = ''
        ImageID = Image['ImageId']
        ThisImage = ec2.Image(ImageID)
        ThisImageOwner = ThisImage.owner_id
        AMIName = ThisImage.name
        ImageNewName = AMIName
        ImageTags = ThisImage.tags
        DOB = ThisImage.creation_date
        ImageName = LR("get_name_tag", {"Tags": ImageTags})[1:-1]
        if ImageName.startswith(UnNamedLabel) or len(ImageName) == 0:
            logData['proc'] = "Labeling Image: " + ImageId + " with"
            logData['data'] = AMIName + "current name: " + ImageName
            logData['state'] = "success"
            log_output(logData)
            ImageNewName = [{'Key': 'Name', 'Value': AMIName}]
            ThisImage.create_tags(Tags=ImageNewName)
        else:
            logData['proc'] = "AMI " + ImageID + " already has a name"
            logData['data'] = ImageName
            logData['state'] = "success"
            log_output(logData)
        counter.add()
    logData['state'] = "ending"
    logData['proc'] = "Labeling owned AMIs"
    logData['count'] = counter.number
    log_output(logData)
    # End
    logData['state'] = "ending"
    logData['proc'] = ProgramName + " " + vers
    logData['count'] = counter.total
    log_output(logData)
