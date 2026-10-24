# Radar do Brasileirão

Compare dois clubes da Série A e explore probabilidades de vitória do mandante, empate e vitória do visitante.
Aplicação em Python para torcedores e criadores de conteúdo, com painel Streamlit e API FastAPI.

**Dados até 07/12/2025.** As estimativas representam esse histórico, não a força atual dos clubes em 2026.
Os clubes selecionáveis pertencem à edição mais recente disponível na base.

## Origem e auditoria dos dados

Fonte escolhida: [Campeonato Brasileiro de Futebol — Adão Duque / Kaggle](https://www.kaggle.com/datasets/adaoduque/campeonato-brasileiro-de-futebol).
Versão utilizada: **18**, publicada pelo Kaggle em 05/02/2026, com licença indicada nos metadados como **GPL 2**.
O projeto não redistribui o CSV bruto. Obtenha a base da fonte e preserve sua atribuição e condições de uso.

O arquivo principal contém **9.165 partidas (2003–2025)**. Duas linhas com mando ambíguo (IDs 2826 e 3016)
são colocadas em quarentena, resultando em **9.163 partidas utilizadas**. O CSV original permanece intacto.
O manifesto registra origem, SHA-256, datas, contagens por temporada e registros excluídos.
A temporada 2020 inclui partidas realizadas em janeiro/fevereiro de 2021.

## Instalação — Python 3.12

No terminal, entre na pasta deste repositório. Os comandos abaixo são para PowerShell no Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m radar.data --version 18
.\.venv\Scripts\python.exe run.py
```

O modelo treinado está em `models/radar.joblib`. Após baixar os dados, `run.py` inicia os dois serviços,
abre o navegador e encerra ambos com Ctrl+C. Se o modelo não estiver presente ou quiser reproduzir o treinamento:

```powershell
.\.venv\Scripts\python.exe -m radar.train
```

Em Linux/macOS, substitua o comando de criação por `python3.12 -m venv .venv` e o executável por `.venv/bin/python`.

- Tela: http://127.0.0.1:8501
- Swagger: http://127.0.0.1:8000/docs
- Saúde: http://127.0.0.1:8000/health

Para iniciar separadamente, em dois terminais:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m streamlit run ui/app.py --server.address 127.0.0.1
```

Se o download automático do Kaggle estiver indisponível, baixe o ZIP na página da base, extraia o CSV principal
para `data/manual/campeonato-brasileiro-full.csv` e importe:

```powershell
.\.venv\Scripts\python.exe -m radar.data --file data/manual/campeonato-brasileiro-full.csv
```

## Atualização sob comando

```powershell
.\.venv\Scripts\python.exe -m radar.data
```

Sem `--version`, o importador consulta a versão mais recente do Kaggle. A versão anterior é preservada se o
download ou validação falhar. Reinicie a API para carregar os novos históricos. Retreinar exige executar
`python -m radar.train` separadamente. A resposta informa datas distintas para dados e treinamento.

Nenhuma atualização garante novos jogos: a cobertura depende do autor da base. O download exige internet;
a inferência funciona offline após a preparação. Mudanças no formato do Kaggle podem exigir adaptação do importador.

## API e exemplos

`GET /health` informa carregamento, versão e datas. `GET /v1/teams` fornece os IDs válidos.

`POST /v1/predict`:

```json
{"home_team_id":"flamengo","away_team_id":"palmeiras"}
```

```powershell
$body = @{home_team_id='flamengo'; away_team_id='palmeiras'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/predict -ContentType application/json -Body $body
```

A resposta contém `probabilities` (home_win/draw/away_win), `home`, `away`, `head_to_head`, `data_through`,
`trained_through`, `model_version` e `warnings`. As probabilidades são números entre 0 e 1 e somam 1.
Indicadores incluem aproveitamento, gols, mando, forma recente e Elo. Um exemplo real é salvo em `reports/exemplo_resposta.json`.

Tipos incorretos, campos faltantes ou extras retornam **422**. Clubes iguais/desconhecidos retornam **400**.
Falhas inesperadas retornam **500** com mensagem controlada e log no servidor. Dados/modelo ausentes impedem
a inicialização com instrução clara. Apenas artefatos joblib locais e confiáveis devem ser carregados.

## Modelo e avaliação

Pré-processamento e modelo formam um único pipeline. Variáveis: aproveitamento e gols em janelas de 5/10 jogos,
desempenho no mando e diferença Elo. Nenhuma informação da própria partida entra como preditor.
Os jogos do mesmo dia são processados em bloco, evitando vazamento entre eles.

Treino: **2003–2020**; validação: **2021–2022**; teste: **2023–2024**.
Comparação: frequências históricas, Regressão Logística e HistGradientBoostingClassifier, com parâmetros fixos.
Seleção por log loss de validação. O teste não escolhe modelo ou parâmetros.

Veja [métricas reais](reports/METRICAS.md), [relatório completo](reports/metrics.json) e
[gráfico de calibração](reports/calibration.html). O artefato de produção é retreinado até 2025;
as métricas reportadas são do modelo experimental, que não viu o teste durante o ajuste.

Limitações: histórico antigo, ausência de escalações/lesões e jogos de outras competições; previsões não causais.
O modelo selecionado no experimento não escolheu empate como classe mais provável no teste, embora estime sua
probabilidade. Isso limita o F1 macro. Os percentuais servem para análise exploratória, sem garantia por partida.

## Organização e tecnologias

```text
radar/       importação, indicadores, treinamento e configuração
api/         schemas, services, routers e main (lifespan)
ui/          painel Streamlit que consome a API por HTTP
models/      pipeline serializado e metadados
reports/     métricas, calibração e evidências
tests/       dados, tempo, API e interface
docs/        decisões, roteiro e entrega
data/        snapshots locais, ignorados pelo Git
```

Python 3.12; pandas, scikit-learn, joblib, FastAPI, Pydantic, Uvicorn, Streamlit, Plotly, requests,
pytest e httpx. **Versões exatas de todas as dependências:** `requirements.txt`.

Modelo e histórico são carregados uma única vez por processo no lifespan. Rotas não leem disco nem fazem
downloads. `RADAR_MODEL_PATH`, `RADAR_HISTORY_PATH` e `RADAR_API_URL` permitem configuração opcional.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Testes incluem vazamento temporal, jogos do mesmo dia, temporada 2020, consistência dos dados, atualização
atômica, serialização, probabilidades, carregamento único, erros HTTP e interface com API indisponível.

## Repositório e verificação

[GitHub público](https://github.com/LGpossoli/radar-brasileirao) · [Pull requests](https://github.com/LGpossoli/radar-brasileirao/pulls?q=is%3Apr) · [Verificação](docs/VERIFICACAO.md)

## Planejamento, Git e apresentação

Consulte [decisões e etapas](docs/PLANO_E_DECISOES.md) e [roteiro do vídeo](docs/ROTEIRO_VIDEO.md).
Fluxo: branches de funcionalidade → `develop` → `main`, com PRs e branches preservadas.
Desenvolvimento assistido por IA, conforme solicitado pelo responsável; o enunciado contém restrições a esse uso.

**Vídeo no Google Drive: pendente de gravação pelo aluno.** Inserir o link real antes da submissão.
Entrega no AVA: GitHub público e vídeo de até dez minutos, até 03/11/2026, conforme prazo informado pelo usuário.
Confirmar horário no AVA. Não modificar a versão submetida antes da avaliação.
