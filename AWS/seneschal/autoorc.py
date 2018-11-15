#!/usr/bin/env python3
import logged
import time
import datetime
import aws_tools

# Meta
vers = "1.0"
program_name = "AutoOrc"
desc = "Auto-starts and Auto-stops EC2 & RDS instances based on tags"


# Main function that lambda calls
def main(event):

    # AWS Tags to target for starting and stopping
    start = "autoOrc-up"
    stop = "autoOrc-down"

    # Start instances only on weekdays? (change to False to start every day)
    weekdays = True

    # Define boto3 connections/variables
    rds = aws_tools.aws_client('rds')
    ec2 = aws_tools.aws_resource('ec2')

    # cloudwatch names-space to use for metrics
    cw_ns = 'ORC-Results'

    # Get AutoOrc-down / AutoOrc-up tags on RDS instances
    def get_rds_orc_tags(arn, phase):
        orc_timer = ''
        tags = rds.list_tags_for_resource(ResourceName=arn)

        for tag in tags['TagList']:
            if tag['Key'] == phase:
                orc_timer = tag['Value']

        return orc_timer

    if event['logging']:
        log = logged.log_data(program_name, vers, event['logging'])
    else:
        log = logged.log_data(program_name, vers, False)

    start_tag = "tag:" + start
    stop_tag = "tag:" + stop
    aws_id = event['account_info']['id']

    # Day of the week
    d = datetime.datetime.now()

    # Check to see if today is a weekday
    def weekday(test_date):
        if test_date.isoweekday() in range(1, 6):
            return(True)
        else:
            return(False)

    is_weekday = weekday(d)

    # Define a timer, used to gague shutdown time, in UTC
    timer = time.strftime("%H:%M")

    # Set base filters for running/stopped instances, and matching orc tags
    filter_running = [
        {'Name': 'instance-state-name', 'Values': ['running']},
        {'Name': stop_tag, 'Values': [timer]}
        ]

    filter_stopped = [
        {'Name': 'instance-state-name', 'Values': ['stopped']},
        {'Name': start_tag, 'Values': [timer]}
        ]

    # find available EC2 instances to stop
    orc_inst = ec2.instances.filter(Filters=filter_running)
    orc_rds = rds.describe_db_instances()
    counter = error_counter = 0

    # Stop EC2 Instances
    log.starting("AutoOrc EC2 Shutdown")
    for instance in orc_inst:
        counter += 1
        state_code = 0
        name = aws_tools.get_ec2_instance_name(instance.id)
        response = instance.stop()
        state_code = response['StoppingInstances'][0]['CurrentState']['Code']
        if state_code == 16:
            error_counter += 1
            log.process(" Shutting down instance " + instance.id, "0", name)
        else:
            log.process(" Shutting down instance " + instance.id, "1", name)
    if (counter > 0):
        aws_tools.put_cloudwatch_metric(
                                        cw_ns,
                                        aws_id,
                                        counter,
                                        stop,
                                        'Success'
                                    )
    if (error_counter > 0):
        aws_tools.put_cloudwatch_metric(
                                        cw_ns,
                                        aws_id,
                                        error_counter,
                                        stop,
                                        'Error'
                                    )
    log.ending("AutoOrc EC2 Shutdown")

    # find available EC2 instances to start
    orc_inst_up = ec2.instances.filter(Filters=filter_stopped)
    counter = error_counter = 0
    bad_start_codes = ['32', '48', '64', '80']

    # Cycle through and start tagged EC2 instances
    if is_weekday or weekdays is False:
        log.starting("AutoOrc EC2 Startup")
        for instance in orc_inst_up:
            counter += 1
            state_code = 0
            name = aws_tools.get_ec2_instance_name(instance.id)
            resp = instance.start()
            state_code = resp['StartingInstances'][0]['CurrentState']['Code']
            if state_code in bad_start_codes:
                error_counter += 1
                log.process(
                            " Starting instance " + instance.id,
                            "0", name + " error code: " + str(state_code)
                            )
            else:
                log.process(" Starting instance " + instance.id, "1", name)
        if (counter > 0):
            aws_tools.put_cloudwatch_metric(
                                            cw_ns, aws_id,
                                            counter, start,
                                            'Success'
                                        )
        if (error_counter > 0):
            aws_tools.put_cloudwatch_metric(
                                            cw_ns,
                                            aws_id,
                                            error_counter,
                                            start,
                                            'Error'
                                        )
        log.ending("AutoOrc EC2 Startup")

    # cycle through all RDS instaces, starting/stopping Orc tagged ones
    for rds_inst in orc_rds['DBInstances']:
        rds_name = str(rds_inst['DBInstanceIdentifier'])
        rds_arn = str(rds_inst['DBInstanceArn'])
        rds_status = str(rds_inst['DBInstanceStatus'])
        rds_az_state = str(rds_inst['MultiAZ'])
        if is_weekday or weekdays is False:
            log.starting("AutoOrc RDS Startup")
            if rds_az_state == 'False' and rds_status == 'stopped':
                orc_up = get_rds_orc_tags(rds_arn, start)
                if orc_up == timer:
                    rds.start_db_instance(DBInstanceIdentifier=rds_name)
                    log.process(" Starting RDS database", "1", rds_name)
            log.ending("AutoOrc RDS Startup")
        if rds_az_state == 'False' and rds_status == 'available':
            orc_down = get_rds_orc_tags(rds_arn, stop)
            log.starting("AutoOrc RDS Shutdown")
            if orc_down == timer:
                rds.stop_db_instance(DBInstanceIdentifier=rds_name)
                log.process(" Stopping RDS database", "1", rds_name)

    # End
    log.finished()
