#!/usr/bin/env python

import json
import boto3
import logging
import time
import datetime
from time import mktime
# PMeta
vers = "1.0"
ProgramName = "IAM_userID_reports"
line = "______________________________________________________________________"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
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

    AllIAMUsers = IAM_client.get_paginator('list_users')

    for users in AllIAMUsers.paginate():
        # look at all user data by uncommenting this line
        # print(json.dumps(users, cls=Render))

        print line + "\nIAM Username    |    IAM User ID\n" + line
        for user in users['Users']:
            print user['UserName'] + " | " + user['UserId']

        print(line)
