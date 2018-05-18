import json
import csv
import boto3
import logging
import time
import datetime
from time import mktime
from datetime import datetime, timezone

# Meta
vers = "1.0"
ProgramName = "IAM_Credential_Report"

# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
# Boto3 connections
IAM = boto3.resource('iam')
IAM_client = boto3.client('iam')

def credentials_report(event, context):

    report_state = IAM_client.generate_credential_report()
    print(report_state)
    if "COMPLETE" in report_state['State']:
        all_users = []
        n = event['username']
        report = str(IAM_client.get_credential_report()['Content'], 'utf-8')
        credentials = '\n'.join(report.split('\n')[1:])
        fieldnames = report.split('\n')[0:1]
        fn = list(csv.reader(fieldnames, delimiter=','))[0]
        print(fn)
        reader = csv.DictReader(credentials.split('\n'), fn)
        for item in reader:
            all_users.append(json.dumps(item))
            csv_name = item['user']
            if n == csv_name:
                plc = item['password_last_changed']
        
        print("HERES ALL OF THEM: \n" + str(all_users))
        print("HERES the first user: " +str(json.loads(all_users[0])['user']))
        return(plc)
