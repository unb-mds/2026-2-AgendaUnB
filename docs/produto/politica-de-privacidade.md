---
title: "Política de Privacidade"
description: "Quais dados o Agenda UnB trata, para quê, com quem compartilha e como exercer seus direitos."
---

**Versão 2026-11-20.** Esta Política de Privacidade descreve como a plataforma **Agenda UnB** coleta, utiliza, armazena, compartilha e elimina dados pessoais em conformidade com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 — LGPD).

O Agenda UnB é um projeto acadêmico sem fins comerciais desenvolvido na disciplina Métodos de Desenvolvimento de Software da Universidade de Brasília (UnB, 2026/2). A plataforma não constitui um serviço oficial da Universidade de Brasília.

## 1. Controlador e canal de atendimento

O tratamento de dados pessoais realizado na plataforma é conduzido pela equipe mantenedora do Agenda UnB. Todas as solicitações de titulares, dúvidas sobre privacidade, pedidos de correção ou reclamações devem ser encaminhadas exclusivamente pelo canal oficial de contato: [unbagenda@gmail.com](mailto:unbagenda@gmail.com). Para proteção da sua privacidade, não publique dados pessoais em issues ou discussões públicas do repositório.

## 2. Dados pessoais tratados e finalidades

Para viabilizar o acesso, a organização da agenda pessoal, a descoberta de eventos universitários e as integrações solicitadas pelo usuário, o Agenda UnB trata estritamente as seguintes categorias de dados:

- **Dados de cadastro e autenticação:** nome completo, endereço de e-mail e senha (armazenada exclusivamente pelo serviço de autenticação por meio de resumo criptográfico irreversível), fornecidos diretamente por você no momento do cadastro para criação, proteção e recuperação da conta.
- **Dados de entrada com conta Google:** nome, endereço de e-mail e foto de perfil fornecidos pelo Google mediante sua autorização prévia, quando você opta pela autenticação via OAuth.
- **Perfil de acesso (papel):** classificação como estudante, professor ou administrador, definida no cadastro conforme elegibilidade institucional ou atribuída pela administração para controle de permissões na plataforma.
- **Agenda pessoal e compromissos privados:** eventos, prazos acadêmicos, horários e locais cadastrados diretamente por você, mantidos sob acesso restrito à sua conta.
- **Eventos públicos salvos e notificações:** registros de vínculos com eventos públicos adicionados à sua agenda pessoal, bem como avisos gerados pela plataforma sobre alterações ou moderação de sugestões.
- **Sugestões e publicações de eventos públicos:** informações de eventos que você propõe ou publica no catálogo do campus; após aprovação, o nome associado à publicação pode ser exibido como organizador.
- **Vínculos com turmas:** ofertas de disciplinas que você escolhe seguir no catálogo público, registradas como declaração pessoal sem valor de comprovação de matrícula.
- **Planos de ensino e datas extraídas:** texto sanitizado de planos de ensino enviados por você e os respectivos candidatos a provas e trabalhos extraídos para revisão e importação.
- **Registros de aceite e consentimento:** comprovação de leitura dos Termos de Uso e desta Política de Privacidade, além dos consentimentos específicos concedidos ou revogados por você.
- **Integração com o Google Agenda:** identificadores técnicos de conexão e tokens criptografados necessários para exportar eventos selecionados quando você ativa voluntariamente a integração.
- **Registros técnicos e métricas de acesso:** data, rota acessada, endereço IP e métricas agregadas de navegação gerados automaticamente para segurança da aplicação, diagnóstico de falhas, prevenção de abuso e medição básica de audiência.

O Agenda UnB não solicita número de matrícula, CPF, histórico escolar, notas nem credenciais do SIGAA ou de outros sistemas institucionais. Nenhum dado pessoal é utilizado para publicidade direcionada ou comercializado com terceiros.

## 3. Tratamento de planos de ensino

O envio de planos de ensino em formato PDF aceita arquivos digitais de até **10 páginas** e **10 MB**. O texto é extraído localmente em memória no servidor e o arquivo PDF original é descartado imediatamente após a leitura, não permanecendo armazenado na plataforma.

Para envios em texto ou após a leitura local do PDF, a plataforma aceita até **40.000 bytes** UTF-8 (correspondentes a até 10 páginas) e executa uma etapa automática de sanitização baseada em regras fixas antes de qualquer transmissão externa. Essa rotina substitui endereços de e-mail, telefones brasileiros, sequências numéricas de 9 a 11 dígitos ou CPF e linhas iniciadas por rótulos identificadores (como professor, aluno, nome, matrícula ou CPF). A filtragem automática atua sobre padrões detectáveis e não substitui a conferência prévia pelo usuário caso o texto contenha identificadores fora desses formatos.

Ao acionar **Enviar PDF e extrair** ou **Enviar texto e extrair**, você autoriza o envio do texto sanitizado daquele plano específico para análise automatizada. Antes de iniciar o processamento externo no modelo Gemini, o servidor verifica novamente o conteúdo para bloquear o envio caso identificadores pessoais detectáveis permaneçam presentes.

Toda avaliação extraída constitui apenas uma sugestão com evidência de trecho de origem e só passa a integrar a sua agenda pessoal mediante confirmação explícita. Todo plano inicia em modo **privado**; ao consultar ou confirmar o resultado, a primeira versão com avaliações extraídas torna-se disponível para seguidores autenticados da respectiva turma, preservando o texto integral restrito à conta de origem. O compartilhamento pode ser retirado a qualquer momento na página **Plano de Ensino**, mantendo-se preservadas as cópias independentes já importadas por outros usuários em suas próprias agendas.

## 4. Compartilhamento com fornecedores e fontes consultadas

Para hospedar, operar e disponibilizar suas funcionalidades, o Agenda UnB utiliza prestadores de serviço que processam dados estritamente sob nossas instruções operacionais, parte deles localizada fora do Brasil (Estados Unidos ou rede distribuída global), o que configura transferência internacional de dados:

- **Supabase** (Estados Unidos): provê banco de dados PostgreSQL, autenticação e armazenamento gerenciado, abrigando os dados da conta e registros da aplicação.
- **Render** (Estados Unidos): hospeda a API de backend, processando dados em trânsito e registros técnicos operacionais.
- **Vercel** (rede global): hospeda a aplicação web e coleta métricas agregadas de visitação por meio de `@vercel/analytics/react` (incluindo registros técnicos de acesso, páginas visitadas, país ou região aproximada e tipo de dispositivo ou navegador, sem cookies publicitários).
- **Google (Autenticação)** (Estados Unidos e outros): realiza o login via conta Google, fornecendo nome, e-mail e foto mediante sua autorização.
- **Google (Gemini)** (Estados Unidos e outros): realiza a extração de datas a partir exclusivamente do texto sanitizado cuja análise você autorizou (até **40.000 bytes** UTF-8), com armazenamento de interações desativado (`store: false`).
- **Google (Agenda)** (Estados Unidos e outros): recebe identificador técnico, título, datas e horários dos eventos selecionados, local quando disponível e descrição quando incluída por você, exclusivamente para gravação na agenda secundária **"Agenda UnB"** caso você conecte sua conta.
- **Google Fonts** (rede global): disponibiliza arquivos de tipografia e ícones da interface, recebendo o endereço IP do navegador durante o carregamento desses recursos estáticos.

O catálogo público de turmas (**Followw**) e o portal público **Agenda UnB Notícias** são apenas consultados em modo de leitura pelo servidor, sem envio de cookies, credenciais ou quaisquer dados pessoais de usuários (no caso do Followw, restringindo-se aos endpoints públicos de unidades, turmas e disciplinas por código e semestre). Dados pessoais somente poderão ser fornecidos a autoridades públicas mediante obrigação legal ou ordem judicial aplicável.

## 5. Integração com o Google Agenda

A conexão com o Google Agenda é inteiramente opcional e independente do método de entrada utilizado na sua conta. Ao iniciar a autorização, a plataforma solicita exclusivamente os escopos `openid`, `email` (para validar que a conta Google possui o mesmo endereço de e-mail verificado da sua conta no Agenda UnB) e `https://www.googleapis.com/auth/calendar.app.created` (restrito à agenda secundária **"Agenda UnB"** criada pela própria aplicação, sem acesso às demais agendas da sua conta Google).

Os tokens de acesso e atualização permanecem criptografados no servidor com **Fernet** exclusivamente enquanto a integração estiver ativa; pedidos de autorização não concluídos expiram automaticamente em **10 minutos**. Em cada operação de exportação, você pode selecionar até **20 eventos** pessoais ou públicos salvos. São transmitidos apenas identificador técnico, título, início e término (aplicando-se duração padrão de 1 hora para eventos com horário sem término informado), local quando disponível e descrição quando escolhida, preservando-se as datas civis de eventos de dia inteiro.

Ao desconectar a integração em **Meus Eventos**, revogar o consentimento em **Configurações** ou excluir sua conta, os tokens armazenados são apagados imediatamente e a plataforma solicita ao Google a revogação remota do acesso. Caso o Google não confirme a revogação imediata, a interface exibirá orientações para remoção manual nas permissões da sua Conta Google.

Desconectar a integração ou excluir sua conta no Agenda UnB não remove os eventos que já tiverem sido gravados na sua Conta Google. Para excluí-los, acesse [calendar.google.com](https://calendar.google.com), localize **"Agenda UnB"** em **Minhas agendas**, abra **Configurações e compartilhamento** e utilize **Excluir agenda** para apagar todas as cópias de uma só vez, ou remova eventos específicos individualmente.

## 6. Prazos de retenção e eliminação

Os dados da conta, compromissos da agenda pessoal, eventos públicos salvos, vínculos de turmas, planos enviados (restritos ao texto extraído e às versões geradas), registros de aceite e consentimentos são mantidos enquanto a conta permanecer ativa. Os tokens do Google Agenda são mantidos apenas durante a vigência da conexão e eliminados imediatamente na desconexão, na revogação do consentimento ou na exclusão da conta; pedidos pendentes de autorização expiram em 10 minutos. O arquivo PDF enviado para extração nunca é retido após a leitura local do texto em memória.

Os registros técnicos operacionais seguem os prazos de consulta dos respectivos provedores de infraestrutura (até 1 dia no plano gratuito do Supabase para logs de API e banco, até 7 dias no Render e até 1 hora no plano gratuito da Vercel para logs de execução), sem exportação ou retenção externa paralela pela equipe. Não são mantidas cópias de segurança manuais ou externas fora das rotinas internas dos provedores. Quando uma conta é excluída, apenas contadores estatísticos anônimos do evento de exclusão são preservados, sem qualquer dado que permita identificar o titular.

## 7. Direitos dos titulares

Em conformidade com o artigo 18 da LGPD, você pode exercer os seguintes direitos diretamente na plataforma, na página **Configurações** (`/configuracoes`), ou por meio do canal oficial informado na seção 1:

- **Confirmação e acesso (portabilidade):** visualizar e baixar todos os seus dados pessoais em formato JSON por meio de **Configurações** → **Baixar meus dados**.
- **Correção de dados:** solicitar a atualização de dados cadastrais pelo canal oficial de atendimento, observando-se que nome e foto de contas Google refletem o provedor de autenticação.
- **Revogação de consentimento:** revogar a conexão com o Google Agenda em **Configurações** ou desconectar em **Meus Eventos**; a autorização para envio de texto sanitizado de um plano de ensino à IA é concedida de forma individual por envio em **Plano de Ensino**.
- **Controle de compartilhamento:** gerenciar ou retirar o compartilhamento de versões de planos na página **Plano de Ensino**, sem afetar cópias independentes já importadas anteriormente por outros usuários.
- **Eliminação da conta:** excluir sua conta diretamente em **Configurações** → **Excluir conta**, mediante digitação da frase de confirmação.

A exclusão da conta remove permanentemente o perfil e as credenciais de acesso, compromissos da agenda pessoal, eventos salvos, notificações, vínculos com turmas, votos registrados, operações de importação, registros de aceite e consentimento, tokens e conexão com o Google Agenda (com solicitação de revogação remota), planos de ensino enviados (incluindo versões e candidatos) e eventos públicos sugeridos ou publicados pelo titular. Permanecem apenas as cópias independentes já importadas anteriormente por terceiros em suas agendas privadas, os eventos já gravados na agenda secundária **"Agenda UnB"** no Google Agenda e o registro numérico anônimo da exclusão ocorrida.

As solicitações recebidas pelo canal oficial são respondidas no prazo de até **15 dias**. Você também possui o direito de apresentar petição à Autoridade Nacional de Proteção de Dados (ANPD).

## 8. Segurança da informação

O acesso aos dados é isolado por usuário tanto na camada de API quanto nas políticas de controle de linha (RLS) do banco de dados. Toda comunicação entre navegador, servidor e serviços gerenciados utiliza criptografia em trânsito (TLS/HTTPS). Credenciais e chaves de integração são mantidas fora do código-fonte, e os registros de erro da aplicação não gravam corpos de requisição, conteúdo acadêmico ou tokens de acesso. Em caso de incidente de segurança que possa acarretar risco ou dano relevante aos titulares, a equipe comunicará os usuários afetados e a ANPD nos prazos aplicáveis.

## 9. Público e menores de idade

O Agenda UnB destina-se à comunidade acadêmica universitária e não é direcionado a menores de 18 anos.

## 10. Atualizações desta política

Cada versão desta Política de Privacidade é identificada por sua data de vigência no cabeçalho do documento. Alterações relevantes serão comunicadas na plataforma, com solicitação de novo registro de leitura no acesso subsequente ou na seção **Configurações**.
