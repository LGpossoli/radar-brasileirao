# Verificação da entrega

Verificação realizada em 24/10/2026.

- Python 3.12.15, dependências exatas em requirements.txt.
- 23 testes aprovados no ambiente do projeto e em um segundo ambiente virtual limpo.
- Ruff: todos os checks aprovados.
- Modelo treinado e recarregado com predições equivalentes.
- API real: /health 200; /v1/teams 200; /v1/predict 200.
- Interface conferida no navegador: Flamengo × Palmeiras, probabilidades, tabela e histórico.
- Resultado de exemplo: mandante 53,4838%, empate 25,4215%, visitante 21,0947%.
- Fonte efetivamente baixada do Kaggle, versão 18; manifesto em reports/data_manifest.json.
- CSV bruto e ambiente virtual excluídos do versionamento.

## Observações

Há um aviso de depreciação de Starlette sobre o adaptador httpx utilizado pelo TestClient.
Os testes funcionam nas versões fixadas; o aviso não foi ocultado.

Acurácia no teste: 47,5%. Log loss: 1,0388 versus 1,0613 do baseline.
O modelo não escolheu empate como classe mais provável no conjunto de teste.
As probabilidades se referem ao histórico até 07/12/2025, não a partidas atuais de 2026.

## Pendências que dependem do aluno

Gravar o vídeo com apresentação pessoal, disponibilizá-lo no Google Drive, inserir o link no README
e submeter ambos os links no AVA. O repositório não constitui submissão automática no AVA.
Não foi publicado no site pessoal, conforme decisão de deixar essa etapa para depois.

## Revisão da interface

- 29 testes aprovados após a revisão; Ruff aprovado.
- Painel conferido no navegador em 1280 × 720, sem rolagem na tela principal.
- Inversão real: Flamengo × Palmeiras passa para Palmeiras × Flamengo e recalcula as probabilidades.
- Menu de três pontos com leitura e download do README; controles de desenvolvimento ocultos.
- Testes cobrem cores alternativas de clubes semelhantes e contraste mínimo de 4,5:1 nos rótulos do gráfico.
- Em telas pequenas, o layout se reorganiza e permite rolagem para não ocultar conteúdo.


## Revisão de 25/10/2026 — simulação

Acrescentei a quarta coluna, o seletor dos cinco anos seguintes e a animação de uma rodada
por segundo. Conferi 380 confrontos únicos, mando equilibrado e conservação dos pontos.
Separei a simulação do histórico real e documentei os critérios simplificados de desempate.
Mantive os atalhos para README, Swagger, health e clubes no menu.

Validação desta revisão: 34 testes aprovados e ruff sem erros. Conferi a tela em 1280 × 720, incluindo a rodada 38 e o nome do modelo.

Ajuste de espaço: concentrei os controles de confronto nas três primeiras colunas e subi os controles da simulação. A tabela do campeonato ganhou altura e fonte maior, sem alteração dos modelos.

Revisão dos três modelos: 37 testes aprovados. Conferi o alinhamento dos quatro painéis em 1280 × 720 e a troca de Regressão Logística para Random Forest na interface, com mudança das probabilidades. Os testes verificam os três modelos serializados, a seleção na API e a limpeza da simulação ao trocar o algoritmo.


## Revisão de 26/10/2026 — avaliação histórica visível

51 testes aprovados. O relatório validado contém 760 partidas de teste por modelo,
previstas antes do retreinamento de produção. As contagens e métricas reproduzem os relatórios anteriores.
Testei filtros, troca de modelo, retorno à análise preservando clubes e relatório ausente/incompatível.
O endpoint de avaliação retorna 503 sem derrubar a análise de confrontos nesses casos.
Renomeei o painel para Simulação de temporada e removi o seletor de anos futuros.
O menu da engrenagem abre a avaliação, o README e os atalhos da API.
