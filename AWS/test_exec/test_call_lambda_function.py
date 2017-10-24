#from __future__ import print_function
import boto3
import json

def call_lambda(lambdaName):
    lambda_client = boto3.client('lambda')
    invoke_response = lambda_client.invoke(FunctionName=lambdaName,
                                           InvocationType='RequestResponse'
                                           )
    data = invoke_response['Payload'].read().decode()                               
    data = data[1:-1]
    return(data)    
    
    
def lambda_handler(event, context):
    print(call_lambda('NAME_OF_EXISTING_LAMBDA_FUNCTION?'))
