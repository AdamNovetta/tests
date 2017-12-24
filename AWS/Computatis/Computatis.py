#!/usr/bin/env python3
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
logger.setLevel(logging.INFO)

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


# download a function given location (l) and return the contents
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


# get contents of a specified git object, two types are the script and perms
def get_git_contents(fname, objs):
    if objs == scripts:
        string = gitraw + user + targetRepo + rawBranch + objs + fname + ext
    if objs == perms:
        string = gitraw + user + targetRepo + rawBranch + objs + fname + IAMext
    repo = requests.get(string)
    if(repo.ok):
        file_contents = repo.content
    return(file_contents)


# get all role names on the aws account
def get_IAM_role_names():
    output = []
    roles = IAM_client.list_roles()
    for role in roles['Roles']:
        output.append(role['RoleName'])
    return(output)


# get all owned policy names
def get_IAM_policy_names():
    output = []
    pols = IAM_client.list_policies(Scope='Local')
    for p in pols['Policies']:
        output.append(p['PolicyName'])
    print(" HERES THE POLICES WE HAVE" + str(output))
    return(output)


# get the policy names attached to a role
def get_IAM_role_policies(rname):
    output = IAM_client.list_role_policies(RoleName=rname)
    return(output['PolicyNames'])


# creates a IAM policy with pol contents/json
def create_IAM_policy(pol):
    pname = pol['Statement'][0]['Sid']
    print("===>> creating IAM policy: " + pname)
    # TODO : Create IAM policy


# create IAM role, given a name and policy
def create_IAM_role(rname, pol):
    pname = pol['Statement'][0]['Sid']
    IAMP = get_IAM_policy_names()
    print("  >>----> [ creating role ] " + str(rname))
    # TODO:
    # create a role

    if pname not in IAMP:
        print("  >>----> creating IAM Policy " + str(pname))
        create_IAM_policy(pol)

    print(" >>---------> Attaching IAM policy to role" + str(pol) + str(rname))
    # TODO: add policy to new role...


# update the existing functions code from git source code supplied
def sync_git_to_aws(fname, code):
    output = lambda_client.update_function_code(
                                                    FunctionName=fname,
                                                    ZipFile=code,
                                                    # Publish=True
                                                    DryRun=True
                                                )
    return(output)


# create a new lambda function
def create_lambda_function(fname, code, policy):
    return(print("  =--> function to create is not implemented yet"))
    # TODO: Create a new lambda function


# main
def lambda_handler(event, context):
    LambdaFunctions = get_available_functions()
    IAMRoles = get_IAM_role_names()
    IAMPolicies = get_IAM_policy_names()
    MasterIndex = get_functions_masters()
    AWS_Lambdas = {}
    Git_Functions = {}

    for i in LambdaFunctions:
        Loc = get_function_url(i)
        content = get_function_content(Loc)
        AWS_Lambdas[i] = {}
        AWS_Lambdas[i]['Code'] = content

    for i in MasterIndex:
        GitContents = get_git_contents(i, scripts)
        IAMContents = get_git_contents(i, perms)
        # p = IAMContents['Statement']['Sid']
        Git_Functions[i] = {}
        Git_Functions[i]['Code'] = GitContents
        Git_Functions[i]['IAM'] = IAMContents

    for x in Git_Functions:
        policy = json.loads(Git_Functions[x]['IAM'].decode())
        policyName = policy['Statement'][0]['Sid']
        rolename = "lambda-"+x
        # Look for roles matching this rolename
        if rolename in IAMRoles:
            RolePermissions = get_IAM_role_permissions(rolename)
            print("  --> Role: " + rolename + " exists!")
            # look at permissions on role
            for rp in RolePermissions:
                print("\nRole Permissions: " + str(rp))
                if rp in IAMPolicies:
                    print("Policy exists!")
                else:
                    print("Policy needs to be created")
                    create_IAM_policy(policy)
        else:
            print(" >>> Creating role <<< ")
            create_IAM_role(rolename, policy)
        if x in AWS_Lambdas:
            if AWS_Lambdas[x]['Code'] == Git_Functions[x]['Code']:
                print(x + " already on AWS account and code matches!")
            else:
                print("XXX CODE NOT THE SAME FOR : " + x + " XXX")
                print("Git code:\n" + str(Git_Functions[x]['Code'].decode()))
                print("AWS code:\n" + str(AWS_Lambdas[x]['Code'].decode()))
                sync_git_to_aws(x, Git_Functions[x]['Code'])
        if x not in AWS_Lambdas:
            print(" - Lambda : " + x + " is missing from AWS Lambda list!")
            create_lambda_function(x, Git_Functions[x]['Code'], policy)

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
