# Roteiro de apresentação — até 10 minutos

Grave com seu rosto visível e boa iluminação. Use sua própria explicação e mostre a aplicação real.

| Tempo | Conteúdo e demonstração |
|---|---|
| 0:00–0:50 | Apresentar Radar do Brasileirão: público, pergunta respondida e benefício. |
| 0:50–1:40 | Mostrar Kaggle, versão 18, 9.165 registros originais e data final de 07/12/2025. Explicar as duas linhas ambíguas excluídas. |
| 1:40–2:40 | Explicar histórico anterior ao jogo, janelas 5/10, mando e Elo. Mostrar por que não usamos placar do próprio jogo como entrada. |
| 2:40–3:50 | Mostrar reports/METRICAS.md: treino, validação, teste e comparação com baseline. Explicar que acurácia não significa certeza. |
| 3:50–5:20 | Escolher clubes na tela, analisar e comparar probabilidades, aproveitamento e confrontos diretos. Destacar a data da base. |
| 5:20–6:30 | Swagger: executar /health, /v1/teams e /v1/predict. Demonstrar erro 400 com clubes iguais e 422 com tipo incorreto. |
| 6:30–7:20 | Mostrar schemas/services/routers/main e explicar carregamento único no lifespan. |
| 7:20–8:10 | Explicar ambiente virtual, requirements.txt, download e run.py. Mostrar testes executados. |
| 8:10–9:00 | Mostrar branches e PRs; explicar planejamento por dados, API, interface e qualidade. |
| 9:00–9:40 | Limitações: dados até 2025, empates difíceis, ausência de escalações/lesões e melhoria futura com atualização. |

## Antes da entrega

- Gravar e assistir ao vídeo completo; duração máxima de dez minutos.
- Enviar ao Google Drive e permitir leitura para qualquer pessoa com o link.
- Colocar o link real no README e confirmar os links numa janela sem login.
- Submeter GitHub e vídeo no AVA até 03/11/2026 (confirmar horário no AVA).
- Congelar a versão submetida até a avaliação.

## Perguntas para praticar

Por que não dividir aleatoriamente? Por que a temporada 2020 contém partidas de 2021?
Qual a diferença entre acurácia e log loss? Por que probabilidades não são garantias?
Onde ocorre o carregamento do modelo? O que acontece se o usuário informar um clube desconhecido?
Qual a diferença entre atualizar os dados e retreinar? Por que o artefato final tem mais dados que o modelo avaliado?
