T005 - Melhorias em services e injeção de dependências

O que foi implementado:
- Extraídas constantes para app/config.py (N_CLIPS, MODEL_SIZE, OVERLAY_POSITION).
- AIService agora usa N_CLIPS no prompt.
- VideoService modificado para lidar com ausência de faster_whisper e moviepy durante import,
  facilitando testes locais sem dependências pesadas.

Por que esta abordagem:
- Facilita testes unitários (fakes/mocks) sem instalar modelos grandes.
- Torna comportamentos configuráveis via config.

Decisões e edge cases:
- Se faster_whisper não estiver instalado, VideoService lança erro claro apenas quando usado.

Como testar:
- Rode `./.venv_mago/bin/python -m pytest`.

Dívida técnica:
- Poderíamos injetar o modelo via construtor para maior testabilidade (futuro).
