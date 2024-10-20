from langfuse.callback import CallbackHandler
import os
from dotenv import load_dotenv
load_dotenv(override=True)

lengfuse_secret_key = os.getenv('langfuse_secret_key')
lengfuse_public_key = os.getenv('langfuse_public_key')
langfuse_cloud = os.getenv('langfuse_cloud')

langfuse_handler = CallbackHandler(
    secret_key=lengfuse_secret_key,
    public_key=lengfuse_public_key,
    host=langfuse_cloud, 
)