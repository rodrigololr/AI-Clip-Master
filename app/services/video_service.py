import shutil
import types
import subprocess
import shlex

# optional imports to keep module import lightweight for tests/environments
try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception:
    WhisperModel = None

try:
    from moviepy.editor import VideoFileClip  # type: ignore
except Exception:
    VideoFileClip = None


class VideoServiceError(RuntimeError):
    pass


class VideoService:
    def __init__(self, model_size="tiny"):
        # allow tests to inject a fake model by setting attrs after init
        if WhisperModel is not None:
            try:
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception:
                # in case model fails to initialize, set a lazy erroring object
                self.model = types.SimpleNamespace(
                    transcribe=lambda *a, **k: (_ for _ in ()).throw(
                        VideoServiceError("faster-whisper instantiation failed")
                    )
                )
        else:
            # faster_whisper not installed; set a placeholder that raises on use
            self.model = types.SimpleNamespace(
                transcribe=lambda *a, **k: (_ for _ in ()).throw(
                    VideoServiceError("faster-whisper não está instalado no ambiente.")
                )
            )
        self.min_clip_duration = 3.0
        # verificar se o ffmpeg esta disponivel no PATH, necessario para moviepy
        if shutil.which("ffmpeg") is None:
            # nao levantamos excecao aqui para manter a inicializacao leve,
            # mas qualquer tentativa de cortar video vai falhar com mensagem clara.
            self._ffmpeg_missing = True
        else:
            self._ffmpeg_missing = False

    def transcribe(self, video_path):
        try:
            segments, _ = self.model.transcribe(video_path, beam_size=1)
        except Exception as exc:
            raise VideoServiceError(
                "Nao foi possivel transcrever o audio do video."
            ) from exc

        lines = []
        for segment in segments:
            lines.append(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")

        if not lines:
            raise VideoServiceError(
                "Nao foi encontrado conteudo de audio suficiente para transcricao."
            )

        return "\n".join(lines)

    def cut_clip(self, video_path, start, end, output_name):
        if getattr(self, "_ffmpeg_missing", False):
            raise VideoServiceError(
                "ffmpeg nao encontrado no sistema. Instale ffmpeg para cortar videos."
            )

        # Ensure moviepy is available at runtime
        # Prefer using moviepy if available because it handles many formats
        use_moviepy = VideoFileClip is not None

        try:
            start = float(start)
            end = float(end)
        except (TypeError, ValueError) as exc:
            raise VideoServiceError("Timestamps invalidos para corte de clip.") from exc

        if end <= start:
            raise VideoServiceError("Intervalo invalido para corte de clip.")

        # If moviepy is available, prefer its robust handling of formats and timestamps
        if use_moviepy:
            try:
                with VideoFileClip(video_path) as video:
                    duration = float(video.duration or 0)
                    if duration <= 0:
                        raise VideoServiceError("Duracao do video invalida para corte.")

                    # normalizar os timestamps para dentro do range do video
                    safe_start = max(0.0, min(start, duration))
                    safe_end = max(0.0, min(end, duration))

                    # garantir duracao minima do clip
                    if safe_end - safe_start < self.min_clip_duration:
                        # tentar expandir para a direita
                        safe_end = min(duration, safe_start + self.min_clip_duration)
                        # se nao for possivel, tentar expandir para esquerda
                        if safe_end - safe_start < self.min_clip_duration:
                            safe_start = max(0.0, safe_end - self.min_clip_duration)

                    if (
                        safe_end <= safe_start
                        or safe_end - safe_start < self.min_clip_duration
                    ):
                        raise VideoServiceError(
                            f"Nao foi possivel ajustar os timestamps para um corte valido (video duracao={duration:.2f}s, requested={start}->{end})."
                        )

                    new_clip = video.subclip(safe_start, safe_end)
                    try:
                        new_clip.write_videofile(
                            output_name,
                            codec="libx264",
                            audio_codec="aac",
                            threads=1,
                            logger=None,
                        )
                    except Exception as exc:
                        raise VideoServiceError(
                            "Falha ao renderizar o clip de video."
                        ) from exc
                    finally:
                        new_clip.close()

                return output_name
            except VideoServiceError:
                # re-raise known service errors
                raise
            except Exception as exc:
                # If moviepy fails at runtime, we'll attempt a direct ffmpeg fallback
                # only if ffmpeg is present. Capture the exception for diagnostics.
                moviepy_exc = exc

        # At this point either moviepy wasn't available or it failed; attempt ffmpeg
        # ffmpeg path already checked at init, so build a safe ffmpeg call
        # Probe input duration with ffprobe if available to normalize timestamps
        input_duration = None
        try:
            if shutil.which("ffprobe"):
                probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(video_path)}"
                completed = subprocess.run(
                    probe_cmd, shell=True, check=False, capture_output=True, text=True
                )
                if completed.returncode == 0 and completed.stdout:
                    try:
                        input_duration = float(completed.stdout.strip().splitlines()[0])
                    except Exception:
                        input_duration = None
        except Exception:
            input_duration = None

        # Normalize start/end using probed duration when available
        if input_duration is not None and input_duration > 0:
            duration = float(input_duration)
            safe_start = max(0.0, min(start, duration))
            safe_end = max(0.0, min(end, duration))
        else:
            # fall back to optimistic clipping based on provided timestamps
            safe_start = max(0.0, start)
            safe_end = max(safe_start + self.min_clip_duration, end)

        # ensure the requested clip length meets min duration
        if safe_end - safe_start < self.min_clip_duration:
            safe_end = safe_start + self.min_clip_duration
            if input_duration is not None:
                safe_end = min(safe_end, input_duration)

        # Build ffmpeg command (re-encode to ensure compatibility)
        clip_length = max(0.0, safe_end - safe_start)
        cmd = (
            f"ffmpeg -hide_banner -loglevel error -ss {safe_start:.3f} -i {shlex.quote(video_path)} "
            f"-t {clip_length:.3f} -c:v libx264 -c:a aac -pix_fmt yuv420p -y {shlex.quote(output_name)}"
        )

        try:
            completed = subprocess.run(cmd, shell=True, check=False)
            if completed.returncode != 0:
                raise VideoServiceError(
                    "ffmpeg falhou ao cortar o video (codigo != 0)."
                )
        except VideoServiceError:
            raise
        except Exception as exc:
            # If we had a moviepy exception earlier, chain it for diagnostics
            if "moviepy_exc" in locals():
                raise VideoServiceError(
                    "Falha ao cortar video com ffmpeg e moviepy."
                ) from moviepy_exc
            raise VideoServiceError("Falha ao cortar video com ffmpeg.") from exc

        return output_name
