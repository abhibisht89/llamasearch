import json
import requests
from fastapi import HTTPException
from loguru import logger
from typing import List

# Search engine related. You don't really need to change this.
BING_SEARCH_V7_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
BING_MKT = "en-US"
GOOGLE_SEARCH_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
SERPER_SEARCH_ENDPOINT = "https://google.serper.dev/search"
# Specify the number of references from the search engine you want to use.
# 8 is usually a good number.
REFERENCE_COUNT = 8

# Specify the default timeout for the search engine. If the search engine
# does not respond within this time, we will return an error.
DEFAULT_SEARCH_ENGINE_TIMEOUT = 100

def search_with_bing(query: str, subscription_key: str) -> List[dict]:
    """
    Search with bing and return the contexts.

    Args:
    query (str): The search query.
    subscription_key (str): The bing subscription key.

    Returns:
    List[dict]: A list of search results.
    """
    params = {"q": query, "mkt": BING_MKT}
    try:
        response = requests.get(
            BING_SEARCH_V7_ENDPOINT,
            headers={"Ocp-Apim-Subscription-Key": subscription_key},
            params=params,
            timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error searching with bing: {e}")
        raise HTTPException(500, "Error searching with bing")
    json_content = response.json()
    try:
        contexts = json_content["webPages"]["value"][:REFERENCE_COUNT]
    except KeyError:
        logger.error(f"Error parsing bing response: {json_content}")
        return []
    return contexts


def search_with_google(query: str, subscription_key: str, cx: str) -> List[dict]:
    """
    Search with google and return the contexts.

    Args:
    query (str): The search query.
    subscription_key (str): The google subscription key.
    cx (str): The google custom search engine id.

    Returns:
    List[dict]: A list of search results.
    """
    params = {
        "key": subscription_key,
        "cx": cx,
        "q": query,
        "num": REFERENCE_COUNT,
    }
    try:
        response = requests.get(
            GOOGLE_SEARCH_ENDPOINT, params=params, timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error searching with google: {e}")
        raise HTTPException(500, "Error searching with google")
    json_content = response.json()
    try:
        contexts = json_content["items"][:REFERENCE_COUNT]
    except KeyError:
        logger.error(f"Error parsing google response: {json_content}")
        return []
    return contexts


def search_with_serper(query: str, subscription_key: str) -> List[dict]:
    """
    Search with serper and return the contexts.

    Args:
    query (str): The search query.
    subscription_key (str): The serper subscription key.

    Returns:
    List[dict]: A list of search results.
    """
    payload = json.dumps({
        "q": query,
        "num": (
            REFERENCE_COUNT
            if REFERENCE_COUNT % 10 == 0
            else (REFERENCE_COUNT // 10 + 1) * 10
        ),
    })
    headers = {"X-API-KEY": subscription_key, "Content-Type": "application/json"}
    try:
        logger.info(
            f"{payload} {headers} {subscription_key} {query} {SERPER_SEARCH_ENDPOINT}"
        )
        response = requests.post(
            SERPER_SEARCH_ENDPOINT,
            headers=headers,
            data=payload,
            timeout=DEFAULT_SEARCH_ENGINE_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error searching with serper: {e}")
        raise HTTPException(500, "Error searching with serper")
    json_content = response.json()
    try:
        
        # convert to the same format as bing/google
        contexts = [
            {"name": c["title"], "url": c["link"], "snippet": c["snippet"]}
            for c in json_content["organic"][:REFERENCE_COUNT]
        ]
    except KeyError:
        logger.error(f"Error parsing serper response: {json_content}")
        return []
    return contexts

def convert_ddg_to_google_format(ddg_results):
    google_format_results = []
    for result in ddg_results:
        google_result = {
            "name": result.get("title", ""),
            "url": result.get("href", ""),
            "snippet": result.get("body", "")
        }
        google_format_results.append(google_result)
    return google_format_results

def search_with_duckduckgo(query):
    from duckduckgo_search import DDGS
    try:
        ddg_results = DDGS().text(query, max_results=10)
        # print(ddg_results)
        google_format_results = convert_ddg_to_google_format(ddg_results)
        # google_img_format_results=search_image_with_duckduckgo(query)
        # return google_format_results+google_img_format_results
        return google_format_results

    except Exception as err:
        print(err)
        return []

def convert_ddg_images_to_google_format(ddg_results):
    google_format_results = []
    for result in ddg_results:
        google_result = {
            "name": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("thumbnail", "")
        }
        google_format_results.append(google_result)
    return google_format_results
   
def search_image_with_duckduckgo(query):
    from duckduckgo_search import DDGS
    try:
        ddgs = DDGS()
        ddg_results = ddgs.images(
                                    keywords=query,
                                    region="wt-wt",
                                    safesearch="on",
                                    size=None,
                                    color="Monochrome",
                                    type_image=None,
                                    layout=None,
                                    license_image=None,
                                    max_results=10,
                                ) 
        # print(ddg_results)
        google_format_results = convert_ddg_images_to_google_format(ddg_results)
        return google_format_results
    except Exception as err:
        print(err)
        return []