#   Canaria - Lambda Function - V 1.0
--------------------------------------------------------------------------------
## Purpose:
This program alerts an SNS topic to possible insecure configurations. Currently the checks performed are:
- [x] Public S3 buckets: Any bucket with 'everyone' permissions, any 'all authenticated s3 accounts' is also a warning

#### Usage:
   - Run manually in Lambda or (recommended) on a triggered cron
   (suggested hourly or sooner, depending on AWS usage)
   - **Create an IAM role with the following policies attached**:
      - AmazonS3FullAccess
      - AmazonSNSRole
      - IAMReadOnlyAccess
      - AmazonSNSFullAccess
   - Create an SNS Topic called: **AWS_Alerts** (or if you reuse an existing SNS topic, change the variable **sns_arn** in the script to your topic)
   - Lambda Configuration:
        * runtime : python 2.7
        * handler : lambda_function.lambda_handler
        * role : (create a role with TODO/TODO )
        * description : Sends alert to *SNS TOPIC* for insecure configurations
        Advanced Configuration:
            * Memory : 128 MB
            * Timeout : 1 min (should be enough several hundred buckets)
            * DQL Resource: None
            * VPC : No VPC (not needed really...)
            * Enable active tracing : unchecked (also not really needed)
            * KMS key : default

##### Releases:
    v1.0 - Checks S3 buckets for insecure connections

######  p.s. - comment out (or uncomment) print lines to alter logging output