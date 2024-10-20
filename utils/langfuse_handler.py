from langfuse.callback import CallbackHandler
import os
from dotenv import load_dotenv
load_dotenv(override=True)

lengfuse_secret_key = os.getenv('LANGFUSE_SECRET_KEY')
lengfuse_public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
langfuse_cloud = os.getenv('LANGFUSE_CLOUD')

langfuse_handler = CallbackHandler(
    secret_key=lengfuse_secret_key,
    public_key=lengfuse_public_key,
    host=langfuse_cloud, 
)