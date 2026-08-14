#!/bin/bash

# One worker per container: this is an ASGI app, so concurrency comes from the event loop
# and scale comes from replicas.
#
# The shutdown window is generous because a single `/ask` request can spend minutes waiting
# on an LLM.
#
# --host is not configurable: uvicorn defaults to 127.0.0.1, and anything other than
# 0.0.0.0 here leaves the container listening where nothing can reach it.
#
# `exec` so uvicorn is PID 1 and gets SIGTERM directly: otherwise the container is killed
# outright, cutting in-flight requests and skipping the FastAPI lifespan shutdown.
exec uvicorn gen3discoveryai.main:app \
  --host 0.0.0.0 \
  --port "${UVICORN_PORT:-8000}" \
  --timeout-graceful-shutdown "${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-300}"
