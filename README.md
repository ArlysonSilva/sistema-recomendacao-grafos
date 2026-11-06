# CineConecta

O CineConecta é um sistema de recomendação de filmes que utiliza grafos bipartidos para identificar relações entre usuários e descobrir novos filmes a partir de avaliações compartilhadas.

O projeto foi desenvolvido para estudo em Engenharia da Computação. Seu foco é tornar visíveis conceitos de Teoria dos Grafos — vértices, arestas, grau, componentes conexas, busca em largura e caminhos — em um recomendador explicável.

## Tecnologias

- Backend: Python 3.10+, FastAPI, Uvicorn e Pydantic.
- Frontend: React 18, TypeScript e Vite.
- Testes: pytest e HTTPX.
- Visualizações opcionais de terminal: NetworkX e Matplotlib.
- Dados: arquivos CSV versionados em `dados/`.

O núcleo do recomendador web e a visualização SVG do grafo são implementados no próprio projeto. NetworkX não participa da API nem do cálculo das recomendações.

## Estrutura de pastas

```text
backend/
  api.py              endpoints HTTP e estado temporário da simulação
dados/                usuários, filmes e avaliações em CSV
docs/
  ARQUITETURA.md      módulos e fluxo dos dados
  GUIA_DO_CODIGO.md   explicação dos arquivos, funções e componentes
frontend/
  src/App.tsx         navegação e coordenação das cinco telas
  src/HomePage.tsx    apresentação acadêmica da tela inicial
  src/types.ts        contratos de dados recebidos da API
  src/style.css       identidade visual e responsividade
src/
  cineconecta.py      grafo e recomendador usados pela aplicação web
  grafo.py            implementação acadêmica histórica usada pelo terminal
  recomendador.py     estratégias e métricas da interface de terminal
  experimentos.py     comparação reproduzível dos algoritmos históricos
  visualizacao.py     geração opcional de imagens
tests/                testes do núcleo, da API e dos algoritmos históricos
main.py               apresentação e experimentos em linha de comando
gerar_dados.py        catálogo e geração controlada dos CSVs
```

As duas implementações de grafo são preservadas porque atendem fluxos distintos. A aplicação web usa `GrafoFilmes`, em `src/cineconecta.py`. O terminal e seus experimentos anteriores usam `GrafoBipartido`, em `src/grafo.py`. A relação entre elas está detalhada em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

Para estudar a implementação arquivo por arquivo, consulte o [Guia do código](docs/GUIA_DO_CODIGO.md).

## Modelo do grafo bipartido

O grafo é composto por dois conjuntos disjuntos de vértices:

- **Usuários:** pessoas que atribuem notas.
- **Filmes:** títulos disponíveis no catálogo.

Uma avaliação cria uma aresta entre um usuário e um filme. A nota de 1 a 5 é armazenada como peso dessa aresta. A aplicação mantém uma lista de adjacência simétrica: a nota pode ser consultada a partir do usuário ou do filme.

```text
Usuário --(nota)--> Filme
```

Não existem arestas usuário–usuário nem filme–filme. O grau de um usuário indica quantos filmes ele avaliou; o grau de um filme indica quantas avaliações recebeu.

## Algoritmos da aplicação web

### Avaliações positivas

Notas 4 e 5 são positivas. Notas 1, 2 e 3 continuam armazenadas no grafo, mas não formam caminhos de recomendação nem conjuntos de interesse positivo.

### Similaridade de Jaccard

Cada usuário é representado pelo conjunto de filmes que avaliou positivamente. Para usuários `A` e `B`:

```text
J(A, B) = |A ∩ B| / |A ∪ B|
```

A interseção contém os filmes positivos em comum. A união contém todos os filmes avaliados positivamente por pelo menos um dos dois usuários. Jaccard mede sobreposição de preferências; não é a média das notas.

### Busca em largura (BFS)

A BFS percorre somente arestas positivas e enumera caminhos simples de três arestas:

```text
Usuário inicial → Filme compartilhado → Usuário semelhante → Filme candidato
```

O filme candidato é aceito somente quando ainda não foi avaliado pelo usuário inicial. Cada caminho é mantido no resultado para explicar a origem da recomendação.

### Pontuação

Um colaborador contribui uma vez para cada filme candidato. Sua nota recebe como peso a similaridade Jaccard com o usuário inicial:

```text
pontuação = Σ(nota do colaborador × Jaccard) / Σ(Jaccard)
```

O resultado é uma média ponderada das avaliações observadas no grafo. Os gêneros classificam o catálogo e ajudam nas análises visuais, mas não participam do Jaccard, da BFS ou dessa pontuação.

### Algoritmos históricos do terminal

`main.py` mantém, separadamente, estratégias de BFS, cosseno, popularidade e combinação híbrida, além de métricas e gráficos acadêmicos. Elas não alteram o resultado exibido pela API web. Essa separação evita confundir a pontuação atual da aplicação com os experimentos anteriores.

## Instalação e execução

### Backend

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.api:app --reload
```

A API ficará disponível em `http://localhost:8000`. A documentação interativa do FastAPI pode ser consultada em `http://localhost:8000/docs`.

### Frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. Por padrão, o frontend consulta `http://localhost:8000/api`. Para usar outro endereço, defina `VITE_API_URL` antes de iniciar o Vite.

### Testes e build

```powershell
# raiz do repositório
python -m pytest -q

# pasta frontend
npm run build
```

### Interface de terminal opcional

```powershell
python main.py
python main.py --experimentos
python main.py --plot
```

`--experimentos` atualiza o CSV comparativo em `outputs/`; `--plot` gera imagens estáticas. Para regenerar os dados, consulte `python gerar_dados.py --help` antes de executar, pois os CSVs são a base da aplicação.

## Como utilizar as telas

1. **Início:** percorra a explicação do modelo, Jaccard, BFS e pontuação. Os totais e o exemplo real vêm da API. Os gráficos descritivos permanecem recolhidos no final.
2. **Usuários:** selecione uma pessoa para consultar notas, gêneros preferidos e usuários com Jaccard positivo.
3. **Recomendações:** escolha um usuário, gere o ranking e abra um filme para ver colaboradores e caminhos explicativos.
4. **Grafo:** alterne entre grafo completo, vizinhança, avaliações positivas, vizinhança expandida e caminho de uma recomendação.
5. **Simulação:** cadastre uma pessoa temporária e registre avaliações. O grafo, os usuários semelhantes e as recomendações são recalculados após cada nota. Use “Ver caminho” para consultar a justificativa e “Restaurar” para apagar a simulação.

A simulação existe apenas na memória do backend. Reiniciar o servidor ou usar “Restaurar” descarta as alterações; os CSVs não são modificados.

## Limitações conhecidas

- A base é pequena e sintética; não representa o comportamento de uma plataforma real.
- O Jaccard considera apenas a presença de avaliações positivas, não a diferença entre notas 4 e 5.
- Usuários sem interesses positivos em comum não geram recomendações personalizadas pelo fluxo web.
- A BFS fica restrita às conexões existentes e pode reforçar grupos já conectados.
- A simulação é global ao processo, sem persistência, autenticação ou separação por sessão.
- A pontuação não é uma previsão de preferência futura e não usa os gêneros dos filmes.
- A aplicação não possui paginação; o volume atual permite carregar a base completa para exploração.
