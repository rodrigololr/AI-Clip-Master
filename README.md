# 🌸 Pollinations Clip Generator

Um gerador de clips inteligentes que utiliza IA para encontrar os melhores momentos em vídeos. 

## 🚀 Como Funciona
1. **Transcrição:** O áudio é convertido em texto localmente usando `faster-whisper`.
2. **Análise de IA:** A transcrição é enviada para a **Pollinations AI** via API (Endpoint `/v1/chat/completions`) para identificar os segmentos mais engajadores.
3. **Corte Automático:** O app realiza o subclip do vídeo original e entrega os arquivos prontos para download.

## 🛠️ Tecnologias
- **Pollinations AI API**: Cérebro do projeto para análise de contexto.
- **Streamlit**: Interface rápida e intuitiva.
- **Faster-Whisper**: Transcrição eficiente.
- **MoviePy**: Edição programática de vídeo.

## 📄 Créditos
Este projeto foi desenvolvido utilizando a infraestrutura da [pollinations.ai](https://pollinations.ai).

[![Built with Pollinations.ai](https://pollinations.ai/badge.svg)](https://pollinations.ai)
