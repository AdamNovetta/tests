#!/usr/bin/env python
import boto3
import logging
import requests
import json

# Program meta
vers = "1.0"
ProgramName = "Computatis"
desc = "Lambda inventory management"

# Output logging - default WARNING. Set to INFO for full output in cloudwatch
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# Repo for all source lambda scripts
repo = requests.get('https://api.github.com/repos/AdamNovetta/AWS-API-TOOLS/contents/scripts/')

# Define boto3 connections/variables
lambda_client = boto3.client('lambda')


def get_available_functions():
    AFList = []
    AvailableFunctions = lambda_client.list_functions()['Functions']
    for function in AvailableFunctions:
        if function['FunctionName'] != ProgramName:
            AFList.append(function['FunctionName'])
    return(AFList)


def get_functions_masters():
    GFList = []
    if(repo.ok):
        repoItem = json.loads(repo.content)
        for script in repoItem:
            for item in script:
                if item == "name" and script[item].endswith(".py"):
                    GFList.append(script[item])
    # print(json.dumps(repoItem))
    return(GFList)


def lambda_handler(event, context):
    LambdaFunctions = get_available_functions()
    MasterIndex = get_functions_masters()

    print("Available Functions on AWS: " + str(LambdaFunctions))
    print("Full list of functions on Git: " + str(MasterIndex))
