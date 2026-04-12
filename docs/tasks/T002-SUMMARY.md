T002 - Instrumentacao: rastrear traceback do import moviepy

O que foi implementado
- Adicionada instrumentacao no startup do app para capturar e persistir o
  traceback completo caso `import moviepy.editor` falhe. O traceback e salvo em
  `logs/moviepy_import_trace.txt` (append) para facilitar o debug em ambientes
  remotos como Streamlit Community Cloud.

Porque essa abordagem
- Nos ambientes gerenciados nao ha acesso direto ao console do processo e os
  logs de importacao podem ser silenciosos. Persistir o traceback em um
  arquivo dentro do repo (pasta `logs/`) facilita recuperar o erro a partir
  dos artefatos de build / logs do deploy.

Decisoes e edgecases tratados
- A instrumentacao e minimal e nao altera o fluxo normal do app. Em caso de
  falha ao escrever o arquivo de log, o erro original nao e mascarado.
- O conteudo do traceback tambem e retornado no health-check em memory via
  `_check_health()` dentro da chave `moviepy.traceback`.

Como testar
1. Inicie o app localmente em um ambiente sem moviepy (por exemplo, crie um
   venv limpo sem instalar moviepy) e acesse a sidebar > Diagnostico.
2. Verifique que `moviepy` aparece com `ok: False` e que `traceback` contem a
   pilha de importacao.
3. Abra `logs/moviepy_import_trace.txt` e confirme que o traceback foi salvo com
   timestamp.

Debito tecnico / proximos passos
- Adicionar um teste unitario que monkeypatch `importlib` para forcar uma
  excecao durante o import e afirmar que o arquivo de log e criado.
- Opcional: sincronizar este log com o sistema de observabilidade (Sentry)
  para alertas automáticos.
