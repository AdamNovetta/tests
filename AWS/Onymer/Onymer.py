#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime


# Program meta -----------------------------------------------------------------
vers = "4.1"
ProgramName = "Onymer"
Desc = "Tags/Names EC2 assests (AMIs/EBSs/IFs/Snaps) based on EC2 Instance name"

# Define boto3 connections/variables
region = "us-east-1"
ec2 = boto3.resource("ec2", region_name=region)
EC2Client = boto3.client('ec2')
LClient = boto3.client('lambda')


def LR(function_name, payload=None):

    if payload != None:
        pload = { "FunctionName": function_name, "FunctionPayload": payload }
    else:
        pload = { "FunctionName": function_name }

    LambdaRelayOutput = LClient.invoke(
            FunctionName='lambda_function_relay',
            InvocationType='RequestResponse',
            Payload=json.dumps(pload)
            )
    data = LambdaRelayOutput['Payload'].read().decode()
    return(data)

# Getting the Account ID needed to filter snapshots/AMIs
MyAWSID = LR("get_account_ID")[1:-1]
OIDS = [MyAWSID]


# Label applied to anything not named and un-attached
UnattachedLabel = "- UNATTACHED - "
# Used as a temp variable to identify things without names
UnNamedLabel = "(no name)"
# Don't touch this unless AWS changes their labeling on marketplace snapshots!
GenericSnapshot = "Created"


# debug helper, has nothing to do with actual renaming process
def logging_debug(proc, state, count):
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)
    endoutput = output = d = ''
    d = datetime.datetime.now()
    output = "[ > | - " + ProgramName + " - " + vers + " | ---> " + state + proc
    output += " process <--- @ " + str(d) + " < ]"
    print(output)
    if "ending" in state:
        endoutput = "[ <!> ____ Processed: " + str(count)
        endoutput += " objects while running " + proc + " task _____ <!> ]"
        print(endoutput)


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


# Finds the AWS Tag:Name.value in a dict of tags
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


# Main function
def lambda_handler(event, context):
    # counting objects tracking vars
    counter = name_counter()
    # EBS renaming process
    logging_debug(" volume rename ", "starting", 0)
    for Volume in ec2.volumes.all():
        VolumeName = LR("get_name_tag", { "Tags" : Volume.tags })[1:-1]
        if Volume.state == 'in-use':
            InstanceID = Volume.attachments[0]['InstanceId']
            InstanceMount = Volume.attachments[0]['Device']
            InstanceName = LR("get_ec2_instance_name", {
                                                    "Region": region,
                                                    "EC2ID": InstanceID
                                                })[1:-1]
            NewVolumeName = "[ " + InstanceName + " ]-" + InstanceMount
            VolumesNewName = [{'Key': 'Name','Value': NewVolumeName}]
            if VolumeName != NewVolumeName:
                print("-- [ Attached volume (" + Volume.id + ") re-named: " + NewVolumeName + " ] --")
                Volume.create_tags(Tags=VolumesNewName)
            else:
                print("--> Attached volume (" + Volume.id + ") named correctly, ('" + VolumeName + "') ")
        if Volume.state == 'available':
            NewVolumeName = UnattachedLabel + VolumeName
            VolumesNewName = [{'Key': 'Name','Value': NewVolumeName}]
            if not VolumeName.startswith('- UNATTACHED -'):
                print("---- [ Unattached volume re-named: " + NewVolumeName + " ] ----")
                Volume.create_tags(Tags=VolumesNewName)
            else:
                print("----> Unttached volume (" + Volume.id + ") named correctly, ('" + VolumeName + "') ")
        counter.add()
    logging_debug(" volume rename ", "ending", counter.number )
    # Network Interface rename process
    logging_debug(" interface rename ", "starting", 0)
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
                attached_instance = ThisInterface.attachment['InstanceId']
                if attached_instance is not None:
                    named = LR("get_ec2_instance_name", {
                                                            "Region": region,
                                                            "EC2ID": InstanceID
                                                        })
                else:
                    named = "No-Instance-ID"
            else:
                try:
                    named = Interface['Description']
                except:
                    named = "non-ec2-network-interface"
        if attached == "available":
            named = UnattachedLabel
        InterfacesNewName = [{'Key': 'Name','Value': named}]
        ThisInterface.create_tags(Tags=InterfacesNewName)
        # Print interface
        print(" ---> [ " + ThisInterface.network_interface_id + " interface has been labeled: " + named + " ] ")
        counter.add()
    logging_debug(" interface rename ", "ending", counter.number)
    # Snapshot labeling process
    logging_debug(" snapshot labeling ", "starting", 0)
    DescribeAllSnapshots = EC2Client.describe_snapshots(OwnerIds=OIDS)
    counter.reset()
    for Snapshot in DescribeAllSnapshots['Snapshots']:
        ThisSnapshot = NewSnapshotName = ''
        SnapshotID = Snapshot['SnapshotId']
        ThisSnapshot = ec2.Snapshot(SnapshotID)
        SnapshotOwner = ThisSnapshot.owner_id
        Desc = ThisSnapshot.description
        SnapshotTags = ThisSnapshot.tags
        Dob = ThisSnapshot.start_time
        Dob = Dob.strftime("%m/%d/%y")
        SnapshotName = get_tag_name(SnapshotTags)
        SnapshotVolume = ThisSnapshot.volume_id
        if SnapshotName.startswith(UnNamedLabel):
            if Desc.startswith(GenericSnapshot):
                if SnapshotVolume is not None:
                    OriginalVolume = ec2.Volume(SnapshotVolume).id
                    if OriginalVolume is not None:
                        try:
                            NewSnapshotName = get_tag_name(ec2.Volume(SnapshotVolume).tags)
                        except:
                            print("{ No volume with ID [" + SnapshotVolume +"] exists! }")
                            NewSnapshotName = "Old-" + SnapshotVolume + "-Snapshot-" + Dob
                        print("---> [ Labeling Snapshot: " + SnapshotID + " with: " + NewSnapshotName + " , as its new name tag ]")
                else:
                    NewSnapshotName = "CreateImage" + SnapshotVolume + "-Snapshot-" + Dob
                    print("---> [ Labeling Snapshot: " + SnapshotID + " : " + NewSnapshotName + " ]")
            else:
                NewSnapshotName = Desc
            print("---> [ Labeling Snapshot: " + SnapshotID + " : " + Desc + " ]")
            print("......currently named: " + SnapshotName + ", described as: " + Desc)
            Snapshot_new_name = [{'Key': 'Name','Value': NewSnapshotName}]
            ThisSnapshot.create_tags(Tags=Snapshot_new_name)
        else:
            print("--> Snapshot: " + SnapshotID + " already has a name: " + SnapshotName)
        counter.add()
    logging_debug(" snapshot labeling ", "ending", counter.number)
    # AMI labeling process
    logging_debug(" My AMIs labeling ", "starting", 0)
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
        ImageName = get_tag_name(ImageTags)
        if ImageName.startswith(UnNamedLabel) or len(ImageName) == 0:
            print("---> [ Labeling Image: " + ImageID + "  with: " + AMIName + " ]")
            print("......currently named: " + ImageName)
            ImageNewName = [{'Key': 'Name','Value': AMIName}]
            ThisImage.create_tags(Tags=ImageNewName)
        else:
            print("--> AMI " + ImageID + "already has a name - " + ImageName)
        counter.add()
    logging_debug(" My AMIs labeling ", "ending", counter.number)
    # End reporting process
    print("[ [ ----->>>>> [ [ [ Processed: " + str(counter.total) + " total objects ] ] ] <<<<<----- ] ]")
