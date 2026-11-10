# Validação e revisão técnica — S7-B01, 10/11/2026

Escopo: issue #51 atualizada pelo solicitante, RF06/RNF02/RNF06/RNF10. Branch
`feat/geminiapi`, processamento `syllabus-v3-approved-text`. Integração das turmas,
importação pela interface e habilitação hospedada pertencem às dependências.

## Critérios e evidências

| Cenário | Evidência | Resultado |
| --- | --- | --- |
| PDF até dez páginas e texto bruto limitado | Testes de preparação, tamanho exato, UTF-8 e página nula | Aprovado localmente |
| Descarte do original e temporário | Sem chamada ao Storage; fechamento antes de persistir e em falha | Aprovado localmente |
| Minimização e autorização do texto exato | Hash canônico, payload conferido no navegador, edição revoga confirmações | Aprovado localmente |
| Isolamento entre contas | API, RLS/PostgREST e privilégios SQL com JWT/contas sintéticas | Aprovado localmente |
| Só provas e trabalhos; datas sem inferência | Corpus Gemini + testes de aulas/bibliografia/tipos inválidos/datas/horários | Aprovado no corpus |
| Retry/recuperação/fencing | Testes de lease expirado, limites de custo/tentativas, commit atômico e execução antiga | Aprovado localmente |
| Reprocessamento explícito | Candidatos pendentes anteriores descartados, nova versão e orçamento acumulado | Aprovado localmente |
| Autorização concorrente | Duas conexões PostgreSQL retornam uma versão | Aprovado localmente |
| Imutabilidade do snapshot | Trigger rejeita alteração durante execução, inclusive pelo backend | Aprovado localmente |
| Provedor indisponível/429/timeout/JSON inválido | Erros sanitizados, retry limitado e alternativa manual | Aprovado localmente |
| Sem avaliações | Conclusão vazia, sem evento automático | Aprovado localmente |
| RNF06 | Cinco PDFs sintéticos com Gemini; preparação e espera humana separadas | Todos abaixo de 20s; limites descritos no guia |

[Relatórios e comandos](processamento-planos-s7.md). Resultados executados no
ambiente local não equivalem a homologação ou implantação em produção.

## Execuções finais

- Backend: **171 aprovados, um ignorado**, incluindo PostgreSQL, Auth, Storage e
  PostgREST locais. O caso Gemini opt-in da suíte HTTP ficou desabilitado.
- Preparação no Windows: **25 aprovados**, incluindo fechamento do temporário,
  privacidade, hash, autorização, limites e tempo humano separado.
- Frontend: **16 testes de lógica** e **38 testes de navegador** aprovados,
  incluindo teclado, temas claro/escuro, desktop e celular.
- Build do frontend aprovado, com aviso preexistente de bundle acima de 500 kB.
- Corpus Gemini real: sete acertos, zero omissões e datas inventadas, cinco
  arquivos abaixo de 20s, com preparação medida separadamente.
- Migrações aplicadas somente na instância descartável local; nenhum projeto
  hospedado foi alterado. Contas, objetos e dados sintéticos foram limpos.

## Revisão de código

**Revisor técnico automatizado:** Codex. **Revisor humano:** a registrar após
aprovação; não foi atribuída aprovação nominal a integrante da equipe.

Foram revisados contratos, permissões, transições de estado, dados enviados ao
Gemini, registros no banco, retenção do PDF, logs e preservação das rotas legadas.

Problemas encontrados e corrigidos:

- O JSONB muda a ordem dos campos: o hash agora é canônico nos dois lados e possui
  regressão específica, sem alterar texto/espaços aprovados.
- O temporário do PDF precisava ser fechado antes de persistir texto: o registro
  recebe somente tamanho/metadados e páginas; testes cobrem sucesso e falha.
- O rascunho anterior às correções do estudante não precisava permanecer: após
  autorização, conserva-se apenas a versão corrigida também no texto preparado.
- Planos históricos não podiam ser marcados como aguardando nova autorização de
  texto inexistente: a indicação só vale para a preparação S7.
- A negação SQL passa por privilégios revogados, além de RLS: o teste legado foi
  ajustado para esperar `42501`, preservando a exigência de bloquear a escrita.

A revisão não encontrou bloqueio de implementação nos cenários verificados.
A etapa de implantação exige revisão humana das migrações e elegibilidade.

## Pendências externas e fechamento

- [ ] Revisar/aplicar migrações e validar o ambiente hospedado com dados sintéticos.
- [ ] Registrar em S7-B02 a elegibilidade do público, termos/tier e infraestrutura.
- [ ] Integrar os consumidores de candidatos/turmas em S7-B04/S7-F03/S7-D01.
- [ ] Anexar URL do PR e identificar a versão efetivamente implantada na issue.
- [ ] Registrar o revisor humano e sua aprovação dos contratos, permissões e dados.

Nenhuma flag foi ativada no `.env`, nenhuma chave entrou no repositório e não
houve alteração do Supabase na nuvem. As evidências de fechamento permanecem
abertas até essas etapas ocorrerem; não se declara aprovação de produção.
