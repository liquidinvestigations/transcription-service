"""Delete files from /tmp that match our download links and are older than configured age."""

import time
import os
import logging
import os
import stat
import tempfile


AUTODELETE_AGE_H = int(os.getenv('AUTODELETE_AGE_H') or '6')
log = logging.getLogger(__name__)

def file_age_in_hours(pathname):
    # https://stackoverflow.com/questions/6879364/print-file-age-in-seconds-using-python/6879539#6879539
    return round(int((time.time() - os.stat(pathname)[stat.ST_MTIME])) / 3600, 3)


def run_autodelete():
    log.info('running auto-delete...')
    parent_dir = tempfile.gettempdir()
    for filename in os.listdir(parent_dir):
        if not filename.endswith('-transcript.zip'):
            continue
        file = os.path.join(parent_dir, filename)

        age_hours = file_age_in_hours(file)
        if age_hours > AUTODELETE_AGE_H:
            log.warning('deleting file (age %s h): %s', age_hours, file)
            os.remove(file)



if __name__ == '__main__':
    run_autodelete()
