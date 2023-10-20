# Gen3 Discovery AI Service

Data discovery using AI. This service allows for configuring multiple topics
for users to send queries and get intelligent AI-generated responses.

## Overview

Provides an API for querying about specific pre-configured topics. 
Queries will be augmented with relevant information from a 
knowledge library for that topic. Augmented queries will then be sent 
to a foundational large language model 
for a response. 

## Details

This is a [Retrieval Augmented Generation (RAG) architecture](https://arxiv.org/abs/2005.11401), where there is a
knowledge library related to a topic. Upon receiving a query, additional information is retrieved from the library, relevancy compared to
user query, and prompt to a foundational AI LLM model is augmented with the 
additional context from the knowledge library and a system prompt.

**Initial support**

    Knowledge Library:
        - Chromadb in-mem vector database with OpenAI Embedding
            - Embedding model is configurable, default: `text-embedding-ada-002`
        - (TBD) AWS Aurora Postgres with pgvector w/ OpenAI Embeddings
        - (TBD) Others?

    Foundational Model:
        - OpenAI's Models (configurable, default: `gpt-3.5-turbo`)
        - (TBD) AWS Bedrock?
        - (TBD) Our own trained model?
        - (TBD) Others?

We build on other open source libraries and tools when we can, and in this case,
there is a lot of excellent work out there. We are building this on top of the
shoulders of giants for many of the knowledge libraries and foundational model 
interactions. We're using `langchain` and `chromadb`, among others.

## Quickstart

Create OpenAI API Account and get OpenAI API key (you have to attach a credit card).
https://platform.openai.com

> NOTE: You should set a reasonable spend limit, the default is large

Now create a `.env` file:

```.env
OPENAI_API_KEY=REDACTED
```

Install and run service locally:

```commandline
poetry install
python run.py
```

Hit the API:

```commandline
curl --location 'http://127.0.0.1:8000/ask/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{"query": "Do you have COVID data?"}'
```

Ask for configured topics:

```commandline
curl --location 'http://127.0.0.1:8000/topics/' \
--header 'Accept: application/json'
```

## Configure Topics

TODO: rework, topics should be combo of knowledge library and system prompt

Topics are a combination of embeddings and system prompt. This service
can support multiple topics at once, switching between the necessary pre-loaded
embeddings and prompts.

So you can have a topic of "Gen3 Documentation" and "BDC Datasets" at the same
time and switch between them.

See `gen3discoveryai/config.py` for details.

You can configure more topics in a `.env` file.

```txt
TOPICS=default,custom,anothertopic
CUSTOM_SYSTEM_PROMPT=You answer questions about datasets that are available in BioData Catalyst. You'll be given relevant dataset descriptions for every dataset that's been ingested into BioData Catalyst. You are acting as a search assistant for a biomedical researcher (who will be asking you questions). The researcher is likely trying to find datasets of interest for a particular research question. You should recommend datasets that may be of interest to that researcher.
CUSTOM_EMBEDDINGS_PATH=embeddings/embeddings.csv
ANOTHERTOPIC_SYSTEM_PROMPT=FOOBAR
ANOTHERTOPIC_EMBEDDINGS_PATH=embeddings/anothertopic.csv
```

## Manual Build, Upload to Private Quay Repository, and Pull into Dev Env

Manual upload to Quay

```commandline
sudo docker build -t gen3-openai .
sudo docker tag gen3-openai quay.io/cdis/gen3-openai
docker login quay.io
sudo docker push quay.io/cdis/gen3-openai
```

Configure environment to read from private quay repository

* Give test account access
* Click on test robot account in quay
* Follow instructions for "Credentials for {account}" on the "Kubernetes Secret" tab

Configure g3auto secret with OpenAI API key

Add `gen3-openai` entry to "manifest.json"

Manually create service

```commandline
g3kubectl apply -f "${GEN3_HOME}/kube/services/gen3-openai/gen3-openai-service.yaml"
gen3 roll gen3-openai
```

Make sure revproxy nginx conf has /openai routing to this service


## Authz

- For `/topics` endpoints, requires `read` on `/gen3_discovery_ai/topics`
- For `/ask` endpoint, requires `read` on `/gen3_discovery_ai/ask/{topic}`
- For `/_version` endpoint, requires `read` on `/gen3_discovery_ai/service_info/version`
- For `/_status` endpoint, requires `read` on `/gen3_discovery_ai/service_info/status`


## Local Dev

You can `python run.py` in a virtual environment.

### Automatically format

Quick script to run `isort` and `black` over everything if 
you don't integrate those with your editor/IDE:

```bash
./clean.sh
```

### Linting with Github's Super Linter Locally

See how to set up with [Visual Studio Code](https://github.com/super-linter/super-linter/blob/main/README.md#codespaces-and-visual-studio-code).

And/or use Docker to run locally.

First get the same linter config that Github is using. It's 
stored alongside our other global workflows and defaults in 
our `.github` repo.

```bash
git clone git@github.com:uc-cdis/.github.git ~/.gen3/.github
```

#### Modifying the Linter configs

#### Edit the `~/.gen3/linters/.isort.cfg` 

```env
known_first_party=gen3discoveryai
```

Now run super linter:

```bash
docker run --rm \
    -e RUN_LOCAL=true \
    --env-file "$HOME/.gen3/.github/.github/linters/super-linter.env" \
    -v "$HOME/.cache/pypoetry/virtualenvs":"/home/runner/.cache/pypoetry/virtualenvs" \
    -v "$HOME/.gen3/.github/.github/linters":"/tmp/lint/.github/linters" -v "$PWD":/tmp/lint \
    ghcr.io/super-linter/super-linter:slim-v5
```