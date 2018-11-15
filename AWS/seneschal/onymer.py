#!/usr/bin/env python3
import json
import time
import datetime
import logged
import aws_tools


# Meta
vers = "4.3.2"
program_name = "Onymer"
desc = "Tags EC2 assests (AMIs/EBSs/IFs/Snaps) based on EC2 Instance name tag"


# Main function
def main(event):
    # Define boto3 connections/variables
    ec2 = aws_tools.aws_resource('ec2')

    # Getting the Account ID needed to filter snapshots/AMIs
    my_aws_id = event['account_info']['id']
    oids = [str(my_aws_id)]

    # Label applied to anything not named and un-attached
    unattached_label = "- UNATTACHED - "

    # Used as a temp variable to identify things without names
    no_name_label = "(no name)"

    # Don't touch this unless AWS changes labeling on marketplace snapshots!
    generic_snapshot = "Created by CreateImage"
    ec2_instances = aws_tools.instance_ids()
    if event['logging']:
        log = logged.log_data(program_name, vers, event['logging'])
    else:
        log = logged.log_data(program_name, vers, False)

    # EBS renaming process
    log.starting("volume rename")
    for volume in ec2.volumes.all():
        volume_name = aws_tools.get_tag_name(volume.tags)
        if volume.state == 'in-use':
            instance_id = volume.attachments[0]['InstanceId']
            instance_mount = volume.attachments[0]['Device']
            instance_name = ec2_instances.name(instance_id)
            new_volume_name = "[ " + instance_name + " ]-" + instance_mount
            volumes_new_name = [{'Key': 'Name', 'Value': new_volume_name}]
            if volume_name != new_volume_name:
                log.process(
                            "EBS " + volume.id + " renamed",
                            "1",
                            new_volume_name
                            )
                volume.create_tags(Tags=volumes_new_name)
            else:
                log.process(
                            " EBS " + volume.id + " named correctly",
                            "1",
                            new_volume_name
                            )
        if volume.state == 'available':
            new_volume_name = unattached_label + volume_name
            volumes_new_name = [{'Key': 'Name', 'Value': new_volume_name}]
            if not volume_name.startswith('- UNATTACHED -'):
                log.process(
                            "unattached EBS " + volume.id + " renamed",
                            "1",
                            new_volume_name
                            )
                volume.create_tags(Tags=volumes_new_name)
            else:
                log.process(
                            "unattached EBS " + volume.id + " correctly named",
                            "1",
                            new_volume_name
                            )
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
                except Exception:
                    interface_new_name = "non-ec2-network-interface"
        if interface.status == "available":
            interface_new_name = unattached_label
        interfaces_new_name = [{'Key': 'Name', 'Value': interface_new_name}]
        interface.create_tags(Tags=interfaces_new_name)
        log.process(
                    " Interface " + interface.id + " labeled ",
                    "1",
                    interface_new_name
                    )
    log.ending("interface rename")

    # Snapshot labeling process
    log.starting("snapshot labeling")
    all_snapshots = ec2.snapshots.filter(Filters=[{
                                                    'Name': 'owner-id',
                                                    'Values': oids
                                                }])
    for snapshot in all_snapshots:
        desc = snapshot.description
        dob = snapshot.start_time.strftime("%m/%d/%y")
        snap_name = aws_tools.get_tag_name(snapshot.tags)
        if snap_name.startswith(no_name_label) or len(snap_name) == 0:
            if snapshot.description.startswith(generic_snapshot):
                if snapshot.volume_id is not None:
                    try:
                        volume_tags = ec2.Volume(snapshot.volume_id).tags
                        new_snap_name = aws_tools.get_tag_name(volume_tags)
                        status = "1"
                        proc = "Labeling Snapshot: " + snapshot.id + " as "
                        data = new_snap_name
                    except Exception:
                        status = "0"
                        proc = "No volume with ID "
                        data = snapshot.volume_id
                        new_snap_name = "Old-" + snapshot.volume_id
                        new_snap_name += "-Snapshot-" + dob
                else:
                    status = "1"
                    new_snap_name = "CreateImage" + snapshot.volume_id
                    new_snap_name += "-Snapshot-" + dob
                    proc = "Labeling Snapshot: " + snapshot.id + "as  "
                    data = new_snap_name
            else:
                status = "1"
                new_snap_name = desc
                proc = "Labeling Snapashot: " + snapshot.id + " : "
                proc += desc + " as "
                data = new_snap_name
            snapshots_new_name = [{'Key': 'Name', 'Value': new_snap_name}]
            snapshot.create_tags(Tags=snapshots_new_name)
        else:
            status = "1"
            proc = "Snapshot: " + snapshot.id + " already tagged as"
            data = snap_name

        log.process(proc, status, data)
    log.ending("snapshot labeling")

    # AMI labeling process
    log.starting("Labeling owned AMIs")
    all_images = ec2.images.filter(Filters=[{
                                                'Name': 'owner-id',
                                                'Values': oids
                                            }])
    for image in all_images:
        AMI_name = image.name
        dob = image.creation_date[0:10]
        image_name = aws_tools.get_tag_name(image.tags)
        if image_name.startswith(no_name_label) or len(image_name) == 0:
            AMI_name += " " + dob
            proc = "Labeling Image: " + image.id + " with"
            data = AMI_name + " current name: " + image_name
            image_new_name = [{'Key': 'Name', 'Value': AMI_name}]
            image.create_tags(Tags=image_new_name)
        else:
            proc = "AMI " + image.id + " already has a name"
            data = image_name

        log.process(proc, "1", data)
    log.ending("Labeling owned AMIs")

    # End
    log.finished()
