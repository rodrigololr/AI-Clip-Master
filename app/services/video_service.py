import shutil
import types

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

        try:
            start = float(start)
            end = float(end)
        except (TypeError, ValueError) as exc:
            raise VideoServiceError("Timestamps invalidos para corte de clip.") from exc

        if end <= start:
            raise VideoServiceError("Intervalo invalido para corte de clip.")

        # abrir o arquivo primeiro para obter a duracao e validar os timestamps
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

            if safe_end <= safe_start or safe_end - safe_start < self.min_clip_duration:
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
                raise VideoServiceError("Falha ao renderizar o clip de video.") from exc
            finally:
                new_clip.close()

        return output_name
