import time
import uuid
from importlib.metadata import version
from typing import Any

import openai
from fastapi import APIRouter, HTTPException, Request
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from gen3discoveryai import config, logging
from gen3discoveryai.auth import (
    authorize_request,
    get_user_id,
    has_user_exceeded_limits,
    raise_if_global_ai_limit_exceeded,
)
from gen3discoveryai.topic_chains.logging import CustomCallbackHandlerForLogging

root_router = APIRouter()


@root_router.post("/ask/")
@root_router.post("/ask", include_in_schema=False)
async def ask_route(
    request: Request, data: dict, topic: str = "default", conversation_id: str = None
) -> dict:
    """
    Ask about the provided (or default) topic with the query provided.

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data (dict): Body from the POST, should contain `query`
        topic (str, optional): Query string `topic`, specific topic to ask about
        conversation_id (str, optional): Previous conv ID to continue the
            existing conversation. Must match a valid conversation ID for this
            user AND topic must support conversation-based queries.
    """
    await raise_if_global_ai_limit_exceeded()

    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=[f"/gen3_discovery_ai/ask/{topic}"],
    )
    user_id = await get_user_id(request=request)

    if not config.topics.get(topic, None):
        logging.debug(f"user provided topic not found: {topic}")
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="invalid topic, not found"
        )

    query = data.get("query")

    if not query:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="no query provided"
        )

    conversation = None
    if conversation_id:
        conversation = await _get_conversation_for_user(conversation_id, user_id)
        # TODO handle conversation

    if await has_user_exceeded_limits(request=request):
        logging.debug("has_user_exceeded_limits is True")
        raise HTTPException(
            HTTP_429_TOO_MANY_REQUESTS,
            "You've reached a limit for your user. Please try again later.",
        )

    start_time = time.time()
    try:
        topic_config = config.topics[topic]
        raw_response = topic_config["topic_chain"].run(
            query=query, callbacks=[CustomCallbackHandlerForLogging()]
        )
    except openai.error.RateLimitError:
        logging.debug("openai.error.RateLimitError")
        raise HTTPException(HTTP_429_TOO_MANY_REQUESTS, "Please try again later.")
    except openai.error.InvalidRequestError:
        logging.debug("openai.error.InvalidRequestError")
        raise HTTPException(
            HTTP_400_BAD_REQUEST,
            "Invalid request, you may have too much text in your query.",
        )
    except Exception as exc:
        logging.error(
            f"Returning service unavailable. Got unexpected error from chain: {exc}"
        )
        raise HTTPException(
            HTTP_503_SERVICE_UNAVAILABLE,
            "Service unavailable.",
        )

    logging.info(f"user_query={query}")

    end_time = time.time()
    logging.info(f"ask_time={end_time - start_time}")

    documents = []
    for doc in raw_response.get("source_documents"):
        parsed_doc = {
            "page_content": doc.page_content,
            "metadata": doc.metadata
        }
        documents.append(parsed_doc)

    response = {
        "response": raw_response.get("result"),
        "documents": documents,
    }

    # TODO
    if not conversation_id:
        conversation_id = await _get_conversation_id()
    await _store_conversation(user_id, conversation_id)
    response.update({"conversation_id": conversation_id})

    logging.debug(response)

    response.update({"topic": topic})
    return response


@root_router.get("/topics/{provided_topic}/")
@root_router.get("/topics/{provided_topic}", include_in_schema=False)
@root_router.get("/topics/")
@root_router.get("/topics", include_in_schema=False)
async def topics_route(request: Request, provided_topic: str = None) -> dict:
    """
    Get information about topic(s). Information includes the preconfigured
    topic chain name for the topic along with other metadata like the system
    prompt to the foundational model, among other things like the actual LLM
    model used under the hood.

    You are guaranteed the following per topic at the root:
        - `topic_chain`
        - `description`
        - `system_prompt`
        - `metadata`

    > NOTE: `metadata` may contain different things for different `topic_chains`

    Args:
        request (Request): FastAPI request (so we can check authorization)
        provided_topic (str, optional): optional specific topic to get info for
            if provided will filter out everything else

    Returns:
        dict: topic(s) requested in a standard format:
            ```
            {
              "topics": {
                "bdc": {
                  "description": "Ask about available BDC datasets...",
                  "topic_chain": "TopicChainQuestionAnswerRAG",
                  "system_prompt": "You answer questions about datasets...",
                  "metadata": {
                    "model_name": "gpt-3.5-turbo",
                    "model_temperature": "0.33",
                    "num_similar_docs_to_find": "4",
                    "similarity_score_threshold": "0.5"
                  }
                }
              }
            }
            ```
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_discovery_ai/topics"],
    )

    if provided_topic and not config.topics.get(provided_topic, None):
        raise HTTPException(status_code=404, detail="invalid topic")

    output = {}

    for topic, values in config.topics.items():
        output[topic] = {"topic_chain": values["topic_chain"].NAME}
        output[topic]["description"] = values.get("description", "")
        output[topic]["system_prompt"] = values.get("system_prompt", "")

        # metadata is whatever is left after removing the known values above
        output[topic]["metadata"] = {
            key: value
            for key, value in values.items()
            if key not in ["topic_chain", "description", "system_prompt"]
        }

    if provided_topic:
        output = {provided_topic: output[provided_topic]}

    return {
        "topics": output,
    }


@root_router.get("/_version/")
@root_router.get("/_version", include_in_schema=False)
async def get_version(request: Request) -> dict:
    """
    Return the version of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        dict: {"version": "1.0.0"} the version
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_discovery_ai/service_info/version"],
    )

    service_version = version("gen3discoveryai")

    return {"version": service_version}


@root_router.get("/_status/")
@root_router.get("/_status", include_in_schema=False)
async def get_status(request: Request) -> dict:
    """
    Return the status of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        dict: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_discovery_ai/service_info/status"],
    )
    return {"status": "OK", "timestamp": time.time()}


async def _get_conversation_id() -> str:
    # TODO
    return str(uuid.uuid4())


async def _store_conversation(user_id, conversation_id) -> None:
    # TODO
    pass


async def _get_conversation_for_user(conversation_id, user_id) -> Any:
    # TODO conversation for now
    #      should actually retrieve something based on conversation_id
    #      to see what user's conversation ID it is
    conversation = {"user_id": user_id}

    # you can't continue another user's conversation
    if conversation and conversation.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="invalid conversation_id")

    return None
