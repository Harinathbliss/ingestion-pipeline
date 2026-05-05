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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from botocore.config import Config

config = Config(
    retries = {
        'max_attempts': 10,
        'mode': 'standard' # ఇది ఆటోమేటిక్ గా 'Wait and Retry' చేస్తుంది
    }
)




logger = logging.getLogger()
logger.setLevel('INFO')

s3_client = boto3.client('s3')
bedrock_client = boto3.client(service_name='bedrock-runtime',config=config)




def lambda_handler(event,context):

     
     bucket = event['Records'][0]['s3']['bucket']['name']
     key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
     file_name = key.split('.')
     file_extension = file_name[-1]

     
     logger.info(bucket)
     logger.info(key)
     logger.info(file_extension)
     

     response = s3_client.get_object(Bucket=bucket,Key=key)
     pdf_reader = PdfReader(io.BytesIO(response['Body'].read()))

     full_text = ""
     for page in pdf_reader.pages:
         text = page.extract_text()
         if text:
            full_text += text

     splitter = RecursiveCharacterTextSplitter(
               chunk_size=100,
               chunk_overlap=20,
               separators=["\n\n", "\n", " ", ""]
     )
     
     chunks = splitter.split_text(text)
     proceded_data = []
     for i in range(0,len(chunks),10):
          current_batch = chunks[i : i + 10]
          native_request = {
            "inputStrings": current_batch,
            "embeddingConfig": {
                "outputEmbeddingLength": 1536
            }
          }
          request = json.dumps(native_request)
          bedrock_response = bedrock_client.invoke_model(
          modelId="amazon.titan-embed-text-v2:0", 
          contentType="application/json", 
          accept="application/json", 
          body=request
               )
          response_body = json.loads(bedrock_response.get('body').read())
          embedding = response_body.get('embedding')
          for j, embedding in enumerate(embedding):
            actual_index = i + j
            proceded_data.append({
                "id": actual_index,
                "vector": embedding,
                "text": current_batch[j]
            })

     return {
          "statusCode":200,
           "body":json.dumps({
            "message": proceded_data
     })
     }
