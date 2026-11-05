"""Visualizacoes do grafo bipartido (requer networkx e matplotlib).
 1) layout_ponderado : forca de atracao proporcional a nota -> notas altas aproximam
 2) layout_genero    : filmes agrupados por genero; usuarios no centroide das suas notas
 3) ranking          : barras com o ranking bayesiano, colorido por genero"""
import math
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

CORES = {"Ficcao": "#4C9BE8", "Terror": "#D6455D", "Romance": "#E88FB4",
         "Animacao": "#F2B134", "Documentario": "#6BAF6B"}
COR_NOTA = {1: "#bbbbbb", 2: "#bbbbbb", 3: "#999999", 4: "#555555", 5: "#000000"}


def _grafo_nx(g):
    G = nx.Graph()
    for u in g.usuarios():
        for i, n in g.adj[u].items():
            G.add_edge(u, i, nota=n, weight=(n / 5) ** 3)   # nota 5 -> 1.0 ; nota 2 -> 0.06
    return G


def _usuario_dominante(g, u):
    """Genero em que o usuario tem maior soma de notas (para colorir)."""
    soma = {}
    for i, n in g.adj[u].items():
        soma[g.genero.get(i)] = soma.get(g.genero.get(i), 0) + n
    return max(soma, key=soma.get)


def _legenda(ax):
    h = [Line2D([], [], marker="s", ls="", color=c, label=f"Filme: {k}") for k, c in CORES.items()]
    h += [Line2D([], [], marker="o", ls="", color="#888", label="Usuario (cor = genero dominante)")]
    ax.legend(handles=h, loc="lower left", fontsize=8)


def _desenhar(g, G, pos, titulo, saida, rotulos_usuarios=False):
    fig, ax = plt.subplots(figsize=(14, 10))
    for n in (1, 2, 3, 4, 5):
        arestas = [(a, b) for a, b, d in G.edges(data=True) if d["nota"] == n]
        nx.draw_networkx_edges(G, pos, edgelist=arestas, width=0.4 + 0.5 * n,
                               edge_color=COR_NOTA[n], alpha=0.15 + 0.12 * n, ax=ax)
    us, its = g.usuarios(), g.itens()
    nx.draw_networkx_nodes(G, pos, nodelist=us, node_size=130, node_shape="o",
                           node_color=[CORES[_usuario_dominante(g, u)] for u in us],
                           edgecolors="black", linewidths=0.6, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=its, node_shape="s",
                           node_size=[150 + 45 * g.grau(i) for i in its],
                           node_color=[CORES[g.genero[i]] for i in its],
                           edgecolors="black", linewidths=1.2, ax=ax)
    nx.draw_networkx_labels(G, pos, {i: i for i in its}, font_size=7, ax=ax)
    if rotulos_usuarios:
        nx.draw_networkx_labels(G, pos, {u: u[-2:] for u in us}, font_size=6, ax=ax)
    _legenda(ax)
    ax.set_title(titulo + "\n(espessura/escuro da aresta = nota; tamanho do filme = nº de avaliacoes)")
    ax.axis("off"); fig.tight_layout(); fig.savefig(saida, dpi=130); plt.close(fig)
    print("Imagem salva em", saida)


def layout_ponderado(g, saida="grafo_ponderado.png"):
    G = _grafo_nx(g)
    pos = nx.spring_layout(G, weight="weight", seed=3, k=0.7, iterations=300)
    _desenhar(g, G, pos, "Layout ponderado pelas notas", saida)


def layout_genero(g, saida="grafo_generos.png"):
    G = _grafo_nx(g)
    generos = sorted(set(g.genero.values()))
    centros = {}
    for k, gen in enumerate(generos):
        ang = 2 * math.pi * k / len(generos) + 0.4
        centros[gen] = (4.2 * math.cos(ang), 4.2 * math.sin(ang))
    pos = {}
    for gen in generos:
        its = sorted(i for i in g.itens() if g.genero[i] == gen)
        for k, i in enumerate(its):
            a = 2 * math.pi * k / len(its)
            r = 0.9 if len(its) > 2 else 0.4
            pos[i] = (centros[gen][0] + r * math.cos(a), centros[gen][1] + r * math.sin(a))
    for u in g.usuarios():                      # centroide ponderado por nota^2
        pesos = {i: n ** 2 for i, n in g.adj[u].items()}
        tot = sum(pesos.values())
        x = sum(pos[i][0] * w for i, w in pesos.items()) / tot
        y = sum(pos[i][1] * w for i, w in pesos.items()) / tot
        pos[u] = (x + 0.12 * math.cos(hash(u) % 7), y + 0.12 * math.sin(hash(u) % 7))
    _desenhar(g, G, pos, "Layout por genero (usuarios no centroide das suas notas)", saida, True)


def ranking(g, saida="ranking.png", top=15):
    r = g.ranking("bayes")[:top][::-1]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh([i for i, _ in r], [s for _, s in r], color=[CORES[g.genero[i]] for i, _ in r], edgecolor="black")
    for k, (i, s) in enumerate(r):
        ax.text(s + 0.02, k, f"{s:.2f}  ({g.grau(i)} aval.)", va="center", fontsize=8)
    ax.set_xlim(0, 5.6); ax.set_xlabel("Media bayesiana (nota ponderada pela qtd. de avaliacoes)")
    ax.set_title(f"Ranking dos {top} melhores filmes")
    ax.legend(handles=[Line2D([], [], marker="s", ls="", color=c, label=k) for k, c in CORES.items()], loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(saida, dpi=130); plt.close(fig)
    print("Imagem salva em", saida)


def desenhar(g):
    layout_ponderado(g); layout_genero(g); ranking(g)
