#!/usr/bin/env python3
import json
import boto3
import logged
import onymer
import time
import datetime


##########
# Meta   #
##########
Vers = "1.0"
ProgramName = "Seneschal"
Desc = "AWS Admin Automation Program"
##########
##########

# enable logging output?
logging_output = True

downstream_logging = {'logging': logging_output}


def lambda_handler(event, context):
    print(ProgramName)
    log = logged.log_data(ProgramName, Vers, logging_output)
    log.starting("autotasks")
    if onymer:
        log.starting("Onymer " + onymer.Vers)
        onymer.lambda_handler(downstream_logging, 'None')
