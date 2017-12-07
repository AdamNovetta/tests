#   AutoOrc - Lambda Function - V 3.1
--------------------------------------------------------------------------------

## Purpose:
 Shuts down or starts up instances and RDS databases based on the tags:
 autoOrc-down and autoOrc-up, and the UTC time value in those tags (ie 13:00)

 - [x] v 3.1 - Cleaned up code
 - [x] v 3.0 - RDS instances that aren't multi-az are now able to be Orc'ed via tags
 - [x] v 2.0 - Creates CloudWatch metrics for successful/errored instances state changes
 - [x] v 1.0 - Auto-starts and auto-stops instances based on tags

## Usage:
- Setup a 1 minute interval cloudwatch event (cron trigger) and create the
above tags, specifying times for on/off in 24-hour UTC
- Update region and filter_running.append/filter_stopped.append statements, if
  you want to use other tags to hold the up and down times
