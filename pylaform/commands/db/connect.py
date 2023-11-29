import sqlite3
import os
import shutil


def db():
    path = os.path.abspath(os.curdir)
    if not os.path.exists(os.path.join(path, 'data/resume.db')):
        try:
            shutil.copyfile(os.path.join(path, 'pylaform/resources/resume.db'), os.path.join(path, 'data/resume.db'))
        except Exception as e:
            raise f"Do you have write permissions for the container? Error: {e}"

    return sqlite3.connect(os.path.join(path, "data/resume.db"), check_same_thread=False)
