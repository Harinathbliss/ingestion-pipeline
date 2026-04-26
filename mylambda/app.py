import json
from pydantic import BaseModel


class ChatDemo(BaseModel):
    message:str


def lambda_handler(event,context):
     req = ChatDemo(**event)
     return {
          "statusCode":200,
           "body":json.dumps({
                "message":req.message
     })
     }
