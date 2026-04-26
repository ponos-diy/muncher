#!/bin/bash
set -e
set -x
scriptdir=$(cd $(dirname $0) && pwd)
mkdir -p ./out
podman run \
  --mount type=bind,src=$scriptdir,target=/src,ro \
  --mount type=bind,src=./out,target=/out \
  docker.io/library/python:latest \
  bash -c "python -m pip install build && python -m build --outdir /out /src"
