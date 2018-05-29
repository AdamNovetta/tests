#!/usr/bin/env python3
import json
import csv
import boto3
import logging
import time
import datetime
import os
import dateutil.parser
from time import mktime
from datetime import datetime, timezone, date
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from googleapiclient import discovery
from googleapiclient.errors import HttpError

# Meta
vers = "1.0"
ProgramName = "IAM_Credential_Report"

# output logging, set to INFO for full output in cloudwatch, default is warning
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# Boto3 connections
IAM = boto3.resource('iam')
IAM_client = boto3.client('iam')
paginator = IAM_client.get_paginator('list_account_aliases')



def account_name():
    for response in paginator.paginate():
        AccountAliases = response['AccountAliases']
    if len(AccountAliases) > 1:
        AWSAccountName = str("-".join(AccountAliases))
    else:
        AWSAccountName = str("".join(AccountAliases))
    return(str(AWSAccountName))

# Setup the Sheets API
store = file.Storage('./tmp/credentials.json')
creds = store.get()
service = build('sheets', 'v4', http=creds.authorize(Http()))
# Target google sheet
SPREADSHEET_ID = os.environ['Spreadsheet_ID']
#RANGE_NAME = os.environ['Tab']

# Main
def lambda_handler(event, context):

    # Base variables
    old = ' <!>'
    delim = ','
    spacer = ' / '
    today = datetime.now(timezone.utc)
    # All users in IAM
    AllIAMUsers = IAM_client.get_paginator('list_users')
    values = []
    # Retuns days since an event
    def days_since(event_date):
        if isinstance(event_date, date):
            event = event_date
        else:
            event = dateutil.parser.parse(event_date)
        output = (today - event).days
        if output > 90:
            output = str(output)+old
        return(str(output))

    # Get master Credential Report from AWS
    def parse_AWS_credential_report():

        all_users = []

        # Check for source Credential Report from AWS
        def check_for_credential_report():
            try:
                IAM_client.get_credential_report()
                return(True)
            except:
                report_state = IAM_client.generate_credential_report()
                if "COMPLETE" in report_state['State']:
                    return(True)
                if "STARTED" or "INPROGRESS" in report_state['State']:
                    time.sleep(5)
                    print("waiting for report to generate...")
                return(False)

        while not check_for_credential_report():
            check_for_credential_report()

        # Read AWS Credential Report and sort CSV -> JSON
        report = str(IAM_client.get_credential_report()['Content'], 'utf-8')
        credentials = '\n'.join(report.split('\n')[1:])
        fieldnames = report.split('\n')[0:1]
        fn = list(csv.reader(fieldnames, delimiter=','))[0]
        values.append([
            "Name",
            "ID",
            "Est. Last Login (days)",
            "Password age (days)",
            "API Keys age (days)",
            "API used (days)",
            "MFA age (days)"
            ])

        reader = csv.DictReader(credentials.split('\n'), fn)
        for item in reader:
            all_users.append(json.dumps(item))

        return(all_users)

    aws_users = parse_AWS_credential_report()
    for user in aws_users:
        Data = json.loads(user)
        UserName = Data['user']

        if "<root_account>" not in UserName:
            UserID = IAM.User(UserName).user_id
            UserCreated = days_since(Data['user_creation_time'])
            PasswordEnabled = Data['password_enabled']
            if PasswordEnabled == "true":
                if "no_information" not in Data['password_last_used']:
                    PasswordUsed = days_since(Data['password_last_used'])
                else:
                    PasswordUsed = "Not logged"
                PasswordChanged = days_since(Data['password_last_changed'])
            else:
                PasswordUsed = "Never"
                PasswordChanged = "No password"

            MFAActive = Data['mfa_active']
            if MFAActive == "true":
                    MFADOB = days_since(
                        IAM_client.list_mfa_devices(
                            UserName=UserName
                            )
                        ['MFADevices'][0]['EnableDate']
                        )
            else:
                MFADOB = "No MFA"

            APIKey1 = Data['access_key_1_active']
            APIKey2 = Data['access_key_2_active']

            if APIKey1 == "true":
                APIKey1DOB = days_since(Data['access_key_1_last_rotated'])
            else:
                APIKey1DOB = "Not active"

            if "N/A" not in Data['access_key_1_last_used_date']:
                APIKey1LastUsed = days_since(
                                            Data['access_key_1_last_used_date'])
            else:
                APIKey1LastUsed = "Not used"

            if APIKey2 == "true":
                APIKey2DOB = days_since(Data['access_key_2_last_rotated'])
            else:
                APIKey2DOB = "Not active"

            if "N/A" not in Data['access_key_2_last_used_date']:
                APIKey2LastUsed = days_since(
                                            Data['access_key_2_last_used_date'])
            else:
                APIKey2LastUsed = "Not used"
        else:
            UserID = "Root Account"
            PasswordUsed = days_since(Data['password_last_used'])
            PasswordChanged = "Not tracked"
            APIKey1LastUsed = APIKey2LastUsed = APIKey1DOB = APIKey2DOB = "-"
            if Data['mfa_active'] == "true":
                MFADOB = "MFA Active"
            else:
                MFADOB = "No MFA"
        values.append([
                        UserName,
                        UserID,
                        PasswordUsed,
                        PasswordChanged,
                        APIKey1DOB + " / " + APIKey2DOB,
                        APIKey1LastUsed + " / " + APIKey2LastUsed,
                        MFADOB
                        ])

    BODY_VALUES = {
        'values': values
    }

    valueInputOptionValue = 'USER_ENTERED'
    
    def add_tab_if_missing(tab_name):
        try:
            spreadsheet_update_body = {
                                        'requests': [{
                                            "addSheet": {
                                                "properties": {
                                                        "title": tab_name
                                                    }
                                                }
                                            }]
                                        }
                                            
            tab_request = service.spreadsheets().batchUpdate(
                                                spreadsheetId=SPREADSHEET_ID,
                                                body=spreadsheet_update_body
                                                )
            response1 = tab_request.execute()
            print(response1)
        except HttpError as err:
            print("Tab already exists")
            
    AWS_account_name = account_name()
    RANGE_NAME = AWS_account_name.upper()

    add_tab_if_missing(RANGE_NAME)


    request = service.spreadsheets().values().update(
                                        spreadsheetId=SPREADSHEET_ID,
                                        range="'"+RANGE_NAME+"'",
                                        valueInputOption=valueInputOptionValue,
                                        body=BODY_VALUES
                                        )
    response = request.execute()
    
    print(response)
