# S6-F02 — Editor local (entrega parcial do tópico 2)

Esta entrega prepara edição, seleção e descarte de avaliações sem depender de um
contrato HTTP ainda não publicado. Não conclui o tópico 2 nem a issue S6-F02.
A área de revisão está conectada à rota `/plano-de-ensino` e aparece com
`make dev` para usuários autenticados. Sem plano aberto, orienta selecionar um
envio no histórico. Ao abrir um plano, acompanha os estados reais da consulta:
carregamento, erro, pendente, processando, falha, concluído vazio, concluído sem
detalhes disponíveis e estado desconhecido. Não contém dados de demonstração e
não grava eventos. Upload e consultas existentes são reutilizados.

O editor de campos continua aguardando candidatos reais: a API atual só fornece
metadados e contagem. Uma contagem positiva não é transformada em candidatos
fictícios. A seção “O que poderei revisar?” explica as possibilidades e limites.
Esta integração não conclui a edição real nem a confirmação da S6-F02.

Para verificar no produto: execute `make dev`, entre na conta, abra
`http://localhost:5173/plano-de-ensino` e procure “Revisar avaliações”. Abra um
plano pelo botão “Acompanhar” no histórico para ver o estado correspondente.

## Arquitetura e uso futuro

- `src/lib/syllabusReview.js`: `createReviewDraft(items)` recebe uma lista local
  com `id` único e strings opcionais `title`, `type`, `date` (`AAAA-MM-DD`) e
  `time` (`HH:mm`). Rejeita identificadores ausentes/duplicados. Essa estrutura
  **não é um contrato de API**; será necessário um adaptador para S6-B02.
- Cada rascunho começa com `decision: 'pending'` e `utcOffset: ''`. Não se
  presume seleção, horário ou fuso do navegador. Decisões locais possíveis:
  `pending`, `selected`, `discarded`.
- `SyllabusReviewEditor` recebe `value`, `onChange` e `disabled` opcional. O
  componente pai é dono do estado. Deve inicializar uma vez por plano/conta,
  preservar o rascunho durante falhas e não recriá-lo a cada consulta de polling.
  Ao trocar plano/conta, deve desmontar o editor (por exemplo, usando `key`).
- O botão **Conferir selecionados** valida apenas os itens selecionados e move
  o foco ao primeiro campo inválido. Não equivale a confirmar na agenda.
- Descartar mantém os campos para permitir voltar à seleção. Tipo é editável,
  sem inventar enumeração obrigatória antes do contrato. Título não vazio,
  data real, horário de 24 horas e deslocamento UTC explícito são exigidos para
  selecionados. Os limites do backend serão alinhados quando publicados.
- `utcOffset` representa a diferença explícita para UTC na data escolhida, no
  formato `±HH:mm`, entre -14:00 e +14:00. Não representa uma zona IANA nem
  calcula horário de verão. Não há conversão ou serialização HTTP nesta etapa.
- Edições são somente em memória; não sobrevivem a recarga. Não se utiliza
  localStorage para guardar dados privados ou simular persistência.

## Validação

Execute em `frontend`:

```sh
npm test
npm run build
npx playwright test tests/syllabus-review.spec.js --workers=2
npx playwright test tests/syllabus.spec.js --workers=2
```

O harness é servido exclusivamente por interceptação do Playwright: carrega o
componente real com dados de teste, sem criar rota ou modo simulado no produto.
Verifica seleção, descarte/reseleção, preservação das edições, foco, teclado,
ausência de chamadas à API, estado vazio e layouts de 360/768/1365 px em ambos
os temas. Screenshots ficam em `frontend/test-results/`.

Aplicação dos guias reais do Impeccable: `harden` orienta validação, identificação
única, foco, mensagens e preservação; `polish` orienta uso dos tokens existentes,
espaçamento, campos legíveis e adaptação dos temas e tamanhos de tela.

## Pendências fora desta entrega

Candidatos e evidências de origem (tópico 1), integração dos dados reais no
editor, contrato/endpoint de confirmação S6-B02, procedência, atualização da
agenda e testes da jornada integrada. Nenhuma mudança em backend, banco,
infraestrutura ou outra issue integra esta entrega.
