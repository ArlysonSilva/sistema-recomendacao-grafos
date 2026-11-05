# Sistema de Recomendação de Filmes com Grafos Bipartidos

Trabalho de Teoria dos Grafos. Usuários e filmes são vértices de um grafo bipartido; uma aresta
(usuário, filme) representa "o usuário avaliou o filme". As recomendações saem de caminhos de
tamanho 3 encontrados por BFS.

## Como executar
```bash
python3 gerar_dados.py          # opcional: regenera dados/avaliacoes.csv
python3 main.py                 # estatísticas + recomendações + avaliação
python3 main.py --plot          # também salva grafo.png (precisa de networkx e matplotlib)
```
O núcleo (`grafo.py`, `recomendador.py`) usa apenas a biblioteca padrão; o NetworkX só é usado para desenhar.

## Arquivos
| Arquivo | Conteúdo |
|---|---|
| `grafo.py` | Classe `GrafoBipartido`: grau, vizinhança, Jaccard, BFS, caminho mínimo, componentes, teste de bipartição |
| `recomendador.py` | Recomendação por BFS, fallback por popularidade, avaliação leave-one-out |
| `main.py` | Programa principal |
| `visualizacao.py` | Desenho do grafo |
| `gerar_dados.py` | Gera o dataset sintético |
| `relatorio.md` | Relatório do trabalho |
