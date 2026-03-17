#!/bin/bash

nginx
poetry run gunicorn gen3discoveryai.main:app -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py --user gen3 --group gen3
