#!/usr/bin/env python
import os
import boto3
import logging
import requests
import json
import zipfile
from urllib.request import urlopen

# Program meta
vers = "1.0"
ProgramName = "Computatis"
desc = "Lambda inventory management"

# Output logging - default WARNING. Set to INFO for full output in cloudwatch
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# User/Repo settings for all source lambda scripts on Github
user = 'AdamNovetta'
giturl = 'https://api.github.com/repos/'
gitraw = 'https://raw.githubusercontent.com/'
targetRepo = '/AWS-API-TOOLS'
gitContent = '/contents'
targetSubDir = '/scripts/'
rawSub = '/master'


# Filetype of Lambda scripts
ext = '.py'

# Define boto3 connections/variables
lambda_client = boto3.client('lambda')


# Get AWS Lambda functions currently in this AWS account
def get_available_functions():
    AFList = []
    AvailableFunctions = lambda_client.list_functions()['Functions']
    for function in AvailableFunctions:
        if function['FunctionName'] != ProgramName:
            AFList.append(function['FunctionName'])
    return(AFList)


# Get the AWS stored URL (S3 URL) for the lambda function
def get_function_url(func):
    function = lambda_client.get_function(FunctionName=func)
    location = function['Code']['Location']

    return(location)


def get_function_content(l):
    FileObject = requests.get(l)
    if(FileObject.ok):
        file_contents = ''
        contents = requests.get(l)
        zfn = "aws.zip"
        zname = os.path.join("/tmp", zfn)
        zfile = open(zname, 'wb')
        # check if file exists
        zfile.write(contents.content)
        zfile.close()
        archive = zipfile.ZipFile(zname, 'r')
        FIZ = archive.namelist()
        for item in FIZ:
            if item.endswith(ext):
                file_contents = archive.read(item)
        if(file_contents):
            return(file_contents)


# Get AWS Lambda functions with .py extentions on the designated repo above
def get_functions_masters():
    repo = requests.get(giturl + user + targetRepo + gitContent + targetSubDir)
    GFList = []
    if(repo.ok):
        repoItem = json.loads(repo.content)
        for script in repoItem:
            for item in script:
                if item == "name" and script[item].endswith(ext):
                    GFList.append(script[item].split('.')[0])
    else:
        print("ERROR!!!!\n" + str(repo))

    return(GFList)


def get_git_contents(fname):
    string = gitraw + user + targetRepo + rawSub + targetSubDir + fname + ext
    repo = requests.get(string)
    if(repo.ok):
        file_contents = repo.content
    return(file_contents)


def lambda_handler(event, context):
    LambdaFunctions = get_available_functions()
    MasterIndex = get_functions_masters()
    AWS_Lambdas = {}
    Git_Functions = {}

    for i in LambdaFunctions:
        Loc = get_function_url(i)
        content = get_function_content(Loc)
        AWS_Lambdas[i] = content

    for i in MasterIndex:
        GitContents = get_git_contents(i)

        Git_Functions[i] = GitContents
    for x in Git_Functions:
        if x in AWS_Lambdas:
            if AWS_Lambdas[x] == Git_Functions[x]:
                print(x + " is on the AWS account and the Code matches!")
            else:
                print("XXX CODE NOT THE SAME FOR : " + x + " XXX")
                print("Code on git: \n" + str(Git_Functions[x].decode()))
                print("Code on AWS: \n" + str(AWS_Lambdas[x].decode()))
        if x not in AWS_Lambdas:
            print(" - " + x + " is missing from AWS Lambda list!")

    # TODO
    # check/diff local functions vs master index (and versions):
    # - if code locally differs from master list, pull from master list
    # - if code isn't on this AWS account:
    #       - create IAM policy
    #       - create Role
    #       - create laambda scripts
    #       - assign: role/lambda_script/settings
    #       - publish version/create alias?
    # report changes and additions / extra meta?
    # error outputs on failure for any function/steps
