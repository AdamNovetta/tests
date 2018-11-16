#!/usr/bin/env python3
import os
import logged
import onymer
import autoorc
import effingo
import aws_tools

vers = "1.0"
program_name = "Seneschal"
desc = "AWS Admin Automation Program"

topic = os.environ['sns_topic']
logging_output = os.environ['logging_enabled']

aws_id = aws_tools.get_account_id()
account_name = aws_tools.get_account_name()
region_name = aws_tools.get_current_region()

downstream_logging = {'logging': logging_output}
sns_topic_name = {'sns_topic': topic}
account = {'account_info': {
                            'name': account_name,
                            'id': aws_id,
                            'region_name': region_name
                        }}

pass_event = {**downstream_logging, **sns_topic_name, **account}


def lambda_handler(event, context):

    # available autotasks
    autotasks = ['onymer', 'autoorc', 'effingo']

    log = logged.log_data(program_name, vers, logging_output)

    def autotask_subroutine(task):
        if task:
            routine = eval(task)
            name = routine.program_name
            ver = routine.vers
            routine.main(pass_event)
            log.subroutine(" [[ Subroutine " + name + " " + ver, "finished ]]")

    log.starting("autotasks")
    for item in autotasks:
        autotask_subroutine(item)

    log.ending("autotasks")
