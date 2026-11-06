"""Avaliação reproduzível dos recomendadores da interface de linha de comando.

Todos os cenários usam a mesma divisão de treino e teste para que as métricas
possam ser comparadas sem alterar o grafo recebido.
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

from .recomendador import (
    diversificar_recomendacoes, ndcg_at_k, precision_at_k, recall_at_k,
    recomendar_bfs, recomendar_cosseno, recomendar_hibrido, mais_populares,
)

CONFIGURACOES_PESOS = {
    "40-40-20": (0.40, 0.40, 0.20),
    "50-30-20": (0.50, 0.30, 0.20),
    "30-50-20": (0.30, 0.50, 0.20),
    "30-40-30": (0.30, 0.40, 0.30),
    "50-40-10": (0.50, 0.40, 0.10),
}


def criar_divisao(grafo, seed=42, fracao_teste=0.2, nota_minima=4):
    """Cria um grafo de treino e itens relevantes ocultos, sem alterar a origem."""
    rng = random.Random(seed)
    treino = type(grafo)()
    teste = defaultdict(set)
    for usuario in grafo.usuarios():
        positivos = sorted(filme for filme, nota in grafo.adj[usuario].items()
                           if nota >= nota_minima)
        quantidade = min(len(positivos), max(1, round(len(positivos) * fracao_teste))) if positivos else 0
        ocultos = set(rng.sample(positivos, quantidade)) if quantidade else set()
        teste[usuario] = ocultos
        for filme, nota in grafo.adj[usuario].items():
            if filme not in ocultos:
                treino.add_aresta(usuario, filme, nota)
    treino.genero.update(grafo.genero)
    return treino, dict(teste)


def _recomendar(grafo, usuario, algoritmo, k, pesos=None, centralizar=False,
                 diversidade=0.0):
    avaliados = grafo.vizinhos(usuario) if usuario in grafo.adj else set()
    if algoritmo == "BFS":
        itens = [filme for filme, _, _ in recomendar_bfs(grafo, usuario, k)]
    elif algoritmo == "Cosseno":
        itens = [filme for filme, _, _ in recomendar_cosseno(
            grafo, usuario, k, centralizar=centralizar)]
    elif algoritmo == "Popularidade":
        itens = mais_populares(grafo, avaliados, k)
    else:
        recomendacoes = recomendar_hibrido(grafo, usuario, len(grafo.itens()),
                                           pesos=pesos, centralizar=centralizar)
        if diversidade:
            recomendacoes = diversificar_recomendacoes(recomendacoes, grafo, diversidade,
                                                       len(grafo.itens()))
        itens = [item["filme"] for item in recomendacoes[:k]]
    return [filme for filme in itens if filme not in avaliados]


def avaliar_divisao(treino, teste, algoritmo, k=5, pesos=None,
                    centralizar=False, diversidade=0.0):
    """Métricas macro e métricas individuais para uma divisão já definida."""
    individuais = {}
    for usuario, relevantes in teste.items():
        if not relevantes:
            continue
        recomendados = _recomendar(treino, usuario, algoritmo, k, pesos,
                                   centralizar, diversidade)
        individuais[usuario] = {
            "Precision@K": precision_at_k(recomendados, relevantes, k),
            "Recall@K": recall_at_k(recomendados, relevantes, k),
            "NDCG@K": ndcg_at_k(recomendados, relevantes, k),
        }
    if not individuais:
        return {"Precision@K": 0.0, "Recall@K": 0.0, "NDCG@K": 0.0}, individuais
    medias = {chave: sum(m[chave] for m in individuais.values()) / len(individuais)
              for chave in ("Precision@K", "Recall@K", "NDCG@K")}
    return medias, individuais


def executar_experimentos(grafo, saida_csv, k=5, seed=42):
    """Compara algoritmos, centralização, pesos e diversidade no mesmo holdout."""
    treino, teste = criar_divisao(grafo, seed=seed)
    cenarios = [
        ("BFS", "padrao", "BFS", None, False, 0.0),
        ("Cosseno", "original", "Cosseno", None, False, 0.0),
        ("Cosseno", "centralizado", "Cosseno", None, True, 0.0),
        ("Popularidade", "padrao", "Popularidade", None, False, 0.0),
    ]
    for nome, pesos in CONFIGURACOES_PESOS.items():
        for diversidade in (0.0, 0.08):
            cenario = f"pesos-{nome};diversidade-{diversidade:.2f}"
            cenarios.append(("Hibrido", cenario, "Hibrido", pesos, False, diversidade))

    linhas = []
    for metodo, config, algoritmo, pesos, centralizar, diversidade in cenarios:
        medias, individuais = avaliar_divisao(treino, teste, algoritmo, k,
                                               pesos, centralizar, diversidade)
        linhas.append({"tipo": "macro", "usuario": "", "algoritmo": metodo,
                       "configuracao": config, **medias})
        for usuario, metricas in individuais.items():
            linhas.append({"tipo": "usuario", "usuario": usuario,
                           "algoritmo": metodo, "configuracao": config, **metricas})

    destino = Path(saida_csv)
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = ["tipo", "usuario", "algoritmo", "configuracao",
              "Precision@K", "Recall@K", "NDCG@K"]
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)
    return [linha for linha in linhas if linha["tipo"] == "macro"]
