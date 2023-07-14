FROM quay.io/cdis/python:python3.9-buster-2.0.0 as base

FROM base as builder
RUN pip install --upgrade pip poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential gcc make musl-dev libffi-dev libssl-dev git curl bash

COPY . /cache/
COPY . /gen3openai/
WORKDIR /gen3openai
RUN python -m venv /env && . /env/bin/activate && poetry install --no-interaction --no-dev

FROM base
COPY --from=builder /env /env
COPY --from=builder /gen3openai /gen3openai
COPY --from=builder /cache /cache
ENV PATH="/env/bin/:${PATH}"

# Use cache for the tiktoken encoding file
ENV TIKTOKEN_CACHE_DIR="/cache"

WORKDIR /gen3openai

CMD ["/env/bin/gunicorn", "gen3openai.main:app", "-b", "0.0.0.0:80", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py"]
