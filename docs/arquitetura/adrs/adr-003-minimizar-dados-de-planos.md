---
title: "ADR-003 · Minimização de dados de planos de ensino"
---

# ADR-003 · Descartar PDFs e autorizar apenas texto revisado para processamento externo

**Estado** Aceita para a Release 2. Implementação e homologação previstas no planejamento da release.

## Contexto

Planos de ensino podem conter informações sensíveis além do cronograma necessário para extrair datas de provas e trabalhos. O fluxo anterior armazena o PDF em um bucket privado. A decisão da R2 delimita o que o Agenda UnB retém e o que pode enviar ao provedor externo.

## Decisão

Extrair texto localmente e descartar o PDF original ao fim dessa etapa, inclusive quando ela falhar. Antes de chamar o provedor, apresentar ao usuário o trecho minimizado e o destino. A autorização vale para o texto revisado daquela versão. Uma mudança de texto exige nova revisão e autorização. Apenas os candidatos confirmados pelo usuário entram na agenda.

## Alternativas para comparação

Reter o PDF em armazenamento privado permitiria reprocessar o original, mas aumentaria a quantidade de dados sensíveis sob custódia. Enviar o documento completo ao provedor simplificaria a extração, mas exporia conteúdo além do trecho revisado. O recorte aceito usa apenas o texto necessário para o processamento externo.

## Consequências

O sistema precisa limpar arquivos temporários e remover originais legados conforme o contrato de migração. Se uma nova extração depender do PDF descartado, o usuário precisa reenviar o arquivo ou fornecer texto. A interface precisa distinguir revisão, autorização e confirmação dos candidatos.

[Contrato da Release 2](../../atualizacoes.md#contratos-da-release-2) · [Guia do frontend](../../planos-de-ensino-frontend.md) · [Consolidação dos requisitos (#67)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/67)

## Leitura e manutenção

Data deste registro complementar: **2026-11-08**; não representa a data original de aprovação. Nenhuma ADR é substituída por este registro. O estado acima distingue implementação, proposta e decisão da R2; não constitui evidência de homologação.

Consulte o [índice de ADRs](index.md) para o mapa de decisões e o modelo de novos registros. As alternativas são comparações para revisão, não atas de uma avaliação histórica.
