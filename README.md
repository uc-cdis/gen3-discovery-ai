# Gen3 OpenAI Wrapper Service

A proof of concept wrapper service around OpenAI's API that allows for
configuring multiple topics with different embeddings and system prompts.

Blatantly steals code from https://github.com/uc-cdis/ask-gen3

## Quickstart

Create OpenAI API Account and get OpenAI API key (you have to attach a credit card).
https://platform.openai.com

> NOTE: You should set a reasonable spend limit, the default is large

Now create a `.env` file:

```.env
OPENAI_API_KEY=REDACTED
```

Install and run service locally:

```
poetry install
python run.py
```

Hit the API:

```
curl --location 'http://127.0.0.1:8000/ask/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{"query": "Do you have COVID data?"}'
```

Ask for configured topics:

```
curl --location 'http://127.0.0.1:8000/topics/' \
--header 'Accept: application/json'
```

## Configure Topics

Topics are a combination of embeddings and system prompt. This service
can support multiple topics at once, switching between the necessary pre-loaded
embeddings and prompts.

So you can have a topic of "Gen3 Documentation" and "BDC Datasets" at the same
time and switch between them.

See `gen3openai/config.py` for details.

You can configure more topics in a `.env` file.

```
TOPICS=default,custom,anothertopic
CUSTOM_SYSTEM_PROMPT=You answer questions about datasets that are available in BioData Catalyst. You'll be given relevant dataset descriptions for every dataset that's been ingested into BioData Catalyst. You are acting as a search assistant for a biomedical researcher (who will be asking you questions). The researcher is likely trying to find datasets of interest for a particular research question. You should recommend datasets that may be of interest to that researcher.
CUSTOM_EMBEDDINGS_PATH=embeddings/embeddings.csv
ANOTHERTOPIC_SYSTEM_PROMPT=FOOBAR
ANOTHERTOPIC_EMBEDDINGS_PATH=embeddings/anothertopic.csv
```

## Manual Build, Upload to Private Quay Repo, and Pull into Dev Env

Manual upload to Quay

```
sudo docker build -t gen3-openai .
sudo docker tag gen3-openai quay.io/cdis/gen3-openai
docker login quay.io
sudo docker push quay.io/cdis/gen3-openai
```

Configure environment to read from private quay repo

* Give test account access
* Click on test robot account in quay
* Follow instructions for "Credentials for {account}" on the "Kubernetes Secret" tab

Configure g3auto secret with OpenAI API key

Add `gen3-openai` entry to "manifest.json"

Manually create service

```
g3kubectl apply -f "${GEN3_HOME}/kube/services/gen3-openai/gen3-openai-service.yaml"
gen3 roll gen3-openai
```

Make sure revproxy nginx conf has /openai routing to this service