
#!/usr/bin/env python3
import json
import boto3
import logged
import time
import datetime

##########
## Meta ##
##########
Vers = "1.0"
ProgramName = "Seneschal AAAP"
Desc = "AWS Admin Automation Program"
##########
##########

    
def lambda_handler(event, context):
    log = logged.log_data(ProgramName,Vers)
    log.starting("autotasks")
