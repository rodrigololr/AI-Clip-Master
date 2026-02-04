import streamlit as st
from services.video_service import VideoService
from services.ai_service import AIService
import json
import os

st.set_page_config(page_title="Pollinations Clip Gen", page_icon="🌸")

st.title("🌸 Pollinations Video Clip Generator")
st.markdown("### Deixe a IA encontrar os melhores momentos do seu vídeo")

uploaded_file = st.file_uploader("Suba seu vídeo (mp4)", type=['mp4'])

if uploaded_file:
    # Salva temporariamente
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())

    video_service = VideoService()
    ai_service = AIService()

    if st.button("Gerar Clips"):
        with st.status("Processando...", expanded=True) as status:
            st.write("📝 Transcrevendo áudio...")
            transcription = video_service.transcribe("temp_video.mp4")
            
            st.write("🧠 Identificando momentos com Pollinations AI...")
            moments_json = ai_service.identify_best_moments(transcription)
            moments = json.loads(moments_json).get('moments', [])

            clips_gerados = []
            
            for i, m in enumerate(moments):
                st.write(f"🎬 Cortando momento {i+1}: {m['label']}...")
                out_file = f"clip_{i}.mp4"
                video_service.cut_clip("temp_video.mp4", m['start'], m['end'], out_file)
                clips_gerados.append((out_file, m['label']))
                
            status.update(label="Concluído!", state="complete")

        if clips_gerados:
            st.divider()
            st.subheader("✅ Seus Clips estão prontos!")
            cols = st.columns(len(clips_gerados))
            for idx, (file, label) in enumerate(clips_gerados):
                with cols[idx]:
                    st.video(file)
                    st.caption(f"Momento {idx+1}: {label}")
                    with open(file, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Baixar",
                            data=f,
                            file_name=file,
                            mime="video/mp4",
                            key=f"btn_{idx}"
                        )

st.sidebar.info("Built with Pollinations AI 🚀")
with st.sidebar:
    st.image("assets/logo-white.svg", width=150) # Seu logo SVG local
    st.markdown("---")
    st.markdown(
        "Este app utiliza a **Pollinations AI** para análise inteligente de mídia."
    )
    # Exibe o badge oficial clicável
    st.markdown("[![Built with Pollinations.ai](assets/badge-built-with.svg)](https://pollinations.ai)")                                                                                                              
