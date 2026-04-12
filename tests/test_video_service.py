import pytest
import types

from app.services.video_service import VideoService, VideoServiceError


class DummySegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def test_transcribe_monkeypatch(monkeypatch):
    svc = VideoService(model_size="tiny")

    def fake_transcribe(path, beam_size=1):
        return ([DummySegment(0.0, 1.0, "hello world")], {})

    # monkeypatch the WhisperModel.transcribe used inside VideoService
    monkeypatch.setattr(svc, "model", types.SimpleNamespace(transcribe=fake_transcribe))

    out = svc.transcribe("/fake/path.mp4")
    assert "hello world" in out


def test_cut_clip_invalid_timestamps(monkeypatch, tmp_path):
    svc = VideoService(model_size="tiny")

    # Simulate ffmpeg present
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/ffmpeg")

    class DummyVideo:
        def __init__(self):
            self.duration = 5.0

        def subclip(self, a, b):
            class Clip:
                def write_videofile(self, output_name, **kwargs):
                    # create an empty file to simulate output
                    open(output_name, "wb").close()

                def close(self):
                    pass

            return Clip()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.video_service.VideoFileClip", lambda path: DummyVideo()
    )

    out_file = tmp_path / "out.mp4"
    # end before start
    with pytest.raises(VideoServiceError):
        svc.cut_clip("/fake.mp4", 4.0, 2.0, str(out_file))


def test_ffmpeg_fallback_when_moviepy_fails(monkeypatch, tmp_path):
    svc = VideoService(model_size="tiny")

    # Simulate ffmpeg present
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/ffmpeg")

    # Simulate that VideoFileClip is not available (None)
    monkeypatch.setattr("app.services.video_service.VideoFileClip", None)

    # Monkeypatch subprocess.run to simulate successful ffmpeg call
    class Completed:
        def __init__(self, returncode=0):
            self.returncode = returncode

    def fake_run(cmd, shell=True, check=False, capture_output=False, text=False):
        return Completed(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)

    out_file = tmp_path / "out_ffmpeg.mp4"
    res = svc.cut_clip("/fake.mp4", 0.0, 4.0, str(out_file))
    assert res == str(out_file)
