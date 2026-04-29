import json
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key
import logging
import boto3
from uuid import uuid4
import urllib.parse
from pypdf import PdfReader
import os
import io

logger = logging.getLogger()
logger.setLevel('INFO')

s3_client = boto3.client('s3')


def lambda_handler(event,context):

     
     bucket = event['Records'][0]['s3']['bucket']['name']
     key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
     file_name = key.split('.')
     file_extension = file_name[-1]

     
     logger.info(bucket)
     logger.info(key)
     logger.info(file_extension)
     

     response = s3_client.get_object(Bucket=bucket,Key=key)
     file_content = response['Body'].read().decode('utf-8')
     pdf_reader = PdfReader(io.BytesIO(response['Body'].read()))

     full_text = ""
     for page in pdf_reader.pages:
         text = page.extract_text()
         if text:
            full_text += text

     
     logger.info(full_text)
     
     return {
          "statusCode":200,
           "body":json.dumps({
            "message":"Successfully Downloaded File"
     })
     }
