# Radar do Brasileirão

Neste projeto, comparo clubes da Série A e exploro probabilidades de vitória do mandante, empate e vitória do visitante.
Aplicação em Python para torcedores e criadores de conteúdo, com painel Streamlit e API FastAPI.

**Dados até 07/12/2025.** As estimativas representam esse histórico, não a força atual dos clubes em 2026.
Os clubes selecionáveis pertencem à edição mais recente disponível na base.

## Origem e auditoria dos dados

Escolhi a fonte: [Campeonato Brasileiro de Futebol — Adão Duque / Kaggle](https://www.kaggle.com/datasets/adaoduque/campeonato-brasileiro-de-futebol).
Versão utilizada: **18**, publicada pelo Kaggle em 05/02/2026, com licença indicada nos metadados como **GPL 2**.
Não redistribuo o CSV bruto neste projeto. Obtenha a base da fonte e preserve sua atribuição e condições de uso.

O arquivo principal contém **9.165 partidas (2003–2025)**. Duas linhas com mando ambíguo (IDs 2826 e 3016)
são colocadas em quarentena, resultando em **9.163 partidas utilizadas**. O CSV original permanece intacto.
Registro no manifesto a origem, o SHA-256, as datas, as contagens por temporada e os registros excluídos.
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

## Interface e leitura dos indicadores

Organizei a tela em quatro áreas: probabilidades, desempenho, confrontos diretos e simulação de campeonatos.
Em um monitor de 1280 × 720, o painel principal foi conferido sem rolagem. Em telas menores, as áreas se
reorganizam e a rolagem é preservada quando necessária para não cortar conteúdo ou reduzir sua legibilidade.

- Escolher um clube atualiza a análise. **Inverter** troca mandante e visitante e recalcula imediatamente.
- **Analisar** força uma nova consulta para a seleção atual.
- O gráfico de pizza em rosca usa as cores dos clubes; quando as principais são próximas, escolhe cores
  secundárias da paleta de cada equipe. Empate usa cinza. Os rótulos continuam distinguindo os resultados.
- Percentuais usam vírgula decimal. Textos das fatias alternam entre branco e preto para contraste mínimo de 4,5:1.
- Aproveitamento é a porcentagem dos pontos possíveis. Gols são médias por partida.
- “No mando” significa jogos em casa para o mandante e fora para o visitante, nos últimos dez disponíveis.
- A sequência V/E/D vai do jogo mais antigo ao mais recente: vitória, empate e derrota.
- Percentuais exatos somam 100%; valores arredondados podem diferir em 0,1 ponto percentual.
- As probabilidades não incorporam fatos posteriores à data informada no rodapé, nem escalações ou lesões.
- O menu **⚙️** contém o README para leitura e atalhos para a documentação interativa, o estado do serviço e os clubes da API. Explicações ficam neste documento.

Deploy, captura de tela e gravação eram controles de desenvolvimento do Streamlit. Foram removidos da
interface de uso, substituindo o menu padrão por um menu próprio em português. A captura não é necessária
para funcionamento do Radar. O gráfico não contém barra de ferramentas em inglês.

## Modelo e avaliação

Reuni o pré-processamento e o modelo em um único pipeline. Uso as variáveis: aproveitamento e gols em janelas de 5/10 jogos,
desempenho no mando e diferença Elo. Nenhuma informação da própria partida entra como preditor.
Os jogos do mesmo dia são processados em bloco, evitando vazamento entre eles.

Treino: **2003–2020**; validação: **2021–2022**; teste: **2023–2024**.
Comparação: frequências históricas, Regressão Logística, Árvore de Decisão e Random Forest, com parâmetros fixos.
Escolho pelo menor log loss na validação. Reservo o teste para a avaliação final.

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
Usei assistência de IA no desenvolvimento; o enunciado contém restrições a esse uso.

**Vídeo no Google Drive: pendente de gravação pelo aluno.** Inserir o link real antes da submissão.
Entrega no AVA: GitHub público e vídeo de até dez minutos, até 03/11/2026, conforme o prazo que defini para a entrega.
Confirmar horário no AVA. Não modificar a versão submetida antes da avaliação.


## Simulação de temporada

Clico em **Simular temporada** para sortear os 380 jogos de turno e returno dos clubes da
temporada mais recente disponível: 38 rodadas, 19 partidas em casa e 19 fora por equipe.
Mostro uma rodada por segundo após a consulta à API. O painel mantém suas dimensões.

Uso as probabilidades do modelo selecionado e mantenho a força histórica constante.
Não alimento o modelo com partidas fictícias. Não projeto acesso, rebaixamento, mudanças
de elenco ou um ano futuro específico. Cada clique usa uma nova semente aleatória.

Uso três pontos por vitória e um por empate. Ordeno por pontos, vitórias e identificador
do clube. Não simulo placares, saldo de gols nem todos os critérios oficiais de desempate.
P = pontos; J = jogos; V = vitórias; E = empates; D = derrotas.

`POST /v1/simulate` recebe `seed` e, opcionalmente, `model_id`. O campo legado `year`
é opcional e serve somente como rótulo; não altera resultados. A animação fica na interface,
sem manter a API esperando 38 segundos. Com a mesma semente e modelo, reproduzo o resultado.

## Escolha do modelo

No seletor do cabeçalho, escolho Regressão Logística, Árvore de Decisão ou Random Forest.
A seleção vale para o confronto e para o campeonato. Ao trocar, recalculo o confronto e
limpo a simulação anterior. Os três pipelines ficam carregados em memória; a seleção de
um usuário não altera a de outro. O treinamento continua sendo feito pelo comando `python -m radar.train`.

Uso C=1 na Regressão Logística; profundidade máxima 5 e pelo menos 80 exemplos por folha na
Árvore; 300 árvores, profundidade máxima 8 e pelo menos 30 exemplos por folha na Random Forest.
Defini esses parâmetros antes desta avaliação, sem otimizar pelo teste. Comparo com as frequências
históricas e escolho o padrão entre os três classificadores pelo menor log loss na validação.
Os resultados do teste 2023–2024 já tinham sido consultados na versão anterior: esta ampliação
é uma comparação retrospectiva, não uma nova avaliação cega em dados nunca examinados.

Posso enviar `model_id` em `/v1/predict` e `/v1/simulate`: `regressao_logistica`,
`arvore_decisao` ou `random_forest`. Se omitir, uso o padrão. IDs desconhecidos retornam 400;
tipos inválidos retornam 422. `/v1/teams` informa o catálogo e o modelo padrão.


## Avaliação visível na aplicação

Abro **⚙️ → Avaliação dos modelos** para consultar acertos, erros, acurácia, F1 macro,
log loss e as previsões individuais do teste. Os filtros não alteram os indicadores do teste completo.

| Etapa | Temporadas | Uso |
|---|---|---|
| Treino experimental | 2003–2020 | Ajustar modelos e pré-processamento |
| Validação | 2021–2022 | Comparar e selecionar pelo menor log loss |
| Teste histórico | 2023–2024 | Medir desempenho fora dos dados de ajuste |
| Modelo da análise e simulação | 2003–2025 | Retreinar os três modelos para uso |

As divisões usam temporadas; 2020 inclui jogos realizados em 2021. Salvo as previsões de
teste antes do retreinamento de produção. Os indicadores avançam somente após cada dia,
sem incorporar resultados futuros. O desempate de probabilidades exatamente iguais usa
a ordem A, D, H do classificador. Acertar o resultado não significa acertar o placar.

O relatório `reports/evaluation.json` reúne identificação do experimento, períodos, métricas
e partidas. Valido probabilidades, placares, contagens e métricas antes de publicá-lo.
Esta é uma comparação retrospectiva; os resultados do teste já foram consultados em versões
anteriores. Não utilizo os modelos retreinados até 2025 para anunciar acertos em 2023–2024.

`GET /v1/evaluation?model_id=regressao_logistica` retorna o relatório do modelo e a comparação
dos três classificadores com as frequências históricas. O relatório é carregado no lifespan.
Modelo desconhecido retorna 400; relatório ausente ou incompatível retorna 503 sem interromper
`/health` ou a análise de confrontos. Para regenerar, executo `python -m radar.train` e reinicio a API.

Deixei para depois a configuração de modelos pela tela, a importação de 2026 e a previsão
de placar exato. O foco desta entrega é a API, a avaliação histórica e a documentação.
