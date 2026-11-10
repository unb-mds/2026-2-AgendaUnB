# Extração privada com autorização — S7-B01

Contrato vigente da issue #51, versão `syllabus-v3-approved-text`.
A versão trazida pelo solicitante substitui a retenção do PDF descrita na S6:
novos PDFs são usados somente na preparação local e descartados antes de registrar
texto no banco. PDFs históricos não são apagados por esta migração.

## Fluxo e limites

1. `POST /api/v1/syllabus/upload`: PDF digital, até 10 MiB e dez páginas. A API
   valida extensão/MIME/assinatura/senha/texto, extrai em subprocesso com prazo,
   fecha o temporário em sucesso/falha e libera os bytes do original. Não chama
   Storage nem Gemini. O registro fica `pendente`, aguardando autorização.
2. Alternativa: `POST /api/v1/syllabus/text`, com `text` obrigatório e `disciplina`/`turma`
   opcionais. Texto tem limite de **40.000 bytes UTF-8**, sem truncamento. A
   referência de página é nula; não se inventa página 1 para texto colado.
3. `GET /api/v1/syllabus/{id}/text`: dono consulta o texto minimizado editável,
   páginas físicas quando disponíveis, destino Google Gemini, disponibilidade,
   limite e hash. A resposta usa `Cache-Control: no-store`. Outro dono recebe 404.
4. `POST /api/v1/syllabus/{id}/extractions`: o dono envia páginas revisadas,
   `textHash`, `authorize: true`, `contentEligible: true` e, quando necessário,
   `reprocess: true`. Só o snapshot exato aprovado fica elegível ao worker.
5. Worker persistente consome o texto aprovado, valida JSON/evidência e grava
   candidatos privados em `candidatos_avaliacao`, sem criar eventos.

O cliente calcula SHA-256 do JSON UTF-8 sem espaços separadores, com as chaves
`pagina`, `texto` nessa ordem em cada página. A ordem dos campos recebidos do
JSONB não afeta o hash. A ordem das páginas, espaços e texto afetam. O hash é uma
verificação de integridade; autenticação e autorização continuam obrigatórias.
`frontend/src/lib/approvedText.js` e o servidor implementam o mesmo formato.

A revisão pode reduzir/editar o texto, mantendo referências pertencentes à
preparação. Após autorizar, o registro ativo conserva somente essa versão corrigida,
substituindo também o rascunho anterior. Editar na interface desmarca as duas
confirmações; nenhuma caixa vem marcada. Não são aceitas URLs de destino ou
instruções de execução. Conteúdo do documento é dado, sem ferramentas ou navegação.

## Minimização e alternativa manual

A preparação remove padrões comuns de e-mail, CPF/matrícula, telefone e linhas
rotuladas com identificadores. Regex não comprova anonimização nem identifica
confidencialidade. Nomes sem rótulo e informações contextuais exigem revisão.
O estudante vê o texto exato e declara que removeu conteúdo pessoal, sensível ou
confidencial antes de autorizar. O cadastro manual permanece acessível para PDF
escaneado, falha, limite atingido, provedor indisponível ou conteúdo inadequado.

O original não é enviado ao Storage. O upload direto ao bucket pelo cliente
fica fechado; objetos históricos continuam privados. Texto preparado/aprovado só
é lido pelo dono e pelo servidor. Logs não recebem PDF, texto integral, exceções
SQL com parâmetros ou retorno bruto do provedor. O snapshot em processamento é
imutável por trigger, inclusive para atualizações acidentais do backend.

## Estados, recuperação e reprocessamento

Estados existentes são preservados: `pendente`, `processando`, `concluido`, `falha`.
`authorizationRequired` distingue preparação à espera do estudante da fila pronta;
`preparedTextAvailable` indica que há texto revisável. Planos históricos sem texto
preparado não recebem autorização retroativa, nem bloqueiam a revisão legada.

O worker só reivindica linhas com autorização e snapshot. A fila é ordenada por
`enfileirado_em`; não pelo tempo que o estudante levou para revisar. Lease, fencing,
reserva de custo, retry e limites continuam persistidos. Repetir a mesma autorização
sem `reprocess` retorna o estado existente e não dispara outra execução.

Uma nova análise de plano finalizado exige `reprocess: true` e nova autorização.
Não é aceita durante execução/fila já autorizada. Candidatos pendentes da versão
anterior são descartados transacionalmente; os já confirmados são preservados.
A reserva acumulada e o contador de tentativas não são zerados. Quando esses
limites acabam, o servidor retorna 409 e oferece organização manual.

429/5xx transitórios e timeouts permitem retry limitado; JSON/evidência inválidos
falham sem gravação parcial. Ausência de provas/trabalhos conclui com zero
candidatos. Unicidade por plano/execução/ordem e fencing impedem publicação dupla.

## Provedor e habilitação por ambiente

Google Gemini API, `gemini-3.5-flash-lite`, REST Interactions API, `store=false`.
Sem ferramentas, uploads remotos, busca, cache ou conversa compartilhada. Só tipos
`prova`/`trabalho` são aceitos; aulas, bibliografia e outros tipos ficam fora.
Data/horário exigem evidência completa no trecho. Não se infere ano, meia-noite,
fuso ou início de um intervalo. Datas ausentes/incompletas ficam nulas e ambíguas.

Os limites continuam: rede 12s, tentativa inteira 18s, lease 90s, duas tentativas,
40.000 bytes de texto, 4.096 tokens de saída e teto configurado USD 0,06 por plano.
A reserva conservadora configurada é USD 0,027040 por tentativa; não é cobrança
medida. Reprocessar consome o orçamento restante. A preparação tem prazo próprio
padrão de 8s para cada subprocesso e até 2,2s adicionais de limpeza.
Preços/modelo são configurados no servidor; veja o [histórico técnico S6](processamento-planos.md).

`GEMINI_API_KEY` permanece no runtime do servidor. As três flags abaixo nascem
falsas e não foram alteradas no `.env` desta entrega:

```dotenv
SYLLABUS_WORKER_ENABLED=false
SYLLABUS_PRIVACY_READY=false
SYLLABUS_PROVIDER_TERMS_READY=false
```

`SYLLABUS_PROVIDER_TERMS_READY` é uma declaração operacional apoiada nas evidências
S7-B02, não uma prova automática de elegibilidade. O provedor recusa chamadas sem
ela, mesmo fora do comando do worker. Autorizar o texto não habilita a produção.

Os [termos oficiais do Gemini](https://ai.google.dev/gemini-api/terms), consultados
em 10/11/2026, restringem idade/elegibilidade dos clientes e vedam conteúdo pessoal,
sensível ou confidencial no serviço não pago. `store=false` não elimina essas
condições nem resolve a possibilidade de público menor de 18 anos. A aprovação
S7-B02 permanece pendente; consentimento e regex não substituem essa análise.

## Migrações e consumidores

Migração nova: `20261110120000_texto_revisado_e_autorizacao_s7.sql`, após fila e
privacidade S6. Adiciona snapshots, autorização, hash, versão e duração da
preparação; permite página nula para texto bruto; concilia políticas de leitura
privada; fecha upload direto e protege snapshot em execução. Dados históricos
permanecem legíveis e sem autorização automática.

Na nuvem auditada, a integração exige revisar/aplicar, na ordem, `20261109120000`,
`20261109130000` e `20261110120000`, alinhando-as com as migrações da equipe.
Nenhuma foi aplicada na nuvem. O auditor exige a migração S7, RLS/privilégios,
políticas, RPC, triggers e bucket correspondentes antes de iniciar o worker.

As rotas legadas de confirmação usam `avaliacoes`; o produtor S7 grava
`candidatos_avaliacao`. A integração da consulta/confirmação HTTP e da jornada
com turmas segue S7-B04/S7-F03 e S7-D01. A RPC privada `revisar_candidatos_plano`
foi exercitada após revisão explícita nos testes locais; o worker não a chama.

## RNF06 e evidências

`preparationDurationMs`: preparação local antes de apresentar o texto.
`reviewDurationMs`: janela entre preparação e autorização, incluindo espera do
estudante; não representa medição de atenção ativa. `totalDurationMs`: fila,
retentativas/recuperação e provedor desde a autorização atual, sem espera humana.
O limite alvo é verificado por análise; custo/tentativas continuam acumulados por
plano. Retentativas/leases podem exceder 20s e são registrados como desvio.

Corpus inteiramente sintético com gabarito: cronograma com aula/bibliografia/lista
fora da seleção, documento vazio de avaliações, datas incompletas, dez páginas e
instrução maliciosa. [Gemini real](benchmarks/syllabus-s7-gemini-2026-11-10.json) e
[referência sem rede](benchmarks/syllabus-s7-reference-2026-11-10.json) registram
acertos, omissões, divergências, extras, datas inventadas, falhas e desvios.

| Caso | Páginas | Acertos | Preparação | Fila + provedor |
| --- | --- | --- | --- | --- |
| Cronograma completo | 1 | 2/2 | 3,490s | 10,026s |
| Sem cronograma | 2 | 0/0 | 2,698s | 7,926s |
| Datas ausentes | 1 | 2/2, datas nulas | 2,065s | 7,751s |
| Dez páginas | 10 | 2/2 | 2,081s | 8,514s |
| Instrução maliciosa | 2 | 1/1 | 2,025s | 6,789s |

Sete acertos, zero omissões/extras/divergências/datas inventadas e nenhum desvio
nessa execução. A preparação do benchmark inclui geração/extração em subprocesso;
SQLite e despacho imediato substituem hospedagem real. O tempo humano é zero por
se tratar de gabarito sintético previamente revisado, não de jornada humana medida.
A amostra não homologa carga/latência em produção nem todos os formatos reais.

O [fluxo HTTP local](benchmarks/syllabus-s7-http-local-2026-11-10.json) complementa
com Auth/JWT reais, API FastAPI via ASGI, PostgreSQL, Storage e PostgREST locais:
nenhum PDF persistido, texto oculto para outra conta, dois candidatos, zero eventos
antes da revisão e um após confirmar, sem duplicar na repetição. Não foram usados
dados reais. Chamada Gemini real ocorreu somente no benchmark sintético acima.

Para reproduzir, na pasta `backend`:

```bash
python -m pytest tests -q
python scripts/benchmark_syllabus.py --output ../docs/benchmarks/syllabus-s7-reference.json
# Opt-in: exclusivamente o corpus sintético versionado, sem habilitar produção.
python scripts/benchmark_syllabus.py --live --output ../docs/benchmarks/syllabus-s7-gemini.json
```

Os testes SQL/HTTP são opt-in e rejeitam banco remoto. Veja o
[executor HTTP local](privacidade-planos.md#integracao-http-local-de-auth-storage-e-processamento).
Nesta máquina, a porta Windows estava interceptada pelo WSL relay; a suíte usou
Python 3.13 na rede do contêiner descartável `agendaunb-s6d02-tests`, com proxy
loopback para o gateway desse mesmo projeto. O banco da aplicação 14322 e o
Supabase hospedado não foram alterados. [Registro de revisão](s7-b01-validacao.md).
