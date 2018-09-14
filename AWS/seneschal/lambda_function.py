#!/usr/bin/env python3
import json
import boto3
import time
import datetime
import logged
import onymer
import autoorc


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

    # available autotasks
    autotasks = ['onymer', 'autoorc']

    log = logged.log_data(ProgramName, Vers, logging_output)

    def autotask_subroutine(task):
        if task:
            routine = eval(task)
            name = routine.ProgramName
            ver = routine.Vers
            routine.lambda_handler(downstream_logging, None)
            log.subroutine(" [ Sub-routine " + name + " " + ver, "finished ]")

    log.starting

    for item in autotasks:
        autotask_subroutine(item)

    log.ending("autotasks")
