from pathlib import Path
import tempfile
import zipfile
import logging

from model import model

import gradio as gr
from fastapi import FastAPI
import time
import tqdm
import sys

import whisper
import whisper.transcribe


MAX_CONTENT_LENGTH_MINUTES = 60
CUSTOM_PATH = "/openai-whisper"
app = FastAPI()

@app.get("/")
def read_main():
    return {"status": "ok"}


def get_media_length_seconds(file_path):
    import subprocess
    cmd = f"    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'"
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
            done_percent = float(self._current) / float(self.total) * 0.96 + 0.02
            progress(done_percent, "Started Transcription...")
            logging.warning('init: %s / %s', self._current, self.total)

        def update(self, n):
            self._current += n
            elapsed = time.time() - self._ts
            done_percent = float(self._current) / float(self.total) * 0.96 + 0.02
            total_duration = elapsed / done_percent
            total_remaining = int((1 - done_percent) * total_duration)

            progress(done_percent, "Running. Estimated Time Left: " + format_dt(total_remaining) + " ")
            logging.warning('update: %s / %s', self._current, self.total)

            if self._current >= self.total:
                logging.warning('pgbar close')
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_value, exc_tb):
            pass

    return _CustomProgressBar


def SpeechToText(audio_or_video_file, progress=gr.Progress()):
    # Inject into tqdm.tqdm of Whisper, so we can see progress
    transcribe_module = sys.modules['whisper.transcribe']
    orig_tqdm = transcribe_module.tqdm.tqdm
    new_tqdm = get_progressbar_cls(progress)
    transcribe_module.tqdm.tqdm = new_tqdm

    if audio_or_video_file is None:
        msg = " <<< Please upload one Audio or Video file, max {MAX_CONTENT_LENGTH_MINUTES} min. Do not refresh the page."
        return [msg, None, None, None]
    progress(0.0, "Checking file...")
    media_length = int(get_media_length_seconds(audio_or_video_file.name) / 60)
    if media_length > MAX_CONTENT_LENGTH_MINUTES * 1.1:
        msg = f"""Error: File too long.

        Limit: {MAX_CONTENT_LENGTH_MINUTES} min.

        Your submission: {media_length} min.
        """
        return [msg, None, None, None]

    progress(0.01, "Detecting Language...")

    input_filename = Path(audio_or_video_file.name).name
    transcript = whisper.transcribe(model, audio_or_video_file.name, verbose=False, fp16=False)
    language = transcript['language']
    text = transcript['text']

    progress(0.99, "Zipping results...")

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

    return (language, srt, text, temp_zipfile.name)


demo = gr.Interface(
    title = 'OpenAI Whisper - Multilingual Transcription Service', 
    fn=SpeechToText, 

    inputs=[
        # gr.Audio(source="upload", type="filepath")
        gr.File(file_types=['audio', 'video'], type="file"),
    ],
    outputs=[
        gr.Label(label="Language"),
        gr.Textbox(label="SRT Subtitle"),
        gr.Textbox(label="Text"),
        gr.File(label="Output Zip"),
    ],
    live=True,
    allow_flagging="never",
    analytics_enabled=False,
)
demo.queue(concurrency_count=1)
app = gr.mount_gradio_app(app, demo, path=CUSTOM_PATH)
# demo.launch(
#     debug=True,
#     share=False,
#     enable_queue=True,
#     show_api=True,
#     server_port=8000,
#     server_name="0.0.0.0",
# )
