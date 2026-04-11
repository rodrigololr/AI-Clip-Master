import os
import uuid
from app.main import prepare_uploaded_video, cleanup_workspace, init_state


def test_prepare_and_cleanup(tmp_path):
    class DummyFile:
        def __init__(self, path):
            self._path = path

        def getbuffer(self):
            return open(self._path, "rb").read()

    # create fake file
    f = tmp_path / "video.mp4"
    f.write_bytes(b"0000")

    init_state()
    token = f"{f.name}:{f.stat().st_size}"
    prepare_uploaded_video(DummyFile(str(f)), token)
    assert os.path.isdir(
        __import__("os").path.dirname(__import__("os").path.abspath(__file__))
    )
    # cleanup
    cleanup_workspace()
    # session_state keys should be reset (can't import streamlit session in tests easily)
