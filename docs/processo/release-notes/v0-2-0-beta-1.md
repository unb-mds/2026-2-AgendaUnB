---
title: "v0.2.0-beta.1"
description: "Prévia da R2 com calendário na agenda, sugestões de eventos com moderação e envio de planos de ensino em PDF."
---

Esta prévia da R2 reúne as mudanças desde a **R1 (v0.1.0)**. Agora você pode alternar entre lista e calendário, salvar eventos do campus na sua agenda pessoal e acompanhar o envio dos seus planos de ensino em PDF.

## Agenda e calendário

- O catálogo público e **Meus Eventos** ganharam visualização em lista e calendário semanal ou mensal, com busca e filtros por campus, área e turno.
- Use **Adicionar aos meus eventos** para acompanhar um evento público na sua agenda pessoal. Alterações de data, local ou título aparecem a partir do evento original. Você pode remover o vínculo a qualquer momento; salvar um evento não equivale a se inscrever nele.
- A página principal de eventos passou para `/eventos`. Os links antigos de `/segunda-pagina` redirecionam para a nova navegação. A tela também ganhou indicadores de carregamento e mensagens de erro mais claras.

## Sugestões, moderação e notificações

- Estudantes podem escolher **Sugerir evento** no formulário de criação. A proposta fica pendente e só aparece no catálogo público depois da aprovação.
- Professores e administradores podem consultar a fila e o histórico de sugestões, aprovar propostas ou recusá-las com justificativa. O estudante recebe notificações no sino sobre o envio e o resultado da análise.
- Administradores ganharam um painel para buscar contas, filtrar perfis e alterar papéis com confirmação. A plataforma impede que um administrador retire o próprio acesso.

## Planos de ensino em prévia

- Em **Envios reais de PDF**, usuários autenticados podem enviar planos particulares, informar disciplina e período, consultar o status e retomar um envio pelo histórico. São aceitos PDFs com texto selecionável, de até 10 MB e 10 páginas nas configurações padrão.
- A **Demonstração interativa** usa dados de exemplo para mostrar o fluxo de seleção de turmas com vínculo autodeclarado, revisão de avaliações e prévia no calendário. Ela não lê o conteúdo dos PDFs, não os envia ao servidor e não altera **Meus Eventos**.
- Envios reais entram como pendentes. A API já oferece consulta e confirmação de avaliações previamente registradas para planos concluídos, mas a extração automática por IA e a revisão e confirmação de avaliações reais pela interface ainda não estão disponíveis. É possível cadastrar as datas manualmente em **Meus Eventos**.

## Para atualizar a partir da R1

- Aplique as migrações pendentes do Supabase em ordem antes de disponibilizar a API e o frontend atualizados. No Supabase local já iniciado, use `npx supabase migration up --local`.
- O envio de PDFs usa o bucket privado `syllabus_files`. Configure `SUPABASE_SERVICE_ROLE_KEY` apenas no backend. O frontend passou para `frontend/`, e o `Makefile` centraliza tarefas de instalação e execução local.

[Comparar a R1 com o commit desta prévia (`7238b5e`)](https://github.com/unb-mds/2026-2-AgendaUnB/compare/R1...7238b5e811b93df33bbb553bbd22f6942e216d87)
