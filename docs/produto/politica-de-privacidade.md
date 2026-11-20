---
title: "Política de Privacidade"
description: "Quais dados o Agenda UnB trata, para quê, com quem compartilha e como exercer seus direitos."
---

**Versão 2026-11-20.** Esta política descreve como o Agenda UnB trata os seus dados pessoais.

O Agenda UnB é um projeto acadêmico da disciplina Métodos de Desenvolvimento de Software (UnB, 2026/2), sem fins comerciais. Ele não é um serviço oficial da Universidade de Brasília. Adotamos a Lei Geral de Proteção de Dados (Lei 13.709/2018, LGPD) como referência para todo o tratamento descrito aqui.

## 1. Quem responde pelos seus dados

- **Responsável:** equipe G8 do Agenda UnB. Pessoas de contato: Felipe Couto Duque e Thomas Augusto Amorim de Araujo.
- **Canal para pedidos e dúvidas:** [unbagenda@gmail.com](mailto:unbagenda@gmail.com). Não publique dados pessoais nas issues do repositório.

## 2. Quais dados tratamos e para quê

| Dado | Para quê | De onde vem |
| --- | --- | --- |
| Nome, e-mail e senha (guardada pelo serviço de autenticação de forma irreversível) | Criar e proteger a sua conta | Você, no cadastro |
| Nome, e-mail e foto da conta Google | Entrar com o Google, se você escolher | Google, com a sua autorização |
| Papel (estudante, professor, administrador) | Definir o que a conta pode fazer na plataforma | Você e a administração |
| Compromissos da agenda pessoal | Mostrar a sua agenda. São visíveis só para você | Você |
| Eventos públicos salvos e notificações da plataforma | Montar a sua agenda e avisar sobre alterações ou moderação | Você e a plataforma |
| Eventos que você sugere ou publica | Agenda pública do campus, após moderação. O nome de quem publica aparece como organizador | Você |
| Turmas que você segue | Mostrar planos compartilhados da turma. É uma declaração sua, não prova de matrícula | Você |
| Planos de ensino que você envia e as datas extraídas | Sugerir provas e trabalhos para a sua agenda | Você |
| Aceite destes documentos e consentimentos | Comprovar o que você leu e autorizou | Você |
| Conexão e tokens do Google Agenda | Exportar eventos selecionados quando você conecta sua conta | Google, com a sua autorização |
| Registros técnicos (data, rota acessada, endereço IP) e métricas agregadas de acesso | Segurança, diagnóstico de falhas, prevenção de abuso e medição básica de visitas | Gerados automaticamente |

Não pedimos matrícula, CPF, notas, nem senha do SIGAA ou de outros sistemas. Não usamos seus dados para publicidade e não os vendemos.

## 3. Planos de ensino

- O envio em PDF aceita arquivos de até **10 páginas** e **10 MB**. O texto é extraído localmente em memória no servidor e o PDF **não é guardado** após a leitura. Arquivos antigos que ainda existiam no armazenamento seguem rotina de eliminação definitiva.
- Antes de qualquer envio à inteligência artificial, o sistema aceita até **40.000 bytes UTF-8** de texto (até 10 páginas) e aplica uma limpeza automática simples por regras fixas (para substituir e-mails, telefones brasileiros, sequências de 9 a 11 dígitos ou CPF e linhas iniciadas por rótulos como professor, aluno, nome, matrícula ou CPF). A remoção automática cobre os padrões detectáveis e pode deixar passar dados fora desses padrões.
- Ao escolher **Enviar PDF e extrair** ou **Enviar texto e extrair**, você autoriza a análise do texto sanitizado daquele plano. A plataforma verifica novamente o texto antes de enviá-lo ao Gemini e impede o processamento de textos antigos com identificadores detectáveis.
- Toda data extraída é uma sugestão e só entra na sua agenda quando você confirma.
- Um plano começa **privado**. Ao consultar ou confirmar o resultado, a primeira versão com avaliações extraídas, incluindo as evidências dessas datas, fica disponível para quem segue a turma. Você pode retirar o compartilhamento. O texto integral preparado fica restrito à sua conta.
- Quem já importou datas de um plano compartilhado mantém as cópias independentes na própria agenda, mesmo que o compartilhamento seja retirado ou a conta de origem seja excluída.

## 4. Com quem compartilhamos

Usamos fornecedores para hospedar e operar a plataforma. Eles tratam dados em nosso nome:

| Fornecedor | O que faz | Dados envolvidos | Local |
| --- | --- | --- | --- |
| Supabase | Banco de dados, autenticação e arquivos | Todos os dados da conta | Estados Unidos |
| Render | Hospeda a API | Dados em trânsito e registros técnicos | Estados Unidos |
| Vercel | Hospeda o site e mede acessos agregados (`@vercel/analytics/react`) | Registros técnicos de acesso, páginas visitadas, país ou região aproximada e tipo de dispositivo/navegador (sem cookies de publicidade) | Rede global |
| Google (login) | Entrada com conta Google | Nome, e-mail e foto, se você usar essa opção | Estados Unidos e outros |
| Google (Gemini) | Extrai datas do texto de um plano | Somente o texto sanitizado cuja análise você autorizou (até 40.000 bytes UTF-8), enviado com armazenamento de interação desativado (`store: false`) | Estados Unidos e outros |
| Google (Agenda) | Exporta eventos para a agenda secundária "Agenda UnB", se você conectar | Identificador técnico, título, datas e horários dos eventos selecionados, local quando disponível e descrição quando escolhida | Estados Unidos e outros |
| Google Fonts | Fontes e ícones do site | Endereço IP, ao carregar os arquivos de fonte | Rede global |

Parte desses fornecedores fica fora do Brasil, o que caracteriza transferência internacional de dados.

O catálogo de turmas (Followw) e a agenda pública de notícias da UnB (`Agenda UnB Notícias`) são **apenas consultados** pelo servidor (no caso do Followw, somente os endpoints públicos de unidades, turmas e disciplinas por código e semestre, sem cookies nem dados de conta): nenhum dado seu é enviado a eles.

Podemos fornecer dados a autoridades quando houver obrigação legal.

## 5. Google Agenda

- A exportação para o Google Agenda é **opcional** e separada do login.
- Ao conectar, solicitamos apenas os escopos `openid`, `email` (para conferir que a conta Google tem o mesmo e-mail verificado da sua conta no Agenda UnB) e `https://www.googleapis.com/auth/calendar.app.created` (acesso restrito à agenda secundária **"Agenda UnB"** criada pela aplicação, sem acesso às suas outras agendas).
- Os tokens de acesso e atualização ficam **criptografados no servidor** (Fernet) apenas enquanto a conexão estiver ativa. O estado temporário do pedido de autorização expira em **10 minutos**.
- Em cada exportação, você seleciona até **20 eventos** pessoais ou públicos salvos. São enviados o identificador técnico, título, início e fim (com duração padrão de 1 hora para eventos com horário sem término), local quando disponível e descrição se você escolher incluí-la. Eventos de dia inteiro mantêm suas datas civis.
- Ao desconectar em **Meus Eventos**, ao revogar o consentimento em **Configurações** ou ao excluir sua conta, apagamos os tokens guardados e solicitamos ao Google a revogação do acesso. Se o Google não confirmar a revogação remota na hora, mostramos um aviso para que você remova o acesso nas permissões da sua Conta Google.
- **Aviso sobre eventos já exportados:** desconectar a integração ou excluir sua conta no Agenda UnB **não apaga** os eventos que já foram exportados. Para removê-los:
    1. Acesse [calendar.google.com](https://calendar.google.com) com a sua Conta Google.
    2. Em **Minhas agendas**, abra o menu da agenda **"Agenda UnB"** → **Configurações e compartilhamento** → **Excluir agenda** para apagar todas as cópias de uma vez.
    3. Se preferir manter a agenda, clique em um evento específico e escolha **Excluir**.

## 6. Por quanto tempo guardamos

| Dado | Prazo |
| --- | --- |
| Conta, agenda pessoal, eventos salvos, turmas, planos, aceites e consentimentos | Enquanto a conta existir |
| Tokens do Google Agenda | Enquanto a conexão estiver ativa; apagados imediatamente na desconexão, na revogação do consentimento ou na exclusão da conta (pedidos pendentes expiram em 10 minutos) |
| PDF original de um plano | Não é guardado nos envios novos (descartado da memória logo após extrair o texto). Eventuais arquivos antigos já concluídos são removidos pela rotina de descarte e na exclusão da conta |
| Texto extraído de um plano | Enquanto a conta existir |
| Registros técnicos | Supabase Free: logs de API e banco consultáveis por até 1 dia; Render Hobby: 7 dias; Vercel Hobby: logs de execução consultáveis por 1 hora. Esses prazos são de consulta operacional dos provedores, não uma garantia de eliminação de todos os registros internos. Não mantemos exportações externas de logs |
| Registro de que uma exclusão de conta ocorreu | Guardado sem identificar a pessoa (apenas quantidades agregadas) |
| Cópias de segurança | Não mantemos cópias manuais ou externas. O plano Free do Supabase não oferece backups automáticos acessíveis à equipe; isso não significa ausência de cópias internas de segurança do fornecedor, cuja eliminação segue seus termos |

## 7. Seus direitos

Você pode exercer os direitos abaixo diretamente na plataforma, em **Configurações** (`/configuracoes`), ou pelo canal da seção 1:

- **acessar e baixar** os seus dados em formato JSON em **Configurações** → **Baixar meus dados**;
- **corrigir** dados da conta pelo canal da seção 1 (nome e foto exibidos no perfil vêm da conta Google ou do cadastro inicial);
- **revogar** o consentimento do Google Agenda em **Configurações** ou desconectar em **Meus Eventos**; a autorização para enviar texto de um plano à IA é dada por plano ao solicitar a extração em **Plano de Ensino**;
- **gerenciar ou retirar o compartilhamento** de planos compartilhados em **Plano de Ensino** (as cópias já importadas por colegas continuam nas agendas deles);
- **excluir sua conta** diretamente em **Configurações** → **Excluir conta**, mediante digitação da frase de confirmação;
- pedir informações ou apresentar reclamação pelo canal da seção 1. Você também pode recorrer à Autoridade Nacional de Proteção de Dados (ANPD).

**O que a exclusão da conta apaga:** perfil e credenciais de acesso, agenda pessoal, eventos salvos, notificações, turmas seguidas, votos registrados, operações de importação, aceites, consentimentos, tokens e conexão do Google Agenda (com solicitação de revogação no Google), planos que você enviou (com todas as versões, candidatos e eventuais arquivos antigos ainda presentes; solicitações pendentes são descartadas) e eventos públicos que você sugeriu ou publicou.

**O que permanece:** as cópias independentes que outras pessoas já importaram para as próprias agendas (sem vínculo com a sua conta), os eventos já exportados para a agenda secundária **"Agenda UnB"** no Google Agenda e o registro anônimo de que uma exclusão ocorreu (somente quantidades, sem dados pessoais).

Respondemos aos pedidos enviados pelo canal de contato em até 15 dias.

## 8. Segurança

O acesso aos dados é restrito por conta, no banco e na API. As conexões usam HTTPS. Chaves e senhas dos serviços ficam fora do código. Registros de erro da aplicação não gravam corpos de requisição, conteúdo acadêmico ou tokens. Em caso de incidente que possa causar risco ou dano relevante, avisaremos as pessoas afetadas e a ANPD.

## 9. Menores de idade

A plataforma é voltada à comunidade universitária. Não é direcionada a menores de 18 anos.

## 10. Mudanças nesta política

Cada versão é identificada pela data de vigência. Quando esta política mudar, comunicaremos na plataforma e pediremos novo registro de leitura ao entrar ou em **Configurações**.
