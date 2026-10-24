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
