#!/usr/bin/env python
import os
import boto3
import logging
import requests
import json
import zipfile

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
scripts = '/scripts/'
perms = '/permissions/'
rawBranch = '/master'


# Filetype and runtime info of Lambda scripts
ext = '.py'
runtime = 'python3.6'
handler = 'lambda_function.lambda_handler'
IAMext = '.IAM'

# Define boto3 connections/variables
lambda_client = boto3.client('lambda')
IAM_client = boto3.client('iam')


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
        zfile.write(contents.content)
        zfile.close()
        archive = zipfile.ZipFile(zname, 'r')
        # check if file exists
        FIZ = archive.namelist()
        for item in FIZ:
            if item.endswith(ext):
                file_contents = archive.read(item)
        if(file_contents):
            return(file_contents)


# Get AWS Lambda functions with .py extentions on the designated repo above
def get_functions_masters():
    string = giturl + user + targetRepo + gitContent + scripts
    repo = requests.get(string)
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


def get_git_contents(fname, objs):
    if objs == scripts:
        string = gitraw + user + targetRepo + rawBranch + objs + fname + ext
    if objs == perms:
        string = gitraw + user + targetRepo + rawBranch + objs + fname + IAMext
    repo = requests.get(string)
    if(repo.ok):
        file_contents = repo.content
    return(file_contents)


def get_IAM_role_names():
    output = []
    roles = IAM_client.list_roles()
    for role in roles['Roles']:
        output.append(role['RoleName'])
    return(output)


def get_IAM_role_permissions(rname):
    output = IAM_client.list_role_policies(RoleName=rname)
    return(output['PolicyNames'])


def sync_git_to_aws(fname, code):
    output = lambda_client.update_function_code(
                                                    FunctionName='string',
                                                    ZipFile=code,
                                                    # Publish=True
                                                    DryRun=True
                                                )
    return(output)


def create_lambda_function(fname, code):
    return(print("   --> function to create is not implemented yet"))


def lambda_handler(event, context):
    LambdaFunctions = get_available_functions()
    IAMRoles = get_IAM_role_names()
    MasterIndex = get_functions_masters()
    AWS_Lambdas = {}
    Git_Functions = {}

    for i in LambdaFunctions:
        rolename = "lambda-"+i
        Loc = get_function_url(i)
        content = get_function_content(Loc)
        AWS_Lambdas[i] = {}
        AWS_Lambdas[i]['Code'] = content
        if rolename in IAMRoles:
            print(get_IAM_role_permissions(rolename))

    for i in MasterIndex:

        GitContents = get_git_contents(i, scripts)
        IAMContents = get_git_contents(i, perms)
        # p = IAMContents['Statement']['Sid']
        Git_Functions[i] = {}
        Git_Functions[i]['Code'] = GitContents
        Git_Functions[i]['IAM'] = IAMContents

    for x in Git_Functions:
        policy = json.loads(Git_Functions[x]['IAM'].decode())
        print(policy['Statement'][0]['Sid'])
        if x in AWS_Lambdas:
            if AWS_Lambdas[x]['Code'] == Git_Functions[x]['Code']:
                print(x + " already on AWS account and code matches!")
            else:
                print("XXX CODE NOT THE SAME FOR : " + x + " XXX")
                print("Git code:\n" + str(Git_Functions[x]['Code'].decode()))
                print("AWS code:\n" + str(AWS_Lambdas[x]['Code'].decode()))
                sync_git_to_aws(x, Git_Functions[x]['Code'])
        if x not in AWS_Lambdas:
            print(" - " + x + " is missing from AWS Lambda list!")
            create_lambda_function(x, Git_Functions[x]['Code'])

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
