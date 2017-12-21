#!/usr/bin/env python
import json
import boto3
import logging
import time
import datetime
from time import mktime
# Meta
vers = "1.0"
ProgramName = "IAM_roleID_reports"
line = "______________________________________________________________________"

# Output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boto3 connections
IAM = boto3.resource('iam')
IAM_client = boto3.client('iam')


def lambda_handler(event, context):
    heading = ['Role Name', 'Role ID']
    names = []
    IDs = []
    column = 0
    AllIAMRoles = IAM_client.get_paginator('list_roles')

    def length_check(check, col=column):
        if len(check) > col:
            col = len(check)

        return(col)

    for roles in AllIAMRoles.paginate():
        # look at all user data by uncommenting this line
        # print(json.dumps(roles, cls=Render))
        for role in roles['Roles']:
            n = role['RoleName']
            i = role['RoleId']
            names.append(n)
            IDs.append(i)
            items = [n, i]
            length = max(map(length_check, items))
            if length > column:
                column = length

    output = [heading] + list(zip(names, IDs))
    print("\n")
    for i, d in enumerate(output):
        line = ' | '.join(str(x).ljust(column) for x in d)
        print(line)
        if i == 0:
            print('-' * len(line))
    print("\n")
