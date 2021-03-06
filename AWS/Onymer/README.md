#   Onymer - Lambda Function - V 4.2
--------------------------------------------------------------------------------
## Purpose:
This will rename all EBS volumes, network interfaces, snapshots, and AMIs (owned by the account running the script) in the AWS 'region = ' to:
- [x] EBS volumes:  **[ _instance-name-tag_ ]-/_mount_/_point_**
- [x] Interfaces: **_instance-name-tag_**
- [x] Snapshots: **[ _instance-name-tag_ ]-/_mount_/_point_** (or description if it's not an EC2 instance interface)
- [x] AMIs: __*AMI-Name value*__ (required to make an image, kinda redundant?)
###### (Also renames all unattached entities to "- UNATTACHED -previousName" or just "- UNATTACHED -" if no previous name exists)
#### Usage:
   - Run manually in Lambda or (recommended) on a triggered cron
   (suggested hourly or sooner)
   - Update region and UnattachedLabel vars to suit your setup
   - Lambda Configuration:
        * runtime : python 2.7
        * handler : lambda_function.lambda_handler
        * role : (create a role with TODO/TODO )
        * description : Auto-names all EBS volumes and EC2 Network interfaces
        Advanced Configuration:
            * Memory : 128 MB
            * Timeout : 2 min (should be enough for 1000-1500 checked objects)
            * DQL Resource: None
            * VPC : No VPC (not needed really...)
            * Enable active tracing : unchecked (also not really needed)
            * KMS key : default

##### Releases:
    v4.2 - re-organized/better formatting on logging output
    v4.1 - Cleaned up the code and added a 'try' to put interfaces descriptions in as the name, when it's not a EC2 interface
    v4.0 - Added auto-name Snapshots and AMIs to this script
    v3.0 - Added Auto-name all EC2 network interfaces to the script
    v2.0 - Auto-rename all EBS volumes, now includes unattached volumes
    v1.0 - Auto-name all EBS volumes

######  p.s. - comment out (or uncomment) print lines to alter logging output
