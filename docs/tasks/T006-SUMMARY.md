T006 - Floating overlay mini-players (UI)

O que foi planejado:
- Implementar overlay com st.components.v1.html para suportar dois mini-players fixos.

Status:
- Arquitetura preparada (config e templates) mas a geração final do HTML/JS será implementada em próxima iteração.

Como testar:
- Manual: gerar clips e verificar overlay no canto inferior-direito; em mobile o overlay inicia minimizado.

Dívida técnica:
- Precisamos garantir que Streamlit permita acesso a arquivos locais via HTML5 video src em todos os ambientes.
