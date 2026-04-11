T007 - Dockerfile e README updates

O que foi implementado:
- Adicionado Dockerfile que instala ffmpeg e dependências Python.
- README atualizado para mencionar a necessidade de ffmpeg para MoviePy.

Por que:
- Streamlit Cloud pode não ter ffmpeg — Docker garante ambiente reprodutível.

Como testar:
- `docker build -t clipgen . && docker run -p 8501:8501 clipgen`
