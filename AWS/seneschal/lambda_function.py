#!/usr/bin/env python3
import json
import boto3
import time
import datetime
import logged
import onymer
import autoorc
import effingo
import aws_tools

##########
# Meta   #
##########
vers = "1.0"
program_name = "Seneschal"
desc = "AWS Admin Automation Program"
##########
##########

# enable logging output?
logging_output = True
downstream_logging = {'logging': logging_output}


def lambda_handler(event, context):
    #my_account_name = aws_tools.get_account_name()
    #print(my_account_name)
    #my_account = aws_tools.get_account_id()
    #print(my_account)
    ############################################################################
    # available autotasks
    # All #
    ############################################################################
    #autotasks = ['onymer', 'autoorc', 'effingo']
    autotasks = ['autoorc']

    log = logged.log_data(program_name, vers, logging_output)

    def autotask_subroutine(task):
        if task:
            routine = eval(task)
            name = routine.program_name
            ver = routine.vers
            routine.lambda_handler(downstream_logging, None)
            log.subroutine(" [ Sub-routine " + name + " " + ver, "finished ]")

    log.starting("autotasks")
    for item in autotasks:
        autotask_subroutine(item)

    log.ending("autotasks")
