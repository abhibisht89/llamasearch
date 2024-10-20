from dotenv import load_dotenv
load_dotenv(override=True)

import concurrent.futures
import glob
import json
import os
import re
import traceback
from typing import Annotated, List, Generator, Optional

from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from loguru import logger

from leptonai.photon import Photon, StaticFiles
from leptonai.photon.types import to_bool
from leptonai.util import tool

from utils.utils import extract_all_json

from llm.configure_llm import togetherai_client, openai_client, hf_tgi_client, ollama_client

from retrieval.search import search_with_google, search_with_serper,search_with_duckduckgo
from prompt.prompt import _rag_query_text, _more_questions_prompt, _default_query, _more_questions_prompt_no_tool_call

class RAG(Photon):
 
    def init(self):
        """
        Initializes photon configs.
        """
        self.backend = os.environ["SEARCH_BACKEND"].upper() #"DUCKDUCKGO"
        print("SEARCH_BACKEND: ",self.backend)

        if self.backend == "GOOGLE":
            self.search_api_key = os.environ["GOOGLE_SEARCH_API_KEY"]
            self.search_function = lambda query: search_with_google(
                query,
                self.search_api_key,
                os.environ["GOOGLE_SEARCH_CX"],
            )
        elif self.backend == "SERPER":
            self.search_api_key = os.environ["SERPER_SEARCH_API_KEY"]
            self.search_function = lambda query: search_with_serper(
                query,
                self.search_api_key,
            )
        elif self.backend == "DUCKDUCKGO":
            self.search_function = lambda query: search_with_duckduckgo(
                query
            )
        else:
            raise RuntimeError("Backend must be DUCKDUCKGO, SERPER or GOOGLE.")
        
        # An executor to carry out async tasks, such as uploading to KV.

        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.handler_max_concurrency * 2
        )

        self.CLIENT=os.environ["CLIENT"].upper()
        print("LLM_CLIENT: ",self.CLIENT)

        if self.CLIENT=="OPENAI":
            self.client=openai_client()
        elif self.CLIENT=="TOGETHER":
            self.client=togetherai_client()
        elif self.CLIENT=="HF_TGI":
            self.client=hf_tgi_client()
        elif self.CLIENT=="OLLAMA":
            self.client=ollama_client()

    def get_related_questions(self, query, contexts):
        """
        Gets related questions based on the query and context.
        """

        def ask_related_questions(
            questions: Annotated[
                List[str],
                [(
                    "question",
                    Annotated[
                        str, "related question to the original question and context."
                    ],
                )],
            ]
        ):
            """
            ask further questions that are related to the input and output.
            """
            pass
        
        if  self.CLIENT=='OPENAI':
            try:
                response = self.client.chat.completions.create(
                    model=os.environ["OPENAI_LLM"],
                    messages=[
                        {
                            "role": "system",
                            "content": _more_questions_prompt.format(
                                context="\n\n".join([c["snippet"] for c in contexts])
                            ),
                        },
                        {
                            "role": "user",
                            "content": query,
                        },
                    ],
                    tools=[{
                        "type": "function",
                        "function": tool.get_tools_spec(ask_related_questions),
                    }],
                    max_tokens=512,
                )
                related = response.choices[0].message.tool_calls[0].function.arguments
                logger.error(f"related*****: {related}")


                if isinstance(related, str):
                    related = json.loads(related)
                logger.trace(f"Related questions: {related}")
                return related["questions"][:5]
            except Exception as e:
                # For any exceptions, we will just return an empty list.

                logger.error(
                    "encountered error while generating related questions:"
                    f" {e}\n{traceback.format_exc()}"
                )
                return []
        else:
            try:
                if self.CLIENT == "OLLAMA":
                    llm_model = os.environ["OLLAMA_LLM"]
                elif self.CLIENT == "HF_TGI":
                    llm_model = os.environ["HF_TGI_LLM"]
                else:
                    llm_model = os.environ["TOGETHER_LLM"]
                response = self.client.chat.completions.create(
                    model=llm_model,
                    messages=[
                        {
                            "role": "system", # for llama3 change this to system
                            "content": _more_questions_prompt_no_tool_call.format(
                                context="\n\n".join([c["snippet"] for c in contexts])
                            ),
                        },
                        {
                            "role": "user",  # for llama3 change this to user
                            "content": query,
                        },
                    ],
                    max_tokens=512,
                )
                related = response.choices[0].message.content
                #some post processing on the response

                related=extract_all_json(related)

                logger.error(f"related*****: {related}")

                if isinstance(related, str):
                    related = json.loads(related)
                logger.trace(f"Related questions: {related}")
                return related["questions"][:5]
            except Exception as e:
                logger.error(
                    "encountered error while generating related questions:"
                    f" {e}\n{traceback.format_exc()}"
                )
                return []   

    def _raw_stream_response(
        self, contexts, llm_response, related_questions_future
    ) -> Generator[str, None, None]:
        """
        A generator that yields the raw stream response. You do not need to call
        this directly.
        """
        # First, yield the contexts.
        yield json.dumps(contexts)
        yield "\n\n__LLM_RESPONSE__\n\n"
        # Second, yield the llm response.
        if not contexts:
            # Prepend a warning to the user
            yield (
                "(The search engine returned nothing for this query. Please take the"
                " answer with a grain of salt.)\n\n"
            )
        for chunk in llm_response:
            if chunk.choices:
                yield chunk.choices[0].delta.content or ""
        if related_questions_future is not None:
            related_questions = related_questions_future.result()
            try:
                result = json.dumps(related_questions)
            except Exception as e:
                logger.error(f"encountered error: {e}\n{traceback.format_exc()}")
                result = "[]"
            yield "\n\n__RELATED_QUESTIONS__\n\n"
            yield result

    def stream_response(
        self, contexts, llm_response, related_questions_future, search_uuid
    ) -> Generator[str, None, None]:
        """
        Streams the result and uploads to KV.
        """
        # First, stream and yield the results.
        all_yielded_results = []
        for result in self._raw_stream_response(
            contexts, llm_response, related_questions_future
        ):
            all_yielded_results.append(result)
            yield result

    @Photon.handler(method="POST", path="/query")
    def query_function(
        self,
        query: str,
        search_uuid: str,
        generate_related_questions: Optional[bool] = True,
    ) -> StreamingResponse:
        """
        Query the search engine and returns the response.

        The query can have the following fields:
            - query: the user query.
            - search_uuid: a uuid that is used to store or retrieve the search result. If
                the uuid does not exist, generate and write to the kv. If the kv
                fails, we generate regardless, in favor of availability. If the uuid
                exists, return the stored result.
            - generate_related_questions: if set to false, will not generate related
                questions. Otherwise, will depend on the environment variable
                RELATED_QUESTIONS. Default: true.
        """

        # First, do a search query.
        query = query or _default_query
        # logger.error(f"query*****: {query}")
        query = re.sub(r"\[/?INST\]", "", query)
        contexts = self.search_function(query)

        system_prompt = _rag_query_text.format(
            context="\n\n".join(
                [f"[[citation:{i+1}]] {c['snippet']}" for i, c in enumerate(contexts)]
            )
        )

        try:
            client = self.client

            if self.CLIENT == "OLLAMA":
                llm_model = os.environ["OLLAMA_LLM"]
            elif self.CLIENT == "HF_TGI":
                llm_model = os.environ["HF_TGI_LLM"]
            elif self.CLIENT == "TOGETHER":
                llm_model = os.environ["TOGETHER_LLM"]
            else:
                llm_model = os.environ["OPENAI_LLM"]
            
            llm_response = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},  # for mixtral change this to user
                    {"role": "user", "content": query},   # for mixtral change this to assistant
                ],
                max_tokens=4000,
                stream=True,
                temperature=0.7,
            )

            if  generate_related_questions:
                related_questions_future = self.executor.submit(
                    self.get_related_questions, query, contexts
                )
            else:
                related_questions_future = None

        except Exception as e:
            logger.error(f"encountered error: {e}\n{traceback.format_exc()}")
            return HTMLResponse("Internal server error.", 503)

        return StreamingResponse(
            self.stream_response(
                contexts, llm_response, related_questions_future, search_uuid
            ),
            media_type="text/html",
        )

    @Photon.handler(mount=True)
    def ui(self):
        return StaticFiles(directory="ui")

    @Photon.handler(method="GET", path="/")
    def index(self) -> RedirectResponse:
        """
        Redirects "/" to the ui page.
        """
        return RedirectResponse(url="/ui/index.html")