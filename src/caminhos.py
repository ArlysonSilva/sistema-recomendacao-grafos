"""Caminhos do projeto, independentes do diretório de execução."""
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ_PROJETO / "dados"
ARQUIVO_AVALIACOES = PASTA_DADOS / "avaliacoes.csv"
ARQUIVO_FILMES = PASTA_DADOS / "filmes.csv"
PASTA_OUTPUTS = RAIZ_PROJETO / "outputs"
GRAFO_PNG = PASTA_OUTPUTS / "grafo.png"
GRAFO_GENEROS_PNG = PASTA_OUTPUTS / "grafo_generos.png"
GRAFO_PONDERADO_PNG = PASTA_OUTPUTS / "grafo_ponderado.png"
RANKING_PNG = PASTA_OUTPUTS / "ranking.png"
SAIDA_EXECUCAO = RAIZ_PROJETO / "docs" / "saida_execucao.txt"
