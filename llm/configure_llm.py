import os
import threading
import httpx
# from openai import OpenAI
from langfuse.openai import openai


def get_thread_local_client(model, base_url, api_key, timeout):
    thread_local = threading.local()
    try:
        return thread_local.client
    except AttributeError:
        thread_local.client = openai.OpenAI(
            timeout=timeout,
            base_url=base_url,
            api_key=api_key,
        )
        return thread_local.client

def openai_client():
    openai_llm = os.getenv('OPENAI_LLM')
    openai_api_key_gpt35 = os.getenv('OPENAI_API_KEY')
    return get_thread_local_client(
        model=openai_llm,
        base_url=None,
        api_key=openai_api_key_gpt35,
        timeout=httpx.Timeout(connect=10, read=120, write=120, pool=10)
    )

def togetherai_client():
    together_llm = os.getenv('TOGETHER_LLM')
    together_endpoint = os.getenv('TOGETHER_ENDPOINT')
    together_api_key = os.getenv('TOGETHER_API_KEY')

    return get_thread_local_client(
        model=together_llm,
        base_url=together_endpoint,
        api_key=together_api_key,
        timeout=httpx.Timeout(connect=10, read=120, write=120, pool=10)
    )

def hf_tgi_client():
    hf_tgi_host = os.getenv('HF_TGI_HOST')
    return get_thread_local_client(
        model="",
        base_url=hf_tgi_host,
        api_key="EMPTY",
        timeout=httpx.Timeout(connect=10, read=120, write=120, pool=10)
    )

def ollama_client():
    ollama_host = os.getenv('OLLAMA_HOST')
    ollama_llm = os.getenv('OLLAMA_LLM')
    return get_thread_local_client(
        model=ollama_llm,
        base_url=ollama_host,
        api_key="EMPTY",
        timeout=httpx.Timeout(connect=100, read=120, write=120, pool=100)
    )