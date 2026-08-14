# TEMPORARY: points at the base-images branch build (branch `feat/pythonuv`, where the workflow
# tags `$BRANCH_NAME-3.13-pythonpoetry`). Revert to `3.13-pythonpoetry` before
# merging, or main will build against a branch tag that eventually gets pruned.
ARG AZLINUX_BASE_VERSION=feat_pythonuv-3.13-pythonpoetry

# Base stage with python-poetry-base
FROM quay.io/cdis/amazonlinux-base:${AZLINUX_BASE_VERSION} AS base

ENV appname=gen3discoveryai

# Tooling and environment only: no application sources here, so a source-only change cannot
# invalidate the dependency layer in `builder`. poetry and the empty /venv it installs into
# both come from the base image.
WORKDIR /$appname

# The workdir has to stay writable by gen3: chromadb persists topic embeddings under
# ./knowledge at startup.
RUN chown -R gen3:gen3 /${appname}

# Builder stage
FROM base AS builder

# copy ONLY poetry artifact, install the dependencies but not gen3discoveryai
# this will make sure that the dependencies are cached
COPY --chown=gen3:gen3 poetry.lock pyproject.toml /$appname/

# --no-root because the project itself is installed further down, once its sources are in
RUN poetry install -vv --without dev --no-interaction --no-root

# copy source code and needed files ONLY after installing dependencies
COPY --chown=gen3:gen3 . /$appname

# Run poetry again so this app itself gets installed too
RUN poetry install --without dev --no-interaction

# Creating the runtime image
FROM base

# poetry installs the project as an editable package, so /venv holds a .pth pointing back at
# this source tree: both are needed at runtime.
COPY --from=builder /venv /venv
COPY --from=builder /${appname} /${appname}
WORKDIR /${appname}

# Cache the necessary tiktoken encoding file. Kept inside the app directory rather than
# tiktoken's default of /tmp, which a deployment can mount over or wipe, leaving the running
# service to fetch the encoding over the network on its first request.
ENV TIKTOKEN_CACHE_DIR=/${appname}/.tiktoken_cache
RUN python -c "from langchain_classic.text_splitter import TokenTextSplitter; TokenTextSplitter.from_tiktoken_encoder(chunk_size=100, chunk_overlap=0)"

# The base image already selects the non-root gen3 user, so USER is left alone everywhere.
CMD ["/bin/bash", "-c", "/${appname}/dockerrun.bash"]
