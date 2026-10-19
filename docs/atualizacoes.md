# Atualizações pós-Release 1

**Referência documental: 18/10/2026 - fim da Sprint 05.** Este documento registra o estado posterior à [v0.1.0](release-notes/v0.1.0.md), sem atribuir uma nova versão ou afirmar implantação em produção.

## Agenda e calendário

- `/eventos` substitui `/segunda-pagina` como rota principal. A rota antiga redireciona preservando parâmetros e fragmento; `#plano-de-ensino` abre a página independente de planos.
- Catálogo e Meus Eventos oferecem lista e calendário mensal/semanal, mantendo busca e filtros por campus, área e turno.
- O calendário permite avançar/voltar períodos e retornar a Hoje; a grade tem rolagem horizontal em telas pequenas e usa datas locais do navegador.
- **Adicionar aos meus eventos** salva um vínculo com o evento público aprovado, mantendo seus dados atualizados a partir do original. Remover o vínculo não exclui o evento. Salvar não equivale a inscrição ou confirmação de participação.

## Sugestões, notificações e administração

- Estudantes sugerem eventos no mesmo formulário Criar Evento, selecionando a visibilidade apropriada. A API e o banco mantêm essas propostas pendentes até análise.
- `/sugestoes` permite a professores e administradores consultar pendências e histórico, buscar, paginar e aprovar/recusar propostas. Recusas exigem justificativa de até 2.000 caracteres.
- Notificações persistidas confirmam envio e comunicam aprovação/recusa ao estudante. O sino mostra contagem de não lidas e permite marcá-las como lidas; atualiza ao enviar, ao retornar à janela e a cada 30 segundos.
- `/admin`, exclusivo de admins, permite busca por nome/e-mail, filtros de papel e confirmação de e-mail, consulta ao último acesso e alteração de cargos com confirmação.
- RPCs verificam permissões no banco, detectam alterações concorrentes e impedem o admin de remover o próprio acesso. Cadastro e autopromoção para professor exigem `@unb.br`; atribuição por admin admite outro domínio.

## API e persistência

A FastAPI ganhou `POST /api/v1/suggestions` e GET/PUT/DELETE de `/api/v1/me/saved-events`, conforme [Padrões](padroes.md). Moderação e gestão de usuários usam RPCs do Supabase, não as rotas `/admin` propostas anteriormente.

Após as cinco migrações da base R1, o repositório inclui:

| Migração | Mudança |
| --- | --- |
| `20261014120000` | Sugestões pendentes, justificativa de recusa e contador de interessados |
| `20261014120100` | Regras de acesso e RPCs administrativas |
| `20261014120200` | Bucket privado `syllabus_files`, PDF até 10 MB e isolamento por pasta do usuário |
| `20261016000000` | Vínculos de eventos públicos salvos com RLS por proprietário |
| `20261018000000` | Moderação por professores/admins, RPCs paginadas, origem estudantil e notificações transacionais |
| `20261018000100` | Atribuição de professor por admin sem restrição de domínio; cadastro/autopromoção continuam institucionais |

Aplique as migrações pendentes em ordem antes de disponibilizar o código atualizado. No ambiente local já iniciado: `npx supabase migration up --local`. Os detalhes estão nos guias de [eventos salvos](eventos-salvos.md) e [painel administrativo](painel-administrativo.md).

## Ainda em preparação

`/plano-de-ensino` informa que envio de PDFs e extração de avaliações ainda não estão disponíveis e oferece organização manual da agenda. O bucket privado é infraestrutura preparatória. Upload de atestados, parser, revisão assistida e validação colaborativa continuam planejados, assim como inscrições, histórico de participação, lembretes de proximidade, exportação `.ics` e coleta externa.

## Verificação disponível

O projeto contém testes pytest da API (eventos, sugestões e vínculos salvos), testes Node de calendário e testes PostgreSQL de RLS/RPC/triggers. Estes últimos exigem `TEST_SUPABASE_DB_URL` local e são ignorados se ela não estiver configurada. Consulte [Contribuição](CONTRIBUTING.md). A existência das suítes não afirma execução ou aprovação em um ambiente de produção.
