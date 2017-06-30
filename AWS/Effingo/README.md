#   Effingo - Lambda Function - V 1.0
--------------------------------------------------------------------------------
## Purpose:
This program makes snapshots of the EBS volumes on a daily/weekly/monthly schedule


TODO: Add an IAM policy example/template

#### Usage:
   - Run manually in Lambda or (recommended) on a triggered cron
   (suggested hourly or sooner, depending on AWS usage)
   - Lambda Configuration:
        * runtime : python 2.7
        * handler : lambda_function.lambda_handler
        * role : (create a role with TODO/TODO )
        * description : Sends alert to *SNS TOPIC* for insecure configurations
        Advanced Configuration:
            * Memory : 128 MB
            * Timeout : 1 min (should be enough several thousand objects)
            * DQL Resource: None
            * VPC : No VPC (not needed really...)
            * Enable active tracing : unchecked (also not really needed)
            * KMS key : default

##### Releases:
    v1.0 - Checks S3 buckets for insecure connections

######  p.s. - comment out (or uncomment) print lines to alter logging output
