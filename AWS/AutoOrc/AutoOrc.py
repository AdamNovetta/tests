#!/usr/bin/env python
###########################################
#                                         #
#   AutoOrc - Lambda Function - V 1.0     #
#                                         #
######################################################################################################################
#  Copyright 2016 Novetta, Inc. P&T Infrastructure or its affiliates. All Rights Reserved.                           #
#                                                                                                                    #
#  This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES                                                  #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
#                                                                                                                    #
# Support -> PT-INFRASTRUCTURE@novetta.com                                                                         #
######################################################################################################################


# needed stuff
import json, boto3, logging, time, datetime

# output logging for INFO
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# define timer, used to gague shutdown time
timer = time.strftime("%H:%M")


# define the connection, replace region if your instances aren't in this region
region = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region)


# main function, that lambda 'calls'
def lambda_handler(event, context):
    print "[ Current Time: " + timer + " ]"

    # filter for all running EC2 instances with the 'autoOrc-down' tag set to current time
    # (assumes you've already created the EC2 instance tag, and applied it to intances with a time to stop [in UTC])
    filter_running = [{
            'Name': 'tag:autoOrc-down',
            'Values': [timer]
        },
        {
            'Name': 'instance-state-name',
            'Values': ['running']
        }
        ]
    # filter for all stopped EC2 instances with the 'autoOrc-up' tag set to current time
    # (assumes you've already created the EC2 instance tag, and applied it to intances with a time to start [in UTC])
    filter_stopped = [{
            'Name': 'tag:autoOrc-up',
            'Values': [timer]
        },
        {
            'Name': 'instance-state-name',
            'Values': ['stopped']
        }
        ]

    # check all instances that match the 'filter_running' filter
    running_instances = ec2.instances.filter(Filters=filter_running)

    # check all instances that match the 'filter_stopped' filter
    stopped_instances = ec2.instances.filter(Filters=filter_stopped)

    # all running instance's IDs
    RunningInstances = [instance.id for instance in running_instances]

    # all stopped instance's IDs
    StoppedInstances = [instance.id for instance in stopped_instances]

    # only shutdown if there are actually instances that match.
    if len(RunningInstances) > 0:
        # Print the instances stopping for logging purposes
        print "---> Running instances to be shutdown: "
        print RunningInstances
        # perform the shutdown
        shuttingDown = ec2.instances.filter(InstanceIds=RunningInstances).stop()
        print shuttingDown

    else:
        print "[  No Instances to shutdown now  ]"
    # only startup if there are actually instances that match.
    if len(StoppedInstances) > 0:
        # Print the instances starting for logging purposes
        print "---> Stopped instances that will be started: "
        print StoppedInstances
        # perform the startup
        startingUp = ec2.instances.filter(InstanceIds=StoppedInstances).start()
        print startingUp

    else:
        print "[  No Instances to start now  ]"
