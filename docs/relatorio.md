# Sistema de Recomendação de Conteúdo Usando Grafos Bipartidos

**Disciplina:** Teoria dos Grafos  **Aluno(a):** _________  **Data:** _________

## 1. Introdução
Plataformas de streaming precisam sugerir conteúdo novo a cada usuário. Uma forma natural de
representar o problema é um grafo: usuários e filmes são vértices, e consumir um filme é uma
aresta. Este trabalho implementa um recomendador que usa apenas conceitos de grafos: grafos
bipartidos, grau, caminhos, conectividade, BFS e análise de vizinhança.

## 2. Modelagem
O grafo G = (U ∪ I, E) é **bipartido**: U é o conjunto de usuários, I o de filmes, e toda aresta liga
um usuário a um filme. A nota (1 a 5) é guardada como peso da aresta. A representação é por
**lista de adjacência** (dicionário de dicionários), com custo de memória O(V + E). A propriedade de
bipartição é verificada por 2-coloração com BFS (`eh_bipartido`).

**Dados:** 185 avaliações sintéticas (31 usuários, 27 filmes), geradas por `gerar_dados.py`, no
formato `usuario,filme,nota`. Como o ambiente de desenvolvimento não tinha internet, o MovieLens
não foi usado, mas o carregador aceita qualquer CSV nesse formato. Os dados têm 4 perfis de gosto
(ficção, terror, romance, animação), alguns usuários com gosto misto (que criam "pontes" entre perfis),
um usuário com uma única avaliação e uma componente isolada, para testar casos extremos.

## 3. Conceitos aplicados
| Conceito | Onde foi usado |
|---|---|
| Grafo bipartido | Modelagem e verificação por 2-coloração |
| Grau | Grau do usuário = nº de filmes vistos; grau do filme = popularidade |
| Vizinhança | N(u) = filmes de u; usuários a distância 2 compartilham filmes; similaridade de Jaccard |
| Caminhos | Caminho mínimo por BFS; caminhos u → i → v → j geram as recomendações |
| Conectividade | Componentes conexas e diâmetro |
| BFS | Distâncias, caminho mínimo, componentes, 2-coloração e geração de candidatos |

## 4. Algoritmo de recomendação
Para um usuário *u*:
1. Executa BFS a partir de *u* com limite de profundidade 3.
2. Os vértices a distância 2 são usuários parecidos *v* (compartilham ao menos um filme com *u*).
3. Os filmes *j* a distância 3 são candidatos: vizinhos de algum *v* que *u* ainda não viu.
4. Pontuação: `score(j) = Σ_v Jaccard(u, v) · nota(v, j)/5`, considerando só notas ≥ 4.
5. Retorna os N maiores scores, indicando o usuário que mais contribuiu (explicação da sugestão).

Se não houver candidatos, o sistema recomenda os filmes de maior grau (**fallback por popularidade**).

**Complexidade:** a BFS custa O(V + E). A pontuação percorre os vizinhos dos usuários a distância 2,
no pior caso O(E).

## 5. Resultados (execução de `main.py`)
**Estatísticas:** 31 usuários, 27 filmes, 185 arestas, densidade 22,1%, grafo bipartido = verdadeiro.
Grau médio: 5,97 por usuário e 6,85 por filme. Mais populares: *O Exorcista* e *Hereditário* (grau 12).

**Conectividade:** duas componentes. A principal tem 54 vértices (diâmetro 6); a outra tem 4
vértices (2 usuários e 2 documentários), sem ligação com o restante. Não existe caminho entre
`user01` e *Cosmos*.

**Exemplo de caminho mínimo:** user01 → Blade Runner → user23 → Toy Story (distância 3).
Em grafos bipartidos, a distância usuário–filme é sempre ímpar e usuário–usuário é sempre par.

**Recomendações para `user01`** (perfil ficção): *A Chegada*, *Hereditário*, *It: A Coisa*, *Corra!*,
*Diário de uma Paixão*. O primeiro vem de `user06`, o usuário mais parecido (Jaccard 0,60).

**Avaliação (leave-one-out, top-5):** para cada usuário, esconde-se um filme bem avaliado e
verifica-se se ele aparece nas 5 recomendações.

| Método | Hit rate (28 usuários) |
|---|---|
| Recomendação por BFS/grafo | 89,3% |
| Baseline: mais populares | 3,6% |

## 6. Discussão e limitações
- O ganho sobre o baseline é grande, mas os dados são **sintéticos e com perfis bem separados**, então
  o resultado tende a ser otimista. Com dados reais (como o MovieLens) o hit rate seria menor.
- **Cold start:** um usuário com 1 avaliação ainda recebe sugestões (via usuários que viram o mesmo
  filme), mas pouco personalizadas. Usuários em componente isolada, sem candidatos, caem no fallback.
- **Bolhas de gosto:** componentes pequenas e isoladas nunca recebem itens de fora.
- O Jaccard ignora as notas; poderia ser trocado por similaridade do cosseno ponderada pelas notas.

## 7. Conclusão
O modelo de grafo bipartido permitiu implementar um recomendador interpretável (cada sugestão tem
um caminho que a justifica) usando BFS e análise de vizinhança. Como trabalhos futuros: usar o
MovieLens, projetar o grafo em um grafo só de usuários, testar PageRank personalizado e
comparar com filtragem colaborativa por matriz.

## 8. Extensao: notas, generos e ranking
- **Layout ponderado:** usa-se `peso = (nota/5)^3` como forca de atracao no layout de forcas, de modo que
  arestas com nota alta aproximam usuario e filme (nota 5 pesa 1,0; nota 2 pesa 0,06).
- **Layout por genero:** os filmes sao agrupados por genero (`dados/filmes.csv`) e cada usuario e posicionado
  no centroide dos seus filmes, ponderado por nota^2. Usuarios de gosto misto ficam entre os grupos.
- **Ranking:** media bayesiana `(v*R + m*C)/(v+m)`, com v = nº de avaliacoes do filme, R = media do filme,
  C = media global e m = 4. Penaliza filmes com poucas avaliacoes. Top 3: *Matrix* (4,75), *Interestelar* (4,73),
  *Antes do Amanhecer* (4,57). Tambem ha ranking por genero e nota media por genero.

## Referências
- CORMEN, T. et al. *Algoritmos: Teoria e Prática*. Capítulo sobre buscas em grafos (BFS).
- DIESTEL, R. *Graph Theory*. Springer.
- HARPER, F. M.; KONSTAN, J. A. The MovieLens Datasets. *ACM TiiS*, 2015.
