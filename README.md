# Gen3 Discovery AI Service

Information discovery using generative artificial intelligence (AI). This service allows for configuring multiple topics
for users, so they can send queries and get intelligent AI-generated responses.

## Overview

Provides an API for querying about specific pre-configured topics. 

Most topics will augment queries with relevant information from a 
knowledge library for that topic. Augmented queries will then be sent 
to a foundational large language model (LLM) for a response. 

## Details

This is intended to primarily support a [Retrieval Augmented Generation (RAG) architecture](https://arxiv.org/abs/2005.11401), where there is a
knowledge library related to a topic.

> The API itself is flexible per topic, so if a RAG architecture doesn't make sense, there are options to support others in the future.

In RAG, upon receiving a query, additional information is retrieved from a knowledge library, relevancy compared to
user query, and prompt to a foundational LLM model is augmented with the 
additional context from the knowledge library (alongside a configured system prompt
to guide the LLM on how it should interpret the context and response).

### Initial support

    Knowledge Library:
        - Chromadb in-mem vector database
        - (TBD) Google Vertex AI Vector Search
        - (TBD) AWS Aurora Postgres with pgvector
        - (TBD) Others?

    Knowledge Library Embeddings:
        - Google Vertex AI PaLM Embeddings 
        - OpenAI Embeddings

    Foundational Model:
        - Google PaLM API Models (configurable, model:`chat-bison`)
        - OpenAI's Models (configurable, model: `gpt-3.5-turbo`)
        - (TBD) CTDS trained/tuned model
        - (TBD) AWS Bedrock?
        - (TBD) Others?

### Background

Gen3 builds on other open source libraries, specifications, and tools when we can, and we tend to lean
towards the best tools in the community or research space as it evolves (especially in 
cases where we're on the bleeding edge).

In the case of generative AI and LLMs,
there is a lot of excellent work out there. We are building this on the
shoulders of giants for many of the knowledge libraries and foundational model 
interactions. We're using `langchain`, `chromadb`, among others.

## Quickstart

### Setup

This documented setup all relies on our `TopicChainOpenAiQuestionAnswerRAG` Topic Chain, which is the default as of now.

#### OpenAI Key

Create [OpenAI API](https://platform.openai.com) Account and get OpenAI API key (you have to attach a credit card).

> NOTE: You should set a reasonable spend limit, the default is large

#### Configuration

Topics are a combination of system prompt, description, what topic chain to use, and additional metadata (usually used by the topic chain). This service
can support multiple topics at once.

You can have a topic of "Gen3 Documentation" and "Data Commons Datasets" at the same
time.

The configuration is done via a `.env` which allows environment variable overrides if you don't want to use the actual file.

Here's an example `.env` file you can copy and modify:

```.env
########## Secrets ##########

OPENAI_API_KEY=REDACTED

########## Topic Configuration ##########

# you must have `default`, you can add others a comma-separated string
TOPICS=default,anothertopic

# default setup. These will be used both for the actual default topic AND as the value for subsequent topics
# when a configuration is not provided. e.g. if you don't provide FOOBAR_SYSTEM_PROMPT then the DEFAULT_SYSTEM_PROMPT
# will be used
DEFAULT_SYSTEM_PROMPT=You are acting as a search assistant for a researcher who will be asking you questions about data available in a particular system. If you believe the question is not relevant to data in the system, do not answer. The researcher is likely trying to find data of interest for a particular reason or with specific criteria. You answer and recommend datasets that may be of interest to that researcher based on the context you're provided. If you are using any particular context to answer, you should cite that and tell the user where they can find more information. The user may not be able to see the documents you are citing, so provide the relevant information in your response. If you don't know the answer, just say that you don't know, don't try to make up an answer. If you don't believe what the user is looking for is available in the system based on the context, say so instead of trying to explain how to go somewhere else.
DEFAULT_RAW_METADATA=model_name:gpt-3.5-turbo,model_temperature:0.33,num_similar_docs_to_find:5,similarity_score_threshold:0.75
DEFAULT_DESCRIPTION=Ask about available datasets, powered by public dataset metadata like study descriptions

# Additional topic configurations
ANOTHERTOPIC_DESCRIPTION=Ask about available datasets, powered by public dataset metadata like study descriptions
ANOTHERTOPIC_RAW_METADATA=model_name:gpt-3.5-turbo,model_temperature:0.45,num_similar_docs_to_find:6,similarity_score_threshold:0.75
ANOTHERTOPIC_SYSTEM_PROMPT=You answer questions about datasets that are available in the system. You'll be given relevant dataset descriptions for every dataset that's been ingested into the system. You are acting as a search assistant for a biomedical researcher (who will be asking you questions). The researcher is likely trying to find datasets of interest for a particular research question. You should recommend datasets that may be of interest to that researcher.
ANOTHERTOPIC_CHAIN_NAME=TopicChainOpenAiQuestionAnswerRAG

########## Debugging and Logging Configurations ##########

# DEBUG makes the logging go from INFO to DEBUG
DEBUG=False

# VERBOSE_LLM_LOGS makes the logging for the chains much more verbose (useful to testing issues in the chain, but
# pretty noisy for any other time)
VERBOSE_LLM_LOGS=False

# DEBUG_SKIP_AUTH will COMPLETELY SKIP AUTHORIZATION for debugging purposes
DEBUG_SKIP_AUTH=False
```

The topic configurations are flexible to support arbitrary new names `{{TOPIC NAME}}_SYSTEM_PROMPT` etc. See `gen3discoveryai/config.py` for details.

#### Knowledge Library Population

Now you need to store some data in the knowledge library. You can write your own script or modify the following to get all the public metadata from a Gen3 instance using the Discovery Metadata API.

```bash
poetry run python ./bin/load_into_knowledge_store.py
```

The `TopicChain` class includes a `store_knowledge` method which expects a list of `langchain` documents. This is the default output of  `langchain.text_splitter.TokenTextSplitter`. Langchain has numerous document loaders that can be fed into the splitter already, so [check out the langchain documentation](https://python.langchain.com/docs/modules/data_connection/document_loaders).

### Running locally

Install and run service locally:

```bash
poetry install
poetry run python run.py
```

Hit the API:

```bash
curl --location 'http://0.0.0.0:8089/ask/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{"query": "Do you have COVID data?"}'
```

> You can change the port in the `run.py` as needed

Ask for configured topics:

```bash
curl --location 'http://0.0.0.0:8089/topics/' \
--header 'Accept: application/json'
```

## Authz

Relies on Gen3 Framework Service's Policy Engine.

- For `/topics` endpoints, requires `read` on `/gen3_discovery_ai/topics`
- For `/ask` endpoint, requires `read` on `/gen3_discovery_ai/ask/{topic}`
- For `/_version` endpoint, requires `read` on `/gen3_discovery_ai/service_info/version`
- For `/_status` endpoint, requires `read` on `/gen3_discovery_ai/service_info/status`

## Local Dev

You can `poetry run python run.py` after install to run the app locally.

For testing, you can `poetry run pytest`. The default `pytest` options specified 
in the `pyproject.toml` additionally 
runs coverage and will error if it falls below >95% that it's at now.

#### Automatically format code and run pylint

Quick script to run `isort` and `black` over everything if 
you don't integrate those with your editor/IDE.

> NOTE: This requires the beginning of the setup for using Super Linter locally. You must have the global linter configs in `~/.gen3/.github/.github/linters`

This also runs just `pylint` to check Python code for lint.

Here's the command:

```bash
./clean.sh
```

> NOTE: GitHub's Super Linter runs more than just `pylint` so it's worth setting that up locally to run before pushing large changes. See [this](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L7) for instructions. Then you can run pylint more frequently as you develop.

#### Testing Docker Build

The `Dockerfile` has some comments at the top with commands. Check that out.
