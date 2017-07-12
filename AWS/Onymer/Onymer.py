#!/usr/bin/env python
# tools needed
import json, boto3, logging, time, datetime
# Program meta -----------------------------------------------------------------
vers = "4.0"
prog_name = "Onymer"
# AWS assumptions --------------------------------------------------------------
region = "us-east-1"
# functions to connect to AWS API
ec2 = boto3.resource("ec2", region_name=region)
ec2_client = boto3.client('ec2')
# Getting the Account ID needed to filter snapshots/AMIs
My_AWS_ID = boto3.client('sts').get_caller_identity().get('Account')
OIDS = [My_AWS_ID]
# Label being applied to anything not named and no longer attached
UnattachedLabel = "- UNATTACHED - "
# Used as a temp variable to identify things without names
UnNamedLabel = "(no name)"
# Don't touch these unless Amazon changes their labeling on marketplace snapshots!
GenericSnapshot = "Created"
# ------------------------------------------------------------------------------
# Support Functions
# ------------------------------------------------------------------------------
# debug helper, has nothing to do with actual renaming process
def logging_debug(proc, state):
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)
    d = ''
    d = datetime.datetime.now()
    print "[ > | - " + prog_name + " - " + vers + " | ---> " + state + proc + " process <--- @ " + str(d) + " < ]"

# Iteration counter for naming passes / debugging
def name_counter(ThisPass):
    ThisPass += 1
    return ThisPass

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
    Name_Tag = ''
    if TAGS is not None:
        for tags in TAGS:
            if tags["Key"] == 'Name':
                Name_Tag = tags["Value"]
    else:
        Name_Tag = UnNamedLabel
    return Name_Tag
# ------------------------------------------------------------------------------
# Main Function
# ------------------------------------------------------------------------------
def lambda_handler(event, context):
    # counting objects tracking vars
    counter = 0
    total_objects = 0
    # --- EBS Volume rename process ---
    logging_debug(" volume rename ", "starting")
    for volume in ec2.volumes.all():
        VolumeName = get_tag_name(volume.tags)
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
        if volume.state == 'available':
            NewVolumeName = UnattachedLabel + VolumeName
            volume_new_name = [{'Key': 'Name','Value': NewVolumeName}]
            if not VolumeName.startswith('- UNATTACHED -'):
                print "---- [ Unattached volume re-named: " + NewVolumeName + " ] ----"
                volume.create_tags(Tags=volume_new_name)
            else:
                print "----> Unttached volume (" + volume.id + ") named correctly, ('" + VolumeName + "') "
        counter = name_counter(counter)
    logging_debug(" volume rename ", "ending")
    print "[ <!> ____ Processed: " + str(counter) + " volumes _____ <!> ]"
    # --- Interface rename process ---
    logging_debug(" interface rename ", "starting")
    network_interfaces = ec2_client.describe_network_interfaces()
    total_objects = counter
    counter = 0
    for interface in network_interfaces['NetworkInterfaces']:
        attached = ''
        interfaceID = interface['NetworkInterfaceId']
        named = "[ no attachment status? ]"
        THIS_INTERFACE = ''
        THIS_INTERFACE = ec2.NetworkInterface(interfaceID)
        attached = THIS_INTERFACE.status
        if attached == "in-use":
            if 'InstanceId' in THIS_INTERFACE.attachment:
                attached_instance = THIS_INTERFACE.attachment['InstanceId']
                if attached_instance is not None:
                    named = get_instance_name(attached_instance)
                else:
                    named = "No-Instance-ID"
            else:
                named = "non-ec2-network-interface"
        if attached == "available":
            named = UnattachedLabel
        Interface_new_name = [{'Key': 'Name','Value': named}]
        THIS_INTERFACE.create_tags(Tags=Interface_new_name)
        #print interface
        print " ---> [ " + THIS_INTERFACE.network_interface_id + " interface has been labeled: " + named + " ] "
        counter = name_counter(counter)
    logging_debug(" interface rename ", "ending")
    print "[ <!> _____ Processed: " + str(counter) + " interfaces _____ <!> ]"
    # --- Snapshot labeling process ---
    ############################################################################
    logging_debug(" snapshot labeling ", "starting")
    describe_all_snapshots = ec2_client.describe_snapshots(OwnerIds=OIDS)
    total_objects = total_objects + counter
    counter = 0
    for SNAPSHOT in describe_all_snapshots['Snapshots']:
        THIS_SNAPSHOT = ''
        ALL_TAGS = ''
        NewSnapshotName=''
        SnapshotID = SNAPSHOT['SnapshotId']
        THIS_SNAPSHOT = ec2.Snapshot(SnapshotID)
        SnapshotOwner = THIS_SNAPSHOT.owner_id
        Desc = THIS_SNAPSHOT.description
        SNAPSHOT_TAGS = THIS_SNAPSHOT.tags
        Dob = THIS_SNAPSHOT.start_time
        Dob = Dob.strftime("%m/%d/%y")
        SnapshotName = get_tag_name(SNAPSHOT_TAGS)
        SnapshotVolume = THIS_SNAPSHOT.volume_id
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
            THIS_SNAPSHOT.create_tags(Tags=Snapshot_new_name)
        else:
            print "--> Snapshot: " + SnapshotID + " already has a name: " + SnapshotName
        counter = name_counter(counter)
    ############################################################################
    logging_debug(" snapshot labeling ", "ending")
    print "[ <!> _____ Processed: " + str(counter) + " snapshots _____ <!> ]"
    # --- My AMI labeling process ---
    logging_debug(" My AMI labeling ", "starting")
    describe_all_images = ec2_client.describe_images(Owners=OIDS)
    total_objects = total_objects + counter
    counter = 0
    for IMAGE in describe_all_images['Images']:
        THIS_IMAGE = ''
        ALL_TAGS = ''
        ImageID = IMAGE['ImageId']
        THIS_IMAGE = ec2.Image(ImageID)
        THIS_IMAGES_OWNER = THIS_IMAGE.owner_id
        AMI_name = THIS_IMAGE.name
        Image_new_name = AMI_name
        IMAGE_TAGS = THIS_IMAGE.tags
        DOB = THIS_IMAGE.creation_date
        ImageName = get_tag_name(IMAGE_TAGS)
        if ImageName.startswith(UnNamedLabel) or len(ImageName) == 0:
            print "---> [ Labeling Image: " + ImageID + "  with: " + AMI_name + " ]"
            print "......currently named: " + ImageName
            Image_new_name = [{'Key': 'Name','Value': AMI_name}]
            THIS_IMAGE.create_tags(Tags=Image_new_name)
        else:
            print "--> AMI " + ImageID + "already has a name - " + ImageName
        counter = name_counter(counter)
    logging_debug(" My AMI labeling ", "ending")
    print "[ <!> _____ Processed: " + str(counter) + " AMIs _____ <!> ]"
    total_objects = total_objects + counter
    print "[ [ ----->>>>> [ [ [ Processed:" + str(total_objects) + " total objects ] ] ] <<<<<----- ] ]"
