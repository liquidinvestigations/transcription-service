#!/bin/bash
set -ex
IMG="liquidinvestigations/openai-whisper-gradio:main"
NAME=whisper
docker rm -f $NAME
docker build . --tag $IMG
docker run -d --rm --name $NAME -p 8000:8000 $IMG
( docker push $IMG || echo "\n[WARNING] CANNOT PUSH TO DOCKER HUB \n" ) &
docker logs -f $NAME
