ARG AZLINUX_BASE_VERSION=master

# Base stage with python-build-base
FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

ENV appname=gen3discoveryai

WORKDIR /$appname

RUN chown -R gen3:gen3 /${appname}

# Builder stage
FROM base AS builder

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    kernel-devel libffi-devel libxml2-devel libxslt-devel postgresql-devel python3-devel \
    git && yum clean all

USER gen3

RUN pip install --upgrade pip
RUN pip3 install --no-cache-dir --upgrade poetry

# copy ONLY poetry artifact, install the dependencies but not gen3discoveryai
# this will make sure that the dependencies are cached
COPY poetry.lock pyproject.toml /$appname/
COPY ./docs/openapi.yaml /$appname/docs/openapi.yaml
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --no-root --only main --no-interaction \
    && poetry show -v

# copy source code ONLY after installing dependencies
COPY --chown=gen3:gen3 . /$appname

# Run poetry again so this app itself gets installed too
RUN poetry lock -vv \
    && poetry install -vv --only main --no-interaction

RUN git config --global --add safe.directory /${appname} && COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" > /$appname/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >> /$appname/version_data.py

# install gen3discoveryai
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --only main --no-interaction \
    && poetry show -v

#Creating the runtime image
FROM base
ENV appname=gen3discoveryai

USER root

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    postgresql-devel shadow-utils\
    bash && yum clean all

COPY --from=builder /${appname} /${appname}

# Switch to non-root user 'gen3' for the serving process
USER gen3

WORKDIR /${appname}

EXPOSE 80

RUN pip3 install --no-cache-dir --upgrade poetry

# RUN useradd -ms /bin/bash appuser

# USER appuser

# Cache the necessary tiktoken encoding file
RUN poetry run python -c "from langchain.text_splitter import TokenTextSplitter; TokenTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=0)"

CMD ["poetry", "run", "gunicorn", "gen3discoveryai.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py"]
