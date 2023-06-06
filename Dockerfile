FROM python:3.11-bullseye

RUN apt update && apt install -y ffmpeg git

WORKDIR /app
RUN pip3 install pipenv
ADD Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile
# ADD requirements.txt ./
# RUN pip3 install -r requirements.txt

ENV GRADIO_SERVER_PORT 8000
ENV PYTHONUNBUFFERED TRUE
ENV GRADIO_ANALYTICS_ENABLED FALSE

ADD model.py ./

RUN python3 model.py

ADD app.py ./
ADD autodelete.py ./
ADD in-container.sh ./

CMD ./in-container.sh

ENV NUM_THREADS=16
ENV CONCURRENCY_COUNT=1
ENV AUTODELETE_AGE_H=6
