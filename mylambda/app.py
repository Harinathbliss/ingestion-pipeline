import json
from pydantic import BaseModel
import logging

logger = logging.getLogger()
logger.setLevel('INFO')


class ChatDemo(BaseModel):
    message:str


def lambda_handler(event,context):
     request_body = json.loads(event.get('body',{}))
     
     logging.info(f"Request Body {request_body}")

     req = ChatDemo(**request_body)

     logging.info(f"Request Received {req}")
     
     return {
          "statusCode":200,
           "body":json.dumps({
                "message":req.message
     })
     }
