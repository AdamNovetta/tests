#!/bin/bash
#########################################################
#  
#  [ VARIABLES ]
#
#       VOLUMES: gets all volumes from US-EAST-Zone
#
#       LOGFILE: output of this script to log file
#
#       ARRAY: ALL EBS Volume ID's
#
#       VOLUMEID: placeholder for individual volumeID
#       VOLUME:  All volume details for volumeid
#       ATTACHED:  Volume state (attached or avail)
#       INSTANCEID: Volume's attached EC2 Instance ID
#       INSTANCE_NAME:  name of inscance volume is on
#       MOUNTPOINT:     /dev/??? for ebs
#       VOLUME_NAME:    current ebs vol name
#       VOLUME_NAME_NEW:  new format ebs volume name tag
#
########################################################:#
VOLUMES=$(/usr/local/bin/aws ec2 describe-volumes --region us-east-1 --query 'Volumes[*].VolumeId[]' |grep -v '}\|\]\|\[\|\{'|  awk -F '"' '{print $2}')
LOGFILE=/var/log/aws/EBS-rename-`date +\%m-\%d-\%y`_log
RENAMES=0
ARRAY=($VOLUMES)

echo " " >> $LOGFILE
echo " Starting AWS EBS rename job at : `date +\%H:\%M`" >> $LOGFILE
echo " Number of volumes: [ ${#ARRAY[@]} ]" >> $LOGFILE
echo "---------------------------------------------------------------" >> $LOGFILE
  for i in "${ARRAY[@]}"; do
      VOLUMEID=$i
      VOLUME=$(/usr/local/bin/aws ec2 describe-volumes --region us-east-1 --filters Name=volume-id,Values="$VOLUMEID" )
      ATTACHED=$(echo "$VOLUME" | grep -v '}\|\]\|\[\|\{'| grep -m 1 State | awk -F '"' '{print $4}' )
      if [ "$ATTACHED" == "attached" ];
      then
        INSTANCEID=$(echo "$VOLUME" | grep -v '}\|\]\|\[\|\{' | grep InstanceId | awk -F '"' '{print $4}')
        INSTANCE_NAME=$(/usr/local/bin/aws ec2 describe-instances --filters Name=instance-id,Values="$INSTANCEID" --query 'Reservations[*].Instances[*].Tags[*]'|grep -B1 Name | grep -v Name | awk -F '"' '{print $4}')
        MOUNTPOINT=$(echo "$VOLUME" | grep -v '}\|\]\|\[\|\{'| grep Device | awk -F '"' '{print $4}')
        VOLUME_NAME=$(echo "$VOLUME" |grep -v '}\|\]\|\[\|\{'| awk -F '"' '{print $4}' |grep -B1 Name | grep -v Name)
        VOLUME_NAME_NEW=$(echo "$INSTANCE_NAME-$MOUNTPOINT")
        if [ "$VOLUME_NAME" != "$VOLUME_NAME_NEW" ];
          then
            echo " $VOLUME_NAME_NEW  - is the new name for volume $i , instead of [ $VOLUME_NAME ]" >> $LOGFILE
            /usr/local/bin/aws ec2 create-tags --resources $VOLUMEID --tags Key=Name,Value=$VOLUME_NAME_NEW
            ((RENAMES++))
           echo " " >> $LOGFILE
          else
            echo " $VOLUMEID already named correctly : $VOLUME_NAME" >> $LOGFILE
          fi
      else
           VOLUME_NAME=$(echo "$VOLUME" |grep -v '}\|\]\|\[\|\{'| awk -F '"' '{print $4}' |grep -B1 Name | grep -v Name)
           VOLUME_NAME_NEW=$(echo "$VOLUMEID UNATTACHED")
            if [ "$VOLUME_NAME" != "$VOLUME_NAME_NEW" ];
            then
              echo " $VOLUMEID - is no longer attached to an EC2 instance and will be renamed to $VOLUME_NAME_NEW, instead of [ $VOLUME_NAME ]" >> $LOGFILE
              /usr/local/bin/aws ec2 create-tags --resources $VOLUMEID --tags Key=Name,Value="$VOLUME_NAME_NEW"
              echo " " >> $LOGFILE
              ((RENAMES++))

            fi
        fi
  done

echo "---------------------------------------------------------------" >> $LOGFILE
echo " Finished at : `date +\%H:\%M` " >> $LOGFILE
echo "      Renamed: [ $RENAMES ]   Amazon EBS Volumes" >> $LOGFILE
echo "# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #" >> $LOGFILE
