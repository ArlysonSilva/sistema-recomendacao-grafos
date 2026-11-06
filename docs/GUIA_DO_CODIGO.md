# Guia do código do CineConecta

Este documento apresenta a implementação do projeto por camadas. O objetivo é permitir que uma pessoa que acabou de abrir o repositório localize os dados, acompanhe uma requisição e entenda como uma recomendação é calculada.

## 1. Fluxo geral

```text
dados/*.csv
    ↓ carregar()
GrafoFilmes + dicionários de usuários e filmes
    ↓ consultas da API
JSON enviado pelo FastAPI
    ↓ request()
estado dos componentes React
    ↓
tabelas, listas e SVGs das cinco telas
```

O backend é responsável por ler os dados, executar os algoritmos e preparar respostas JSON. O frontend não recalcula Jaccard ou recomendações; ele apresenta os valores recebidos e organiza a interação.

## 2. Dados persistentes

Os arquivos em `dados/` são a fonte permanente da aplicação:

| Arquivo | Conteúdo | Campos principais |
| --- | --- | --- |
| `usuarios.csv` | pessoas da base original | `id`, `nome`, `generos_preferidos` |
| `filmes.csv` | catálogo | `id`, `titulo`, `genero` |
| `avaliacoes.csv` | relações do grafo | `usuario_id`, `filme_id`, `nota` |

Uma linha de `avaliacoes.csv` representa uma aresta. A simulação não escreve nesses arquivos: todas as suas alterações existem apenas enquanto o backend está em execução.

## 3. Núcleo da aplicação web

### `src/cineconecta.py`

Esse é o módulo principal da aplicação web.

#### Classe `GrafoFilmes`

O grafo usa duas estruturas:

```python
tipo[id] = "usuario" ou "filme"
adj[id_origem][id_destino] = nota
```

A avaliação é gravada nos dois sentidos da lista de adjacência. Isso facilita partir tanto de um usuário quanto de um filme, mas continua representando uma única aresta não direcionada.

| Método | Responsabilidade |
| --- | --- |
| `add_vertice()` | cria um usuário ou filme e impede tipos conflitantes |
| `add_avaliacao()` | liga usuário e filme com nota de 1 a 5 |
| `grau()` | informa quantas arestas chegam ao vértice |
| `vizinhos()` | devolve os vértices ligados diretamente |
| `bfs()` | percorre o grafo por níveis e registra distância e predecessor |
| `caminhos_positivos()` | enumera caminhos formados apenas por notas 4 ou 5 |
| `caminho_minimo()` | reconstrói um caminho a partir dos predecessores da BFS |
| `componentes()` | separa grupos de vértices conectados |
| `eh_bipartido()` | verifica se toda aresta liga partições diferentes |
| `positivos()` | reúne os filmes avaliados com nota 4 ou 5 |
| `jaccard()` | mede a sobreposição entre dois conjuntos de filmes positivos |

#### Função `carregar()`

Lê os três CSVs, cria todos os vértices, adiciona as avaliações e retorna:

```python
grafo, usuarios, filmes
```

`usuarios` e `filmes` guardam nomes e gêneros. O objeto `grafo` guarda conexões e notas.

#### Função `similares()`

Para cada outro usuário:

1. obtém os filmes positivos dos dois usuários;
2. calcula Jaccard;
3. descarta resultados iguais a zero;
4. informa os filmes positivos em comum;
5. ordena do maior Jaccard para o menor.

#### Função `recomendacoes()`

A função recebe um grafo, os dicionários de metadados e o usuário de origem. O processamento é:

```text
1. Guardar todos os filmes já avaliados pelo usuário.
2. Executar a busca de caminhos positivos com três arestas.
3. Interpretar cada caminho como:
   usuário → filme compartilhado → colaborador → filme candidato.
4. Descartar candidatos já avaliados.
5. Calcular o Jaccard entre usuário e colaborador.
6. Agrupar colaboradores e caminhos por filme candidato.
7. Calcular a pontuação ponderada.
8. Ordenar pontuação, quantidade de colaboradores e título.
```

A fórmula usada é:

```text
pontuação = Σ(nota do colaborador × Jaccard) / Σ(Jaccard)
```

Um mesmo colaborador contribui uma vez para a pontuação de cada candidato. Os caminhos adicionais continuam disponíveis para explicar por quais filmes compartilhados a recomendação foi alcançada.

## 4. Backend HTTP

### `backend/api.py`

O módulo cria a aplicação FastAPI, configura CORS, carrega a base e mantém o estado temporário da simulação.

#### Estado mantido em memória

| Variável | Uso |
| --- | --- |
| `grafo_original` | dados permanentes usados pelas quatro telas fora da simulação |
| `usuarios` | metadados dos usuários originais |
| `filmes` | metadados do catálogo |
| `grafo_simulacao` | cópia do grafo que pode receber avaliações temporárias |
| `alteracoes` | histórico das avaliações temporárias |
| `usuario_simulado` | ID e nome da pessoa criada na simulação |

#### Modelos de entrada

- `NovoUsuarioSimulado`: valida o nome da pessoa temporária.
- `AvaliacaoSimulada`: valida usuário, filme e nota entre 1 e 5.
- `UsuarioSelecionado`: mantém compatibilidade com a rota de recomendação da simulação.

#### Funções auxiliares

| Função | Responsabilidade |
| --- | --- |
| `validar_usuario()` | interrompe a requisição quando o usuário original não existe |
| `generos_preferidos()` | conta gêneros presentes nas avaliações positivas |
| `lista_usuarios()` | transforma usuários em objetos adequados ao frontend |
| `usuarios_da_simulacao()` | combina metadados originais com a pessoa temporária |
| `serializar_exemplo()` | converte um caminho real no exemplo da página inicial |
| `montar_estado_simulacao()` | reúne perfil, histórico, similares e recomendações em uma resposta |

#### Rotas de consulta

| Método e rota | Retorno |
| --- | --- |
| `GET /api/estatisticas` | totais de usuários, filmes, avaliações e componentes |
| `GET /api/usuarios` | usuários originais e seus graus |
| `GET /api/filmes` | catálogo e quantidade de avaliações |
| `GET /api/usuarios/{id}/preferencias` | avaliações e gêneros do usuário |
| `GET /api/usuarios/{id}/similares` | Jaccard e filmes em comum |
| `GET /api/recomendacoes/{id}` | ranking, colaboradores e caminhos |
| `GET /api/grafo` | nós e arestas filtrados para o SVG |
| `GET /api/exemplo` | caminho real usado na explicação inicial |
| `GET /api/analise` | distribuições usadas nos gráficos descritivos |

`GET /api/grafo` aceita modos diferentes. O backend escolhe quais nós e arestas enviar; o frontend apenas define suas posições no SVG.

#### Rotas da simulação

| Método e rota | Ação |
| --- | --- |
| `GET /api/simulacao` | consulta o estado atual |
| `POST /api/simulacao/usuario` | limpa a simulação anterior e cria a pessoa temporária |
| `POST /api/simulacao/avaliacao` | impede duplicidade, grava a nota e recalcula os resultados |
| `POST /api/simulacao/restaurar` | recria a cópia do original e remove o perfil temporário |

Notas 1, 2 e 3 aparecem no histórico e no grafo, mas não entram nos conjuntos positivos. Notas 4 e 5 podem criar conexões para Jaccard e caminhos de recomendação.

## 5. Frontend

### `frontend/src/types.ts`

Centraliza os formatos esperados nas respostas da API. Por exemplo:

- `Stats`, `User` e `Movie`: dados gerais;
- `Preferences` e `SimilarUser`: informações de usuários;
- `Recommendation`, `Contributor` e `RecommendationPath`: resultado explicável;
- `GraphData`: nós, arestas e caminhos do SVG;
- `Example` e `Analysis`: dados da tela inicial;
- `SimulationState`: perfil, histórico e resultados temporários.

Esses tipos ajudam o compilador TypeScript, mas não substituem a validação do Pydantic no backend.

### `frontend/src/App.tsx`

`App` controla a tela ativa e os estados compartilhados. A função `request()` concentra as chamadas HTTP e transforma erros da API em mensagens exibidas na interface.

Principais funções:

| Função | Responsabilidade |
| --- | --- |
| `loadPageData()` | carrega estatísticas, usuários, filmes, análise e exemplo inicial |
| `generateRecommendations()` | solicita recomendações para um usuário original |
| `startSimulation()` | envia o nome e recebe o perfil temporário vazio |
| `applySimulation()` | registra uma avaliação e substitui o estado pelos resultados recalculados |
| `restoreSimulation()` | solicita a limpeza e redefine os controles locais |
| `selectUser()` | sincroniza o usuário escolhido entre telas |

Componentes definidos no arquivo:

| Componente | Tela ou responsabilidade |
| --- | --- |
| `Usuarios` | busca, avaliações, gêneros e pessoas semelhantes |
| `Recomendacoes` | ranking e detalhes dos caminhos |
| `Grafo` | controles dos recortes do grafo |
| `GraphView` | cálculo de posições e desenho SVG de nós e arestas |
| `Simulacao` | cadastro temporário, avaliações, resultados e grafo atualizado |

#### Atualização automática da simulação

Ao registrar uma avaliação, `applySimulation()` recebe do backend o histórico completo, os usuários semelhantes e as recomendações. Em seguida, o componente seleciona o próximo filme disponível e atualiza o contador usado para recarregar o grafo. Não existe uma etapa separada para “gerar” recomendações.

#### Visualização do grafo

`GraphView` recebe `GraphData` e escolhe um layout conforme o modo:

- vizinhança: usuário no centro e filmes ao redor;
- expandida ou caminho: partições em colunas;
- completa ou positiva: distribuição por forças com valores determinísticos.

Usuários são azuis e filmes são verdes. As arestas mostram notas, e as relações de um caminho selecionado recebem destaque. O `viewBox` do SVG permite adaptação a diferentes larguras de tela.

### `frontend/src/HomePage.tsx`

Organiza a introdução acadêmica em uma sequência: modelo bipartido, avaliações positivas, Jaccard, BFS, pontuação, exemplo real e acesso às outras telas. `BipartiteModel` desenha um exemplo conceitual; `ExampleGraph` usa valores obtidos da API; `Bars` apresenta os gráficos descritivos recolhidos.

### `frontend/src/style.css`

Define a paleta, tipografia, espaçamento, layouts, componentes de formulário, tabelas, SVGs e regras responsivas. As classes da simulação usam duas colunas em telas largas e uma coluna abaixo de 900 pixels.

## 6. Implementação de terminal

A aplicação web não importa os módulos abaixo, mas eles permanecem como parte dos estudos e experimentos do projeto:

| Arquivo | Responsabilidade |
| --- | --- |
| `src/grafo.py` | classe `GrafoBipartido`, operações de grafo, ranking e estatísticas |
| `src/recomendador.py` | estratégias BFS, cosseno, popularidade e híbrida; métricas de avaliação |
| `src/experimentos.py` | divisão treino/teste e comparação reproduzível das estratégias |
| `src/visualizacao.py` | geração opcional de imagens com NetworkX e Matplotlib |
| `main.py` | interface de linha de comando para análises, experimentos e gráficos |
| `gerar_dados.py` | atualização controlada do catálogo usado nos CSVs |
| `src/caminhos.py` | caminhos centralizados para dados, resultados e imagens |

Essa separação é importante: os resultados mostrados pelo frontend vêm de `src/cineconecta.py`, enquanto os módulos históricos permitem comparar outras estratégias pelo terminal.

## 7. Testes

- `tests/test_cineconecta.py` verifica o núcleo web, as rotas, os modos do grafo e a simulação sem alteração dos CSVs.
- `tests/test_sistema.py` verifica a implementação de terminal, as estratégias e as métricas.

O teste da simulação cria Gabriel Oliveira, registra avaliações positivas e uma nota 3, confirma a ausência de duplicidade, verifica que filmes avaliados não são recomendados e restaura o estado original.

## 8. Como acompanhar uma recomendação no código

Para estudar uma execução completa:

1. comece em `generateRecommendations()` ou `applySimulation()` no frontend;
2. localize a rota correspondente em `backend/api.py`;
3. siga a chamada para `recomendacoes()` em `src/cineconecta.py`;
4. acompanhe `caminhos_positivos()`, `positivos()` e `jaccard()`;
5. observe a montagem de `contribuidores`, `caminhos` e `pontuacao`;
6. retorne ao componente React que apresenta a resposta;
7. abra `GraphView` para verificar como o caminho é desenhado.

Esse percurso cobre o fluxo principal do CineConecta sem envolver os módulos históricos do terminal.
