#   Computatis - Lambda Function - V 1.0
--------------------------------------------------------------------------------
## Purpose:
      This program syncs scripts and permissions on a target Github repo to AWS.

#### Process:  
      - Checks if there are IAM policies in the AWS account matching the IAM templates (files in the permissions folder ending in .IAM)
      - Updates/creates IAM policies if they're missing
      - Checks if there is an IAM Role with the name "lambda-**NAME_OF_FUNCTION**" for each script being synced from Github
      - Creates roles if they're missing, and attaches the IAM policy (detaching policies not matching Git repo copies)
      - Checks if there's a Lambda function matching each script on Github (in the scripts directory matching the 'ext =' variable) and creates or updates the function depending
      - Attaches the IAM Role and IAM policy matching the name of the script on Github

##### Releases:
          v1.0 - Syncs Lambda scripts to AWS from Github, pairing them with an IAM Role+Policy from the same repos /permissions folder
