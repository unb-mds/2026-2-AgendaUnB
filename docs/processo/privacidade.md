---
title: "Privacidade e ciclo de vida dos dados"
description: "Inventário de dados, direitos do titular, exclusão, descarte de PDFs e procedimento de incidente (S8-D01)."
---

# Privacidade e ciclo de vida dos dados

Registro técnico da [S8-D01 (#83)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83). Estado em **10/11/2026**. Os textos para o usuário são a [Política de Privacidade](../produto/politica-de-privacidade.md) e os [Termos de Uso](../produto/termos-de-uso.md).

Este documento descreve o que está implementado e o que ainda depende de decisão ou de outra entrega. Ele não é parecer jurídico. As bases legais indicadas são uma proposta a validar.

## Decisões que a equipe precisa tomar

| # | Decisão | Proposta | Por quê |
| --- | --- | --- | --- |
| D1 | Quem é a pessoa de contato e qual o canal de atendimento ao titular | E-mail único do grupo, lido por duas pessoas | A política e os termos têm marcações **[DEFINIR]** que impedem a publicação |
| D2 | Eventos públicos de uma conta excluída | Manter o comportamento atual: são excluídos com a conta | Alternativa: manter o evento publicado sem autor. Exige mudar a regra `eventos_autor_ou_fonte` |
| D3 | Revisões de terceiros sobre o plano de uma conta excluída | Manter o comportamento atual: saem com o plano | As revisões ficam ligadas ao plano de origem. Preservá-las exigiria transferir o plano para outra conta |
| D4 | Retenção de registros técnicos (Render, Vercel, Supabase) | Conferir o padrão de cada plano e registrar aqui | Sem prazo definido não dá para informar o titular |
| D5 | Fontes carregadas do Google Fonts | Hospedar as fontes junto com o site | Evita enviar o IP de todo visitante ao Google |

## Inventário de dados pessoais

Base legal: referência aos incisos do art. 7º da LGPD. O projeto tem finalidade acadêmica; a LGPD é adotada como referência de boas práticas.

| Dado | Onde fica | Finalidade | Base legal proposta | Retenção | Exclusão |
| --- | --- | --- | --- | --- | --- |
| E-mail, senha (hash), identidade Google, último acesso | Supabase Auth (`auth.users`) | Autenticação | Execução do serviço pedido pelo titular (V) | Enquanto a conta existir | Exclusão da conta |
| Nome, e-mail, papel, avatar | `profiles` | Identificação e permissões | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Mudanças de papel | `auditoria_papeis` (S8-D02) | Auditoria de permissões | Legítimo interesse em segurança (IX) | Enquanto a conta existir | Cascata |
| Agenda pessoal | `eventos_pessoais` | Agenda do titular | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Eventos salvos, avisos, notificações | `eventos_salvos`, `lembretes`, `notificacoes` | Agenda e lembretes | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Eventos sugeridos ou publicados | `eventos` (`autor_id`) | Agenda pública; nome do autor como organizador | Execução do serviço (V) | Enquanto a conta existir | Cascata (ver D2) |
| Turmas seguidas | `vinculos_turma` | Acesso a conteúdo da turma | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| PDF do plano | Não é guardado nos envios novos (o texto é extraído no upload). Planos antigos: Storage `syllabus_files` | Extração local do texto | Execução do serviço (V) | Envios novos: não armazenado. Antigos: até o descarte | Script de descarte |
| Texto preparado e texto autorizado do plano | `planos_ensino.texto_preparado`, `texto_aprovado` | Revisão pelo titular e envio autorizado à IA | Execução do serviço (V) e **consentimento** para o envio (I) | Enquanto a conta existir | Cascata; aparece na exportação |
| Metadados do plano, versões e candidatos | `planos_ensino`, `versoes_plano`, `avaliacoes` | Sugerir datas | Execução do serviço (V) | Enquanto a conta existir | Cascata (ver D3) |
| Texto enviado ao provedor de IA | Não é guardado pela plataforma além do necessário à extração | Extração de datas | **Consentimento** específico (I) | Conforme o provedor | Revogação impede novos envios |
| Votos | `votos_avaliacao` | Validação colaborativa | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Operações de importação | `operacoes_importacao`, `itens_importacao` | Evitar duplicar eventos em retries | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Aceites e consentimentos | `aceites_termos`, `consentimentos` | Comprovar ciência e autorização | Cumprimento de obrigação e exercício de direitos (II, VI) | Enquanto a conta existir | Cascata |
| Tokens do Google Agenda | A definir na [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82) | Exportação | **Consentimento** (I) | Até desconectar | Desconexão e exclusão da conta |
| Endereço IP e rota acessada | Logs dos provedores; memória do limitador de taxa | Segurança e diagnóstico | Legítimo interesse (IX) | Ver D4 | Expiração |

**Sem dado pessoal:** `cliques_evento` (identificador aleatório do clique), `coletas_eventos`, `sincronizacoes_catalogo`, `exclusoes_conta` (só contagens), `campus`, `categories`, `disciplinas` e `ofertas_turma`. Eventos coletados podem citar nomes de palestrantes já divulgados pela fonte institucional.

## Operadores e transferências

| Operador | Papel | Dados | Local |
| --- | --- | --- | --- |
| Supabase | Banco, Auth, Storage | Todos os dados da conta | `us-east-1` (EUA) no projeto de homologação |
| Render | API | Trânsito e logs | EUA (região a confirmar na [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)) |
| Vercel | SPA | Logs de acesso | Rede global |
| Google Identity | Login OAuth | Nome, e-mail, foto | EUA e outros |
| Google Gemini | Extração | Apenas o trecho autorizado | EUA e outros |
| Google Calendar | Exportação ([#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82)) | Título, descrição selecionada, local e datas | EUA e outros |
| Google Fonts | Fontes | IP do visitante | Rede global (ver D5) |

Followw e Agenda UnB Notícias são fontes **consultadas** pelo servidor. Nenhum dado de usuário é enviado a elas.

## Aceite não é consentimento

| | Aceite de termos | Consentimento |
| --- | --- | --- |
| Tabela | `aceites_termos` | `consentimentos` |
| O que registra | Que a conta leu uma **versão** dos Termos ou da Política | Autorização para uma **finalidade** específica |
| Finalidades | — | `google_agenda` |
| Pode ser revogado | Não se aplica | Sim, a qualquer momento (`revogar_consentimento`) |
| Vínculo com o conteúdo | Versão do documento (data de vigência) | `referencia_id` e `conteudo_hash` do que foi autorizado |

**Envio ao provedor de IA.** A autorização é registrada no próprio plano, pela S7-B01: `texto_aprovado` (o trecho exato mostrado ao usuário), `hash_texto_aprovado` e `autorizado_em`. O worker confere o hash antes de chamar o provedor, e o trigger `planos_preserva_texto_autorizado` impede alterar o snapshot durante o processamento. Por isso `consentimentos` não aceita a finalidade `envio_texto_ia`: um segundo registro da mesma autorização poderia divergir do primeiro.

## Direitos do titular na API

| Direito | Contrato | Observação |
| --- | --- | --- |
| Ver o que está pendente de leitura | `GET /api/v1/me/legal-documents` | `[{"document":"terms","currentVersion":"2026-11-10","acceptedVersion":null,"pending":true}, …]` |
| Registrar leitura | `PUT /api/v1/me/legal-acceptances/{terms\|privacy}` com `{"version":"2026-11-10"}` → 204 | Só aceita a versão vigente (409 se o documento mudou) |
| Acesso e portabilidade | `GET /api/v1/me/data-export` → JSON para download | `Cache-Control: no-store`. Não inclui dados de outras contas, caminhos internos nem hashes |
| Exclusão | `DELETE /api/v1/me` com `{"confirmation":"EXCLUIR MINHA CONTA"}` → 204 | 409 para o último administrador |
| Correção | Edição do perfil (nome e foto), já existente | E-mail é imutável no perfil |
| Revogar compartilhamento | `DELETE …/versions/{id}/sharing` ([#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77)) | Função `retirar_compartilhamento` |

A versão vigente de cada documento fica em `CURRENT_LEGAL_VERSIONS` (`backend/src/modules/account/repository.py`). Ao publicar um texto novo, atualize a data nos dois lugares: as contas voltam a aparecer como pendentes.

**Para o front-end** ([#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74), [#78](https://github.com/unb-mds/2026-2-AgendaUnB/issues/78)): links para os dois documentos no cadastro e em Configurações; após entrar, consultar `legal-documents` e apresentar o que estiver pendente; em Configurações, os botões **Baixar meus dados** e **Excluir conta** (com digitação da frase de confirmação).

## O que acontece na exclusão da conta

Sequência do `DELETE /api/v1/me`:

1. `preparar_exclusao_conta` confere a regra do último administrador, registra as contagens em `exclusoes_conta` e devolve os arquivos da conta.
2. A API remove os PDFs do Storage.
3. A API exclui o usuário no Supabase Auth. A cascata do banco apaga o restante.
4. `concluir_exclusao_conta` marca o registro como concluído.

Se o passo 2 ou 3 falhar, a conta continua existindo e o pedido pode ser repetido. A ordem garante que nunca sobra arquivo sem dono.

| Apagado | Mantido |
| --- | --- |
| Perfil e credenciais | Eventos que **outras contas** já importaram para a própria agenda (ficam sem vínculo com a origem) |
| Agenda pessoal, eventos salvos, avisos e notificações | Registro da exclusão, só com contagens |
| Turmas seguidas, votos, operações de importação | Eventos já exportados ao Google Agenda do titular |
| Aceites e consentimentos | Dados em cópias de segurança, até expirarem |
| Planos enviados, com todas as versões, candidatos e votos recebidos | |
| Eventos públicos sugeridos ou publicados pela conta | |

**Correção incluída nesta entrega:** `eventos_pessoais.user_id` não tinha ação de exclusão. Qualquer conta com um compromisso na agenda **não podia ser excluída** (erro de chave estrangeira). Agora usa `ON DELETE CASCADE`.

Pendente para a [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82): quando os tokens do Google Agenda existirem, a exclusão deve revogá-los no provedor antes do passo 3, e a tabela de tokens deve usar `ON DELETE CASCADE`.

## Descarte do PDF original (ADR-003)

- **Novos envios** já não guardam o PDF: a S7-B01 extrai o texto no upload e grava só `texto_preparado`.
- **Planos antigos** podem ter o PDF no Storage. `arquivos_a_descartar()` lista os que já têm processamento encerrado (`concluido` ou `falha`); `registrar_descarte_arquivo(plano)` limpa o caminho e grava `arquivo_descartado_em`.
- A regra `planos_particular_exige_fonte` (PDF ou texto preparado) passa a aceitar também o descarte registrado: um plano antigo processado continua válido sem o arquivo.
- **Originais legados:**

```bash
cd backend
python -m scripts.descartar_pdfs             # só mostra quantos seriam removidos
python -m scripts.descartar_pdfs --executar  # remove do Storage e registra o descarte
```

O script pode ser interrompido e repetido. Planos pendentes ou em processamento não são tocados. Depois do descarte, `filePath` passa a vir nulo para o dono; o front-end não deve depender dele.

## Logs

- O SQLAlchemy foi configurado com `hide_parameters`: mensagens de erro não trazem os valores das consultas.
- Falhas de banco são registradas com tipo e SQLSTATE, sem traceback, porque a mensagem do PostgreSQL pode conter a linha recusada.
- Erros de PDF e de Storage registram só o tipo da exceção e o status HTTP.
- As chamadas administrativas ao Supabase não registram id, caminho, corpo de resposta nem chave.
- `erro_codigo` de coletas e sincronizações aceita só um código curto.

Testes automatizados verificam que conteúdo de linha, identificadores e chave de serviço não aparecem nos logs (`test_account_api.py`). **Não verificado:** os logs dos provedores no ambiente publicado e o worker de extração, que ainda não está na `dev`.

## Atendimento ao titular

1. **Receber** o pedido pelo canal definido (D1) e registrar a data.
2. **Confirmar a identidade** pela própria conta: pedir que a pessoa faça o pedido autenticada ou responder ao e-mail cadastrado. Não pedir documentos.
3. **Atender.** Acesso, portabilidade e exclusão são feitos pelo próprio titular na plataforma. Se ele não conseguir, um administrador orienta; a exclusão manual segue a mesma sequência da API.
4. **Responder** em até 15 dias, informando o que foi feito e o que permanece (tabela acima).
5. **Registrar** data, tipo de pedido e desfecho, sem copiar os dados do titular.

Pedidos que envolvam conteúdo de terceiros (por exemplo, remover uma cópia importada por outra conta) não são atendidos automaticamente: a cópia pertence à agenda de quem a importou.

## Procedimento de incidente

Referência: [guia de segurança da ANPD para agentes de pequeno porte](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-vf.pdf). Confirmar o regulamento de comunicação de incidentes vigente no momento do ocorrido.

| Etapa | O que fazer | Quem |
| --- | --- | --- |
| 1. Conter | Trocar as chaves afetadas (secreta do Supabase, senha do banco, segredo OAuth, chave do Gemini), revogar sessões e, se preciso, pausar a API | Quem detectou, com Luis e Felipe |
| 2. Registrar | Data e hora, como foi descoberto, sistemas e tipos de dados afetados, quantidade estimada de contas | Felipe |
| 3. Avaliar | Há risco ou dano relevante aos titulares? Considerar dados acadêmicos, credenciais e conteúdo privado | Equipe, com o responsável (D1) |
| 4. Comunicar | Se houver risco relevante: titulares afetados e ANPD (LGPD, art. 48). O regulamento da ANPD prevê prazo de **três dias úteis** a partir do conhecimento do incidente | Responsável (D1) |
| 5. Corrigir | Eliminar a causa, adicionar teste que reproduza a falha e atualizar o registro da verificação de segurança (S8-D02) | Responsável pela área |
| 6. Encerrar | Registro final com causa, impacto, medidas e data de encerramento | Felipe |

A comunicação aos titulares diz, em linguagem simples: o que aconteceu, quais dados, o que já foi feito e o que a pessoa deve fazer (por exemplo, trocar a senha).

## Verificação

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_privacy_database.py tests/test_account_api.py -q
```

| Critério de aceite | Evidência | Estado |
| --- | --- | --- |
| Acesso ponta a ponta | `test_export_contains_the_account_data_and_nobody_elses`, `test_export_is_a_private_download` | Verificado no banco local e na API com dublês. **Falta** a tela e o ambiente publicado |
| Exclusão ponta a ponta | `test_account_deletion_end_to_end`, `test_delete_requires_explicit_confirmation_and_removes_files_first` | Idem. **Falta** exercitar Auth e Storage reais |
| Descarte do PDF após a extração | Envios novos não guardam o PDF (S7-B01); `test_original_pdf_is_discarded_and_the_plan_remains` | Verificado no banco local |
| Eliminação de originais legados | `scripts/descartar_pdfs.py` | **Falta** executar no ambiente hospedado |
| Tarefas pendentes e cópias independentes | Lembretes pendentes e votos saem na cascata; cópias importadas por terceiros permanecem (mesmo teste de exclusão) | Verificado no banco local. Fila de extração: com a [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51) |
| Conteúdo acadêmico e tokens fora dos logs | `test_database_errors_are_logged_without_row_content`, `test_supabase_admin_calls_never_log_identifiers` | Verificado na API. **Falta** revisar logs dos provedores e do worker |
| Google Calendar: desconexão, revogação e tokens | — | **Depende** da [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82) |
| Política e termos publicados no cadastro e em Configurações | Textos e endpoints prontos | **Falta** D1 e a interface |
