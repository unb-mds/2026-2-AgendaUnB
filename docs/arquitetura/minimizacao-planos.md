---
title: "Minimização de dados pessoais em planos de ensino"
description: "Padrões determinísticos de detecção e mascaramento de dados pessoais, preservação de conteúdo acadêmico e contrato de preparação de planos de ensino."
---

A preparação determinística trata PDFs com texto selecionável e textos colados no mesmo pipeline antes da persistência do snapshot privado e do envio ao provedor externo de IA. O descarte imediato do PDF e a autorização explícita sobre o texto sanitizado seguem o [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos).

| Categoria | Formatos de referência e casos sintéticos |
| --- | --- |
| Nome pessoal | `Professor(a): Pessoa Exemplo`, `Docente · Pessoa Exemplo`, `Monitor(a)`, `Aluno(a)`, `Discente`, `Coordenador(a)`, `Prof.`, `Profa.`, `Dr.` e `Dra.` seguidos de nome |
| Contato | `pessoa@example.test`, `+55 (61) 90000-0000`, `WhatsApp: 61900000000` |
| Documento | CPF pontuado ou rotulado, RG com rótulo, matrícula UnB com e sem barra, SIAPE com rótulo |
| Data pessoal | `Data de nascimento: 01/02/1990` |
| Perfil pessoal | Currículo Lattes, LinkedIn de pessoa e URL rotulada como site pessoal |
| Endereço | `Endereço residencial: Rua Exemplo, 123` |

A detecção cobre cabeçalhos, campos separados por barra vertical, tabelas e rótulos com valor na linha seguinte, alinhada aos modelos reais de formulários e termos da UnB ([Formulário de monitoria](https://design.unb.br/wp-content/uploads/Form_inscri_monitoria_grad.pdf) · [Termo de monitoria](https://ppgdsci.unb.br/images/FORMULARIOS/Termo_de_Compromisso_monitoria.pdf) · [Validador de documentos do SIGAA](https://sigaa.unb.br/sigaa/public/autenticidade/form.jsf)). Números ambíguos como RG, SIAPE e matrícula de nove dígitos exigem contexto rotulado; CPF compacto sem rótulo exige dígitos verificadores válidos para evitar falsos positivos em códigos acadêmicos.

## Campos acadêmicos preservados

- Nomes de disciplinas com números ou algarismos romanos, como `Estrutura de Dados 1`, `Matemática Discreta 2` e `Cálculo Diferencial e Integral II`.
- Códigos de disciplina e turma, como `CIC0004` e `Turma 01`.
- Semestres, como `2026.2` e `2026/2`.
- Títulos e siglas de avaliações, como `Prova 1`, `P1` e `Trabalho Final`.
- Datas acadêmicas numéricas, por extenso ou ISO, além de horários e intervalos (`14:30`, `das 08h00 às 10h00`).
- Locais acadêmicos, como `Sala 204`, `Auditório Central` e `Bloco B`.

A preservação de datas e títulos acompanha as orientações institucionais para calendários de avaliação da UnB ([Orientações do DEG para planos de ensino](https://deg.unb.br/wp-content/uploads/orientacoes_ementas_programas_pe.pdf)).

## Exemplos sintéticos de sanitização

Os fluxos de PDF digital e texto colado passam pela mesma higienização (`backend/src/modules/syllabus/minimization.py`). PDFs mantêm o número da página (`pagina: 1`, `2`, ...), enquanto textos colados utilizam `pagina: null`. Em ambos os casos, `redactedCount` registra o total de trechos mascarados na preparação inicial e `textHash` corresponde ao SHA-256 compacto das páginas sanitizadas.

**PDF digital (texto extraído da página 1)**

```text
Disciplina: Estrutura de Dados 1 | Prof. Pessoa Exemplo | RG: 12.345.678-X
Prova 1: 20/11/2026 14:30 Sala 204
```

```text
Disciplina: Estrutura de Dados 1 | Prof. [identificador removido] | RG: [identificador removido]
Prova 1: 20/11/2026 14:30 Sala 204
```

**Texto colado em campo editável**

```text
Disciplina: Estrutura de Dados 1 | Prof. Pessoa Exemplo | CPF: 000.000.000-00
Prova 1 - 10/11/2026 - 14:00.
```

```text
Disciplina: Estrutura de Dados 1 | Prof. [identificador removido] | CPF: [identificador removido]
Prova 1 - 10/11/2026 - 14:00.
```

## Garantias de privacidade e contrato

- **Minimização e LGPD:** a preparação local reduz os dados retidos no snapshot privado (`texto_preparado` / `texto_aprovado`) e o texto enviado ao provedor externo. Snapshots legados que contenham dados pessoais detectáveis são bloqueados antes da chamada externa com `erro_codigo = 'texto_com_dados_pessoais'`, orientando novo envio.
- **Revisão humana:** as avaliações extraídas são apresentadas para conferência e confirmação explícita do usuário antes de qualquer gravação em `eventos_pessoais`.
- **Contrato da prévia:** as respostas de preparação, autorização e detalhe retornam `redactedCount` (fora do cálculo de `textHash`), permitindo que a interface informe o total de remoções ao usuário durante e após a análise.
- **Verificação automatizada:** os fluxos de preparação, mascaramento e validação de prévia são cobertos em `backend/tests/test_syllabus_processing.py`, `backend/tests/test_syllabus_privacy_minimization.py` e nos testes E2E `frontend/tests/syllabus-consent.spec.js` e `frontend/tests/syllabus.spec.js`.
