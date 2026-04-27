import json
from pydantic import BaseModel
import logging
import boto3
from uuid import uuid4

logger = logging.getLogger()
logger.setLevel('INFO')

bedrock = boto3.client(service_name="bedrock-runtime",region_name='us-east-1')
dynamodb = boto3.resource('dynamodb',region_name='us-east-1')
table = dynamodb.Table('MyChatHistoryTable')


class ChatDemo(BaseModel):
    message:str
    userid:str


def lambda_handler(event,context):
     request_body = json.loads(event.get('body',{}))
     
     logging.info(f"Request Body {request_body}")

     req = ChatDemo(**request_body)

     logging.info(f"Request Received {req}")

     user_id = req.userid or str(uuid4)
    

     native_request = {
            "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{req.message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
            "max_gen_len": 512,
            "temperature": 0.5,
            "top_p": 0.9
    }
    
     model_id = 'meta.llama3-8b-instruct-v1:0' 

     response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(native_request)
    )
    
     response_body = json.loads(response.get('body').read())
        
        
     answer = response_body.get('generation', '')

     table.put_item(
          Item={
               "userid":user_id,
               "question":req.message,
               "answer":answer
          }
     )



     
     return {
          "statusCode":200,
           "body":json.dumps({
                "message":req.message,
                "answer":answer
     })
     }
