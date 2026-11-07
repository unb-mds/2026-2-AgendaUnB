# Protótipo visual — Planos de ensino

HTML e CSS estáticos, separados da página funcional. Não usa JavaScript, API,
autenticação, armazenamento ou processamento de arquivos. Conteúdo, turmas e
datas são exemplos ilustrativos, não dados oficiais da UnB.

## Abrir

Com `make dev` na raiz, visite:

http://localhost:5173/prototipo-plano-de-ensino/index.html

Inclua `index.html`: neste servidor Vite, o endereço apenas da pasta retorna
a aplicação React, que não possui essa rota, em vez do protótipo estático.

Também funciona abrindo `index.html` diretamente no navegador. As fontes Inter
e Orbitron são carregadas do Google Fonts; sem internet há fallback local.
O tema acompanha a preferência clara/escura do sistema ou navegador.

## Jornada apresentada

1. Comprovante de matrícula e turmas vinculadas.
2. Identificação de planos ausentes, pendentes e vinculados.
3. Envio de PDF com destino explícito (disciplina, turma e semestre).
4. Revisão das avaliações, evidência da origem e exemplo de dado ausente.
5. Confirmação do vínculo do plano, separada do envio à agenda privada.
6. Seleção de turmas prontas e prévia de Meus Eventos.
7. Catálogo geral como consulta secundária, sem confundir matrícula e exploração.

Os links internos apenas navegam entre seções. Botões de upload, edição,
confirmação e envio são ilustrativos; campos são somente leitura. Não há uploads
ou eventos reais. Para mostrar toda a jornada sem implementar funcionalidades,
estados diferentes aparecem simultaneamente com disciplinas de exemplo.

## Revisão visual

Aplicados os guias locais `polish` e `harden` do Impeccable: identidade existente,
hierarquia, agrupamento, teclado, foco, rótulos, estados pendentes e bloqueados,
privacidade do comprovante, associação explícita à turma e prevenção visual de
confirmação com informações faltantes. Inspeção no Chromium em desktop/mobile,
nos dois temas. Isso valida o protótipo visual, não a jornada funcional futura.
