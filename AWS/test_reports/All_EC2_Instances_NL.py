import json
import boto3
import logging

client = boto3.client('ec2')

response = client.describe_instances()


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


def lenth_check(check, col=column):
    if len(check) > col:
        col = len(check)

    return col


for instance in response['Reservations']:
    n = get_tag_name(instance['Instances'][0]['Tags'])
    s = instance['Instances'][0]['State']['Name']
    i = instance['Instances'][0]['InstanceId']
    items = [n, s, i]
    names.append(n)
    statuses.append(s)
    IDs.append(i)
    if max(map(lenth_check, items)) > column:
        column = max(map(lenth_check, items))

output = [heading] + list(zip(IDs, names, statuses))
print("\n")
for i, d in enumerate(output):
    line = ' | '.join(str(x).ljust(column) for x in d)
    print(line)
    if i == 0:
        print('-' * len(line))
