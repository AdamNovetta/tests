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

    class Render(json.JSONEncoder):

        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return int(mktime(obj.timetuple()))

            return json.JSONEncoder.default(self, obj)

    AllIAMRoles = IAM_client.get_paginator('list_roles')

    for roles in AllIAMRoles.paginate():
        # look at all user data by uncommenting this line
        # print(json.dumps(roles, cls=Render))

        print line + "\nIAM Role Name    |    IAM Role ID\n" + line
        for role in roles['Roles']:
            print role['RoleName'] + " | " + role['RoleId']

        print(line)
