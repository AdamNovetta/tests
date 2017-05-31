#!/usr/bin/env python
'''
   Auto-NCA-Cluster - Lambda Function - V 1.0
--------------------------------------------------------------------------------
Copyright 2016 Novetta, Inc.
P&T Infrastructure or its affiliates. All Rights Reserved.

  This file is distributed on an AS IS BASIS, WITHOUT WARRANTIES OR CONDITIONS
  OF ANY KIND, express or implied.

Support: PT-INFRASTRUCTURE@novetta.com
--------------------------------------------------------------------------------
'''
# ver 1.4.1 - new user-data format
# ver 1.4 - adding orc times
# ver 1.3 - node volumes changed
# ver 1.2 - new nodes in cluster
# ver 1.1.1 - limiting region scope
# ver 1.1 - new vpc
# ver 1.0 - Script created
# (DOB: 2016)

'''
Purpose:
    Automatically creates a NCA cluster when called. Takes a variable for the
    repository to use for katello/foreman to install NCA software.

    (This is used for NCA's CI processes)

Usage:


'''

import argparse, json, boto3, logging, time, datetime, random

# output logging for INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# define timer, used to gague shutdown time
timer = time.strftime("%H:%M")

# define the connection, replace region if your instances aren't in this region
region = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region)

# define instance constants
NCA_SGs = 'sg-5a5dcb3c'
NCA_KeyPair = 'nca_engineer'
NCA_Image = 'ami-1ae6e40d'
NodeSize = 'm4.2xlarge'



# Check for repo argument and set it to 'repo'
parser = argparse.ArgumentParser()
parser.add_argument("a", nargs='?', default="check_string_empty")
args = parser.parse_args()

if args.a == 'check_string_empty':
    print 'No repo name spcified'
else:
    repo = args.a

#temp hack VVVV until the above if statement is working
repo = "NCA_4_5"

# Setup an automatic number for this cluster, based on whats not used 0-9
def cluster_number():
    # Setup list for the used projects tags
    Projects = []
    # Filter to check for instances that are still in use
    filter_in_use = [{
        'Name': 'instance-state-name',
        'Values': [
            'stopped',
            'running',
            'pending'
            ]
        }
        ]
    # Start the check for the in use instances with 'ncac' project tag
    used_instances = ec2.instances.filter(Filters=filter_in_use)
    UsedInstances = [instance.id for instance in used_instances]
    for instance in UsedInstances:
        EC2Instance = ec2.Instance(instance)
        # TODO - Need catch-case for blank names (or no tags)
        if EC2Instance.tags != None:
            for tags in EC2Instance.tags:
                if tags["Key"] == 'Project':
                    if tags["Value"].startswith('ncac'):
                        ClusterNumber = tags["Value"].translate(None, 'ncac')
                        if ClusterNumber not in Projects:
                            Projects.append(ClusterNumber)

    # Look for a free number in the NCAC clusters
    counter = 0
    while (counter < 10):
        if counter in Projects:
            counter += 1
        else:
            new_number = counter
            counter = 11
    if counter == 10:
        # Exit if no free numbers for cluster
        print "No cluster numbers available..."
        sys.exit(-1)
    # Return the number that can be used in the cluster
    return str(new_number)

def random_subnet():
    subnets=['subnet-bf6a9ac9', 'subnet-bf6a9ac9', 'subnet-bf6a9ac9']
    return random.choice(subnets)

def cloud_config(ThisCluster, ThisNode):
    # TODO
    fqdn = ThisCluster + ThisNode + ".cpd.novetta.com"
    CloudConfig = """
#cloud-config
runcmd:
 - [ sh, -c, 'hostnamectl set-hostname """ + fqdn + """']
 - [ sh, -c, 'echo \"""" + fqdn + """\" > /etc/salt/minion_id']
 - [ sh, -c, 'curl -s http://169.254.169.254/latest/meta-data/local-ipv4 >> /etc/hosts']
 - [ sh, -c, 'echo \" """ + fqdn + " " + ThisCluster + ThisNode + """\" >> /etc/hosts']
 - [ sh, -c, 'printf "grains: \\n  product: nca\\n  cluster: """ + ThisCluster + """\\n  nodetype: """ + ThisNode + """\\n  repo_name: """ + repo + """\\n  aws_instance_ID: " >> /etc/salt/minion']
 - [ sh, -c, 'curl -s http://169.254.169.254/latest/meta-data/instance-id >> /etc/salt/minion']
 - [ sh, -c, 'printf "\\n " >> /etc/salt/minion']
 - service salt-minion start
 - chkconfig salt-minion on
 - [ sh, -c, 'sleep 100']
 - [ sh, -c, 'salt-call state.highstate']
 - [ sh, -c, 'salt-call mine.update']
"""
    return CloudConfig

def ebs_volume(NodeClass):
    Type1Nodes = ['web', 'dec1', 'dec2']
    vol1 = [
    {
        'DeviceName': '/dev/sda1',
        'Ebs': {
            'VolumeSize': 120,
            'DeleteOnTermination': True,
            'VolumeType': 'gp2',
            }
    }
    ]
    vol2 = [
    {
        'DeviceName': '/dev/sda1',
        'Ebs': {
            'VolumeSize': 120,
            'DeleteOnTermination': True,
            'VolumeType': 'gp2'
        }
    },
    {
        'DeviceName': '/dev/sdb',
        'Ebs': {
            'VolumeSize': 200,
            'DeleteOnTermination': True,
            'VolumeType': 'standard'
        }
    }
    ]
    if NodeClass in Type1Nodes:
        return vol1
    else:
        return vol2

def request_instance(Node,Cluster,UD,Vols,Subnet):
    client = boto3.client('ec2')
    response = client.run_instances(
    DryRun=False,
    ImageId=NCA_Image,
    MinCount=1,
    MaxCount=1,
    KeyName=NCA_KeyPair,
    SecurityGroupIds=[NCA_SGs],
    UserData=UD,
    InstanceType=NodeSize,
    BlockDeviceMappings=Vols,
    Monitoring={ 'Enabled': False },
    SubnetId=Subnet,
    InstanceInitiatedShutdownBehavior='stop'
    )
    ThisInstance = response.instance
    ThisInstance.wait_until_running()
    print "Instance started" + ThisInstance.state

def lambda_handler(event, context):
    nca_cluster_number = cluster_number()
    new_cluster = 'ncac' + nca_cluster_number
    nodes=['etl1', 'etl2', 'dec1', 'dec2', 'dbl', 'dbw1', 'dbw2', 'dbw3', 'sen1', 'web']
    print "new cluster will be: " + new_cluster
    for node in nodes:
        UserData = cloud_config(new_cluster, node)
        vol_attachments = ebs_volume(node)
        print "Node : " + node
        print "User-data: "
        print(UserData)
        print "Volumes:"
        print(vol_attachments)
        request_instance(node, new_cluster, UserData, vol_attachments, random_subnet())
