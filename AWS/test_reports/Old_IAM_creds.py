#!/usr/bin/env python

import json
import boto3
import logging
import time
import datetime
from time import mktime
from datetime import datetime, timezone

# Meta
vers = "1.0"
ProgramName = "Old_IAM_creds"

# output logging for INFO, to see full output in cloudwatch, default to warning
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Boto3 connections
IAM = boto3.resource('iam')
IAM_client = boto3.client('iam')


def lambda_handler(event, context):
    heading = [
                'Name',
                'ID',
                'Password age (days)',
                'API Key(s) age (days)',
                'MFA(s) age (days)'
                ]
    names = []
    IDs = []
    pw = []
    api = []
    mfa = []
    old = ' <!>'
    column = 0
    today = datetime.now(timezone.utc)
    AllIAMUsers = IAM_client.get_paginator('list_users')
    API_keys = IAM_client.get_paginator('list_access_keys')

    def length_check(check, col=column):
        if len(check) > col:
            col = len(check)

        return(col)

    for users in AllIAMUsers.paginate():
        for user in users['Users']:
            apia = []
            mfaa = []
            n = user['UserName']
            i = user['UserId']
            uaks = API_keys.paginate(UserName=n)
            try:
                pwa = (today - IAM.LoginProfile(n).create_date).days
                a = str(pwa)
                if pwa >= 365:
                    a += old
            except:
                a = 'No password'
            key = IAM_client.list_access_keys(UserName=n)
            if key['AccessKeyMetadata']:
                for api_key in key['AccessKeyMetadata']:
                    if api_key['Status'] == 'Active':
                        age = (today - api_key['CreateDate']).days
                        b = str(age)
                        if age >= 365:
                            b += old
                        apia.append(b)
                    else:
                        apia.append('1 Inactive key')
                apia = ' / '.join(apia)
            else:
                apia = 'No API keys'
            p = apia
            try:
                mfas = IAM_client.list_mfa_devices(UserName=n)
                if mfas['MFADevices']:
                    for multi in mfas['MFADevices']:
                        mfa_age = (today - multi['EnableDate']).days
                        c = str(mfa_age)
                        if mfa_age >= 365:
                            c += old
                        mfaa.append(c)
                    m = ' / '.join(mfaa)
                else:
                    m = 'No MFA'
            except:
                m = 'No MFA'
            names.append(n)
            IDs.append(i)
            pw.append(a)
            api.append(p)
            mfa.append(m)
            items = [n, i, a, p, m]
            length = max(map(length_check, items))
            if length > column:
                column = length

    output = [heading] + list(zip(names, IDs, pw, api, mfa))

    for i, d in enumerate(output):
        line = ' | '.join(str(x).ljust(column) for x in d)
        print(line)
        if i == 0:
            print('-' * len(line))
    print("\n")
