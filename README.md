<p align="center">
  <img src="frontend/public/banner.png" alt="Banner Agenda UnB" width="760">
</p>

# Agenda UnB

**Plataforma centralizada de eventos e organização acadêmica da Universidade de Brasília**

<p align="center">
  <a href="https://github.com/unb-mds/2026-2-AgendaUnB/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/unb-mds/2026-2-AgendaUnB/supabase-ci.yml?branch=dev&label=CI%20%26%20Testes&logo=github" alt="Status do CI">
  </a>
  <a href="https://agendaunb.com.br/docs">
    <img src="https://img.shields.io/badge/Docs-Mintlify-008bff?logo=readthedocs&logoColor=white" alt="Documentação Online">
  </a>
  <a href="https://github.com/unb-mds/2026-2-AgendaUnB/issues">
    <img src="https://img.shields.io/github/issues/unb-mds/2026-2-AgendaUnB?color=003366&label=Issues%20Abertas" alt="Issues Abertas">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/Licen%C3%A7a-MIT-008744" alt="Licença MIT">
  </a>
  <a href="https://www.unb.br/">
    <img src="https://img.shields.io/badge/UnB-MDS%202026%2F2%20%7C%20Grupo%20G8-003366" alt="UnB - MDS 2026/2">
  </a>
</p>

O **Agenda UnB** é uma plataforma web colaborativa de eventos e organização acadêmica desenvolvida para os estudantes e docentes da **Universidade de Brasília (UnB)** centralizarem sua rotina em um único lugar. O sistema integra um catálogo público de eventos dos campi a um organizador acadêmico inteligente com extração automatizada de datas de planos de ensino, e é totalmente gratuito e de código aberto.

## Documentação

- [Instalar e executar o Agenda UnB](docs/processo/execucao-local.md)
- [Documentação oficial](https://agendaunb.com.br/docs)
- [Arquitetura e modelo de dados](docs/arquitetura/visao-geral.md)
- [Requisitos do sistema](docs/produto/requisitos.md)
- [Diretrizes de acessibilidade](ACCESSIBILITY.md)
- [Política de segurança](SECURITY.md)
- [Contribuindo com o Agenda UnB](docs/processo/contribuindo.md)

Acesse a aplicação em funcionamento em **[agendaunb.com.br](https://agendaunb.com.br)**, ou explore nossos protótipos e quadros de planejamento no **[Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217)** e no **[Miro](https://miro.com/app/board/uXjVHtiWi4U=/)**. Consulte também os [arquivos de documentação no repositório](docs/).

## Termos de uso e privacidade

Estudantes podem usar e-mail e senha ou entrar com o Google. O perfil docente exige e-mail institucional `@unb.br` confirmado. A agenda pessoal e o texto preparado ficam restritos à conta. O PDF é descartado após a leitura e a primeira versão elegível de avaliações pode ficar disponível a quem segue a turma. [Política de Privacidade](docs/produto/politica-de-privacidade.md) · [Termos de Uso](docs/produto/termos-de-uso.md).

## Sobre o Agenda UnB

A rotina de um estudante da UnB costuma estar fragmentada: a grade fica no SIGAA, as datas de provas estão espalhadas em PDFs de planos de ensino e os eventos acadêmicos e culturais circulam por redes sociais, cartazes e grupos de WhatsApp. O Agenda UnB foi criado para reunir essas informações em uma única aplicação web produtiva, aberta e extensível.

### Experiências acadêmicas unificadas

Queremos permitir que cada estudante acompanhe a vida universitária e seus compromissos de estudo sem precisar alternar entre dezenas de portais. O Agenda UnB reúne dois eixos principais em uma interface responsiva (com temas claro e escuro):

- **Agenda do Campus:** Catálogo público de eventos acadêmicos, culturais e esportivos de todos os campi da UnB (**Darcy Ribeiro (Plano Piloto), FCTE (Gama), FCTS (Ceilândia), FUP (Planaltina) e FAL**), com visualização em lista ou calendário (mensal e semanal), filtros por área, campus e turno, além de salvamento na agenda pessoal e envio de sugestões com moderação.
- **Organizador Acadêmico.** Agenda pessoal com compromissos privados, eventos públicos salvos, lembretes e exportação para Google Agenda ou ICS. O envio de PDF ou texto autoriza a extração de candidatos a provas e trabalhos após sanitização automática. Cada pessoa revisa e confirma as datas que importa.

<p align="center">
  <img src="frontend/public/agendaunb-mobile.png" alt="Telas de Planos de ensino, página inicial e Meus Eventos do Agenda UnB, com botões para exportar a agenda e criar eventos" width="720">
</p>

### Arquitetura moderna e resultados rápidos

O Agenda UnB foi estruturado com tecnologias modernas e gratuitas para garantir carregamento rápido, segurança de dados e facilidade de manutenção pela equipe:

| Camada | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite 6, React Router 7 | SPA responsiva com temas claro/escuro e tipografia *Orbitron + Inter* |
| **Backend (API)** | Python 3, FastAPI, SQLAlchemy 2, Pydantic 2 | API REST com validação automática, moderação e extração com IA |
| **Banco de Dados** | PostgreSQL (Supabase) | Dados relacionais protegidos por *Row Level Security (RLS)* |
| **Autenticação e Storage** | Supabase Auth & Storage | Google OAuth, e-mail/senha, JWT e buckets privados por usuário |
| **Documentação e CI** | Mintlify e GitHub Actions | Documentação publicada em `/docs` e validação da aplicação e das migrações |

### Desenvolvimento produtivo e execução simplificada

O ambiente local do Agenda UnB utiliza **GNU Make**, **Supabase CLI** e **Docker**, permitindo que qualquer pessoa contribuidora suba o banco de dados, o backend e o frontend com poucos comandos e veja suas alterações em tempo real:

```bash
make setup
make dev
```

Para encerrar os serviços e parar os containers locais do Supabase, pressione `Ctrl+C` e execute `make stop`. Consulte o [guia de execução local](docs/processo/execucao-local.md).

### Modelo aberto, seguro e extensível

O Agenda UnB funciona em qualquer ambiente de desenvolvimento (com suporte nativo a VS Code, Docker e Supabase CLI) e segue padrões rigorosos de segurança e qualidade: perfis criados automaticamente via *triggers*, moderação atômica de sugestões estudantis, isolamento de dados privados por usuário e integração contínua automatizada.

O Agenda UnB é um projeto de código aberto da disciplina de **Métodos de Desenvolvimento de Software (MDS)** da UnB. Consulte o [guia de contribuição](docs/processo/contribuindo.md) ou abra uma [issue no GitHub](https://github.com/unb-mds/2026-2-AgendaUnB/issues).

## Criadores

| <a href="https://github.com/thomas4ugust0"><img src="https://github.com/thomas4ugust0.png" width="170" alt="Thomas Araujo"/><br><sub><b>Thomas Araujo</b></sub></a><br>`FRONTEND` | <a href="https://github.com/heitormontt"><img src="https://github.com/heitormontt.png" width="170" alt="Heitor Monteiro"/><br><sub><b>Heitor Monteiro</b></sub></a><br>`BACKEND` | <a href="https://github.com/pontesluis"><img src="https://github.com/pontesluis.png" width="170" alt="Luis Davi"/><br><sub><b>Luis Davi</b></sub></a><br>`BANCO DE DADOS` |
| :---: | :---: | :---: |
| <a href="https://github.com/Bielziin07"><img src="https://github.com/Bielziin07.png" width="170" alt="Gabriel Escramin"/><br><sub><b>Gabriel Escramin</b></sub></a><br>`FRONTEND` | <a href="https://github.com/marrathomaz"><img src="https://github.com/marrathomaz.png" width="170" alt="Thomaz Marra"/><br><sub><b>Thomaz Marra</b></sub></a><br>`BACKEND` | <a href="https://github.com/felipecduque7"><img src="https://github.com/felipecduque7.png" width="170" alt="Felipe Duque"/><br><sub><b>Felipe Duque</b></sub></a><br>`BANCO DE DADOS` |
