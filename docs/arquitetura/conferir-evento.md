---
title: "Dados de Conferir evento: redirecionamento por clique"
description: "Como a API registra os redirecionamentos de Conferir evento (S8-B02)."
---

# Dados de Conferir evento: redirecionamento por clique

Guia de integração da migração `20261110151000_eventos_conferir_evento.sql`, parte de dados da [S8-B02 (#79)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79). Falta na aplicação: o endpoint `outbound-clicks`, o histórico e o botão no front-end.

**Regra geral:** o que precisa valer em qualquer caminho de escrita está em chaves únicas, triggers e funções. A aplicação chama as funções; não reimplementa as regras. Nada daqui é gravável pelo navegador.

## 1. Conferir evento

```python
@router.post("/events/{event_id}/outbound-clicks")
def conferir_evento(event_id: UUID, payload: OutboundClick, db: Session = Depends(get_db)):
    try:
        url = db.execute(
            text("select public.registrar_clique_evento(:e, :c)"),
            {"e": event_id, "c": payload.click_id},
        ).scalar_one()
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "P0002":
            raise HTTPException(404, "Evento indisponível ou sem link")
        raise
    return {"external_url": url}
```

- A função só devolve o link de evento **aprovado** e com URL `http(s)`; caso contrário, erro `P0002`.
- O mesmo `click_id` para o mesmo evento conta uma vez. Outro `click_id` conta de novo.
- `cliques_evento` guarda apenas `evento_id`, `click_id` e `criado_em`. Não há usuário, IP ou agente: o contador não identifica pessoas e não mede visitantes únicos, inscrição ou presença.
- O endpoint é público (visitantes também conferem). Aplique nele o limite de taxa de escrita da API.
- `registrar_interesse(uuid)` foi removida. O contador `interessados_count` (no ORM, `redirect_count`) só muda por esta função.

O histórico (compromissos privados passados e eventos públicos passados ainda salvos) é consulta de leitura sobre `eventos_pessoais` e `eventos_salvos`; os índices `(user_id, data_hora)` e de eventos aprovados por data já existem.

## 2. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_clique_evento` | Não | Não | Não | Sim |
| `cliques_evento` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `eventos.interessados_count` | Lê (catálogo) | Lê; não altera | Lê; não altera | Sim |

## 3. Testes

`backend/tests/test_event_clicks_database.py` cobre os cenários de aceite que dependem do banco: contagem uma vez por `click_id`, recusa de evento pendente, sem link ou inexistente, registro sem dado pessoal e contador fechado ao navegador.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_event_clicks_database.py -q
```

Fora desta entrega: o endpoint, o histórico de eventos passados e a evidência no ambiente publicado.
