# Política de Segurança

A segurança e a privacidade dos dados acadêmicos são prioridades no **Agenda UnB**. Este documento descreve as versões suportadas, os controles aplicados e como relatar vulnerabilidades de forma responsável.

## Versões suportadas

As correções de segurança são aplicadas continuamente na branch principal (`main`) e na versão em produção (`https://agendaunb.com.br`):

| Versão / Branch | Suporte de segurança |
| --- | --- |
| `main` (`v0.2.x` / produção) | Suportada |
| `v0.1.0` | Encerrado |

## Como relatar uma vulnerabilidade

**Não abra uma issue pública no GitHub para relatar falhas de segurança, vazamento de dados ou credenciais expostas.**

Envie o relato de forma privada para o canal oficial da equipe mantenedora:

- **E-mail:** `unbagenda@gmail.com` (assunto sugerido: `[SEGURANÇA] Resumo da vulnerabilidade`)

### O que incluir no relato

Para agilizar a análise e a correção, inclua sempre que possível:

1. **Componente afetado:** frontend (`frontend/`), API (`backend/`), esquema/políticas RLS (`supabase/migrations/`), integrações (`Google Calendar`, `Gemini`, `Followw`, `Agenda UnB Notícias`) ou infraestrutura.
2. **Descrição técnica:** tipo da falha (ex.: quebra de controle de acesso/RLS, XSS, CSRF, bypass de confirmação de e-mail, exposição de dados sensíveis) e pré-condições necessárias.
3. **Passos de reprodução:** sequência mínima de requisições, rotas ou ações de interface que demonstram o problema (sem executar ataques destrutivos em produção).
4. **Impacto estimado:** quais dados, papéis (`student`, `professor`, `admin`) ou operações podem ser comprometidos.

### Processo de resposta

1. **Confirmação de recebimento:** confirmação inicial do relato e triagem de severidade (**Alta**, **Média** ou **Baixa**).
2. **Investigação e correção:** reprodução em ambiente local isolado, desenvolvimento do patch (código e/ou migração SQL) e adição de teste automatizado de regressão.
3. **Implantação e divulgação:** aplicação da correção em produção e atualização da documentação de [Verificação de segurança](../docs/processo/seguranca.md) após a mitigação.

## Práticas e salvaguardas do projeto

- **Autorização em camadas:** validação de sessão JWT e e-mail confirmado na API FastAPI, funções RPC com verificação explícita de papel e políticas Row Level Security (RLS) no PostgreSQL/Supabase.
- **Minimização e privacidade de planos de ensino:** descarte imediato do arquivo PDF original após extração local de texto em memória, sanitização automática de dados pessoais e envio ao provedor de IA com `store: false`.
- **Proteção de credenciais e OAuth:** escopo mínimo (`calendar.app.created`) para o Google Calendar em projeto OAuth dedicado, validação de `state` e PKCE S256, e armazenamento de tokens cifrados com Fernet exclusivamente no servidor.
- **Higiene do repositório:** bloqueio de variáveis sensíveis com prefixo `VITE_` no build do frontend e auditoria de dependências (`pip-audit` e `npm audit`).

Para detalhes completos da matriz de acesso e dos controles verificados, consulte [`docs/processo/seguranca.md`](../docs/processo/seguranca.md) e [`docs/processo/privacidade.md`](../docs/processo/privacidade.md).
