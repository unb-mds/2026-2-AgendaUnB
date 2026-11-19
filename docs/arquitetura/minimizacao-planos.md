# Minimização de dados pessoais em planos de ensino

Na S8-B04, a mesma preparação determinística deve tratar PDFs com texto
selecionável e textos colados. O [ADR-003](adrs/adr-003-minimizar-dados-de-planos.md)
define o descarte do PDF e a autorização sobre o texto revisado.

| Categoria | Formatos de referência e casos sintéticos |
| --- | --- |
| Nome pessoal | `Professor(a): Pessoa Exemplo`, `Docente · Pessoa Exemplo`, `Monitor(a)`, `Aluno(a)`, `Discente`, `Coordenador(a)`, `Prof.`, `Profa.`, `Dr.` e `Dra.` seguidos de nome |
| Contato | `pessoa@example.test`, `+55 (61) 90000-0000`, `WhatsApp: 61900000000` |
| Documento | CPF pontuado ou rotulado, RG com rótulo, matrícula UnB com e sem barra, SIAPE com rótulo |
| Data pessoal | `Data de nascimento: 01/02/1990` |
| Perfil pessoal | Currículo Lattes, LinkedIn de pessoa e URL rotulada como site pessoal |
| Endereço | `Endereço residencial: Rua Exemplo, 123` |

As máscaras existentes e os formatos de cabeçalho cobertos pelos testes de
preparação são o ponto de partida. As variantes da tabela são exemplos
sintéticos para regressão. Um cabeçalho isolado, um campo ao lado de outro
separado por barra vertical, uma linha tabular e um rótulo com valor na linha
seguinte representam layouts distintos.

## Campos acadêmicos a preservar

- Nomes de disciplinas com números ou romanos, como Estrutura de Dados 1,
  Matemática Discreta 2 e Cálculo Diferencial e Integral II.
- Códigos de disciplina e turma, como CIC0004 e Turma 01.
- Semestres, como 2026.2 e 2026/2.
- Títulos e siglas de avaliações, como Prova 1, P1 e Trabalho Final.
- Datas acadêmicas numéricas, por extenso ou em ISO, além de horários
  e intervalos, como 14:30 e das 08h00 às 10h00.
- Locais acadêmicos, como Sala 204, Auditório Central e Bloco B.
