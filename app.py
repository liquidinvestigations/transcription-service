import datetime
import os
from pathlib import Path
import tempfile
import zipfile
import logging
import time
import sys

from model import MODEL_NAMES
from autodelete import AUTODELETE_AGE_H

import gradio as gr
from fastapi import FastAPI
# import tqdm

import whisper
import whisper.transcribe

log = logging.getLogger(__name__)
log.warning('configuring app...')

CONCURRENCY_COUNT = int(os.getenv('CONCURRENCY_COUNT') or '1')
log.warning('concurrency = %s', CONCURRENCY_COUNT)

MAX_CONTENT_LENGTH_MINUTES = 60
CUSTOM_PATH = "/openai-whisper"
app = FastAPI()


@app.get("/")
def read_main():
    return {"status": "ok"}


def get_media_length_seconds(file_path):
    import subprocess
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'"
    return float(subprocess.check_output(cmd, shell=True).decode('ascii'))


def format_dt(total_remaining):
    if total_remaining > 120:
        remaining_txt = str(int(total_remaining / 60)) + ' minutes'
    else:
        remaining_txt = str(int(total_remaining)) + ' seconds'
    return remaining_txt


def get_progressbar_cls(progress):
    class _CustomProgressBar():
        def __init__(self, *args, **kwargs):
            self._current = 0
            self._ts = time.time()
            self.total = kwargs['total']
            done_percent = float(self._current) / \
                float(self.total) * 0.96 + 0.02
            progress(done_percent, "Started Transcription...")
            logging.warning('init: %s / %s', self._current, self.total)

        def update(self, n):
            self._current += n
            elapsed = time.time() - self._ts
            done_percent = float(self._current) / \
                float(self.total) * 0.96 + 0.02
            total_duration = elapsed / done_percent
            total_remaining = int((1 - done_percent) * total_duration)

            progress(done_percent, "Running. Estimated Time Left: " +
                     format_dt(total_remaining) + " ")
            logging.warning('update: %s / %s', self._current, self.total)

            if self._current >= self.total:
                logging.warning('pgbar close')

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, exc_tb):
            pass

    return _CustomProgressBar


def SpeechToText(_markdown_helptext, audio_or_video_file, model_name, progress=gr.Progress()):
    t0 = time.time()

    # Inject into tqdm.tqdm of Whisper, so we can see progress
    transcribe_module = sys.modules['whisper.transcribe']
    orig_tqdm = transcribe_module.tqdm.tqdm
    new_tqdm = get_progressbar_cls(progress)
    transcribe_module.tqdm.tqdm = new_tqdm

    if audio_or_video_file is None:
        msg = ""
        return [msg, None, None, None]
    progress(0.0, "Checking file...")
    media_length = round(get_media_length_seconds(
        audio_or_video_file.name) / 60, 2)
    if media_length > MAX_CONTENT_LENGTH_MINUTES * 1.2:
        msg = f"""Error: File too long.

        Track Length Limit: {MAX_CONTENT_LENGTH_MINUTES} min.

        Your submission: {media_length} min.
        """
        return [msg, None, None, None]

    progress(0.01, "Detecting Language...")

    transcript = whisper.transcribe(
        whisper.load_model(model_name),
        audio_or_video_file.name,
        verbose=False,
        fp16=False,
    )
    language = transcript['language']
    text = transcript['text']

    progress(0.99, "Zipping results...")

    input_filename = Path(audio_or_video_file.name).name
    with tempfile.NamedTemporaryFile(suffix='-transcript.zip',
                                     prefix=input_filename + '-', delete=False) as temp_zipfile:
        with tempfile.TemporaryDirectory() as transcribe_dir:
            writer = whisper.utils.get_writer("all", transcribe_dir)
            writer(transcript, "transcript")
            with open(Path(transcribe_dir) / 'transcript.srt', 'r') as f:
                srt = f.read()
            with zipfile.ZipFile(temp_zipfile, mode="w") as archive:
                for file_path in Path(transcribe_dir).iterdir():
                    archive.write(file_path, arcname=file_path.name)

    progress(1, "Done.")

    # remove monkeypatch
    transcribe_module.tqdm.tqdm = orig_tqdm
    del new_tqdm

    proc_time_min = round((time.time() - t0) / 60, 2)
    speed_x = round((media_length / (0.01 + proc_time_min)), 2)
    media_length_str = str(datetime.timedelta(seconds=int(60*media_length)))
    proc_time_str = str(datetime.timedelta(seconds=int(60*proc_time_min)))
    info_msg = f"""
    ## Result Info
    ###  _Language:_ {language}
    ###  _Track Length:_ {media_length_str}
    ###  _Processing time:_ {proc_time_str}
    ###  _Speed:_ {speed_x}x ({model_name})
    """
    return (info_msg, temp_zipfile.name, srt, text)


DEFAULT_MODEL = MODEL_NAMES[int(len(MODEL_NAMES)/2)]
demo = gr.Interface(
    title='OpenAI Whisper - Multilingual Transcription Service',
    fn=SpeechToText,

    inputs=[
        gr.Markdown(
            f"""
            ## Upload Limit

            Audio or Video files, **at most {MAX_CONTENT_LENGTH_MINUTES} minutes** in length.

            ## Speed

            - Tiny model speed ~= 5x
            - Small model speed ~= 2.5x
            - Medium model speed ~= 1.2x
            - Large(-v2) model speed ~= 0.6x

            ## Notice

            - **Do not refresh the page**; you will lose all progress.
                - Do not let your computer sleep while operation finishes.
            - Zip file download link valid for {AUTODELETE_AGE_H}h after creation.
            - Transcription Service does not log username or identity.

            """
        ),
        gr.File(
            file_types=['audio', 'video'], type="file", label="File",
            info=f"Audio or Video files under {MAX_CONTENT_LENGTH_MINUTES} minutes in length.",
        ),
        gr.Dropdown(
            MODEL_NAMES, value=DEFAULT_MODEL, label="Model",
            info="Bigger model means slower & more accurate results."
        ),
    ],
    outputs=[
        gr.Markdown(label="Result Info", info='Output Info.'),
        gr.File(label="Output Zip",
                info=f'Link available for {AUTODELETE_AGE_H}h, only for people with the link.'),
        gr.Textbox(label="SRT Subtitle",
                   info='Subtitle format with timecodes.'),
        gr.Textbox(label="Text", info='All text.'),
    ],
    live=True,
    allow_flagging="never",
    analytics_enabled=False,
)
demo.queue(concurrency_count=CONCURRENCY_COUNT)
log.warning('starting server...')
gr_app = gr.mount_gradio_app(app, demo, path=CUSTOM_PATH)
