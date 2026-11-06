# Sistema de recomendação de filmes com grafos bipartidos

Projeto acadêmico de Engenharia da Computação. A versão 1.1.0 amplia o recomendador existente, preservando o grafo bipartido próprio, os dados sintéticos, o BFS e o ranking bayesiano. Não usa bibliotecas de Machine Learning.

## Objetivos

- Representar avaliações como arestas ponderadas entre usuários e filmes.
- Explorar conectividade e vizinhanças para produzir recomendações explicáveis.
- Combinar estrutura do grafo, notas, popularidade e diversidade de gêneros.
- Comparar algoritmos com métricas de ranking em uma divisão treino/teste reproduzível.

## Modelo e algoritmos

O grafo possui partições de usuários e filmes; cada avaliação cria uma aresta com nota de 1 a 5. A estrutura é uma lista de adjacência implementada em `src/grafo.py`. A BFS encontra usuários a distância dois e filmes a distância três. O Jaccard continua disponível e mede filmes em comum dividido pela união dos filmes avaliados.

### Similaridade de cosseno

Cada usuário é representado por um vetor de notas, com zero nos filmes não avaliados. O cálculo manual é:

```text
cos(A, B) = (A · B) / (||A|| × ||B||)
```

Vetores nulos e usuários inexistentes retornam zero. Para as notas positivas usadas atualmente, a similaridade fica entre zero e um.

### Recomendações e combinação híbrida

O método por cosseno agrega para cada filme candidato `similaridade × nota/5`, usando avaliações iguais ou superiores a 4. O método BFS anterior também prioriza notas a partir de 4. O método híbrido normaliza cada fonte dividindo os scores pelo máximo da própria fonte e combina:

```text
score = 0,40 × BFS_normalizado
      + 0,40 × cosseno_normalizado
      + 0,20 × popularidade_normalizada
```

Os pesos são constantes ajustáveis em `src/recomendador.py`. Popularidade é o grau do filme, isto é, quantidade de avaliações. Empates são resolvidos pelo nome do filme. Filmes já avaliados pelo usuário são excluídos; sem candidatos personalizados, a popularidade ainda oferece um fallback.

### Diversidade e explicabilidade

A diversificação escolhe os itens em ordem gulosa e desconta `0,08` por ocorrência anterior do mesmo gênero. O desconto é ajustável e não remove candidatos. Filmes sem gênero não recebem penalidade. Cada recomendação híbrida informa filme, score final, contribuições normalizadas de BFS/cosseno/popularidade, gênero, usuário colaborador, nota desse colaborador e motivo derivado dos cálculos.

### Avaliação

Para cada usuário, são ocultadas aleatoriamente, com `seed=42`, 20% das avaliações relevantes (nota >= 4), arredondando a quantidade e garantindo ao menos uma ocultação quando há avaliação relevante. O grafo de treino é construído sem essas arestas, e as recomendações são calculadas somente nele. A avaliação macro agrega os 31 usuários, todos com ao menos uma avaliação relevante ocultada. A divisão e a avaliação não alteram o grafo original.

```text
Precision@K = relevantes recomendados / K
Recall@K    = relevantes recomendados / relevantes ocultados
DCG@K       = soma((2^rel_i - 1) / log2(i + 1)), com posições começando em 1
NDCG@K      = DCG@K / DCG ideal
```

### Resultados experimentais

Métricas calculadas na execução atual com os CSVs do repositório, K=5 e seed 42:

| Algoritmo | Precision@5 | Recall@5 | NDCG@5 |
|---|---:|---:|---:|
| BFS | 0,187 | 0,871 | 0,655 |
| Cosseno | 0,187 | 0,871 | 0,669 |
| Híbrido | 0,174 | 0,823 | 0,632 |
| Popularidade | 0,045 | 0,194 | 0,152 |

São resultados sobre apenas 31 usuários, 27 filmes e 185 avaliações sintéticas, não uma estimativa de desempenho em dados reais. A escolha dos dados e dos parâmetros afeta fortemente as métricas.

## Estrutura

```text
dados/       CSVs de avaliações e catálogo
src/         grafo, recomendador, visualizações e caminhos
outputs/     imagens geradas
docs/        relatório acadêmico e saída textual
tests/       testes automatizados
main.py      análise e interface de linha de comando
gerar_dados.py gerador sintético reproduzível
```

## Instalação e execução

Requer Python 3.9 ou superior. Na raiz do repositório:

```powershell
python -m pip install -r requirements.txt
python -m pytest -v
python main.py
python main.py --usuario user10
python main.py --plot
python main.py --salvar-saida
```

`--usuario` seleciona o usuário para a apresentação das recomendações novas. Os exemplos anteriores continuam sendo exibidos. `--plot` grava os gráficos em `outputs/`; `--salvar-saida` grava a saída em `docs/saida_execucao.txt`.

Para gerar os dados, execute `python gerar_dados.py`. Os arquivos existentes são protegidos; para regenerá-los explicitamente, use `python gerar_dados.py --sobrescrever`.

## Dependências e limitações

NetworkX e Matplotlib são usados somente nas visualizações; pytest executa os testes. O núcleo dos algoritmos usa a biblioteca padrão. O cosseno considera notas como valores positivos sem centralização pela média, e os dados pequenos/sintéticos limitam a generalização. A avaliação é um holdout por usuário sem divisão temporal ou ajuste dos pesos.
