#!/usr/bin/env python
# tools needed
import json
import boto3
import logging
import time
import datetime
################################################################################
# Program meta -----------------------------------------------------------------
vers = "4.1"
ProgramName = "Onymer"
# AWS assumptions --------------------------------------------------------------
region = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=region)
EC2Client = boto3.client('ec2')
# Getting the Account ID needed to filter snapshots/AMIs
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
OIDS = [MyAWSID]
# Label being applied to anything not named and no longer attached, feel free to change
UnattachedLabel = "- UNATTACHED - "
# Used as a temp variable to identify things without names, change to whatever
UnNamedLabel = "(no name)"
# Don't touch these unless Amazon changes their labeling on marketplace snapshots!
GenericSnapshot = "Created"
################################################################################
# ------------------------------------------------------------------------------
# Support Functions
# ------------------------------------------------------------------------------


# debug helper, has nothing to do with actual renaming process
def logging_debug(proc, state, count):
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)
    d = ''
    d = datetime.datetime.now()
    print "[ > | - " + ProgramName + " - " + vers + " | ---> " + state + proc + " process <--- @ " + str(d) + " < ]"
    if "ending" in state:
        print "[ <!> ____ Processed: " + str(count) + " objects while running " + proc + " task _____ <!> ]"


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


# returns the instance Name|tag:value given an instanceID
def get_instance_name(ec2id):
    EC2Instance = ec2.Instance(ec2id)
    InstanceName = ''
    if EC2Instance.tags is not None:
        for tags in EC2Instance.tags:
            if tags["Key"] == 'Name':
                InstanceName = tags["Value"]
    else:
        InstanceName = UnNamedLabel
    return InstanceName


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


################################################################################
# ------------------------------------------------------------------------------
# Main Function
# ------------------------------------------------------------------------------
def lambda_handler(event, context):
    # counting objects tracking vars
    counter = name_counter()
    ############################################################################
    # --- EBS Volume rename process ---
    ############################################################################
    logging_debug(" volume rename ", "starting", 0)
    for Volume in ec2.volumes.all():
        VolumeName = get_tag_name(Volume.tags)
        if Volume.state == 'in-use':
            InstanceID = Volume.attachments[0]['InstanceId']
            InstanceMount = Volume.attachments[0]['Device']
            InstanceName =  get_instance_name(InstanceID)
            NewVolumeName = "[ " + InstanceName + " ]-" + InstanceMount
            VolumesNewName = [{'Key': 'Name','Value': NewVolumeName}]
            if VolumeName != NewVolumeName:
                print "-- [ Attached volume (" + Volume.id + ") re-named: " + NewVolumeName + " ] --"
                Volume.create_tags(Tags=VolumesNewName)
            else:
                print "--> Attached volume (" + Volume.id + ") named correctly, ('" + VolumeName + "') "
        if Volume.state == 'available':
            NewVolumeName = UnattachedLabel + VolumeName
            VolumesNewName = [{'Key': 'Name','Value': NewVolumeName}]
            if not VolumeName.startswith('- UNATTACHED -'):
                print "---- [ Unattached volume re-named: " + NewVolumeName + " ] ----"
                Volume.create_tags(Tags=VolumesNewName)
            else:
                print "----> Unttached volume (" + Volume.id + ") named correctly, ('" + VolumeName + "') "
        counter.add()
    logging_debug(" volume rename ", "ending", counter.number )
    ############################################################################
    # --- Interface rename process ---
    ############################################################################
    logging_debug(" interface rename ", "starting", 0)
    NetworkInterfaces = EC2Client.describe_network_interfaces()
    counter.reset()
    for Interface in NetworkInterfaces['NetworkInterfaces']:
        attached = ''
        InterfaceID = Interface['NetworkInterfaceId']
        named = "[ no attachment status? ]"
        ThisInterface = ''
        ThisInterface = ec2.NetworkInterface(InterfaceID)
        attached = ThisInterface.status
        if attached == "in-use":
            if 'InstanceId' in ThisInterface.attachment:
                attached_instance = ThisInterface.attachment['InstanceId']
                if attached_instance is not None:
                    named = get_instance_name(attached_instance)
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
        #print interface
        print " ---> [ " + ThisInterface.network_interface_id + " interface has been labeled: " + named + " ] "
        counter.add()
    logging_debug(" interface rename ", "ending", counter.number)
    ############################################################################
    # --- Snapshot labeling process ---
    ############################################################################
    logging_debug(" snapshot labeling ", "starting", 0)
    DescribeAllSnapshots = EC2Client.describe_snapshots(OwnerIds=OIDS)
    counter.reset()
    for Snapshot in DescribeAllSnapshots['Snapshots']:
        ThisSnapshot = ''
        NewSnapshotName=''
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
                            print "{ No volume with ID [" + SnapshotVolume +"] exists! }"
                            NewSnapshotName = "Old-" + SnapshotVolume + "-Snapshot-" + Dob
                        print "---> [ Labeling Snapshot: " + SnapshotID + " with: " + NewSnapshotName + " , as its new name tag ]"
                else:
                    NewSnapshotName = "CreateImage" + SnapshotVolume + "-Snapshot-" + Dob
                    print "---> [ Labeling Snapshot: " + SnapshotID + " : " + NewSnapshotName + " ]"
            else:
                NewSnapshotName = Desc
            print "---> [ Labeling Snapshot: " + SnapshotID + " : " + Desc + " ]"
            print "......currently named: " + SnapshotName + ", described as: " + Desc
            Snapshot_new_name = [{'Key': 'Name','Value': NewSnapshotName}]
            ThisSnapshot.create_tags(Tags=Snapshot_new_name)
        else:
            print "--> Snapshot: " + SnapshotID + " already has a name: " + SnapshotName
        counter.add()
    logging_debug(" snapshot labeling ", "ending", counter.number)
    ############################################################################
    # --- My AMI labeling process ---
    ############################################################################
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
            print "---> [ Labeling Image: " + ImageID + "  with: " + AMIName + " ]"
            print "......currently named: " + ImageName
            ImageNewName = [{'Key': 'Name','Value': AMIName}]
            ThisImage.create_tags(Tags=ImageNewName)
        else:
            print "--> AMI " + ImageID + "already has a name - " + ImageName
        counter.add()
    logging_debug(" My AMIs labeling ", "ending", counter.number)
    ############################################################################
    print "[ [ ----->>>>> [ [ [ Processed: " + str(counter.total) + " total objects ] ] ] <<<<<----- ] ]"
