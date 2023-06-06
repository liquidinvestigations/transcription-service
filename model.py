import logging
import os

log = logging.getLogger(__name__)

import torch
NUM_THREADS = int(os.getenv('NUM_THREADS') or '4')
NUM_THREADS = min(NUM_THREADS, os.cpu_count())
torch.set_num_threads(NUM_THREADS)
log.warning('config: running torch on %s threads', NUM_THREADS)

import whisper

log = logging.getLogger(__name__)
log.warning('loading models...')

MODEL_NAMES = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2']
for name in MODEL_NAMES:
    log.warning('loading model: %s', name)
    whisper.load_model(name)
log.warning('done loading models.')
