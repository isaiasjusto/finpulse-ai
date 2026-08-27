# FinPulse AI

### Plataforma end-to-end de dados, Machine Learning, MLOps, explicabilidade e IA governada para previsão de churn e retenção bancária

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![dbt](https://img.shields.io/badge/dbt-Analytics_Engineering-FF694B?logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![MLflow](https://img.shields.io/badge/MLflow-Tracking_%26_Registry-0194E2?logo=mlflow&logoColor=white)](https://mlflow.org/)
[![MinIO](https://img.shields.io/badge/MinIO-S3_Compatible-C72E49?logo=minio&logoColor=white)](https://min.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Model_Serving-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Analytics_Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-111111)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/status-Customer_360_AI_integrated-16A085)](#status-do-projeto)

![Solução técnica do FinPulse AI para previsão de churn](docs/architecture/finpulse-ai-solution-overview.png)

## Visão geral

O **FinPulse AI** transforma dados de clientes de cartão de crédito em uma solução rastreável de previsão de churn, explicabilidade e apoio governado à retenção.

O projeto cobre o fluxo completo entre armazenamento, qualidade, transformação analítica, treinamento, validação, registro, serving, explicabilidade, consumo operacional e geração de recomendações com IA local.

Além de estimar a probabilidade de cancelamento, a plataforma:

- organiza a carteira por faixa de risco e prioridade;
- permite investigar clientes individualmente;
- apresenta métricas e matriz de confusão;
- explica previsões global e individualmente com SHAP;
- mantém rastreabilidade entre modelo, scoring e cliente;
- aplica um catálogo determinístico de ações de retenção;
- força contato prioritário quando o cliente combina alto risco com prioridade Alta ou Crítica;
- exclui atributos pessoais não acionáveis das evidências operacionais e do contexto enviado ao LLM;
- utiliza um LLM local para selecionar uma ação permitida quando não existe uma política determinística e produzir uma mensagem de abordagem;
- valida estruturalmente a saída da IA antes de entregá-la ao usuário;
- mantém a decisão final sob revisão humana.

O projeto foi construído como portfólio prático de:

- Engenharia de Dados;
- Analytics Engineering com dbt;
- Ciência de Dados e Machine Learning;
- MLOps com MLflow e MinIO;
- model serving com FastAPI;
- explicabilidade com SHAP;
- aplicações analíticas com Streamlit;
- IA generativa local com Ollama e Llama;
- governança de recomendações;
- testes de falha e contratos de API;
- arquitetura reproduzível com Docker Compose.

---

## Resultado atual

O CatBoost foi selecionado como modelo champion após benchmark de dez algoritmos, análise de overfitting, validação cruzada e avaliação em teste reservado.

| Métrica no teste reservado | Resultado |
|---|---:|
| ROC AUC | **0,9934** |
| Average Precision | **0,9699** |
| Accuracy | **0,9753** |
| Balanced Accuracy | **0,9417** |
| Precision | **0,9508** |
| Recall | **0,8923** |
| F1-score | **0,9206** |

Matriz de confusão no threshold oficial:

| Resultado | Clientes |
|---|---:|
| True Negative | 1.686 |
| False Positive | 15 |
| False Negative | 35 |
| True Positive | 290 |

Essas métricas representam uma única avaliação no conjunto de teste reservado após a escolha do algoritmo e dos thresholds na validação.

A solução operacional atualmente entrega:

- modelo `finpulse-churn-catboost`, versão 3, registrado com alias `champion`;
- batch scoring dos 10.127 clientes;
- previsões persistidas no PostgreSQL;
- snapshot de scoring em Parquet no MinIO;
- FastAPI `0.5.0` para serving, scoring, clientes, avaliação, explicabilidade e retenção;
- dashboard multipágina em Streamlit;
- Cliente 360 integrado com perfil, indicadores financeiros, comportamento, SHAP individual e recomendação de retenção;
- priorização de retenção por risco e relevância de negócio;
- explicabilidade global com SHAP para as 19 features originais;
- explicabilidade individual com fatores que aumentam e reduzem a previsão;
- catálogo governado de ações de retenção;
- Ollama executando `llama3.1:8b` localmente;
- endpoint de recomendação de retenção com saída estruturada;
- painel de recomendação integrado ao Streamlit, com geração sob demanda, spinner, cache por cliente e opção de tentar novamente;
- política determinística que força `priority_retention_contact` para risco High com prioridade Alta ou Crítica;
- exclusão de idade, gênero, dependentes, escolaridade, estado civil e faixa de renda das evidências operacionais enviadas ao LLM;
- validação por Pydantic e regras determinísticas;
- tratamento controlado de indisponibilidade, timeout e resposta inválida da IA;
- rastreabilidade entre treinamento, versão do modelo e execução do scoring.

---

## Problema de negócio

Uma instituição financeira precisa priorizar clientes para ações de retenção sem abordar toda a carteira indiscriminadamente.

O modelo responde:

> Qual é a probabilidade de churn deste cliente e em qual faixa de risco ele deve ser classificado?

A explicabilidade responde:

> Quais características mais contribuíram para aumentar ou reduzir a previsão produzida pelo modelo?

A camada operacional responde:

> Quais clientes devem ser priorizados para análise?

A camada de IA governada acrescenta:

> Considerando apenas as evidências disponíveis e as ações autorizadas pelo sistema, qual abordagem de retenção pode ser sugerida para revisão humana?

O FinPulse separa deliberadamente essas responsabilidades.

A IA generativa **não calcula o risco, não recalcula SHAP e não cria políticas de retenção**.

Essas responsabilidades pertencem ao modelo e ao código determinístico.

---

## Thresholds e faixas de risco

Foram definidos dois pontos de operação:

| Uso | Threshold aproximado | Objetivo |
|---|---:|---|
| Watchlist | `0,2075` | aumentar a cobertura de clientes potencialmente em risco |
| Classificação oficial | `0,4762` | equilibrar precision e recall pelo melhor F1 na validação |

As faixas utilizadas no consumo das previsões são:

```text
Low     probability < 0.2075
Medium  0.2075 <= probability < 0.4762
High    probability >= 0.4762
```

---

## Dataset

O projeto utiliza o arquivo `BankChurners.csv`, disponibilizado no dataset público [Credit Card Customers](https://www.kaggle.com/datasets/sakshigoyal7/credit-card-customers).

| Característica | Valor |
|---|---:|
| Clientes | 10.127 |
| Clientes existentes | 8.500 |
| Clientes em churn | 1.627 |
| Taxa de churn | 16,07% |
| Colunas brutas | 23 |
| Features usadas pelo modelo | 19 |
| Valores nulos | 0 |
| Clientes duplicados | 0 |

O target original é `Attrition_Flag`, transformado no mart em `churn_flag`.

As duas colunas `Naive_Bayes_Classifier_*` foram removidas antes da modelagem por apresentarem vazamento direto do target.

O identificador do cliente e o texto original da classe também não são utilizados como features.

> O CSV não é versionado neste repositório. Consulte as condições de uso da fonte e faça o upload do arquivo para o bucket `raw` do MinIO.

---

# Arquitetura

```text
BankChurners.csv
        ↓
MinIO / raw
        ↓
PostgreSQL / raw.bank_churners
        ↓
dbt / staging e marts
        ↓
Jupyter / EDA, benchmark e validação
        ↓
MLflow Tracking + Model Registry
        ↓
CatBoost champion
        ↓
Batch scoring
        ↓
PostgreSQL / previsões e marts analíticos
        ↓
FastAPI
   ├── serving
   ├── scoring
   ├── avaliação
   ├── SHAP global
   ├── SHAP individual
   └── retenção
        ↓
Catálogo determinístico de ações
        ↓
Ollama / Llama 3.1 8B
        ↓
Pydantic + regras de governança
        ↓
Recomendação para revisão humana
        ↓
Streamlit / operação e Cliente 360
```

## Responsabilidades por componente

| Componente | Responsabilidade |
|---|---|
| MinIO | dado bruto, artefatos do MLflow e snapshots de scoring |
| PostgreSQL | dados operacionais, previsões, prioridades, marts analíticos e backend do MLflow |
| dbt | staging, marts, documentação e testes de qualidade |
| Jupyter | ingestão, análise, treinamento, validação e scoring |
| CatBoost | cálculo da probabilidade de churn |
| MLflow | experimentos, métricas, parâmetros, lineage e Model Registry |
| SHAP | explicabilidade global e individual do modelo |
| FastAPI | serving, consultas operacionais, explicabilidade e orquestração da recomendação |
| Catálogo de retenção | definição determinística das ações autorizadas por faixa de risco |
| Ollama | runtime local do modelo de linguagem |
| Llama 3.1 8B | seleção entre ações permitidas quando não há ação determinada por política e geração da mensagem de abordagem |
| Pydantic | validação do contrato estruturado da recomendação |
| Streamlit | experiência analítica e operação de retenção |
| Docker Compose | reprodução, healthchecks e comunicação entre serviços |
| Humano | revisão e decisão final sobre qualquer ação recomendada |

---

# Princípio de governança da IA

Uma das decisões centrais do FinPulse é separar aquilo que deve ser garantido pelo software daquilo que pode ser produzido probabilisticamente por um modelo de linguagem.

```text
CatBoost
→ calcula churn_probability

SHAP
→ explica a contribuição das features

Código determinístico
→ controla contexto factual e regras

Catálogo de retenção
→ define ações permitidas

Política determinística
→ força contato prioritário em High + Alta/Crítica

Llama
→ escolhe uma ação permitida quando a política não resolveu a ação
→ escreve suggested_message

Pydantic
→ valida a estrutura

Humano
→ revisa e decide
```

A regra de projeto adotada é:

> Se o software consegue garantir uma regra, ela não deve depender da obediência do LLM.

Por isso, o modelo de linguagem não controla:

- `customer_id`;
- `churn_probability`;
- `risk_band`;
- `priority_label`;
- metadados de geração;
- resumo factual do risco;
- interpretação oficial do SHAP;
- evidências extraídas do SHAP;
- pontos obrigatórios de atenção;
- orientação oficial associada à ação escolhida.

Na implementação atual, a parte efetivamente probabilística é concentrada principalmente em:

- `suggested_message`;
- `recommended_action_id`, somente quando nenhuma política determinística resolve previamente a ação.

Para clientes com risco `High` e prioridade `Alta` ou `Crítica`, o serviço força `priority_retention_contact`, independentemente da escolha devolvida pelo LLM.

Nos demais casos, `recommended_action_id` só pode assumir valores previamente autorizados pelo catálogo e compatíveis com a faixa de risco.

---

# Catálogo de retenção

As ações disponíveis são definidas em código:

```text
maintain_relationship
preventive_contact
transaction_engagement
financial_profile_review
priority_retention_contact
```

A disponibilidade depende da faixa de risco.

| Ação | Low | Medium | High |
|---|:---:|:---:|:---:|
| `maintain_relationship` | ✅ | ✅ | ❌ |
| `preventive_contact` | ❌ | ✅ | ✅ |
| `transaction_engagement` | ❌ | ✅ | ✅ |
| `financial_profile_review` | ❌ | ✅ | ✅ |
| `priority_retention_contact` | ❌ | ❌ | ✅ |

Uma ação válida no enum, mas incompatível com a faixa de risco do cliente, também é bloqueada.

Além da compatibilidade por faixa, existe uma política operacional obrigatória:

```text
risk_band = High
+
priority_label = Alta ou Crítica
→ priority_retention_contact
```

Nesse cenário, somente a ação prioritária é apresentada ao LLM e o serviço normaliza a resposta final para essa ação.

O LLM não possui autorização para inventar novas ações nem enfraquecer uma ação determinada pela política.

---

# IA de retenção

## Runtime

A camada de IA utiliza:

```text
Provider: Ollama
Model: llama3.1:8b
Host interno: http://ollama:11434
Timeout padrão: 120 segundos
Temperature: 0
Structured output: Pydantic JSON Schema
```

O Ollama é executado como serviço independente no Docker Compose.

O ambiente local utiliza:

```text
OLLAMA_NO_CLOUD=1
```

mantendo a inferência do modelo no ambiente local.

Quando disponível, a inferência pode utilizar GPU NVIDIA.

## Contexto enviado ao LLM

A IA recebe apenas contexto controlado, incluindo:

- probabilidade de churn;
- faixa de risco;
- prioridade operacional;
- sinais acionáveis que aumentam a previsão segundo SHAP;
- fatores acionáveis que reduzem a previsão segundo SHAP;
- conjunto de ações de retenção permitidas.

Atributos pessoais continuam disponíveis no modelo e na explicabilidade técnica, mas não são utilizados como evidência operacional de retenção.

Antes da montagem do contexto, o serviço remove:

- idade;
- gênero;
- número de dependentes;
- escolaridade;
- estado civil;
- faixa de renda.

Esse filtro acontece antes do limite de cinco fatores, evitando que atributos bloqueados ocupem o espaço de sinais transacionais, financeiros ou de relacionamento.

O prompt também determina que:

- SHAP não representa causalidade;
- valores brutos não devem ser reinterpretados livremente como "alto", "baixo" ou similares;
- ações permitidas representam política, não evidência;
- a mensagem ao cliente não deve mencionar churn, score, risco, SHAP, prioridade ou modelo;
- nenhuma decisão deve ser executada automaticamente;
- a recomendação exige revisão humana.

---

# Fluxo de recomendação

Para um cliente real, a rota executa:

```text
customer_id
    ↓
PostgreSQL
    ↓
19 features do cliente
    ↓
CatBoost champion
    ↓
probabilidade de churn
    ↓
SHAP individual
    ↓
risk_band + priority_label
    ↓
filtro de evidências operacionais
    ↓
catálogo de ações + política determinística
    ↓
RetentionAIService
    ↓
contexto controlado e ações autorizadas
    ↓
Ollama / Llama 3.1 8B
    ↓
Pydantic
    ↓
governança determinística
    ↓
CustomerRetentionRecommendationResponse
```

O fluxo foi validado de ponta a ponta com o cliente de teste `809849358`.

A probabilidade armazenada no scoring e a probabilidade reconstruída pelo champion foram equivalentes:

```text
0.9999282856387735
```

O fluxo real atravessou:

```text
PostgreSQL
→ CatBoost champion v3
→ SHAP
→ prioridade
→ catálogo
→ RetentionAIService
→ Ollama
→ Llama 3.1 8B
→ Pydantic
→ recomendação
```

---

# Camadas de dados

## Raw

`raw.bank_churners` preserva a granularidade de um cliente por linha.

## Staging

`staging.stg_bank_churners` padroniza nomes, tipos e target.

Os testes cobrem identificador, unicidade, valores aceitos e campos críticos.

## Mart de Machine Learning

`marts.mart_customer_churn_model` entrega 10.127 clientes com:

- `customer_id`;
- `churn_flag`;
- 19 features numéricas e categóricas;
- nenhuma coluna direta de leakage.

As contagens de clientes e churn foram reconciliadas entre MinIO, raw, staging e mart.

## Previsões e consumo analítico

As previsões do champion e os indicadores utilizados pela aplicação são organizados em marts dedicados, incluindo:

- `marts.mart_customer_churn_predictions`;
- `marts.mart_churn_dashboard_overview`;
- `marts.mart_churn_risk_distribution`;
- `marts.mart_churn_retention_priority`;
- `marts.mart_churn_customer_priority`.

Essa separação mantém o dado de modelagem independente das visões voltadas ao consumo operacional.

---

# Metodologia de Machine Learning

## Separação dos dados

Como o dataset não possui uma coluna temporal de observação, foi utilizado split estratificado:

- 60% treino;
- 20% validação;
- 20% teste reservado.

O teste foi utilizado uma única vez após a seleção do modelo e do threshold.

## Benchmark

Foram avaliados:

1. Logistic Regression;
2. K-Nearest Neighbors;
3. Gaussian Naive Bayes;
4. Decision Tree;
5. Random Forest;
6. Extra Trees;
7. HistGradientBoosting;
8. XGBoost;
9. LightGBM;
10. CatBoost;
11. Dummy Classifier como baseline.

A seleção considerou principalmente **Average Precision**, adequada ao desbalanceamento do target, além de ROC AUC, balanced accuracy, precision, recall e F1.

Também foram realizados:

- comparação entre treino e validação;
- validação cruzada estratificada com cinco folds;
- permutation importance;
- análise de precision, recall e F1 por threshold;
- avaliação final em conjunto de teste congelado.

---

# MLOps e scoring

O experimento final é rastreado no MLflow com:

- parâmetros do modelo;
- métricas oficiais e de watchlist;
- features numéricas e categóricas;
- thresholds e faixas de risco;
- resultados do teste final;
- assinatura e exemplo de entrada;
- pipeline completo do CatBoost.

O modelo registrado é:

```text
finpulse-churn-catboost
```

A versão 3 foi promovida com o alias estável:

```text
champion
```

A URI utilizada pelo serving é:

```text
models:/finpulse-churn-catboost@champion
```

A validação de load-back recuperou o modelo a partir dos artefatos persistidos no MinIO e executou inferência com as 19 features sem depender do objeto mantido em memória durante o treinamento.

O batch scoring processou os 10.127 clientes:

| Faixa de risco | Clientes | Probabilidade média |
|---|---:|---:|
| Low | 8.354 | 0,0108 |
| Medium | 174 | 0,3146 |
| High | 1.599 | 0,9205 |

As previsões foram gravadas em:

```text
marts.mart_customer_churn_predictions
```

Um snapshot completo em Parquet foi armazenado no bucket `curated`, enquanto a execução foi registrada no experimento:

```text
finpulse-churn-scoring
```

A validação final cruzou PostgreSQL, MLflow e MinIO, confirmando:

- 10.127 clientes únicos;
- versão 3 do modelo;
- alias `champion`;
- Run ID do treinamento;
- Run ID do scoring;
- integridade do snapshot por SHA-256;
- correspondência entre o mart e o arquivo recuperado do MinIO.

---

# API e model serving

A FastAPI carrega uma única vez, durante a inicialização, o modelo resolvido pela URI:

```text
models:/finpulse-churn-catboost@champion
```

O artefato é recuperado pelo MLflow a partir do MinIO e mantido em memória para as inferências seguintes.

Os dados operacionais são consultados no PostgreSQL por meio do SQLAlchemy.

## Endpoints

| Método | Rota | Responsabilidade |
|---|---|---|
| `GET` | `/` | identifica o serviço e direciona para a documentação |
| `GET` | `/health` | verifica API, champion e PostgreSQL |
| `GET` | `/model-info` | retorna versão, alias, Run ID e origem do modelo |
| `GET` | `/model-explainability/global` | calcula a importância global com SHAP |
| `GET` | `/model-evaluation/confusion-matrix` | retorna a matriz de confusão do teste reservado |
| `GET` | `/portfolio/summary` | entrega indicadores consolidados da carteira |
| `GET` | `/scoring/latest` | retorna último scoring, modelo e métricas |
| `GET` | `/customers` | lista clientes com filtro de risco e paginação |
| `GET` | `/customers/{customer_id}` | retorna features e previsão armazenada |
| `POST` | `/customers/{customer_id}/predict` | executa nova inferência e compara com scoring armazenado |
| `GET` | `/customers/{customer_id}/explainability` | retorna SHAP individual |
| `POST` | `/customers/{customer_id}/retention-recommendation` | gera recomendação governada de retenção |
| `POST` | `/predict` | executa inferência a partir das 19 features |

A documentação OpenAPI pode ser explorada em:

```text
http://localhost:8000/docs
```

---

# Contrato de falhas da IA

O endpoint de retenção diferencia falhas operacionais da dependência de IA.

| HTTP | Situação |
|---|---|
| `200 OK` | recomendação válida |
| `502 Bad Gateway` | IA respondeu, mas o conteúdo não passou no contrato esperado |
| `503 Service Unavailable` | serviço local de IA indisponível |
| `504 Gateway Timeout` | IA ultrapassou o limite de tempo |

Exemplos:

```json
{
  "detail": "Retention AI returned an invalid response."
}
```

```json
{
  "detail": "Retention AI service is unavailable."
}
```

```json
{
  "detail": "Retention AI service timed out."
}
```

Esses cenários foram validados manualmente e posteriormente automatizados com mocks no teste da camada HTTP.

---

# Testes da camada de retenção

A implementação de retenção possui testes separados por responsabilidade.

## RetentionAIService

Os testes cobrem:

- saída válida;
- ação inexistente;
- ação incompatível com Low;
- ação incompatível com Medium;
- ações válidas para Low, Medium e High;
- ausência de fatores protetivos;
- ausência de fatores de risco;
- ausência total de fatores SHAP;
- indisponibilidade do Ollama;
- timeout;
- JSON inválido;
- resposta estruturada incompleta;
- exclusão de atributos pessoais das evidências operacionais;
- aplicação do filtro antes do limite de cinco fatores;
- imposição de contato prioritário para `High + Alta/Crítica`;
- sobrescrita de uma ação mais fraca devolvida pelo LLM.

## Endpoint HTTP

A camada FastAPI possui testes automatizados para:

```text
200 OK
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

O `RetentionAIService` possui **15 testes automatizados** cobrindo geração, governança, ausência de evidências e falhas da dependência de IA.

A suíte completa de `tests/api` executa atualmente **37 testes aprovados**, cobrindo serviço de retenção, schemas, contrato HTTP e integração da API.

Os testes HTTP utilizam mocks para validar o comportamento da API sem depender de provocar falhas reais no Ollama em todas as execuções.

Os cenários reais também foram validados manualmente:

```text
Ollama disponível     → 200
resposta inválida     → 502
Ollama indisponível   → 503
timeout                → 504
```

---

# Dashboard analítico

O Streamlit transforma previsões e métricas técnicas em uma experiência de análise e priorização.

A aplicação combina os marts analíticos do PostgreSQL com endpoints da FastAPI.

## Visão Executiva

- ROC AUC, Balanced Accuracy, F1-score e Recall do champion;
- distribuição da carteira entre baixo, médio e alto risco;
- quantidade e participação de clientes por faixa;
- probabilidade média e volume transacionado por segmento;
- matriz de prioridade de retenção;
- indicadores executivos.

## Clientes em Risco

- ranking operacional dos clientes priorizados;
- probabilidade individual de churn;
- faixa de risco e prioridade de negócio;
- filtros, ordenação e paginação;
- informações financeiras e comportamentais.

## Cliente 360

O Cliente 360 reúne o contexto individual e a operação de retenção em uma única experiência.

A página apresenta:

- busca e seleção de clientes;
- probabilidade de churn;
- faixa de risco;
- prioridade operacional;
- perfil e tempo de relacionamento;
- atividade, inatividade e contatos;
- limite de crédito, saldo rotativo e crédito disponível;
- utilização do limite;
- volume, quantidade e variação das transações;
- fatores que aumentam e reduzem a previsão segundo SHAP;
- recomendação governada de retenção integrada à interface.

A recomendação é gerada somente quando o usuário seleciona **Gerar recomendação**.

O painel apresenta separadamente:

- resumo factual do caso;
- interpretação controlada do risco;
- principais sinais operacionais;
- fatores protetivos;
- ação recomendada;
- orientação de abordagem;
- mensagem sugerida ao cliente;
- pontos de atenção;
- provider e modelo utilizados;
- aviso de revisão humana obrigatória.

A experiência também inclui:

- spinner durante a inferência;
- cache por cliente na sessão do Streamlit;
- geração de uma nova recomendação sob demanda;
- mensagens de erro;
- opção de tentar novamente;
- proteção contra execução automática de qualquer ação.

## Análise do Modelo

A área de análise reúne:

- identificação e métricas do modelo champion;
- matriz de confusão;
- explicabilidade global com SHAP;
- tradução das features para linguagem de negócio;
- ranking das variáveis mais influentes;
- rastreabilidade por modelo, versão, Run ID e data do scoring.

A importância SHAP global representa a intensidade média da influência de cada variável na carteira analisada.

Ela não indica, isoladamente, se valores maiores sempre aumentam ou reduzem o risco.

---

# Explicabilidade Individual

A API disponibiliza explicabilidade individual para cada cliente, incluindo:

- probabilidade e classificação de churn;
- valor observado de cada variável;
- contribuição SHAP de cada feature;
- participação relativa de cada fator na explicação;
- fatores que aumentam a previsão;
- fatores que reduzem a previsão;
- validação da reconstrução da probabilidade prevista;
- identificação do modelo, versão, alias e Run ID utilizados.

Importante:

> Uma contribuição SHAP informa a direção e intensidade da contribuição de uma feature para a previsão do modelo. Ela não estabelece relação causal.

Por isso, a camada de IA é proibida de transformar automaticamente os valores observados em afirmações causais.

---

# Estrutura do projeto

```text
finpulse-ai/
├── api/
│   ├── main.py
│   ├── model_service.py
│   ├── retention_ai_service.py
│   ├── retention_catalog.py
│   ├── database.py
│   ├── customer_repository.py
│   ├── portfolio_repository.py
│   └── schemas.py
├── app/
│   ├── pages/
│   │   ├── 1_Visao_Geral.py
│   │   ├── 2_Clientes_em_Risco.py
│   │   ├── 3_Clientes_360.py
│   │   └── 5_Analise_do_Modelo.py
│   ├── services/
│   ├── styles/
│   └── streamlit_app.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── curated/
├── dbt/finpulse_dbt/
│   ├── macros/
│   └── models/
│       ├── staging/
│       └── marts/
├── docker/
│   ├── api/
│   ├── jupyter/
│   ├── mlflow/
│   ├── postgres/init/
│   └── streamlit/
├── docs/architecture/
├── notebooks/
│   ├── 00_churn_data_ingestion.ipynb
│   ├── 01_churn_dashboard_features.ipynb
│   ├── 02_churn_model_training.ipynb
│   └── 03_churn_model_registry_validation.ipynb
├── models/
├── reports/
├── src/
├── tests/api/
│   ├── test_api_integration.py
│   ├── test_retention_ai_service.py
│   ├── test_retention_recommendation_endpoint.py
│   └── test_retention_recommendation_schema.py
├── docker-compose.yml
└── README.md
```

---

# Como executar

## Pré-requisitos

- Docker Desktop com Docker Compose;
- Git;
- acesso ao arquivo `BankChurners.csv`;
- GPU NVIDIA opcional para inferência local acelerada.

## 1. Clone o repositório

```bash
git clone https://github.com/isaiasjusto/finpulse-ai.git
cd finpulse-ai
```

## 2. Construa e inicie os serviços

```bash
docker compose up -d --build
docker compose ps
```

Serviços locais:

| Serviço | URL ou porta |
|---|---|
| Streamlit | `http://localhost:8501` |
| FastAPI | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| MLflow | `http://localhost:5000` |
| JupyterLab | `http://localhost:8888` |
| pgAdmin | `http://localhost:5050` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |
| Ollama | `http://localhost:11434` |
| PostgreSQL | `localhost:5433` |

Na primeira inicialização, o Compose prepara a infraestrutura persistente da aplicação.

## 3. Disponibilize o dado bruto

No console do MinIO, envie:

```text
raw/BankChurners.csv
```

Depois execute:

```text
00_churn_data_ingestion.ipynb
```

para ingestão e validação das camadas.

## 4. Execute o dbt

O projeto foi validado com:

```text
dbt-core 1.11.12
dbt-postgres 1.10.2
```

```bash
cd dbt/finpulse_dbt
dbt build
```

## 5. Execute os notebooks

```text
00_churn_data_ingestion.ipynb
01_churn_dashboard_features.ipynb
02_churn_model_training.ipynb
03_churn_model_registry_validation.ipynb
```

## 6. Disponibilize o modelo de linguagem

O runtime utilizado é o Ollama.

Modelo atual:

```text
llama3.1:8b
```

Exemplo:

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

Para verificar o modelo carregado:

```bash
docker compose exec ollama ollama ps
```

## 7. Valide a API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/model-info
curl http://localhost:8000/scoring/latest
```

Documentação:

```text
http://localhost:8000/docs
```

Exemplo de recomendação:

```bash
curl -X POST \
  http://localhost:8000/customers/809849358/retention-recommendation
```

## 8. Abra o dashboard

```text
http://localhost:8501
```

---

# Executando os testes da API

A imagem dedicada de testes isola as dependências necessárias sem alterar o container principal da API.

Para executar toda a suíte:

```bash
docker compose --profile test run --rm --build api-tests python -m pytest -q tests/api
```

Resultado validado:

```text
37 passed, 1 warning
```

Para executar apenas os testes do serviço de retenção:

```bash
docker compose --profile test run --rm --build api-tests python -m pytest -q tests/api/test_retention_ai_service.py
```

Resultado validado:

```text
15 passed
```

Para executar somente o contrato HTTP da recomendação:

```bash
docker compose --profile test run --rm --build api-tests python -m pytest -q tests/api/test_retention_recommendation_endpoint.py
```

Os testes utilizam mocks para validar respostas, políticas e falhas da dependência de IA sem exigir chamadas reais ao Ollama em todas as execuções.

---

# Reprodutibilidade

- versões Python fixadas por serviço;
- imagem do Jupyter fixada por digest;
- MLflow e bibliotecas de Machine Learning versionadas;
- CatBoost registrado no MLflow Model Registry;
- alias estável `champion`;
- volumes persistentes para PostgreSQL, MinIO e Ollama;
- inicialização automatizada dos componentes locais;
- healthchecks para serviços principais;
- comunicação interna por Docker Compose;
- scoring rastreável;
- snapshot de scoring com validação SHA-256;
- explicabilidade reproduzível a partir do champion;
- saída da IA estruturada com Pydantic;
- catálogo determinístico de ações;
- testes de indisponibilidade, timeout e resposta inválida;
- inferência local do LLM;
- revisão humana obrigatória antes de qualquer ação.

As credenciais presentes no Compose são exclusivas para desenvolvimento local.

Um ambiente produtivo deve utilizar secrets, segregação de ambientes e usuários com privilégios mínimos.

---

# Limitações

- O dataset é público e educacional e não representa uma carteira bancária em produção.
- Não existe timestamp de referência para validação temporal; por isso o split é estratificado.
- As métricas refletem este dataset e não devem ser generalizadas para outra população sem nova validação.
- A alta capacidade preditiva depende principalmente de variáveis transacionais fortemente associadas ao target.
- As explicações SHAP representam contribuições para a previsão aprendida pelo modelo e não relações causais.
- O LLM não elimina a necessidade de validação humana.
- Recomendações geradas pela IA são sugestões de abordagem, não decisões automáticas.
- O sistema não concede descontos, crédito, benefícios ou ofertas automaticamente.
- O projeto não representa recomendação financeira, score regulatório ou decisão automática de crédito.
- Monitoramento contínuo de drift e performance ainda não foi implementado.

---

# Status do projeto

- [x] Ambiente Docker com PostgreSQL, MinIO, Jupyter, pgAdmin e MLflow
- [x] Dependências versionadas e imagens reproduzíveis
- [x] Ingestão e validação do dado bruto
- [x] Modelos dbt de staging e mart
- [x] Testes de qualidade e auditoria de leakage
- [x] EDA e features para dashboard
- [x] Benchmark de dez modelos
- [x] Análise de overfitting e validação cruzada
- [x] CatBoost avaliado no teste reservado
- [x] MLflow Tracking e Model Registry
- [x] Artefatos persistidos no MinIO
- [x] Alias `champion` e validação de load-back
- [x] Batch scoring dos 10.127 clientes
- [x] Mart de previsões no PostgreSQL
- [x] Snapshot Parquet no MinIO
- [x] Execução do scoring registrada no MLflow
- [x] Validação cruzada entre PostgreSQL, MLflow e MinIO
- [x] API com FastAPI e serving do champion
- [x] Consultas de carteira e clientes pelo PostgreSQL
- [x] Healthcheck de API, modelo e banco
- [x] Dashboard multipágina com Streamlit
- [x] Visão executiva e distribuição de risco
- [x] Operação de retenção e clientes priorizados
- [x] Matriz de confusão no dashboard
- [x] Explicabilidade global com SHAP
- [x] Rastreabilidade de modelo e scoring
- [x] Explicabilidade individual com SHAP
- [x] Cliente 360 como página independente
- [x] Catálogo governado de ações de retenção
- [x] Ollama integrado ao Docker Compose
- [x] Llama 3.1 8B executando localmente
- [x] RetentionAIService com structured output
- [x] Separação entre campos determinísticos e probabilísticos
- [x] Recomendações inteligentes de retenção via API
- [x] Endpoint `/customers/{customer_id}/retention-recommendation`
- [x] Tratamento HTTP de resposta inválida, indisponibilidade e timeout
- [x] Testes automatizados da camada de retenção
- [x] Exclusão de atributos pessoais das evidências operacionais
- [x] Política determinística para contato prioritário
- [x] Suíte completa da API com 37 testes aprovados
- [x] Validação end-to-end com cliente real
- [x] Integração da recomendação de IA ao Cliente 360
- [x] Cache de recomendação por sessão no Streamlit
- [x] Experiência visual de loading, retry e erros de IA
- [ ] Assistente FinPulse com chat
- [ ] Alertas e automações com n8n
- [ ] Monitoramento de dados, drift e performance

---

# Próximas evoluções

A integração operacional entre Cliente 360 e IA governada está concluída.

O fluxo entregue é:

```text
Usuário seleciona o cliente
        ↓
Cliente 360 carrega contexto e SHAP
        ↓
Usuário solicita a recomendação
        ↓
Streamlit chama a FastAPI
        ↓
evidências pessoais não acionáveis são removidas
        ↓
catálogo e política determinística controlam as ações
        ↓
RetentionAIService prepara o contexto
        ↓
Ollama / Llama gera a parte autorizada da resposta
        ↓
Pydantic e regras de governança validam e normalizam o resultado
        ↓
Cliente 360 apresenta a recomendação para revisão humana
```

As próximas evoluções planejadas são:

1. adicionar capturas e vídeo demonstrativo do produto;
2. reutilizar os serviços governados no Assistente FinPulse com chat;
3. adicionar RAG para políticas e documentos controlados;
4. automatizar alertas e fluxos operacionais com n8n;
5. implementar monitoramento de dados, drift e performance.

O futuro Assistente FinPulse não substituirá o pipeline governado existente.

Previsões, SHAP, prioridade, ações autorizadas e regras operacionais continuarão sendo fornecidos por componentes determinísticos. O LLM permanecerá restrito à interpretação e comunicação dentro do contexto permitido.

---

# Decisões de engenharia

Algumas decisões importantes tomadas durante o desenvolvimento:

### O LLM não calcula o risco

O score continua sendo responsabilidade exclusiva do modelo champion.

### O LLM não explica livremente o modelo

As evidências utilizadas na recomendação são derivadas das contribuições SHAP calculadas pelo sistema.

### O LLM não define quais ações existem

O catálogo de retenção é código determinístico.

### O LLM não pode executar ações

A saída é apenas uma recomendação submetida a revisão humana.

### Erros externos possuem contrato explícito

Indisponibilidade, timeout e resposta inválida são diferenciados na camada HTTP.

### Testes de falha usam mocks

Depois da validação manual real, os cenários de falha são reproduzidos de forma rápida e determinística em testes automatizados.

---

# Autor

**Isaias Justo**  
Data Scientist | Machine Learning | Analytics & Data Engineering

[LinkedIn](https://www.linkedin.com/in/isaias-justo-a8b998185/) · [GitHub](https://github.com/isaiasjusto)

---

Se este projeto foi útil ou interessante, considere deixar uma ⭐ no repositório.
