# Arquitetura do CineConecta

## Visão geral

O CineConecta possui uma fonte persistente e três camadas simples:

```text
CSV em dados/ → núcleo em src/cineconecta.py → API em backend/api.py → React em frontend/src/
```

Os arquivos CSV são a fonte persistente. O núcleo transforma as linhas em um grafo bipartido. A API consulta esse grafo e serializa objetos JSON. O frontend coordena as cinco telas e desenha as relações com SVG.

## Fonte de dados

- `usuarios.csv`: `id`, nome e gêneros informativos.
- `filmes.csv`: `id`, título e gênero.
- `avaliacoes.csv`: `usuario_id`, `filme_id` e nota.

`carregar()` lê os três arquivos e devolve `(grafo, usuarios, filmes)`. Os dicionários fornecem nomes e gêneros; o grafo concentra as relações e notas.

## Núcleo do grafo web

`GrafoFilmes`, em `src/cineconecta.py`, mantém:

```text
tipo[id] = "usuario" | "filme"
adj[usuario_id][filme_id] = nota
adj[filme_id][usuario_id] = nota
```

A duplicação da nota nos dois sentidos simplifica consultas de vizinhança. Ela representa uma única aresta não direcionada; a API conta avaliações a partir da partição de usuários para não duplicar o total.

As principais operações são:

- `bfs`: calcula distâncias e predecessores por níveis.
- `caminhos_positivos`: enumera caminhos simples de três arestas usando notas 4 ou 5.
- `positivos`: cria o conjunto de filmes positivos de um usuário.
- `jaccard`: divide o tamanho da interseção pelo tamanho da união desses conjuntos.
- `componentes`: repete a BFS a partir dos vértices ainda não visitados.
- `recomendacoes`: descarta filmes já avaliados, agrega colaboradores e calcula a média ponderada por Jaccard.

## API e estado da simulação

`backend/api.py` carrega os dados uma vez ao iniciar:

```text
grafo_original  → base consultada pelas telas Início, Usuários, Recomendações e Grafo
grafo_simulacao → cópia profunda usada somente pelo perfil temporário
alteracoes      → avaliações registradas durante a simulação
usuario_simulado → identificação e nome da pessoa temporária ativa
```

As quatro telas que consultam usuários reais continuam lendo `grafo_original`. A tela Simulação cria uma pessoa apenas em memória e consulta `grafo_simulacao`. Assim, as avaliações temporárias não modificam estatísticas, recomendações ou grafos dos usuários originais. Restaurar cria outra cópia do grafo original, remove a pessoa temporária e esvazia a lista de avaliações simuladas.

Principais grupos de endpoints:

- `/api/estatisticas`, `/api/usuarios` e `/api/filmes`: visão geral da base.
- `/api/usuarios/{id}/preferencias` e `/similares`: detalhes de um usuário.
- `/api/recomendacoes/{id}`: ranking, colaboradores e caminhos explicativos.
- `/api/grafo`: recortes de vértices e arestas para o SVG.
- `/api/exemplo`: um caminho real completo para a apresentação inicial.
- `/api/analise`: distribuições usadas nos gráficos recolhidos.
- `GET /api/simulacao`: estado completo da simulação ativa.
- `POST /api/simulacao/usuario`: cria a pessoa temporária e reinicia o estado simulado.
- `POST /api/simulacao/avaliacao`: registra uma nota e devolve similaridades e recomendações recalculadas.
- `POST /api/simulacao/restaurar`: remove a pessoa e todas as avaliações temporárias.

## Frontend

`App.tsx` mantém a navegação e o estado compartilhado. Ao iniciar, solicita estatísticas, usuários, filmes, análises e o exemplo. Efeitos adicionais carregam detalhes somente quando o usuário ou a tela ativa mudam.

`types.ts` descreve o formato dos objetos JSON. Esses tipos não executam validação em tempo de execução; o FastAPI/Pydantic valida entradas no backend, e o TypeScript ajuda a manter o consumo consistente no frontend.

`HomePage.tsx` organiza a apresentação acadêmica. Os totais e o grafo do exemplo usam dados da API. O pequeno grafo conceitual é apenas uma ilustração didática do modelo.

Na tela Simulação, `App.tsx` mantém o nome digitado, o filme e a nota selecionados, o estado retornado pela API e a recomendação cujo caminho está aberto. Cada avaliação substitui esse estado pela resposta mais recente do backend e solicita novamente o recorte do grafo do usuário temporário.

## Visualização SVG do grafo

`GraphView`, em `App.tsx`, recebe listas de nós e arestas já filtradas pela API. O modo selecionado determina o layout:

- vizinhança: usuário central e filmes em disposição radial;
- expandida e caminho: usuários e filmes em colunas, preservando a leitura bipartida;
- completa e positiva: simulação de forças determinística feita no frontend.

Os círculos azuis representam usuários e os verdes representam filmes. Rótulos, opacidade, contornos e cores de aresta destacam o usuário selecionado, seus vizinhos e os caminhos. O SVG usa `viewBox`, por isso adapta sua escala à largura disponível.

## Fluxo de uma recomendação

```text
1. Frontend solicita /api/recomendacoes/{usuario}
2. API escolhe o grafo original ou o grafo temporário conforme o usuário
3. BFS positiva encontra caminhos usuário-filme-usuário-filme
4. Filmes já avaliados são removidos
5. Jaccard define o peso de cada colaborador
6. Média ponderada produz a pontuação
7. API retorna ranking, contribuidores e caminhos
8. Frontend apresenta a lista e permite abrir a justificativa no grafo
```

## Implementação histórica de terminal

`src/grafo.py`, `src/recomendador.py`, `src/experimentos.py`, `src/visualizacao.py` e `main.py` formam uma trilha acadêmica anterior. Ela inclui cosseno, popularidade, combinação híbrida, métricas e imagens estáticas. Esses módulos permanecem testados e executáveis, mas não são importados pela API web. A separação é intencional: os resultados da interface web vêm somente de `src/cineconecta.py`.
