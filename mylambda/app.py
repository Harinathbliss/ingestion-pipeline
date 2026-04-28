import json
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key
import logging
import boto3
from uuid import uuid4

logger = logging.getLogger()
logger.setLevel('INFO')

s3_client = boto3.client('s3')


def lambda_handler(event,context):

     request_body = event.get('body') or {}
     bucket = request_body['Records'][0]['s3']['bucket']['name']
     key = request_body['Records'][0]['s3']['object']['key']

     response = s3_client.get_object(Bucket=bucket,Key=key)
     file_content = response['Body'].read().decode('utf-8')

     logger.info(file_content)
     



     
     return {
          "statusCode":200,
           "body":json.dumps({
            "message":"Successfully Downloaded File"
     })
     }
