# Planejamento e decisões

1. Dados e modelo: importação Kaggle, auditoria, variáveis anteriores ao jogo, avaliação temporal e serialização.
2. API: contratos, lifespan, serviço de inferência, erros HTTP e Swagger.
3. Interface: painel esportivo, seletor de confrontos, probabilidades e comparações.
4. Qualidade e entrega: testes, execução em ambiente limpo, documentação, vídeo e revisão final.

## Decisões registradas

- Python 3.12; FastAPI e Streamlit, toda lógica escrita em Python.
- Fonte única escolhida pelo usuário: Kaggle / Adão Duque. A versão 18 é mais recente que o espelho GitHub.
- Original: 9.165 partidas até 07/12/2025. Uso: 9.163 após quarentena de IDs 2826 e 3016.
- Esses dois registros descrevem Botafogo-RJ como mandante contra Flamengo na mesma temporada de 2009.
  Sem fonte de correção confirmada, ambos ficam fora do modelo. O CSV original é preservado localmente.
- Partidas em janeiro e fevereiro de 2021 pertencem à temporada 2020. Ordenação das features usa a data real.
- Ausências no histórico são imputadas pela mediana aprendida no treino. Elo inicial 1500, K=20 e mando +65.
- Treino 2003–2020, seleção 2021–2022 e teste 2023–2024. Nenhum ajuste é decidido pelo teste.
- Modelo de produção retreinado no histórico completo, incluindo 2025. Métricas do relatório pertencem ao experimento separado.
- A atualização troca um ponteiro de snapshot com operação atômica. Falha de download ou validação mantém a versão anterior.
- API lê artefatos apenas no lifespan. Atualizações exigem reiniciar; retreinamento é um comando independente.
- Sem endpoint público de atualização, credenciais Kaggle ou dados brutos no Git.
- Publicação no site pessoal foi adiada pelo usuário; entrega executável local, GitHub público e vídeo no Drive.
- A geração assistida de código foi solicitada explicitamente pelo usuário. O enunciado limita esse uso;
  esta documentação não afirma autoria exclusivamente manual nem conformidade com essa restrição.

## Fluxo Git

`feature/dados-modelo`, `feature/api`, `feature/interface` e `feature/qualidade-entrega` partem de `develop`.
Cada etapa é incorporada por PR; a versão final segue por PR de `develop` para `main`. Branches preservadas.
