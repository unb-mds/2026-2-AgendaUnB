# Planos de ensino — demonstração React

## Abrir e experimentar

Execute `make dev` e abra `http://localhost:5173/plano-de-ensino`.
O modo inicial é **Demonstração interativa**, também acessível sem login.

1. Clique em **Usar PDF de exemplo**, depois **Vincular turmas de exemplo**.
2. Em Conectar planos, escolha uma turma sem plano. Escolha um PDF local ou
   outro exemplo e clique em **Simular extração**.
3. Selecione pelo menos uma avaliação. Edite os campos desejados, informe o
   horário quando ausente e o fuso (por exemplo `-03:00`). Marque a conferência
   e clique em **Confirmar e vincular plano**.
4. Selecione a turma pronta e clique em **Simular envio para Meus Eventos**.
   A prévia exibe os eventos, calendário de novembro/dezembro e lista completa.

Cálculo 1 já contém um plano ilustrativo pronto, para testar a agenda diretamente.
A busca do catálogo filtra nome/sigla sem diferenciar acentos e permite selecionar
campus. Limpar filtros restaura a amostra completa de cinco turmas.

## Limites explícitos

Esta é a conversão interativa do protótipo HTML/CSS, não implementação dos
serviços da Sprint 6. Matrícula, candidatos e procedência são exemplos fixos;
escolher PDF valida tipo/tamanho e guarda somente seu nome em memória. Nenhum
arquivo é lido, enviado ou persistido. Não há IA ou integração com o catálogo
real. A prévia de agenda não altera `/eventos` nem o banco.

As edições sobrevivem à navegação entre etapas dentro da demonstração. Alterar
campos revoga a conferência; confirmar exige seleção e campos válidos. Descartar
preserva a edição, e importações repetidas não duplicam candidatos na prévia.
Planos confirmados ficam somente para leitura neste recorte de demonstração.
Recarregar, sair do modo ou trocar conta reinicia o estado. **Reiniciar
demonstração** exige confirmação e permite cancelar. Temporizadores são
cancelados ao sair, evitando concluir uma simulação abandonada.

## Envio existente

**Envios reais de PDF** preserva o fluxo anterior de upload/histórico. A URL
`/plano-de-ensino?modo=envios` abre esse modo. URLs já existentes com `?plano=ID`
continuam abrindo o acompanhamento real. As dependências e erros de Storage
desse fluxo não foram alterados por esta entrega.

## Arquitetura

- `TeachingPlanPage.jsx`: seleção de modo, navegação, sessão e fluxo existente.
- `TeachingPlanJourney.jsx`: componentes React de matrícula, turmas, revisão,
  catálogo, prévia da agenda e confirmação de reinício.
- `teachingPlanDemo.js`: dados explicitamente ilustrativos e reducer de estados,
  isolado para futura substituição por contratos reais.
- `global.css`: estilos exclusivos prefixados por `tp-`, usando tokens existentes
  e o tema controlado pela navegação. O nome existente é `global.css`, não
  `globals.css`. O HTML/CSS estático permanece como referência separada.

## Validação e Impeccable

Guias locais **harden** e **polish** aplicados: estados vazios, validação, foco,
nomes acessíveis, confirmação para reiniciar, prevenção de duplicatas,
continuidade de edições, temas, responsividade e inspeção de capturas.

```sh
cd frontend
npm test
npm run build
npx playwright test tests/teaching-plan-journey.spec.js tests/syllabus.spec.js --workers=2
```

Os testes de navegador usam sessão controlada apenas nos testes. A demonstração
de produto declara seus exemplos visivelmente e não utiliza endpoints privados.
Os testes do fluxo real continuam cobrindo upload, histórico, recarga e isolamento.
