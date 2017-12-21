#!/usr/bin/env python
import os
import boto3
import logging
import requests
import json
import hashlib
import base64
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
    print("OK the location is - " + l)
    FileObject = requests.get(l)
    if(FileObject.ok):
        contents = requests.get(l)
        print("printed content: " + str(contents.content))
        zfn = "aws.zip"
        zname = os.path.join("/tmp", zfn)
        zfile = open(zname, 'wb')
        # check if file exists
        print(os.listdir("/tmp"))
        zfile.write(contents.content)
        zfile.close()
        archive = zipfile.ZipFile(zname, 'r')
        print(archive.namelist())
        file_contents = archive.read('lambda_function.py')
        print(file_contents)

# Get AWS Lambda functions with .py extentions on the designated repo above
def get_functions_masters():
    repo = requests.get(giturl + user + targetRepo + gitContent + targetSubDir)
    GFList = []
    # print("starting git API pulll....")
    # print("repo info: " + str(repo))
    if(repo.ok):
        repoItem = json.loads(repo.content)
        for script in repoItem:
            # print(str(json.dumps(script)) + "\n --------------------------")
            for item in script:
                if item == "name" and script[item].endswith(ext):
                    GFList.append(script[item].split('.')[0])
    else:
        print("ERROR!!!!\n" + str(repo))
    # print(json.dumps(repoItem))
    return(GFList)


def get_sha256_AWS(function):
    sha256 = lambda_client.get_function(
                                        FunctionName=function
                                        )['Configuration']['CodeSha256']
    return(sha256)


def get_sha256_git(fname):
    string = gitraw + user + targetRepo + rawSub + targetSubDir + fname + ext
    repo = requests.get(string)
    if(repo.ok):
        repoItem = repo.content
        # print(repoItem)

        sha256 = hashlib.sha256(repoItem).digest()
        # encoded = sha256.decode("hex").encode("base64")
        based = base64.b64encode(sha256)
    return(str(based))


def lambda_handler(event, context):
    LambdaFunctions = get_available_functions()
    MasterIndex = get_functions_masters()

    print("Available Functions on AWS: ")
    for i in LambdaFunctions:
        print(i)
        LambdaHash = get_sha256_AWS(i)
        Loc = get_function_url(i)
        content = get_function_content(Loc)
        print(LambdaHash + "\n" + str(Loc))
    print("-----------------------------------------------------\n\n\n\n")
    print("Available Functions on Git: ")
    for i in MasterIndex:
        print(i)
        GitHash = get_sha256_git(i)
        print(GitHash)

    # TODO
    # check/diff local functions vs master index (and versions)
    # create IAM policy
    # create Role
    # create laambda scripts
    # publish version?
    # error outputs
