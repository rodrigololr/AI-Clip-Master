import os
import sys

# Insert repository root into sys.path as the FIRST operation in this file to
# ensure any subsequent imports like `from app.services...` resolve correctly
# when Streamlit runs the script in hosting environments that do not add the
# repo root to PYTHONPATH (observed on Streamlit Community Cloud).
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    # Prepend to sys.path to take precedence over other entries
    sys.path.insert(0, _repo_root)

# Lightweight debug prints to help remote environments surface sys.path issues
try:
    print(f"[startup] repo_root={_repo_root}")
    print(f"[startup] repo_root_in_sys_path={_repo_root in sys.path}")
except Exception:
    pass

import streamlit as st
from app.config import N_CLIPS, MODEL_SIZE, OVERLAY_POSITION
import shutil
import tempfile
import uuid


def _check_health():
    """Return a dict with health checks for runtime dependencies and config."""
    checks = {}
    # POLLINATIONS_API_KEY
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    checks["POLLINATIONS_API_KEY"] = bool(os.getenv("POLLINATIONS_API_KEY"))

    # ffmpeg availability
    try:
        checks["ffmpeg"] = shutil.which("ffmpeg") is not None
    except Exception:
        checks["ffmpeg"] = False

    # faster_whisper and moviepy availability — attempt import to capture errors
    try:
        import importlib

        checks["faster_whisper"] = (
            importlib.util.find_spec("faster_whisper") is not None
        )
    except Exception as e:
        checks["faster_whisper"] = {"ok": False, "error": str(e)}

    try:
        # attempt to import moviepy.editor and capture import error message if any
        try:
            import moviepy.editor as _mp

            checks["moviepy"] = {"ok": True}
        except Exception as imp_exc:
            checks["moviepy"] = {"ok": False, "error": repr(imp_exc)}
    except Exception as e:
        checks["moviepy"] = {"ok": False, "error": str(e)}

    # Configured model
    try:
        from app.config import POLLINATIONS_MODEL

        checks["pollinations_model"] = POLLINATIONS_MODEL
    except Exception:
        checks["pollinations_model"] = None

    return checks


# Defer heavy/service imports to runtime to avoid import-time issues in
# hosted environments (Streamlit Cloud) where package import ordering can
# trigger KeyError during concurrent reloads. Import services lazily inside
# the functions/blocks that use them.

st.set_page_config(page_title="Pollinations Clip Gen", page_icon="🌸")


@st.cache_resource(show_spinner=False)
def get_video_service():
    # Lazy import to avoid import-time KeyError on some hosts
    from app.services.video_service import VideoService

    return VideoService(model_size=MODEL_SIZE)


def init_state():
    defaults = {
        "clips_gerados": [],
        "moments_detectados": [],
        "temp_dir": None,
        "temp_video_path": None,
        "upload_token": None,
        "uploader_version": 0,
        "erro_processamento": None,
        "erro_tecnico": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def cleanup_workspace(reset_upload_token=True):
    temp_dir = st.session_state.get("temp_dir")
    if temp_dir and os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    st.session_state["clips_gerados"] = []
    st.session_state["moments_detectados"] = []
    st.session_state["temp_dir"] = None
    st.session_state["temp_video_path"] = None
    st.session_state["erro_processamento"] = None
    st.session_state["erro_tecnico"] = None
    if reset_upload_token:
        st.session_state["upload_token"] = None


def prepare_uploaded_video(uploaded_file, upload_token):
    cleanup_workspace(reset_upload_token=False)

    temp_dir = tempfile.mkdtemp(prefix="clip_master_")
    input_name = f"input_{uuid.uuid4().hex}.mp4"
    temp_video_path = os.path.join(temp_dir, input_name)

    with open(temp_video_path, "wb") as output_file:
        output_file.write(uploaded_file.getbuffer())

    st.session_state["temp_dir"] = temp_dir
    st.session_state["temp_video_path"] = temp_video_path
    st.session_state["upload_token"] = upload_token


def render_detected_moments(moments):
    st.markdown("### Momentos detectados")
    for index, moment in enumerate(moments, start=1):
        st.markdown(
            f"**Momento {index}:** {moment['label']}  "
            + f"`{moment['start']:.2f}s -> {moment['end']:.2f}s`"
        )


init_state()

st.title("🌸 Pollinations Video Clip Generator")
st.markdown(f"### Deixe a IA encontrar os {N_CLIPS} melhores momentos do seu video")
st.caption(
    f"Configuracao fixa: {N_CLIPS} clips por video e modelo Whisper {MODEL_SIZE}."
)

# Health check in sidebar
with st.sidebar.expander("Diagnostico / Health Check", expanded=False):
    health = _check_health()
    st.markdown("**Status das dependencias e configuracoes:**")
    st.write(health)

uploader_key = f"video_uploader_{st.session_state['uploader_version']}"
uploaded_file = st.file_uploader("Suba seu video (mp4)", type=["mp4"], key=uploader_key)

if st.button("Processar novo video"):
    cleanup_workspace()
    st.session_state["uploader_version"] += 1
    st.rerun()

if uploaded_file:
    current_token = f"{uploaded_file.name}:{uploaded_file.size}"
    if current_token != st.session_state.get("upload_token"):
        prepare_uploaded_video(uploaded_file, current_token)

    video_service = get_video_service()
    # Lazy import AIService here
    from app.services.ai_service import AIService

    ai_service = AIService()

    # Re-check health before attempting processing to decide if cutting is available
    runtime_health = _check_health()
    moviepy_ok = (
        bool(runtime_health.get("moviepy") and runtime_health.get("moviepy").get("ok"))
        if isinstance(runtime_health.get("moviepy"), dict)
        else bool(runtime_health.get("moviepy"))
    )
    ffmpeg_ok = bool(runtime_health.get("ffmpeg"))
    cutting_available = moviepy_ok or ffmpeg_ok

    # Allow user to opt-in to offline fallback if external AI fails
    fallback_checkbox_key = "offline_fallback_enabled"
    if fallback_checkbox_key not in st.session_state:
        st.session_state[fallback_checkbox_key] = False
    st.checkbox(
        "Permitir fallback local da Pollinations (modo degradado)",
        key=fallback_checkbox_key,
        help="Ativa heuristica local caso a API externa falhe (POLLINATIONS_OFFLINE_FALLBACK=1).",
    )

    if not cutting_available:
        st.warning(
            "Corte de video indisponivel neste ambiente. Nem moviepy nem ffmpeg foram detectados corretamente.\n"
            "Voce ainda pode gerar a transcricao e analise, mas o corte sera pulado."
        )

    if st.button("Gerar clips", type="primary"):
        st.session_state["clips_gerados"] = []
        st.session_state["moments_detectados"] = []
        st.session_state["erro_processamento"] = None
        st.session_state["erro_tecnico"] = None

        progress_bar = st.progress(0, text="Preparando processamento...")

        try:
            with st.status("Processando seu video", expanded=True) as status:
                st.write("1/4 - Transcrevendo audio...")
                progress_bar.progress(20, text="Transcrevendo audio")
                transcription = video_service.transcribe(
                    st.session_state["temp_video_path"]
                )

                st.write("2/4 - Identificando os 2 melhores momentos...")
                progress_bar.progress(50, text="Analisando com Pollinations AI")
                moments = ai_service.identify_best_moments(transcription)
                st.session_state["moments_detectados"] = moments
                render_detected_moments(moments)

                st.write("3/4 - Gerando clips...")
                clips_temp = []
                for index, moment in enumerate(moments, start=1):
                    progress_value = 50 + index * 20
                    progress_bar.progress(
                        progress_value, text=f"Cortando clip {index} de {N_CLIPS}"
                    )
                    # If cutting is not available, skip actual cut but record a placeholder
                    out_file = os.path.join(
                        st.session_state["temp_dir"],
                        f"clip_{index}_{uuid.uuid4().hex[:8]}.mp4",
                    )
                    if cutting_available:
                        # perform the cut (moviepy preferred, ffmpeg fallback inside service)
                        video_service.cut_clip(
                            st.session_state["temp_video_path"],
                            moment["start"],
                            moment["end"],
                            out_file,
                        )
                    else:
                        # create an empty placeholder file so UI can still show a download
                        open(out_file, "wb").close()

                    clips_temp.append(
                        {
                            "path": out_file,
                            "label": moment["label"],
                            "start": moment["start"],
                            "end": moment["end"],
                        }
                    )

                st.write("4/4 - Finalizando...")
                progress_bar.progress(100, text="Concluido")
                st.session_state["clips_gerados"] = clips_temp
                status.update(label="Concluido com sucesso", state="complete")

        except Exception as exc:
            # We avoid referencing AIServiceError/VideoServiceError directly to
            # prevent import-time issues in hosted environments. Use the
            # exception class name to categorize known service errors.
            name = exc.__class__.__name__
            if name in ("AIServiceError", "VideoServiceError"):
                st.session_state["erro_processamento"] = str(exc)
            else:
                st.session_state["erro_processamento"] = (
                    "Ocorreu um erro inesperado durante o processamento."
                )
            st.session_state["erro_tecnico"] = repr(exc)

    if st.session_state["erro_processamento"]:
        st.error(st.session_state["erro_processamento"])
        with st.expander("Detalhes tecnicos"):
            st.code(st.session_state["erro_tecnico"] or "Sem detalhes")

    if st.session_state["moments_detectados"]:
        st.divider()
        render_detected_moments(st.session_state["moments_detectados"])

    if st.session_state["clips_gerados"]:
        st.divider()
        st.subheader("Seus clips estao prontos")
        cols = st.columns(2)
        for idx, clip in enumerate(st.session_state["clips_gerados"]):
            with cols[idx % 2]:
                st.video(clip["path"])
                st.caption(
                    f"Clip {idx + 1}: {clip['label']} "
                    f"({clip['start']:.2f}s -> {clip['end']:.2f}s)"
                )
                with open(clip["path"], "rb") as file_data:
                    st.download_button(
                        label=f"Baixar clip {idx + 1}",
                        data=file_data.read(),
                        file_name=f"clip_{idx + 1}.mp4",
                        mime="video/mp4",
                        key=f"btn_{idx}",
                    )
        # Floating overlay HTML generator
        # Use a dedicated builder for overlay HTML and render via streamlit components
        try:
            from streamlit.components.v1 import html as st_html
            from app.ui.overlay import build_overlay_html

            overlay_html = build_overlay_html(
                st.session_state["clips_gerados"], position=OVERLAY_POSITION
            )
            st_html(overlay_html, height=140)
        except Exception:
            # If components not available or file:// access blocked in some envs, ignore gracefully
            pass
else:
    st.info("Envie um video para iniciar o processamento.")

st.sidebar.info("Built with Pollinations AI 🚀")
with st.sidebar:
    st.image("assets/logo-white.svg", width=150)
    st.markdown("---")
    st.markdown(
        "Este app utiliza a **Pollinations AI** para analise inteligente de midia."
    )
    st.markdown("- Saida fixa em 2 clips\n- Modelo de transcricao fixo: tiny")
    st.markdown(
        "[![Built with Pollinations.ai](assets/badge-built-with.svg)](https://pollinations.ai)"
    )
