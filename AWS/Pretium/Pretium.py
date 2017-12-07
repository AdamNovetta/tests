#!/usr/bin/env python
import json
import boto3
import logging
import calendar
import time
import os
from time import mktime
from datetime import datetime

# Program meta
vers = "1.0"
ProgramName = "Pretium"
Desc = "Outputs costs"


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
def logging_debug(proc, state, count):
    logger = logging.getLogger()
    # set below to DEBUG or other to see more errors in event log/console
    logger.setLevel(logging.WARNING)


# Define boto3 connections/variables
client = boto3.client('cloudwatch')


# Render json dumps with datestamps correctly
class Render(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(mktime(obj.timetuple()))
        return json.JSONEncoder.default(self, obj)


# Main function
def get_metric_value(metric):
    today = datetime.today()
    year = int(today.strftime('%Y'))
    month = os.environ['Month']
    if int(month) != 12:
        NextMonth = int(month)+1
    else:
        NextMonth = 1
    DaysInMonth = calendar.mdays[int(month)]
    response = client.get_metric_statistics(
        Namespace='AWS/Billing',
        MetricName='EstimatedCharges',
        Dimensions=[
            {
                'Name': 'ServiceName',
                'Value': metric
            },
            {
                "Name": "Currency",
                "Value": "USD"
            }
			],
        StartTime=datetime(year, int(month), DaysInMonth),
        EndTime=datetime(year, NextMonth, 1),
        Period=86400,
        Statistics=['Maximum']
        )
    try:
        expense = response['Datapoints'][0]['Maximum']
    except:
        expense = "0"
    return expense
