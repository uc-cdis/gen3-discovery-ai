ARG AZLINUX_BASE_VERSION=master

# Base stage with python-build-base
FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

ENV appname=gen3discoveryai

WORKDIR /$appname

RUN chown -R gen3:gen3 /${appname}

# Builder stage
FROM base AS builder

USER gen3

COPY poetry.lock pyproject.toml /${appname}/

RUN poetry lock -vv --no-update \
    && poetry install -vv --only main --no-interaction

COPY --chown=gen3:gen3 . /$appname
# COPY --chown=gen3:gen3 ./deployment/wsgi/wsgi.py /$appname/wsgi.py

# RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
#     kernel-devel libffi-devel libxml2-devel libxslt-devel postgresql-devel python3-devel \
#     git && yum clean all


# Run poetry again so this app itself gets installed too
RUN poetry lock -vv --no-update \
    && poetry install -vv --only main --no-interaction

RUN git config --global --add safe.directory /${appname} && COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" > /$appname/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >> /$appname/version_data.py

# Final stage
FROM base

COPY --from=builder /${appname} /${appname}

# Switch to non-root user 'gen3' for the serving process
USER gen3

WORKDIR /${appname}

# #Creating the runtime image
# FROM quay.io/cdis/amazonlinux:python3.9-master

# ENV appname=gen3discoveryai

# USER root

# EXPOSE 80

# RUN pip3 install --no-cache-dir --upgrade poetry

# RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
#     postgresql-devel shadow-utils\
#     bash && yum clean all

# RUN useradd -ms /bin/bash appuser

# COPY --from=build-deps --chown=appuser:appuser /${appname} /${appname}

# WORKDIR /${appname}

# USER appuser

# Cache the necessary tiktoken encoding file
RUN poetry run python -c "from langchain.text_splitter import TokenTextSplitter; TokenTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=0)"

CMD ["poetry", "run", "gunicorn", "gen3discoveryai.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py"]
