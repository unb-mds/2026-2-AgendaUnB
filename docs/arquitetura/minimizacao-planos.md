---
title: "Minimização de dados pessoais em planos de ensino"
description: "Padrões, preservação de conteúdo acadêmico e evidências da S8-B04."
---

A preparação determinística trata PDFs com texto selecionável e textos colados
no mesmo fluxo. O descarte do PDF e a autorização sobre o texto revisado
seguem o [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos).

| Categoria | Formatos de referência e casos sintéticos |
| --- | --- |
| Nome pessoal | `Professor(a): Pessoa Exemplo`, `Docente · Pessoa Exemplo`, `Monitor(a)`, `Aluno(a)`, `Discente`, `Coordenador(a)`, `Prof.`, `Profa.`, `Dr.` e `Dra.` seguidos de nome |
| Contato | `pessoa@example.test`, `+55 (61) 90000-0000`, `WhatsApp: 61900000000` |
| Documento | CPF pontuado ou rotulado, RG com rótulo, matrícula UnB com e sem barra, SIAPE com rótulo |
| Data pessoal | `Data de nascimento: 01/02/1990` |
| Perfil pessoal | Currículo Lattes, LinkedIn de pessoa e URL rotulada como site pessoal |
| Endereço | `Endereço residencial: Rua Exemplo, 123` |

O formulário de monitoria da graduação apresenta cargo com gênero separado
por espaço, nome do monitor, matrícula, RG, CPF, endereço e telefone, inclusive
em campos tabulares. O termo de monitoria da pós-graduação também inclui
matrícula e nascimento com rótulos abreviados. O validador público do SIGAA
confirma o uso de matrícula, SIAPE e CPF em cabeçalhos de documentos. [Formulário
de monitoria](https://design.unb.br/wp-content/uploads/Form_inscri_monitoria_grad.pdf) ·
[Termo de monitoria](https://ppgdsci.unb.br/images/FORMULARIOS/Termo_de_Compromisso_monitoria.pdf) ·
[Validador de documentos do SIGAA](https://sigaa.unb.br/sigaa/public/autenticidade/form.jsf).

Os valores da tabela e das fixtures são sintéticos. Os testes exercitam
cabeçalhos, campos separados por barra vertical, tabelas e rótulos com valor
na linha seguinte. Números ambíguos como RG, SIAPE e matrícula de nove dígitos
exigem contexto. O CPF compacto sem rótulo exige dígitos verificadores válidos
e preserva números rotulados como identificadores acadêmicos.

## Campos acadêmicos a preservar

- Nomes de disciplinas com números ou romanos, como Estrutura de Dados 1,
  Matemática Discreta 2 e Cálculo Diferencial e Integral II.
- Códigos de disciplina e turma, como CIC0004 e Turma 01.
- Semestres, como 2026.2 e 2026/2.
- Títulos e siglas de avaliações, como Prova 1, P1 e Trabalho Final.
- Datas acadêmicas numéricas, por extenso ou em ISO, além de horários
  e intervalos, como 14:30 e das 08h00 às 10h00.
- Locais acadêmicos, como Sala 204, Auditório Central e Bloco B.

A preservação de datas e títulos acompanha as orientações para os calendários
de avaliação da UnB. [Orientações do DEG para planos de ensino](https://deg.unb.br/wp-content/uploads/orientacoes_ementas_programas_pe.pdf).

## Exemplos sintéticos de antes e depois

O teste autenticado segue uma turma de teste, envia o mesmo conteúdo em
um PDF digital sintético e como texto colado, e lê a prévia com a sessão do
dono. O PDF mantém `pagina: 1`, enquanto o texto colado usa `pagina: null`.
Nos dois casos, `redactedCount` vale `2` e o hash corresponde às páginas
sanitizadas. O acesso com a conta de outro estudante retorna `404`.

**PDF sintético, texto extraído da página 1**

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

## Impactos verificados

- **Privacidade e LGPD:** nos cenários sintéticos, a preparação local reduz
  os dados retidos no snapshot privado e o texto enviado ao provedor simulado.
  Os logs e candidatos persistidos foram verificados com valores sintéticos.
  A revisão humana continua necessária para reconhecer informações fora dos
  formatos cobertos.
- **Contrato:** a alteração na prévia é aditiva. Os `POST` mantêm `202` e
  as páginas, permissões e regras de hash seguem o contrato existente.
  A coluna de contagem e o novo código de falha exigem as duas migrações
  S8-B04 antes de disponibilizar o backend.
- **Extração:** `validate_candidates` produziu os mesmos candidatos de prova
  e trabalho para as entradas de teste antes e depois da preparação, com
  horários, datas, locais nos trechos de origem e referências de página.
  A comparação usa uma resposta controlada do provedor.
