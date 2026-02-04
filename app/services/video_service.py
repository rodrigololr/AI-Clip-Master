from faster_whisper import WhisperModel
from moviepy import VideoFileClip
import os

class VideoService:
    def __init__(self, model_size="tiny"):
        # Usando o tiny para ser o mais simples e rápido possível como você pediu
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, video_path):
        segments, _ = self.model.transcribe(video_path, beam_size=1)
        full_text = ""
        for segment in segments:
            full_text += f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}\n"
        return full_text

    def cut_clip(self, video_path, start, end, output_name):
        with VideoFileClip(video_path) as video:
            new_clip = video.subclipped(start, end)
            new_clip.write_videofile(output_name, codec="libx264", audio_codec="aac", threads=1)
        return output_name
