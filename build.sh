#!/bin/bash -ex
set -ex
IMG="liquidinvestigations/openai-whisper-gradio:main"
NAME=whisper
docker build . --tag $IMG
docker push $IMG || true
docker rm -f $NAME
docker run --rm --name $NAME -p 8000:8000 $IMG

