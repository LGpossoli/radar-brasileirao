# Avaliação do modelo

Treino 2003–2020, validação 2021–2022, teste 2023–2024. Sem ajuste pelo teste.

| Modelo | Log loss validação | Acurácia | F1 macro |
|---|---:|---:|---:|
| frequencias | 1.0743 | 45.00% | 0.2069 |
| regressao_logistica | 1.0363 | 47.11% | 0.2978 |
| arvore_decisao | 1.0521 | 46.84% | 0.2912 |
| random_forest | 1.0371 | 46.71% | 0.2776 |

| Modelo | Log loss teste | Acurácia teste |
|---|---:|---:|
| frequencias | 1.0613 | 47.11% |
| regressao_logistica | 1.0388 | 47.50% |
| arvore_decisao | 1.0465 | 48.42% |
| random_forest | 1.0334 | 47.76% |

Selecionado: **regressao_logistica**.

Teste: log loss **1.0388**, acurácia **47.50%**, F1 macro **0.2817**.
Baseline no teste: log loss **1.0613**.
Superou o baseline no teste: **sim**.

Acurácia não é certeza por partida. Probabilidades são estimativas, não garantias.
A matriz de confusão, Brier e curvas de calibração estão em metrics.json e calibration.html.
Elo usa início 1500, K=20 e vantagem de mando de 65 pontos; parâmetros fixados antes do teste.
Forma e gols usam janelas de 5/10 jogos. Imputação usa somente o treino de cada ajuste.
Históricos avançam durante o teste apenas após a data de cada jogo (avaliação prequential).

Retreinado em todos os dados; métricas acima pertencem ao experimento separado.
Base: 9163 jogos; 2003-03-29 a 2025-12-07.
A temporada 2020 inclui jogos realizados em 2021. As divisões usam temporada, não ano civil.