"""Recomendacao baseada em caminhos usuario -> item -> usuario -> item (BFS ate dist. 3)."""
from collections import defaultdict


def recomendar_bfs(g, usuario, n=5, nota_minima=4):
    """Retorna lista de (item, pontuacao, usuario_que_mais_contribuiu)."""
    dist, _ = g.bfs(usuario, limite=3)
    vizinhos_u = [v for v, d in dist.items() if d == 2]   # usuarios parecidos
    score = defaultdict(float)
    melhor = {}                                           # item -> (sim, usuario)
    for v in vizinhos_u:
        sim = g.jaccard(usuario, v)
        for item, nota in g.adj[v].items():
            if dist.get(item) == 3 and nota >= nota_minima:   # item novo para 'usuario'
                score[item] += sim * (nota / 5)
                if sim > melhor.get(item, (0, None))[0]:
                    melhor[item] = (sim, v)
    ranking = sorted(score.items(), key=lambda x: (-x[1], x[0]))[:n]
    return [(i, s, melhor[i][1]) for i, s in ranking]


def mais_populares(g, excluir=(), n=5):
    """Fallback para cold start: itens de maior grau."""
    itens = [i for i in g.itens() if i not in excluir]
    return sorted(itens, key=lambda i: (-g.grau(i), i))[:n]


def recomendar(g, usuario, n=5):
    """BFS; se nao houver candidatos (cold start / componente isolada) usa popularidade."""
    rec = recomendar_bfs(g, usuario, n)
    if rec:
        return [(i, s) for i, s, _ in rec], "grafo (BFS)"
    return [(i, g.grau(i)) for i in mais_populares(g, g.vizinhos(usuario), n)], "popularidade (fallback)"


def avaliar_leave_one_out(g, n=5, nota_minima=4, usar_grafo=True):
    """Para cada usuario com >=3 itens: esconde 1 item bem avaliado e verifica
    se ele aparece no top-n. Retorna hit rate."""
    acertos = total = 0
    for u in g.usuarios():
        gostou = sorted(i for i, nota in g.adj[u].items() if nota >= nota_minima)
        if g.grau(u) < 3 or not gostou:
            continue
        alvo = gostou[0]
        nota = g.adj[u][alvo]
        g.remove_aresta(u, alvo)
        if usar_grafo:
            top = [i for i, _, _ in recomendar_bfs(g, u, n)]
        else:
            top = mais_populares(g, g.vizinhos(u), n)
        g.add_aresta(u, alvo, nota)                        # restaura
        acertos += alvo in top
        total += 1
    return acertos / total, total
