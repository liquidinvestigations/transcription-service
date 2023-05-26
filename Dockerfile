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

# CMD [ "python3", "app.py"]
CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--server-header", "--date-header", "--timeout-graceful-shutdown", "30", "--no-access-log", "--log-level", "warning" ]
