#!/usr/bin/env python3
import json
import boto3
import logging
import time
import datetime


# Meta
Vers = "4.3.2"
ProgramName = "Onymer"
Desc = "Tags EC2 assests (AMIs/EBSs/IFs/Snaps) based on EC2 Instance name tag"

# Set below to False to disable logging output
ENABLE_LOGGING = True


# Define boto3 connections/variables
ec2 = boto3.resource("ec2")
# Getting the Account ID needed to filter snapshots/AMIs
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')
OIDS = [str(MyAWSID)]


# Label applied to anything not named and un-attached
unattached_label = "- UNATTACHED - "
# Used as a temp variable to identify things without names
no_name_label = "(no name)"
# Don't touch this unless AWS changes their labeling on marketplace snapshots!
generic_snapshot = "Created by CreateImage"


# Finds the AWS Tag:Name.value in a dict of tags
def get_tag_name(all_tags):
    if all_tags is not None:
        for tags in all_tags:
            if tags["Key"] == 'Name':
                name_tag = tags["Value"]
    else:
        name_tag = no_name_label
    return name_tag


# get all the instances and their name tags to avoid multiple lookups
class instance_ids:
    
    def __init__(self):
        self.names = {}
        instances = list(ec2.instances.all())
        for i in instances:
            self.names[i.id] = get_tag_name(ec2.Instance(i.id).tags)

    def name(self, id):
        if id in self.names:
            return(self.names[id])
        else:
            return(False)


# Iteration counter for naming passes / debugging
class counter:
        def __init__(self):
                self.number = 0
                self.total = 0

        def add(self):
                self.number += 1
                self.total += 1

        def reset(self):
                self.number = 0


# logging output class
class log_data:

    # create blank logging matrix and add counter
    def __init__(self):
        self.state = "starting"
        self.proc = ''
        self.data = ''
        self.count = counter()

    def starting(self, process):
        self.count.reset()
        self.state = "starting"
        self.proc = process
        print_log(self)

    def process(self, p, d, s):
        self.state = s
        self.proc = p
        self.data = d
        self.count.add()
        print_log(self)

    def ending(self, process):
        self.state = "ending"
        self.proc = process
        print_log(self)

    def finished(self):
        self.state = "finished"
        print_log(self)
        
    # debug helper, has nothing to do with actual renaming process
    def __str__(self):
        output = d = more_data = ''
        logger = logging.getLogger()
        # set below to DEBUG or INFO to see more errors in event log/console
        logger.setLevel(logging.WARNING)
    
        count = str(self.count.number)
        total = str(self.count.total)
        
        if self.data:
            more_data = str(self.data)
    
        d = str(datetime.datetime.now())
    
        if "0" in self.state:
            output = " X ERROR X " + self.proc + " - " + more_data
        if "1" in self.state:
            output = "+ - " + self.proc + " - " + more_data
        if "starting" in self.state:
            output = "[ " + ProgramName + " - " + Vers + " | " + self.state + " " + self.proc + " process @ " + d + " ]"
        if "ending" in self.state:
            output = "[ <!> ____ Processed: " + count + " objects during " + self.proc + " tasks _____ <!> ]\n"
        if "finished" in self.state:
            output = "\n[ <O> ____ Completed! Processed : " + total + " total objects in " + ProgramName + " run _____ <O> ]\n"

        return(output)
    
def print_log(logger_name):
    if ENABLE_LOGGING:
        print(logger_name)
    
# Main function
def lambda_handler(event, context):
    ec2_instances = instance_ids()
    log = log_data()
    # EBS renaming process
    log.starting("volume rename")
    for volume in ec2.volumes.all():
        volume_name = get_tag_name(volume.tags)
        if volume.state == 'in-use':
            instance_id = volume.attachments[0]['InstanceId']
            instance_mount = volume.attachments[0]['Device']
            instance_name = ec2_instances.name(instance_id)
            new_volume_name = "[ " + instance_name + " ]-" + instance_mount
            volumes_new_name = [{'Key': 'Name', 'Value': new_volume_name}]
            if volume_name != new_volume_name:
                log.process("EBS " + volume.id + " renamed", new_volume_name, "1")
                volume.create_tags(Tags=volumes_new_name)
            else:
                log.process(" EBS " + volume.id + " named correctly", new_volume_name, "1")
        if volume.state == 'available':
            new_volume_name = unattached_label + volume_name
            volumes_new_name = [{'Key': 'Name', 'Value': new_volume_name}]
            if not volume_name.startswith('- UNATTACHED -'):
                log.process("unattached EBS " + volume.id + " renamed", new_volume_name, "1")
                volume.create_tags(Tags=volumes_new_name)
            else:
                log.process("unattached EBS " + volume.id + "is correctly named", new_volume_name, "1")
    log.ending("volume rename")
    # Network Interface rename process
    log.starting("interface rename")
    for interface in ec2.network_interfaces.all():
        interface_new_name = "[ no attachment status? ]"
        if interface.status == "in-use":
            if 'InstanceId' in interface.attachment:
                ec2_id = interface.attachment['InstanceId']
                if ec2_id is not None:
                    interface_new_name = ec2_instances.name(ec2_id)
                else:
                    interface_new_name = "No-Instance-ID"
            else:
                try:
                    interface_new_name = Interface['Description']
                except:
                    interface_new_name = "non-ec2-network-interface"
        if interface.status == "available":
            interface_new_name = unattached_label
        interfaces_new_name = [{'Key': 'Name', 'Value': interface_new_name}]
        interface.create_tags(Tags=interfaces_new_name)
        log.process(" Interface " + interface.id + " labeled ", interface_new_name, "1")
    log.ending("interface rename")
    # Snapshot labeling process
    log.starting("snapshot labeling")
    all_snapshots = ec2.snapshots.filter(Filters=[{
                                                    'Name': 'owner-id',
                                                    'Values': OIDS
                                                }])
    for snapshot in all_snapshots:
        desc = snapshot.description
        dob = snapshot.start_time.strftime("%m/%d/%y")
        snap_name = get_tag_name(snapshot.tags)
        if snap_name.startswith(no_name_label) or len(snap_name) == 0:
            if snapshot.description.startswith(generic_snapshot):
                if snapshot.volume_id is not None:
                    try:
                        volume_tags = ec2.Volume(snapshot.volume_id).tags
                        new_snap_name =  get_tag_name(volume_tags)
                        status = "1"
                        proc = " Labeling SnapID: " + snapshot.id + " as "
                        data = new_snap_name
                    except:
                        status = "0"
                        proc = "no volume with ID " 
                        data = snapshot.volume_id
                        new_snap_name = "Old-" + snapshot.volume_id + "-Snapshot-" + dob
                else:
                    status = "1"
                    new_snap_name = "CreateImage" + snapshot.volume_id + "-Snapshot-" + dob
                    proc = "Labeling SnapID: " + snapshot.id + "as  "
                    data = new_snap_name
            else:
                status = "1"
                new_snap_name = desc
                proc = "Labeling Snapashot: " + snapshot.id + " : " + desc + " as "
                data = new_snap_name
            snapshots_new_name = [{'Key': 'Name', 'Value': new_snap_name}]
            snapshot.create_tags(Tags=snapshots_new_name)
        else:
            status = "1"
            proc = "Snapshot: " + snapshot.id + " already tagged as"
            data = snap_name
            
        log.process(proc, data, status)    
    log.ending("snapshot labeling")
    # AMI labeling process
    log.starting("Labeling owned AMIs")
    all_images = ec2.images.filter(Filters=[{
                                                'Name': 'owner-id',
                                                'Values': OIDS
                                            }])
    for image in all_images:
        AMI_name = image.name
        dob = image.creation_date[0:10]
        image_name = get_tag_name(image.tags)
        if image_name.startswith(no_name_label) or len(image_name) == 0:
            AMI_name += " " + dob
            proc = "Labeling Image: " + image.id + " with"
            data = AMI_name + " current name: " + image_name
            image_new_name = [{'Key': 'Name', 'Value': AMI_name}]
            image.create_tags(Tags=image_new_name)
        else:
            proc = "AMI " + image.id + " already has a name"
            data = image_name
            
        log.process(proc, data, "1")
    log.ending("Labeling owned AMIs")
    # End
    log.finished()
