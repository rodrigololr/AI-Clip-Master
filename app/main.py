import os
import sys

# Ensure repository root is on sys.path so 'app' package imports work when
# running `streamlit run app/main.py` in environments that don't add the
# repository root to PYTHONPATH (some hosting providers like Streamlit Cloud).
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import streamlit as st
from app.services.video_service import VideoService, VideoServiceError
from app.services.ai_service import AIService, AIServiceError
from app.config import N_CLIPS, MODEL_SIZE, OVERLAY_POSITION
import os
import shutil
import tempfile
import uuid

st.set_page_config(page_title="Pollinations Clip Gen", page_icon="🌸")


@st.cache_resource(show_spinner=False)
def get_video_service():
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
    ai_service = AIService()

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
                        progress_value, text=f"Cortando clip {index} de 2"
                    )
                    out_file = os.path.join(
                        st.session_state["temp_dir"],
                        f"clip_{index}_{uuid.uuid4().hex[:8]}.mp4",
                    )
                    video_service.cut_clip(
                        st.session_state["temp_video_path"],
                        moment["start"],
                        moment["end"],
                        out_file,
                    )
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

        except (AIServiceError, VideoServiceError) as exc:
            st.session_state["erro_processamento"] = str(exc)
            st.session_state["erro_tecnico"] = repr(exc)
        except Exception as exc:
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
