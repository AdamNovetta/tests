import json
import boto3
import logging
from pprint import pprint

ec2 = boto3.resource('ec2')
client = boto3.client('ec2')
instances = ec2.instances.all()

def lambda_handler(event, context):
    # get the 'Name' tag out of the batch of tags sent
    def get_tag_name(TAGS):
        NameTag = ''
        if TAGS is not None:
            for tags in TAGS:
                if tags["Key"] == 'Name':
                    NameTag = tags["Value"]

        return(NameTag)


    heading = ['IDs', 'Name', 'Status']
    names = []
    statuses = []
    IDs = []
    column = 0


    def length_check(check, col=column):
        if len(check) > col:
            col = len(check)

        return(col)


    for instance in instances:
        FullDetails = client.describe_instances(InstanceIds=[instance.id])
        detail = FullDetails['Reservations'][0]['Instances'][0]
        n = get_tag_name(detail['Tags'])
        s = detail['State']['Name']
        i = instance.id
        items = [n, s, i]
        names.append(n)
        statuses.append(s)
        IDs.append(i)
        length = max(map(length_check, items))
        if length > column:
            column = length

    output = [heading] + list(zip(IDs, names, statuses))
    print("\n")
    for i, d in enumerate(output):
        line = ' | '.join(str(x).ljust(column) for x in d)
        print(line)
        if i == 0:
            print('-' * len(line))
    print("\n")
