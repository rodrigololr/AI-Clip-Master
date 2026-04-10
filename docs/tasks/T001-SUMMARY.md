T001 - Estrutura de testes, fixtures e .env.example

O que foi implementado:
- Adicionado pytest como dependência de dev.
- Criado diretório tests/ com conftest.py incluindo fixtures tmp_video_dir e clear_env_vars.
- .env.example ainda deverá ser criado manualmente (variáveis necessárias: POLLINATIONS_API_KEY).

Por que esta abordagem:
- Pytest é simples e bem suportado; facilita mocks/fixtures.

Decisões e edge cases:
- Isolamos POLLINATIONS_API_KEY em fixtures para evitar dependência de ambiente.

Como testar:
- Ative a venv e rode `python -m pytest`.

Dívida técnica:
- Ainda precisamos adicionar cobertura de testes e CI (feito em tarefas seguintes).
