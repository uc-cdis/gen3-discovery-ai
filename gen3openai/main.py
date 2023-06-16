import ast
from contextlib import asynccontextmanager
import pandas as pd
import time
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import FastAPI
from fastapi import HTTPException
from importlib.metadata import version

from gen3openai import config, logging
from gen3openai.openai import openai_router


def get_app():
    app = FastAPI(
        title="Gen3 OpenAI Wrapper Service",
        version=version("gen3openai"),
        debug=config.DEBUG,
        root_path=config.URL_PREFIX,
        lifespan=lifespan,
    )
    app.include_router(router)
    app.include_router(openai_router)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPIs way of dealing with startup logic before the app
    starts receiving requests

    https://fastapi.tiangolo.com/advanced/events/#lifespan
    """
    # read from config to get more options
    config.topics = {}

    try:
        config.topics["default"] = {
            "embeddings": await _get_embeddings_dataframe(
                config.DEFAULT_EMBEDDINGS_PATH
            ),
            "system_prompt": config.DEFAULT_SYSTEM_PROMPT,
        }
        logging.info(
            f"Added topic `default` with embeddings: `{config.DEFAULT_EMBEDDINGS_PATH}`"
        )
    except Exception as exc:
        logging.error(
            f"Unable to load default configured embeddings "
            f"from here: {config.DEFAULT_EMBEDDINGS_PATH}. Exception: {exc}"
        )
        raise

    for topic in config.TOPICS.split(","):
        if topic == "default":
            continue

        embeddings_config_key = f"{topic.upper()}_EMBEDDINGS_PATH"
        system_prompt_config_key = f"{topic.upper()}_SYSTEM_PROMPT"

        embeddings_config_value = getattr(config, embeddings_config_key, None)
        system_prompt_config_value = getattr(config, system_prompt_config_key, None)

        try:
            config.topics[topic] = {
                "embeddings": await _get_embeddings_dataframe(embeddings_config_value),
                "system_prompt": system_prompt_config_value,
            }
            logging.info(
                f"Added topic `{topic}` with embeddings from: `{embeddings_config_value}`"
            )
        except Exception as exc:
            logging.error(
                f"Unable to load configured embeddings for topic "
                f"`{topic}` from here: {embeddings_config_value}. Exception: {exc}"
            )
            continue

    yield

    config.topics.clear()


async def _get_embeddings_dataframe(path):
    embeddings_dataframe = pd.read_csv(path)
    embeddings_dataframe["embedding"] = embeddings_dataframe["embedding"].apply(
        ast.literal_eval
    )

    return embeddings_dataframe


router = APIRouter()


@router.get("/")
def read_root():
    return {"Hello": "World"}


@router.get("/version")
def get_version():
    return version("gen3openai")


@router.get("/_status")
async def get_status():
    return dict(status="OK", timestamp=time.time())


app = get_app()
