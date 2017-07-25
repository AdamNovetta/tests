#   AutoOrc - Lambda Function - V 2.0
--------------------------------------------------------------------------------

## Purpose:
 Shuts down or starts up instances based on the ec2 instance tags:
 autoOrc-down and autoOrc-up, and the UTC time value in those tags (ie 13:00)
 
 V 2.0 - Creates CloudWatch metrics for successful/errored jobs 

## Usage:
- Setup a 1 minute interval cloudwatch event (cron trigger) and create the
above tags, specifying times for on/off in 24-hour UTC
- Update region and filter_running.append/filter_stopped.append statements, if
  you want to use other tags to hold the up and down times
