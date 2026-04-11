import os
import tempfile
import shutil
import pytest


@pytest.fixture
def tmp_video_dir(tmp_path):
    d = tmp_path / "videos"
    d.mkdir()
    yield str(d)
    # cleanup handled by tmp_path


@pytest.fixture(autouse=True)
def clear_env_vars(monkeypatch):
    # Ensure POLLINATIONS_API_KEY not set unless test sets it explicitly
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
    yield
