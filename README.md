# Gen3 Discovery AI

Information discovery using generative artificial intelligence (AI). This service allows for configuring multiple topics
for users, so they can send queries and get intelligent AI-generated responses.

## ⚠️ IMPORTANT SETUP NOTES (READ FIRST)

- Python 3.14 is NOT supported (NumPy + LangChain incompatibility).  
  👉 Use Python 3.13.x
- Default backend is Google Vertex AI unless overridden.
- OpenAI users MUST set:
  DEFAULT_CHAIN_NAME=TopicChainOpenAiQuestionAnswerRAG
- The config file must be named exactly `.env` (not `.env.txt`).
- Windows users cannot use Linux-style curl. Use PowerShell Invoke-RestMethod.

**Table of Contents**

- [Overview](#overview)
- [Details](#details)
  - [Currently Supported Backends, Embeddings, and Models](#currently-supported-backends-embeddings-and-models)
  - [Background](#background)
- [Quickstart](#quickstart)
  - [Setup](#setup)
    - [Google Application Credentials](#google-application-credentials)
    - [OpenAI Key](#openai-key)
    - [Configuration](#configuration)
    - [Knowledge Library Population](#knowledge-library-population)
    - [Non-TSV Knowledge Loading](#non-tsv-and-non-markdown-knowledge-loading)
  - [Running locally](#running-locally)
- [Authz](#authz)
- [Local Dev](#local-dev)
  - [Automatically format code and run pylint](#automatically-format-code-and-run-pylint)
  - [Testing Docker Build](#testing-docker-build)
- [Contributing](#contributing)

## Overview

Provides an API for asking about specific pre-configured topics.

Most topics will augment queries with relevant information from a
knowledge library for that topic. Augmented queries will then be sent
to a foundation large language model (LLM) for a response.

## Details

This is intended to primarily support a [Retrieval Augmented Generation (RAG) architecture](https://arxiv.org/abs/2005.11401), where there is a
knowledge library related to a topic.

> The API itself is configurable *per* topic, so if a RAG architecture doesn't make sense for all topics, there is flexibility to support others.

In RAG, upon receiving a query, additional information is retrieved from a knowledge library, relevancy compared to
user query, and prompt to a foundation LLM is augmented with the
additional context from the knowledge library (alongside a configured system prompt
to guide the LLM on how it should interpret the context and respond).

### Currently Supported Backends, Embeddings, and Models

**AI Model Support:**
- ✅ Google Models (configurable, default model: `gemini-2.5-flash`)
  - See [their docs](https://ai.google.dev/gemini-api/docs/models#model-variations) for more model options
- ✅ OpenAI's Models (configurable, default model: `gpt-5-mini`)
  - See [their docs](https://platform.openai.com/docs/models) for more model options
- ✅ Locally hosted models using [Ollama](https://ollama.com/) (configurable, default model: `llama3.2`)
  - Other models untested, but should work. See [available models](https://ollama.com/library)
- :grey_question: AWS Models
- :grey_question: Open Source Models
- :grey_question: Trained/tuned model(s)
- :grey_question: Others

**Knowledge Library:**
- ✅ Chroma in-memory vector database
- :grey_question: Google Vertex AI Vector Search
- :grey_question: AWS Aurora Postgres with pgvector
- :grey_question: Others

**Knowledge Library Embeddings:**
- ✅ [Google Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- ✅ OpenAI Embeddings
- ✅ Ollama Embeddings

> Note: Our use of `langchain` makes adding new models and even architectures beyond RAG possible. Developers should look at the code in the `gen3discoveryai/topic_chains` folder. Also see the [contributing](#contributing) section in this doc.

### Background

Gen3 builds on other open source libraries, specifications, and tools when we can, and we tend to lean
towards the best tools in the community or research space as it evolves (especially in
cases where we're on the bleeding edge like this).

In the case of generative AI and LLMs,
there is a lot of excellent work out there. We are building this on the
shoulders of giants for many of the knowledge libraries and foundation model
interactions. We're using `langchain`, `chromadb`, among others.

We've even contributed back to open source tools like `chromadb` to improve its ability to operate in a FIPS-compliant
environment. :heart:

## Quickstart

## Windows + OpenAI Quickstart (Recommended)

This is the fastest working setup for most users.

### Step 1 — Install Python 3.13

Download and install Python 3.13.x (64-bit):  
https://www.python.org/downloads/windows/

✔ Make sure to check **Add Python to PATH**

---

### Step 2 — Clone repo

```powershell
git clone https://github.com/uc-cdis/gen3-discovery-ai.git
cd gen3-discovery-ai
```
### Setup

This documented examples here presume setting up:

- Google Vertex AI support
- OpenAI support
- Ollama support

> **IMPORTANT NOTE**: Ensure FedRAMP compliance where necessary.

It's unlikely you actually want to set up all these options, so take the parts of the setup and config for your particular needs.

If you're just trying things out, `Ollama` allows you to set up things fully locally, but can require significant GPU resources *depending on the model choice*. The default is fairly small (relative to other models in general), but you may want to find something even smaller if you run into performance issues.

#### Google Application Credentials

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable as the path to
a valid credentials JSON file (likely a service account key).

See [Google Cloud Platform docs](https://cloud.google.com/docs/authentication/application-default-credentials#GAC) for more info.

The credentials will need IAM permissions in a Google Project with Google Vertex AI enabled (which requires the setup
of a billing account). The IAM permissions required are captured in Google's predefined role: `Vertex AI User`.

#### OpenAI Key

Create [OpenAI API](https://platform.openai.com) Account and get OpenAI API key (you have to attach a credit card).

> NOTE: You should set a reasonable spend limit, the default is large

#### Ollama Setup

- [Download Ollama](https://github.com/ollama/ollama)
- Follow the directions to choose and download a model locally
  - The default is `llama3.2`, other models should work by adjusting the configuration, but you may run into issues as we have not tested all model options
- Ensure ollama is running

#### Configuration

Topics are a combination of system prompt, description, what topic chain to use, and additional metadata (usually used by the topic chain). This service
can support multiple topics at once with different topic chains.

You can have a topic of "Gen3 Documentation" and "Data Commons Datasets" at the same
time.

The configuration is done via a `.env` which allows environment variable overrides if you don't want to use the actual file.

Here's an example `.env` file you can copy and modify:

> As noted above, this contains topics for 3 different underlying AI models (Google, OpenAI, and Ollama). You should adjust these based on your needs.

```.env
########## Secrets ##########

OPENAI_API_KEY=REDACTED
GOOGLE_APPLICATION_CREDENTIALS=/home/user/creds.json

########## Topic Configuration ##########

# you must have `default`, you can add others a comma-separated string
TOPICS=default,openaitopic,ollamatopic,gen3docs

# default setup. These will be used both for the actual default topic AND as the value for subsequent topics
# when a configuration is not provided. e.g. if you don't provide FOOBAR_SYSTEM_PROMPT then the DEFAULT_SYSTEM_PROMPT
# will be used
DEFAULT_SYSTEM_PROMPT=You are acting as a search assistant for a researcher who will be asking you questions about data available in a particular system. If you believe the question is not relevant to data in the system, do not answer. The researcher is likely trying to find data of interest for a particular reason or with specific criteria. You answer and recommend datasets that may be of interest to that researcher based on the context you're provided. If you are using any particular context to answer, you should cite that and tell the user where they can find more information. The user may not be able to see the documents you are citing, so provide the relevant information in your response. If you don't know the answer, just say that you don't know, don't try to make up an answer. If you don't believe what the user is looking for is available in the system based on the context, say so instead of trying to explain how to go somewhere else.
DEFAULT_RAW_METADATA=model_name:gemini-2.5-flash,embedding_model_name:textembedding-gecko@003,model_temperature:0.3,max_output_tokens:512,num_similar_docs_to_find:7,similarity_score_threshold:0.6
DEFAULT_DESCRIPTION=Ask about available datasets, powered by public dataset metadata like study descriptions

# OpenAI topic configuration
OPENAITOPIC_DESCRIPTION=Ask about available datasets, powered by public dataset metadata like study descriptions
OPENAITOPIC_RAW_METADATA=model_name:gpt-5-mini,model_temperature:0.45,num_similar_docs_to_find:6,similarity_score_threshold:0.75
OPENAITOPIC_SYSTEM_PROMPT=You answer questions about datasets that are available in the system. You'll be given relevant dataset descriptions for every dataset that's been ingested into the system. You are acting as a search assistant for a biomedical researcher (who will be asking you questions). The researcher is likely trying to find datasets of interest for a particular research question. You should recommend datasets that may be of interest to that researcher.
OPENAITOPIC_CHAIN_NAME=TopicChainOpenAiQuestionAnswerRAG

# Ollama topic configuration
OLLAMATOPIC_SYSTEM_PROMPT=You are acting as a search assistant for a researcher who will be asking you questions about data available in a particular system. If you believe the question is not relevant to data in the system, do not answer. The researcher is likely trying to find data of interest for a particular reason or with specific criteria. You answer and recommend datasets that may be of interest to that researcher based on the context you're provided. If you are using any particular context to answer, you should cite that and tell the user where they can find more information. The user may not be able to see the documents you are citing, so provide the relevant information in your response. If you don't know the answer, just say that you don't know, don't try to make up an answer. If you don't believe what the user is looking for is available in the system based on the context, say so instead of trying to explain how to go somewhere else.
OLLAMATOPIC_RAW_METADATA=model_name:llama3.2,model_temperature:0.3,max_output_tokens:512,num_similar_docs_to_find:6,similarity_score_threshold:0.6
OLLAMATOPIC_DESCRIPTION=Ask about available datasets, powered by public dataset metadata like study descriptions
OLLAMATOPIC_CHAIN_NAME=TopicChainOllamaQuestionAnswerRAG

# another topic using default chain
GEN3DOCS_SYSTEM_PROMPT=You will be given relevant context from all the public documentation surrounding an open source software called Gen3. You are acting as an assistant to a new Gen3 developer, who is going to ask a question. Try to answer their question based on the context, but know that some of the context may be out of date. Let the developer know where they can get more information if relevant and cite portions of the context.
GEN3DOCS_RAW_METADATA=model_temperature:0.5,max_output_tokens:512,num_similar_docs_to_find:7,similarity_score_threshold:0.5
GEN3DOCS_DESCRIPTION=Ask about Gen3, powered by public markdown files in the UChicago Center for Translational Data Science's GitHub

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

In order to utilize the topic chains effectively, you likely need to store some data in the knowledge library.
You can write your own script or utilize the following.
This script currently supports loading from arbitrary TSVs or Markdown files in a directory.

> **IMPORTANT**: Make sure when using `/bin` scripts, the `.env` service configuration
> is set up and appropriately loaded (e.g. execute the script from a directory where there is
> a `.env` config). The `/bin` scripts REQUIRE loading the configuration in order to
> both load the available topics and to properly embed and load into the vectorstore.
>
> NOTE if you're using **Ollama**: The embedding process is pretty expensive locally, so if you don't have a great GPU it could fail (depending on the size of the data you're trying to load). If you're having issues, try using a smaller dataset or a more powerful GPU.

##### Loading TSVs

Here's the knowledge load script which takes a single required argument, being a directory where TSVs are.

See other options with `--help`:

```bash
poetry run python ./bin/load_into_knowledge_store.py tsvs --help
```
> NOTE: This expects that filenames for a specific topic start with that topic name.
> You *can* have multiple files per topic but they need to start with the topic name.
> You can also have nested directories, this will search recursively.

An example `/tsvs` directory:

```commandline
- default.tsv
- bdc/
    - bdc1.tsv
    - bdc2.tsv
```

Example run:

```bash
poetry run python ./bin/load_into_knowledge_store.py tsvs ./tsvs
```

> If you're using this for Gen3 Metadata, you can easily download public metadata
> from Gen3 to a TSV and use that as input (see our [Gen3 SDK Metadata functionality](https://github.com/uc-cdis/gen3sdk-python/blob/master/docs/howto/discoveryMetadataTools.md)
> for details).

##### Loading Markdown

There's an example script that downloads all the public markdown
files from our GitHub org. You can reference
the `bin/download_files_from_github.py` example script if interested.

Once you have Markdown files in a directory, you just need to use the
`./bin/load_into_knowledge_store.py` utility and supply the directory and topic.

See available options:

```bash
poetry run python ./bin/load_into_knowledge_store.py markdown --help
```

> **NOTE**: Unlike TSVs, loading from a Markdown directory requires specifying a single topic for all files in that directory.

Example run:

```bash
poetry run python ./bin/load_into_knowledge_store.py markdown --topic anothertopic ./bin/library
```

#### Non-TSV and Non-Markdown Knowledge Loading

If loading from TSVs or Markdown doesn't work easily for you, you should be able to
easily modify the `./bin/load_into_knowledge_store.py` script to your needs by using a different langchain document loader.

The base `TopicChain` class includes a `store_knowledge` method which expects a list
of `langchain` documents. This is the default output of
`langchain.text_splitter.TokenTextSplitter`. Langchain has numerous document loaders that can be
fed into the splitter already, so [check out the langchain documentation](https://python.langchain.com/docs/modules/data_connection/document_loaders).

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

#### Windows (PowerShell)

⚠️ Windows note: PowerShell aliases `curl` to `Invoke-WebRequest`.  
The Linux-style curl commands below will NOT work on Windows.  
Use the PowerShell example instead.


```powershell
Invoke-RestMethod -Uri "http://localhost:8089/ask/" `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"query":"Do you have COVID data?"}'
```

> You can change the port in the `run.py` as needed

Ask for configured topics:

```bash
curl --location 'http://0.0.0.0:8089/topics/' \
--header 'Accept: application/json'
```

## Authz

Relies on Gen3's Policy Engine.

- For `/topics` endpoints, requires `read` on `/gen3_discovery_ai/topics`
- For `/ask` endpoint, requires `read` on `/gen3_discovery_ai/ask/{topic}`
- For `/_version` endpoint, requires `read` on `/gen3_discovery_ai/service_info/version`
- For `/_status` endpoint, requires `read` on `/gen3_discovery_ai/service_info/status`

## Local Dev

You can `poetry run python run.py` after install to run the app locally.

For testing, you can `poetry run pytest`.

The default `pytest` options specified
in the `pyproject.toml` additionally:

* runs coverage and will error if it falls below the threshold
* profiles using [pytest-profiling](https://pypi.org/project/pytest-profiling/) which outputs into `/prof`

### Automatically format code and run pylint

This quick `clean.sh` script is used to run `isort` and `black` over everything if
you don't integrate those with your editor/IDE.

> NOTE: This requires the beginning of the setup for using Super
> Linter locally. You must have the global linter configs in
> `~/.gen3/.github/.github/linters`. See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1).

`clean.sh` also runs just `pylint` to check Python code for lint.

Here's how you can run it:

```bash
./clean.sh
```

> NOTE: GitHub's Super Linter runs more than just `pylint` so it's worth setting that up locally to run before pushing large changes. See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1) for full instructions. Then you can run pylint more frequently as you develop.

#### Testing Docker Build

To build:

```bash
docker build -t gen3discoveryai:latest .
```

To run:

```bash
docker run --name gen3discoveryai \
--env-file "./.env" \
-v "$GOOGLE_APPLICATION_CREDENTIALS":"$GOOGLE_APPLICATION_CREDENTIALS" \
-p 8089:8089 \
gen3discoveryai:latest
```

> NOTE: If you're using Ollama, you need to ensure it's available to the running container.

To exec into a bash shell in running container:

```bash
docker exec -it gen3discoveryai bash
```

To kill and remove running container:

```bash
docker kill gen3discoveryai
docker rm gen3discoveryai
```

## Contributing

Adding a new `Topic Chain`:

1. Add to `gen3discoveryai/topic_chains/`. Use others as reference. Inherit from base class.
2. Update `gen3discoveryai/topic_chains/__init__.py` to add new class
3. Update `gen3discoveryai/utils.py` to add new class and name
4. Update `README.md`
   - Add to top-level section describing capabilities
   - Add to example configuration
   - Add any additional notes elsewhere in the README as necessary
5. Write tests `tests/test_{{TOPIC_CHAIN}}`
   - Update the `tests/.env` and `tests/badcfg/.env` to add the new topic chain if necessary
6. Test it locally
7. Make a PR 😃
