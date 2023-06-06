#!/bin/bash
set -ex
IMG="liquidinvestigations/openai-whisper-gradio:main"
IMG_TAG="liquidinvestigations/openai-whisper-gradio:v0.1"
NAME=whisper
docker rm -f $NAME
docker build . --tag $IMG
docker run -d --rm --name $NAME -p 8000:8000 $IMG
( set +x; docker push $IMG && ( echo UPLOADED $IMG TO DOCKER HUB ) || echo "\n[WARNING] CANNOT PUSH TO DOCKER HUB \n" ) &
docker logs -f $NAME
