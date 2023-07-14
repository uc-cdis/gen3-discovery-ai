import json
import re
import os
import copy
import json
import openai
import pandas as pd
import ast
from scipy import spatial
import time
import tiktoken

from fastapi import HTTPException, APIRouter, Depends
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_429_TOO_MANY_REQUESTS,
)

from gen3openai import config, logging

openai_router = APIRouter()


@openai_router.get("/topics/{provided_topic}")
@openai_router.get("/topics/")
async def ask(provided_topic: str = None):
    output = {}
    for topic, values in config.topics.items():
        copied_values = copy.deepcopy(values)
        del copied_values["embeddings"]["text"]
        del copied_values["embeddings"]["embedding"]
        output[topic] = copied_values

    if provided_topic:
        output = {topic: output[topic]}

    return {
        "topics": output,
    }


@openai_router.post("/ask/")
async def ask(data: dict, topic: str = "default"):
    response = config.topics.get(topic, None)

    query = data.get("query", "")

    if not query:
        logging.debug("no query provided")

    start_time = time.time()
    try:
        response = ask(query=query, topic=topic)
    except openai.error.RateLimitError:
        raise HTTPException(HTTP_429_TOO_MANY_REQUESTS, f"Please try again later.")

    end_time = time.time()

    response.update({"openai_time": end_time - start_time})

    return response


def ask(
    query: str,
    topic: str,
    model: str = config.CHAT_MODEL,
    token_budget: int = 4096 - 500,
):
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    df = config.topics["default"]["embeddings"]

    message, sources = query_message(
        query,
        df,
        model=model,
        token_budget=token_budget,
    )

    system_prompt = None
    if topic in config.topics:
        system_prompt = config.topics[topic]["system_prompt"]

    if not system_prompt:
        logging.info(
            f"Requested topic `{topic}` does not have a configured system prompt "
            f"Using default."
        )
        system_prompt = config.topics["default"]["system_prompt"]

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {"role": "user", "content": message},
    ]

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
        api_key=str(config.OPENAI_API_KEY).strip(),
    )
    response_message = response["choices"][0]["message"]["content"]

    return {"response": response_message, "sources": sources}


def query_message(
    query: str, df: pd.DataFrame, model: str, token_budget: int
) -> tuple[str, list[str]]:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatedness, paths = strings_ranked_by_relatedness(query, df)
    introduction = ""
    question = f"\n\nQuestion: {query}"
    message = introduction
    num_messages = 0
    for string in strings:
        next_article = f'\n\nDocumentation:\n"""\n{string}\n"""'
        if count_tokens(message + next_article + question) > token_budget:
            break
        else:
            num_messages += 1
            message += next_article
    return message + question, paths[0:num_messages]


# search function
def strings_ranked_by_relatedness(
    query: str,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 100,
) -> tuple[list[str], list[float], list[str]]:
    """Returns a list of strings and relatedness, sorted from most related to least."""
    query_embedding_response = openai.Embedding.create(
        model=config.EMBEDDINGS_MODEL,
        input=query,
        api_key=str(config.OPENAI_API_KEY).strip(),
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]
    strings_and_relatedness = [
        (row["text"], relatedness_fn(query_embedding, row["embedding"]), row["path"])
        for i, row in df.iterrows()
    ]
    strings_and_relatedness.sort(key=lambda x: x[1], reverse=True)
    strings, relatedness, path = zip(*strings_and_relatedness)
    return strings[:top_n], relatedness[:top_n], path


def count_tokens(text):
    encoding = tiktoken.encoding_for_model(config.EMBEDDINGS_MODEL)
    return len(encoding.encode(text))
