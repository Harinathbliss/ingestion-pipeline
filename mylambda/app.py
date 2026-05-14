import json
import logging
import boto3
import urllib.parse
import io
import os
from uuid import uuid4
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from botocore.config import Config
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# AWS SDK Config: Retry mechanism for Free Tier accounts

QDRANT_HOST = "54.81.245.161" 
QDRANT_PORT = 6333


config = Config(
    read_timeout=120,   
    connect_timeout=60,
    retries = {
        'max_attempts': 10,
        'mode': 'standard' 
    }
)

client = QdrantClient(host=QDRANT_HOST, port=6333)

collection_name = "pdf_knowledge_base"

logger = logging.getLogger()
logger.setLevel('INFO')

s3_client = boto3.client('s3')
bedrock_client = boto3.client(service_name='bedrock-runtime', config=config)

def lambda_handler(event, context):
    try:
        # 1. S3 నుండి ఫైల్ వివరాలను పొందడం
        collection_name = "my_pdf_collection"
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        logger.info(f"Processing file: {key} from bucket: {bucket}")

        # 2. PDF చదవడం
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_reader = PdfReader(io.BytesIO(response['Body'].read()))
        client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

        full_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                full_text += text

        # 3. టెక్స్ట్ ని చంక్స్ గా విభజించడం
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, # కొంచెం పెద్ద సైజు పెడితే ప్రాసెసింగ్ ఈజీ అవుతుంది
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_text(full_text)
        logger.info(f"Total chunks created: {len(chunks)}")

        all_embeddings_data = []
        
        # 4. Cohere v3 బ్యాచింగ్ (గరిష్టంగా 96 చంక్స్ ఒకేసారి)
        # ఫ్రీ టైర్ లో ఒకేసారి ఎక్కువ పంపితే 'Throttling' వస్తుంది
        batch_size = 90 
        
        for i in range(0, len(chunks), batch_size):
            current_batch = chunks[i : i + batch_size]
            
            # Cohere v3 Payload Structure
            native_request = {
                "texts": current_batch,
                "input_type": "search_document",
                "truncate": "NONE"
            }
            
            request_body = json.dumps(native_request)
            
            # 5. Bedrock ని ఇన్వోక్ చేయడం
            bedrock_response = bedrock_client.invoke_model(
                modelId="cohere.embed-english-v3", 
                contentType="application/json", 
                accept="application/json", 
                body=request_body
            )
            
            response_json = json.loads(bedrock_response.get('body').read())
            batch_embeddings = response_json.get('embeddings')

            # డేటాను ఒక స్ట్రక్చర్ లో అమర్చడం
            for j, emb in enumerate(batch_embeddings):
                all_embeddings_data.append({
                    "id": str(uuid4()),
                    "text": current_batch[j],
                    "vector": emb
                })

                k = {
                    "id": str(uuid4()),
                    "text": current_batch[j],
                    "vector": emb
                }

                client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                    id=str(uuid4()), 
                    vector=emb,
                    payload={"text": current_batch[j]}
                        )
                        ]
            
                )




        logger.info(f"Successfully generated {len(all_embeddings_data)} embeddings")

        # 6. ఫైనల్ రెస్పాన్స్
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Embeddings generated successfully",
                "count": len(all_embeddings_data),
                # గమనిక: అన్నీ ఎంబెడ్డింగ్స్ బాడీలో పంపితే 6MB లిమిట్ దాటిపోవచ్చు
                "data_preview": all_embeddings_data[:2] # శాంపిల్ కోసం మొదటి రెండు మాత్రమే
            })
        }

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }