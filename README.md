# Sistema de recomendação de filmes com grafos bipartidos

Projeto acadêmico de Engenharia da Computação que implementa um recomendador de filmes com uma representação própria de grafo bipartido. O conjunto de dados é sintético e gerado localmente com seed fixa.

## Objetivos

- Modelar avaliações como arestas ponderadas entre usuários e filmes.
- Analisar graus, conectividade, caminhos e similaridade entre usuários.
- Recomendar filmes por exploração BFS e comparar com popularidade.
- Avaliar recomendações por leave-one-out e ordenar filmes por ranking bayesiano.

## Modelo e algoritmos

O grafo tem duas partições: usuários e filmes. Cada avaliação forma uma aresta entre um vértice de cada partição; a nota de 1 a 5 é o peso. A implementação usa listas de adjacência em `src/grafo.py`, sem depender do NetworkX para algoritmos.

A busca em largura (BFS) percorre o grafo por distância. Para recomendar, são encontrados usuários a distância dois do usuário alvo e filmes bem avaliados por eles a distância três. Filmes já avaliados são excluídos. A similaridade de Jaccard entre dois usuários é a razão entre filmes em comum e filmes distintos avaliados por qualquer um deles.

O ranking bayesiano combina a média de notas do filme (R) com a média global (C), usando `(v × R + m × C) / (v + m)`, onde `v` é o número de avaliações e `m` controla o peso do prior global. Isso reduz a influência de poucas avaliações.

## Estrutura

```text
dados/       CSVs de avaliações e catálogo
src/         grafo, recomendador, visualização e caminhos centralizados
outputs/     imagens produzidas
docs/        relatório e saída textual opcional
tests/       testes automatizados com pytest
main.py      análise e interface de linha de comando
gerar_dados.py gerador reproduzível do conjunto sintético
```

## Instalação e execução

Requer Python 3.9 ou superior.

```bash
python -m pip install -r requirements.txt
python -m pytest -v
python main.py
python main.py --plot
python main.py --salvar-saida
```

Os comandos devem ser executados na raiz do repositório. Os caminhos de dados e saídas são resolvidos a partir da localização do projeto. `--plot` salva as visualizações em `outputs/`; `--salvar-saida` grava a execução textual em `docs/saida_execucao.txt`.

## Geração de dados

```bash
python gerar_dados.py
python gerar_dados.py --sobrescrever
```

Por segurança, a geração se recusa a substituir CSVs existentes. Use `--sobrescrever` explicitamente para regenerá-los. A seed é 42.

## Visualizações

`python main.py --plot` produz o grafo ponderado por notas, o grafo organizado por gênero e o ranking bayesiano. Os layouts de força usam seed fixa e os arquivos são gravados em `outputs/`. NetworkX é usado somente para calcular posições e desenhar o grafo; Matplotlib salva as figuras.

## Resultados e limitações

A execução apresenta estatísticas, componentes, caminhos mínimos, usuários similares, recomendações, hit rate leave-one-out e rankings. Os resultados dependem do pequeno conjunto sintético e não devem ser interpretados como evidência de desempenho em uma plataforma real. A avaliação usa uma divisão leave-one-out simples, sem ajuste de hiperparâmetros nem validação temporal. Cold start é tratado por popularidade.

## Dependências

As dependências externas estão listadas em `requirements.txt`; os algoritmos centrais usam apenas a biblioteca padrão do Python.
