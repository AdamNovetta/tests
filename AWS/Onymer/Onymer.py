#!/usr/bin/env python
'''
   Onymer - Lambda Function - V 3.0
--------------------------------------------------------------------------------
Purpose:
    This will rename all EBS volumes and network interfaces in the 'region = '
    to: [intance-name-tag]-/mount/point
    and interfaces are tagged with the instance name
    This will also rename all unattached to "- UNATTACHED -previousName"

Usage:
   - Run manually in Lambda or (recommended) on a triggered cron
   (suggeted hourly or sooner)
   - Update region and UnattachedLabel vars to suit your setup
   - Lambda Configuration:
        > runtime : python 2.7
        > handler : lambda_function.lambda_handler
        > role : (create a role with TODO/TODO )
        > description : Auto-names all EBS volumes and EC2 Network interfaces
        Advanced Configuration:
            > Memory : 128 MB
            > Timeout : 1 min (should be more than enough for 300-500 checked objects)
            > DQL Resource: None
            > VPC : No VPC (not needed really...)
            > Enable atrive tracing : unchecked (also no really needed)
            > KMS key : default

p.s. - comment out (or uncomment) print lines to alter logging output
'''
import json, boto3, logging, time, datetime
# Program meta 
vers = "3.0"
prog_name = "Onymer"

# AWS assumptions
region = "us-east-1"
ec2 = boto3.resource("ec2", region_name=region)
ec2_client = boto3.client('ec2')
UnattachedLabel = "- UNATTACHED - "

def logging_debug(proc, state):
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)
    d = ''
    d = datetime.datetime.now()
    print "[ > | - " + prog_name + " - " + vers + " | ---> " + state + proc + " process <--- @ " + str(d) + " < ]" 
def name_counter(ThisPass):
    ThisPass += 1
    return ThisPass
def get_instance_name(ec2id):
    # returns the instance Name|tag:value given an instanceID
    EC2Instance = ec2.Instance(ec2id)
    InstanceName = ''
    if EC2Instance.tags is not None:
        for tags in EC2Instance.tags:
            if tags["Key"] == 'Name':
                InstanceName = tags["Value"]
    else:
        InstanceName = "No-Name"
    return InstanceName
def lambda_handler(event, context):
    logging_debug(" volume rename ", "starting")
    counter = 0
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
        counter = name_counter(counter)
    logging_debug(" volume rename ", "ending")
    print " "
    print "[ <!> ____ Renamed/Checked: " + str(counter) + " volumes _____ <!> ]"
    print " "
    logging_debug(" interface rename ", "starting")
    network_interfaces = ec2_client.describe_network_interfaces()
    counter = 0
    for interfaces in network_interfaces:
        if "NetworkInterfaces" in interfaces:
            all_interfaces = network_interfaces[interfaces]
            for interface in all_interfaces:
                attached = ''
                named = "[ no attachment status? ]"
                THIS_INTERFACE = ''
                for metadata in interface:
                    key = metadata
                    value = interface[metadata]
                    if key == "NetworkInterfaceId":
                        interfaceID = value
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
                print " --> [ " + THIS_INTERFACE.network_interface_id + " interface has been labeled: " + named + " ] "
                counter = name_counter(counter)
    logging_debug(" volume rename ", "ending")
    print "[ <!> _____ Renamed/Checked: " + str(counter) + " interfaces _____ <!> ]"
