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
IAMext = '.IAM'
runtime = 'python3.6'
handler = 'lambda_function.lambda_handler'

# Define boto3 connections/variables
lambda_client = boto3.client('lambda')
IAM_client = boto3.client('iam')
iam = boto3.resource('iam')
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')

baseARN = 'arn:aws:iam::' + MyAWSID + ':'


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
        # check if file exists
        archive = zipfile.ZipFile(zname, 'r')
        FIZ = archive.namelist()
        for item in FIZ:
            if item.endswith(ext):
                file_contents = archive.read(item)
        if(file_contents):
            return(file_contents)


# zip updated function code
def zip_new_function(code):
        c = code.decode()
        fn = "lambda_function" + ext
        fname = os.path.join("/tmp", fn)
        fo = open(fname, "w")
        fo.write(c)
        fo.close()
        zfn = "lambda_function.zip"
        zname = os.path.join("/tmp", zfn)
        zfile = zipfile.ZipFile(zname, 'w')
        zfile.write(fname, fn)
        zfile.close()
        output = open(zname, 'rb').read()

        return(output)


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
    else:
        return("CAN'T READ " + fname)


# get all role names on the aws account
def get_IAM_role_names():
    output = []
    roles = IAM_client.list_roles()
    for role in roles['Roles']:
        output.append(role['RoleName'])

    return(output)


# get IAM policy contents
def get_IAM_policy_contents(pname):
    ARN = baseARN + 'policy/' + pname
    try:
        v = IAM_client.get_policy(PolicyArn=ARN)['Policy']['DefaultVersionId']
        pd = IAM_client.get_policy_version(PolicyArn=ARN, VersionId=v)
        output = pd['PolicyVersion']['Document']
    except e as BaseException:
        output = 'No-data for policy' + str(pname) + str(e)

    return(output)


# get all owned policy names
def get_IAM_policy_names():
    output = []
    pols = IAM_client.list_policies(Scope='Local')
    for p in pols['Policies']:
        output.append(p['PolicyName'])

    return(output)


# get the policy names attached to a role
def get_IAM_role_policies(rname):
    all_policies = IAM_client.list_attached_role_policies(RoleName=rname)
    output = []
    for p in all_policies['AttachedPolicies']:
        output.append(p['PolicyName'])

    return(output)


# creates a IAM policy with pol contents/json
def create_IAM_policy(pol):
    pname = pol['Statement'][0]['Sid']
    pdesc = str(pname) + " - (Computatis Synced)"
    pol = json.dumps(pol)
    IAM_client.create_policy(
                                PolicyName=pname,
                                PolicyDocument=pol,
                                Description=pdesc
                            )


# Update an existing IAM policy with new permissions
def update_IAM_policy(pol):
    pname = pol['Statement'][0]['Sid']
    ARN = baseARN + 'policy/' + pname
    pol = json.dumps(pol)
    output = IAM_client.create_policy_version(
                                                PolicyArn=ARN,
                                                PolicyDocument=pol,
                                                SetAsDefault=True
                                            )


# create IAM role, given a name and policy, and create policy if missing
def create_IAM_role(rname, pol):
    pname = pol['Statement'][0]['Sid']
    ARN = baseARN + 'policy/' + pname
    ARPD = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}"""
    rdesc = "Allows lambda function " + rname + " to run (Computatis Synced)"
    IAMP = get_IAM_policy_names()

    if pname not in IAMP:
        create_IAM_policy(pol)
    else:
        current_policy = get_IAM_policy_contents(pname)
        if pol != current_policy:
            update_IAM_policy(pol)

    IAM_client.create_role(
                            RoleName=rname,
                            AssumeRolePolicyDocument=ARPD,
                            Description=rdesc
                        )
    IAM_client.attach_role_policy(RoleName=rname, PolicyArn=ARN)


# update an existing IAM role
def update_role(rname, pname):
    ARN = baseARN + 'policy/' + pname
    IAM_client.attach_role_policy(RoleName=rname, PolicyArn=ARN)


# update the existing functions code from git source code supplied
def sync_git_to_aws(fname, code):
    zc = zip_new_function(code)
    lambda_client.update_function_code(
                                        FunctionName=fname,
                                        ZipFile=zc,
                                        Publish=True
                                    )


# create a new lambda function
def create_lambda_function(fname, code, policy):
    zc = zip_new_function(code)
    rname = "lambda-" + fname
    rARN = "arn:aws:iam::" + MyAWSID + ":role/" + rname
    rdesc = fname + " Lambda function - (Computatis Synced)"
    lambda_client.create_function(
                                    FunctionName=fname,
                                    Runtime=runtime,
                                    Role=rARN,
                                    Handler=handler,
                                    Code={'ZipFile': zc},
                                    Description=rdesc,
                                    Timeout=190,
                                    MemorySize=128,
                                    Publish=True
                                )


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
        Git_Functions[i] = {}
        Git_Functions[i]['Code'] = GitContents
        Git_Functions[i]['IAM'] = IAMContents

    for x in Git_Functions:
        print("\n\n\n----------------[ Checking on function " + str(x) + " ]----------------")
        policy = json.loads(Git_Functions[x]['IAM'].decode())
        policyName = policy['Statement'][0]['Sid']
        rolename = "lambda-" + x

        # Look for roles matching this rolename
        if rolename in IAMRoles:
            RolePermissions = get_IAM_role_policies(rolename)
            print("\n  [ Role: " + rolename + " already exists! ]")
            # look at permissions on role
            print("          Role Permissions:")

            # no permissions attached to role
            if not RolePermissions:
                print("          -> No permissions attached to role ")
                if policyName not in IAMPolicies:
                    print("          -> No IAM policy named : " + str(policyName))
                    create_IAM_policy(policy)
                update_role(rolename, policyName)

            # cycle role permissions
            else:
                if policyName in RolePermissions:
                    print("          ->" + policyName + " policy in " + rolename + " permissions")
                    if policyName in IAMPolicies:
                        pd = get_IAM_policy_contents(policyName)
                        if pd != policy:
                            update_IAM_policy(policy)
                            update_role(rolename, policyName)
                else:
                    create_IAM_policy(policy)
                    update_role(rolename, policyName)
        else:
            print(" >>> Creating role: " + rolename + " <<<")
            create_IAM_role(rolename, policy)
            print(" >>> Done with role " + rolename + " creation <<<")
        if x in AWS_Lambdas:
            if AWS_Lambdas[x]['Code'] == Git_Functions[x]['Code']:
                print("\n  [ Function: " + x + " already on AWS account and code matches! ]\n")
            else:
                print("  [ CODE NOT UP TO DATE FOR : " + x + " ]")
                print("Git code:\n" + str(Git_Functions[x]['Code'].decode()))
                print("AWS code:\n" + str(AWS_Lambdas[x]['Code'].decode()))
                sync_git_to_aws(x, Git_Functions[x]['Code'])
                print("\n")
        if x not in AWS_Lambdas:
            create_lambda_function(x, Git_Functions[x]['Code'], policy)
            print("  - Lambda : " + x + " is missing from AWS Lambda list!\n")
        print("---------------- END RUN ON FUNCTION " + x + "----------------")

    # TODO
    # - remove old permissions if name changes on file
    # - cleanup old functions or old roles?
    # - if code isn't on this AWS account:
    #       - publish version/create alias?
    # report changes and additions / extra meta?
    # error outputs on failure for any function/steps
