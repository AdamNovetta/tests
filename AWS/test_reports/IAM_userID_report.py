#!/usr/bin/env python
#  -----------------------------------------------------------------------------
# tools needed
import json, boto3, logging, time, datetime
from time import mktime
# Program meta -----------------------------------------------------------------
vers = "1.0"
ProgramName = "IAM_userID_reports"
line = "_______________________________________________________________________"
#  -----------------------------------------------------------------------------
# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#  -----------------------------------------------------------------------------
IAM = boto3.resource('iam')
IAM_client = boto3.client('iam')
#  -----------------------------------------------------------------------------
def lambda_handler(event, context):
    class Render(json.JSONEncoder):
    
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return int(mktime(obj.timetuple()))
    
            return json.JSONEncoder.default(self, obj)
    AllIAMUsers = IAM_client.get_paginator('list_users')
    for users in AllIAMUsers.paginate():
        # look at all user data by uncommenting this line
        #print(json.dumps(users, cls=Render))
        print(line)
        print "IAM Username    |    IAM User ID"
        print(line)
        for user in users['Users']:
            print user['UserName'] + " | " + user['UserId']
        print(line)
        
