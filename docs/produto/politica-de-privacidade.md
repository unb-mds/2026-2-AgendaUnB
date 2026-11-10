---
title: "Política de Privacidade"
description: "Quais dados o Agenda UnB trata, para quê, com quem compartilha e como exercer seus direitos."
---

# Política de Privacidade

**Versão 2026-11-10 — proposta para revisão da equipe.** Este texto descreve o tratamento de dados como ele está implementado e planejado para a Release 2. Ele ainda precisa da revisão do responsável definido pela equipe e não substitui orientação jurídica. Os pontos marcados com **[DEFINIR]** dependem de decisão do grupo ([#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83)).

O Agenda UnB é um projeto acadêmico da disciplina Métodos de Desenvolvimento de Software (UnB, 2026/2), sem fins comerciais. Ele não é um serviço oficial da Universidade de Brasília. Adotamos a Lei Geral de Proteção de Dados (Lei 13.709/2018, LGPD) como referência para todo o tratamento descrito aqui.

## 1. Quem responde pelos seus dados

- **Responsável:** equipe G8 do Agenda UnB. **[DEFINIR]** pessoa de contato.
- **Canal para pedidos e dúvidas:** **[DEFINIR]** e-mail de atendimento. Enquanto ele não existir, use as [issues do repositório](https://github.com/unb-mds/2026-2-AgendaUnB/issues) **sem incluir dados pessoais**.

## 2. Quais dados tratamos e para quê

| Dado | Para quê | De onde vem |
| --- | --- | --- |
| Nome, e-mail e senha (guardada pelo serviço de autenticação, de forma irreversível) | Criar e proteger a sua conta | Você, no cadastro |
| Nome, e-mail e foto da conta Google | Entrar com o Google, se você escolher | Google, com a sua autorização |
| Papel (estudante, professor, administrador) e histórico de mudanças de papel | Definir o que a conta pode fazer e auditar permissões | Você e a administração |
| Compromissos da agenda pessoal | Mostrar a sua agenda. São visíveis só para você | Você |
| Eventos públicos salvos e avisos | Montar a sua agenda e lembrar você 24 horas antes | Você e a plataforma |
| Eventos que você sugere ou publica | Agenda pública do campus, após moderação. O nome de quem publica aparece como organizador | Você |
| Turmas que você segue | Mostrar planos compartilhados da turma. É uma declaração sua, não prova de matrícula | Você |
| Planos de ensino que você envia e as datas extraídas | Sugerir provas e trabalhos para a sua agenda | Você |
| Votos em datas de planos compartilhados | Mostrar se a turma confirma ou contesta uma data. Só a contagem é exibida | Você |
| Aceite destes documentos e consentimentos | Comprovar o que você leu e autorizou | Você |
| Registros técnicos (data, rota acessada, endereço IP) | Segurança, diagnóstico de falhas e prevenção de abuso | Gerados automaticamente |

Não pedimos matrícula, CPF, notas, nem senha do SIGAA ou de outros sistemas. Não usamos seus dados para publicidade e não os vendemos.

O contador de **Conferir evento** registra apenas um identificador aleatório do clique. Ele não guarda quem clicou.

## 3. Planos de ensino

- O **PDF original** é lido no envio apenas para extrair o texto e **não é guardado**. Guardamos o texto extraído, que você revisa antes de qualquer processamento. Nada disso é compartilhado com outras pessoas sem a sua decisão.
- Antes de qualquer envio a um serviço de inteligência artificial, mostramos **o trecho exato** que seria enviado e pedimos a sua **autorização específica**. Sem ela, nada é enviado. Se o texto mudar, pedimos de novo.
- Toda data extraída é uma sugestão. Ela só entra na sua agenda quando você confirma.
- Um plano começa **privado**. Ele só fica visível para quem segue a mesma turma se **você** decidir compartilhar, e você pode retirar o compartilhamento quando quiser. Professores e administradores não têm acesso ao seu conteúdo privado.
- Quem já importou datas de um plano compartilhado mantém as cópias na própria agenda, mesmo que o compartilhamento seja retirado ou a conta de origem seja excluída.

## 4. Com quem compartilhamos

Usamos fornecedores para hospedar e operar a plataforma. Eles tratam dados em nosso nome:

| Fornecedor | O que faz | Dados envolvidos | Local |
| --- | --- | --- | --- |
| Supabase | Banco de dados, autenticação e arquivos | Todos os dados da conta | Estados Unidos |
| Render | Hospeda a API | Dados em trânsito e registros técnicos | Estados Unidos |
| Vercel | Hospeda o site | Registros técnicos de acesso | Rede global |
| Google (login) | Entrada com conta Google | Nome, e-mail e foto, se você usar essa opção | Estados Unidos e outros |
| Google (Gemini) | Extrai datas do texto de um plano | Somente o trecho que você autorizar | Estados Unidos e outros |
| Google (Agenda) | Exporta eventos, se você conectar | Título, descrição, local e datas dos eventos que você escolher | Estados Unidos e outros |
| Google Fonts | Fontes do site | Endereço IP, ao carregar as fontes | Rede global |

Parte desses fornecedores fica fora do Brasil, o que caracteriza transferência internacional de dados.

O catálogo de turmas (Followw) e a agenda de notícias da UnB são **apenas consultados**: nenhum dado seu é enviado a eles.

Podemos fornecer dados a autoridades quando houver obrigação legal.

## 5. Google Agenda

A exportação é opcional e depende de uma autorização separada do login. Enviamos só os eventos que você selecionar. Ao desconectar, apagamos as credenciais guardadas e pedimos ao Google a revogação do acesso. **Os eventos já exportados continuam na sua agenda Google**: para removê-los, apague a agenda secundária "Agenda UnB" ou os eventos diretamente no Google.

## 6. Por quanto tempo guardamos

| Dado | Prazo |
| --- | --- |
| Conta, agenda, turmas, planos, votos, aceites e consentimentos | Enquanto a conta existir |
| PDF original de um plano | Não é guardado (planos enviados antes de 10/11/2026 têm o arquivo removido) |
| Texto extraído de um plano | Enquanto a conta existir |
| Registros técnicos | **[DEFINIR]** conforme a retenção de cada fornecedor |
| Registro de que uma exclusão de conta ocorreu | Guardado sem identificar a pessoa (só quantidades) |
| Cópias de segurança | **[DEFINIR]** conforme o plano contratado do banco |

## 7. Seus direitos

Você pode, a qualquer momento:

- **acessar e baixar** os seus dados em Configurações → Meus dados;
- **corrigir** nome e foto no perfil;
- **retirar** o compartilhamento de um plano e **revogar** consentimentos;
- **excluir a conta**, o que apaga os dados descritos na seção 2;
- pedir informações ou apresentar reclamação pelo canal da seção 1. Você também pode recorrer à Autoridade Nacional de Proteção de Dados (ANPD).

**O que a exclusão da conta apaga:** perfil, agenda pessoal, eventos salvos, avisos, turmas seguidas, votos, aceites, consentimentos, os planos que você enviou (com todas as versões) e os eventos públicos que você sugeriu ou publicou. **O que permanece:** as cópias que outras pessoas já importaram para as próprias agendas e os eventos que você exportou para o Google Agenda.

Respondemos aos pedidos em até 15 dias.

## 8. Segurança

O acesso aos dados é restrito por conta, no banco e na API. As conexões usam HTTPS. Chaves e senhas dos serviços ficam fora do código. Em caso de incidente que possa causar risco ou dano relevante, avisaremos as pessoas afetadas e a ANPD.

## 9. Menores de idade

A plataforma é voltada à comunidade universitária. Não é direcionada a menores de 18 anos.

## 10. Mudanças nesta política

Cada versão é identificada pela data de vigência. Quando o texto mudar de forma relevante, pediremos que você leia a nova versão ao entrar.
