import os
from contextlib import asynccontextmanager
from importlib.metadata import version

import fastapi
import yaml
from fastapi import FastAPI

from gen3discoveryai import config, logging
from gen3discoveryai.factory import Factory
from gen3discoveryai.routes import root_router
from gen3discoveryai.topic_chains.question_answer import (
    TopicChainQuestionAnswerRAG,  # ... import more here as implemented
)


def get_app() -> fastapi.FastAPI:
    """
    Return the web framework app object after adding routes

    Returns:
        fastapi.FastAPI: The FastAPI app object
    """

    fastapi_app = FastAPI(
        title="Gen3 Discovery AI Service",
        version=version("gen3discoveryai"),
        debug=config.DEBUG,
        root_path=config.URL_PREFIX,
        lifespan=lifespan,
    )
    fastapi_app.include_router(root_router)

    # this makes the docs at /doc and /redoc the same openapi docs in the docs folder
    # instead of the default behavior of generating openapi spec based from FastAPI
    fastapi_app.openapi = _override_generated_openapi_spec

    return fastapi_app


def _override_generated_openapi_spec():
    json_data = None
    try:
        # TODO make sure Dockerfile puts this in the right spot
        openapi_filepath = os.path.abspath("./docs/openapi.yaml")
        with open(openapi_filepath, "r") as yaml_in:
            json_data = yaml.safe_load(yaml_in)
    except FileNotFoundError:
        logging.warning(
            "could not find custom openapi at `docs/openapi.yaml`, using default generated one"
        )

    return json_data


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """
    Parse the configuration, setup and instantiate necessary classes.

    This is FastAPI's way of dealing with startup logic before the app
    starts receiving requests.

    https://fastapi.tiangolo.com/advanced/events/#lifespan

    Args:
        app (fastapi.FastAPI): The FastAPI app object
    """
    chain_factory = Factory()
    chain_factory.register(
        TopicChainQuestionAnswerRAG.NAME,
        TopicChainQuestionAnswerRAG,
    )
    # ... register more here as implemented

    # read from config to get more options
    config.topics = {}

    for topic in config.TOPICS.split(","):
        description_config_key = f"{topic.upper()}_DESCRIPTION"
        chain_config_key = f"{topic.upper()}_CHAIN_NAME"
        system_prompt_config_key = f"{topic.upper()}_SYSTEM_PROMPT"
        metadata_config_key = f"{topic.upper()}_METADATA"

        description_config_value = getattr(config, description_config_key, "")
        chain_config_value = getattr(config, chain_config_key, "")
        system_prompt_config_value = getattr(config, system_prompt_config_key, "")
        metadata_config_value = getattr(config, metadata_config_key, "")

        topic_raw_cfg = {
            "description": description_config_value,
            "topic_chain": chain_config_value,
            "system_prompt": system_prompt_config_value,
            "metadata": metadata_config_value,
        }

        try:
            config.topics[topic] = {
                "description": topic_raw_cfg["description"],
                "system_prompt": topic_raw_cfg["system_prompt"],
            }
            config.topics[topic].update(topic_raw_cfg["metadata"])

            chain_instance = chain_factory.get(
                topic_raw_cfg["topic_chain"],
                topic=topic,
                metadata=config.topics[topic],
            )
            config.topics[topic].update(
                {
                    "topic_chain": chain_instance,
                }
            )
            logging.info(f"Added topic `{topic}`")
            logging.debug(f"`{topic}` configuration: `{topic_raw_cfg}`")

        except Exception as exc:
            logging.error(
                f"Unable to load `{topic}` configuration with: {topic_raw_cfg}. Exception: {exc}"
            )
            continue

    yield

    config.topics.clear()


app = get_app()