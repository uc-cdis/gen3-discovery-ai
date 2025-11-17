ARG AZLINUX_BASE_VERSION=3.13-pythonnginx

# Base stage with python-build-base
FROM quay.io/cdis/amazonlinux-base:${AZLINUX_BASE_VERSION} AS base

ENV appname=gen3discoveryai

WORKDIR /$appname

RUN chown -R gen3:gen3 /${appname}

# Builder stage
FROM base AS builder

# RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
#     kernel-devel libffi-devel libxml2-devel libxslt-devel postgresql-devel python3-devel \
#     git && yum clean all

USER gen3

# copy ONLY poetry artifact, install the dependencies but not gen3discoveryai
# this will make sure that the dependencies are cached
COPY poetry.lock pyproject.toml /$appname/
COPY ./docs/openapi.yaml /$appname/docs/openapi.yaml

RUN poetry install -vv --without dev --no-interaction

# copy source code and needed files ONLY after installing dependencies
COPY --chown=gen3:gen3 . /$appname

# Run poetry again so this app itself gets installed too
RUN poetry install --without dev --no-interaction

# Creating the runtime image
FROM base

USER gen3

COPY --from=builder /${appname} /${appname}
COPY --from=builder /venv /venv
WORKDIR /${appname}
EXPOSE 80

RUN pip list

# Cache the necessary tiktoken encoding file
RUN poetry run python -c "from langchain_classic.text_splitter import TokenTextSplitter; TokenTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=0)"

CMD ["poetry", "run", "gunicorn", "gen3discoveryai.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py"]
