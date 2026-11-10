---
title: "Dados do catálogo de turmas: sincronização e cache"
description: "Como o adaptador do Followw grava o catálogo e como a API informa o cache (S7-B03)."
---

# Dados do catálogo de turmas: sincronização e cache

Guia de integração da migração `20261110142000_catalogo_sincronizacao.sql`, parte de dados da [S7-B03 (#70)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70). Falta na aplicação: o adaptador do Followw (lista permitida de endpoints públicos, paginação, timeout e tentativas limitadas) e o endpoint do catálogo.

O adaptador consulta a origem e, para cada oferta, chama a função abaixo com a credencial do servidor. Nada aqui é chamável pelo navegador.

## 1. Sincronização

```python
resultado = db.execute(text("select public.registrar_oferta_catalogo(cast(:p as jsonb))"),
                       {"p": json.dumps(oferta)}).scalar_one()   # {"id", "acao"}
```

| Campo | Obrigatório | Observação |
| --- | --- | --- |
| `codigo`, `nome` | sim | Código normalizado em maiúsculas |
| `turma` | sim | Texto. `"01"` e `"1"` são turmas diferentes |
| `ano`, `semestre` | sim | |
| `oferta_origem_id` | não | ID da **oferta** na origem. Preferido como identidade quando existir |
| `disciplina_origem_id` | não | ID da disciplina na origem; na falta, a disciplina é identificada por código, unidade e nível |
| `unidade`, `nivel` | não | |
| `professor`, `horarios` | não | Atualizáveis, fora da identidade |
| `atualizado_na_origem_em` | não | |

`acao` é `criada`, `atualizada` ou `inalterada`. Sincronizações repetidas devolvem sempre o mesmo `id`. Chave incompleta devolve `22023` e colisão entre o ID da origem e a chave natural devolve `55000`: nos dois casos a oferta precisa de revisão antes de aparecer.

A sincronização **nunca remove** ofertas nem vínculos. Registre cada execução em `sincronizacoes_catalogo` (como em `coletas_eventos`: `status`, contadores e um `erro_codigo` curto). Para o contrato do catálogo:

```python
estado = db.execute(text("select public.estado_catalogo()")).scalar_one()
# {"atualizado_em": "2026-11-07T18:00:00+00:00", "desatualizado": true, "tem_cache": true}
```

- `source_updated_at` = `atualizado_em`; `stale` = `desatualizado`;
- sem cache (`tem_cache: false`) e com a origem fora do ar, devolva 503;
- a validade padrão do cache é de 24 horas e pode ser passada como segundo argumento: `estado_catalogo('followw', interval '6 hours')`.

`ofertas_turma.semestre` aceita `1` e `2`. Se a origem trouxer período de verão, a decisão de como representá-lo ainda está aberta e precisa ser tomada antes da sincronização completa.

## 2. Testes

`backend/tests/test_catalog_sync_database.py` cobre os cenários de aceite que dependem do banco: identidade estável entre sincronizações, professor e horário atualizáveis, zeros preservados na turma, semestres distintos, adoção do ID da origem, colisão enviada à revisão e cache desatualizado preservando o último catálogo válido.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_catalog_sync_database.py -q
```

Fora desta entrega: a busca real no Followw, a evidência de que só endpoints públicos foram chamados e a simulação de indisponibilidade no ambiente publicado.
