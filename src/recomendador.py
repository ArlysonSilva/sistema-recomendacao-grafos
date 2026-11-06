"""Recomendadores e métricas da interface acadêmica de linha de comando.

O módulo preserva as estratégias históricas por BFS, cosseno, popularidade e
combinação híbrida. A aplicação web usa o fluxo mais direto de ``cineconecta``.
"""
from collections import defaultdict
from math import log2, sqrt
import random


PESO_BFS = 0.40
PESO_COSSENO = 0.40
PESO_POPULARIDADE = 0.20
PESO_DIVERSIDADE = 0.08


def recomendar_bfs(g, usuario, n=5, nota_minima=4):
    """Pontua candidatos U-I-U-I e informa o usuário que mais contribuiu."""
    if usuario not in g.adj:
        return []
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


def similaridade_cosseno(g, usuario_a, usuario_b, centralizar=False):
    """Cosseno das notas, opcionalmente centralizadas pela média do usuário."""
    if usuario_a not in g.adj or usuario_b not in g.adj:
        return 0.0
    filmes = g.itens()
    media_a = sum(g.adj[usuario_a].values()) / len(g.adj[usuario_a]) if g.adj[usuario_a] else 0
    media_b = sum(g.adj[usuario_b].values()) / len(g.adj[usuario_b]) if g.adj[usuario_b] else 0
    notas_a = [((g.adj[usuario_a].get(filme, 0) - media_a) if filme in g.adj[usuario_a] else 0)
               if centralizar else g.adj[usuario_a].get(filme, 0) for filme in filmes]
    notas_b = [((g.adj[usuario_b].get(filme, 0) - media_b) if filme in g.adj[usuario_b] else 0)
               if centralizar else g.adj[usuario_b].get(filme, 0) for filme in filmes]
    produto = sum(a * b for a, b in zip(notas_a, notas_b))
    norma_a = sqrt(sum(nota * nota for nota in notas_a))
    norma_b = sqrt(sum(nota * nota for nota in notas_b))
    if not norma_a or not norma_b:
        return 0.0
    limite_inferior = -1.0 if centralizar else 0.0
    return max(limite_inferior, min(1.0, produto / (norma_a * norma_b)))


def _normalizar(valores):
    maior = max(valores.values(), default=0.0)
    if maior <= 0:
        return {chave: 0.0 for chave in valores}
    return {chave: valor / maior for chave, valor in valores.items()}


def recomendar_cosseno(g, usuario, n=5, nota_minima=4, centralizar=False):
    """Ordena filmes novos pela soma de similaridade vezes nota normalizada."""
    if usuario not in g.adj:
        avaliados = set()
    else:
        avaliados = g.vizinhos(usuario)
    scores, contribuicoes = defaultdict(float), {}
    for outro in g.usuarios():
        if outro == usuario:
            continue
        similaridade = similaridade_cosseno(g, usuario, outro, centralizar)
        if similaridade <= 0:
            continue
        for filme, nota in g.adj[outro].items():
            if filme in avaliados or nota < nota_minima:
                continue
            scores[filme] += similaridade * (nota / 5)
            atual = contribuicoes.get(filme, (0.0, None, None))
            if (similaridade, outro) > (atual[0], atual[1] or ""):
                contribuicoes[filme] = (similaridade, outro, nota)
    return [(filme, score, contribuicoes[filme][1])
            for filme, score in sorted(scores.items(), key=lambda par: (-par[1], par[0]))[:n]]


def recomendar_hibrido(g, usuario, n=5, nota_minima=4, pesos=None, centralizar=False):
    """Combina BFS, cosseno e popularidade normalizados no intervalo [0, 1]."""
    avaliados = g.vizinhos(usuario) if usuario in g.adj else set()
    bfs = {filme: score for filme, score, _ in recomendar_bfs(g, usuario, len(g.itens()), nota_minima)}
    cosseno = {filme: score for filme, score, _ in recomendar_cosseno(
        g, usuario, len(g.itens()), nota_minima, centralizar)}
    popularidade = {filme: float(g.grau(filme)) for filme in g.itens() if filme not in avaliados}
    bfs_n, cos_n, pop_n = _normalizar(bfs), _normalizar(cosseno), _normalizar(popularidade)
    pesos = pesos or (PESO_BFS, PESO_COSSENO, PESO_POPULARIDADE)
    if len(pesos) != 3 or any(peso < 0 for peso in pesos) or sum(pesos) <= 0:
        raise ValueError("Os pesos devem ser três valores não negativos com soma maior que zero.")
    peso_bfs, peso_cos, peso_pop = (peso / sum(pesos) for peso in pesos)
    candidatos = (set(bfs_n) | set(cos_n) | set(pop_n)) - avaliados
    recs = []
    contrib_bfs = {filme: usuario_vizinho for filme, _, usuario_vizinho in
                   recomendar_bfs(g, usuario, len(g.itens()), nota_minima)}
    for filme in candidatos:
        score_bfs, score_cos, score_pop = bfs_n.get(filme, 0.0), cos_n.get(filme, 0.0), pop_n.get(filme, 0.0)
        score_final = peso_bfs * score_bfs + peso_cos * score_cos + peso_pop * score_pop
        contrib = contrib_bfs.get(filme)
        nota_contrib = g.adj[contrib][filme] if contrib else None
        if not contrib:
            cos_contrib = [(similaridade_cosseno(g, u, usuario, centralizar), u, g.adj[u][filme])
                           for u in g.usuarios() if u != usuario and filme in g.adj[u]
                           and g.adj[u][filme] >= nota_minima]
            if cos_contrib:
                _, contrib, nota_contrib = max(cos_contrib, key=lambda item: (item[0], item[1]))
        similaridade_contrib = (similaridade_cosseno(g, usuario, contrib, centralizar)
                                if contrib and usuario in g.adj else None)
        recs.append({"filme": filme, "score": score_final, "score_bfs": score_bfs,
                     "similaridade": similaridade_contrib, "score_cosseno": score_cos,
                     "popularidade": score_pop,
                     "genero": g.genero.get(filme), "usuario_colaborador": contrib,
                     "nota_colaborador": nota_contrib,
                     "motivo": _motivo(score_bfs, score_cos, contrib, nota_contrib,
                                       similaridade_contrib)})
    return sorted(recs, key=lambda item: (-item["score"], item["filme"]))[:n]


def recomendar_estrategia(g, usuario, algoritmo="hibrido", n=5, pesos=None,
                          diversidade=0.0, centralizar=False):
    """Interface única para os quatro métodos, com dados explicáveis."""
    algoritmo = algoritmo.lower()
    if diversidade < 0:
        raise ValueError("A penalização de diversidade não pode ser negativa.")
    avaliados = g.vizinhos(usuario) if usuario in g.adj else set()
    limite_candidatos = len(g.itens()) if diversidade > 0 else n
    if algoritmo == "bfs":
        base = recomendar_bfs(g, usuario, limite_candidatos)
        recomendacoes = [{"filme": filme, "score": score, "score_bfs": score,
                          "similaridade": None, "score_cosseno": None, "popularidade": None,
                          "usuario_colaborador": colaborador,
                          "nota_colaborador": g.adj[colaborador][filme],
                          "genero": g.genero.get(filme), "algoritmo": "bfs",
                          "motivo": f"{colaborador} avaliou o filme positivamente e foi alcançado pela BFS."}
                         for filme, score, colaborador in base]
    elif algoritmo == "cosseno":
        base = recomendar_cosseno(g, usuario, limite_candidatos, centralizar=centralizar)
        recomendacoes = [{"filme": filme, "score": score, "score_bfs": None,
                          "similaridade": similaridade_cosseno(g, usuario, colaborador, centralizar),
                          "score_cosseno": score, "popularidade": None,
                          "usuario_colaborador": colaborador,
                          "nota_colaborador": g.adj[colaborador][filme],
                          "genero": g.genero.get(filme), "algoritmo": "cosseno",
                          "motivo": f"Avaliações semelhantes contribuíram para este filme via cosseno."}
                         for filme, score, colaborador in base]
    elif algoritmo == "popularidade":
        base = mais_populares(g, avaliados, limite_candidatos)
        recomendacoes = [{"filme": filme, "score": g.grau(filme), "score_bfs": None,
                          "similaridade": None, "score_cosseno": None,
                          "popularidade": g.grau(filme),
                          "usuario_colaborador": None, "nota_colaborador": None,
                          "genero": g.genero.get(filme), "algoritmo": "popularidade",
                          "motivo": f"O filme recebeu {g.grau(filme)} avaliações."}
                         for filme in base]
    elif algoritmo == "hibrido":
        recomendacoes = recomendar_hibrido(g, usuario, limite_candidatos,
                                            pesos=pesos, centralizar=centralizar)
        for item in recomendacoes:
            item["algoritmo"] = "hibrido"
    else:
        raise ValueError("Algoritmo deve ser bfs, cosseno, hibrido ou popularidade.")
    if not recomendacoes and algoritmo != "popularidade":
        recomendacoes = [{"filme": filme, "score": g.grau(filme), "score_bfs": None,
                          "similaridade": None, "score_cosseno": None,
                          "popularidade": g.grau(filme), "usuario_colaborador": None,
                          "nota_colaborador": None, "genero": g.genero.get(filme),
                          "algoritmo": "popularidade (fallback)",
                          "motivo": "Sem candidatos personalizados; sugerido por popularidade."}
                         for filme in mais_populares(g, avaliados, limite_candidatos)]
    if algoritmo != "hibrido" and recomendacoes:
        scores_normalizados = _normalizar({item["filme"]: item["score"] for item in recomendacoes})
        for item in recomendacoes:
            score_original = item["score"]
            item["score_original"] = score_original
            item["score"] = scores_normalizados[item["filme"]]
            if item["algoritmo"] == "bfs":
                item["score_bfs"] = item["score"]
            elif item["algoritmo"] == "cosseno":
                item["score_cosseno"] = item["score"]
            elif "popularidade" in item and item["popularidade"] is not None:
                item["popularidade_avaliacoes"] = int(item["popularidade"])
                item["popularidade"] = item["score"]
    if diversidade > 0:
        recomendacoes = diversificar_recomendacoes(recomendacoes, g, peso=diversidade, n=n)
    return recomendacoes


def _motivo(score_bfs, score_cos, colaborador, nota, similaridade=None):
    if colaborador and nota is not None and (score_bfs > 0 or score_cos > 0):
        if similaridade is not None and similaridade > 0:
            return (f"{colaborador} tem similaridade de cosseno {similaridade:.2f} "
                    f"e avaliou este filme com nota {nota}.")
        return f"A busca em largura encontrou {colaborador}, que avaliou este filme com nota {nota}."
    return "O filme recebeu pontuação pela popularidade entre as avaliações disponíveis."


def diversificar_recomendacoes(recomendacoes, g, peso=PESO_DIVERSIDADE, n=5):
    """Reordena gulosa e levemente, penalizando gêneros repetidos já escolhidos."""
    restantes, escolhidas, contagem = list(recomendacoes), [], defaultdict(int)
    while restantes and len(escolhidas) < n:
        def chave(item):
            genero = item.get("genero") or g.genero.get(item["filme"])
            penalidade = peso * contagem[genero] if genero else 0.0
            return (-(item["score"] - penalidade), -item["score"], item["filme"])
        selecionado = min(restantes, key=chave)
        restantes.remove(selecionado)
        selecionado = dict(selecionado)
        selecionado["score_diversificado"] = max(0.0, selecionado["score"] - peso * contagem[selecionado.get("genero")])
        escolhidas.append(selecionado)
        if selecionado.get("genero"):
            contagem[selecionado["genero"]] += 1
    return escolhidas


def precision_at_k(recomendados, relevantes, k=5):
    return len(set(recomendados[:k]) & set(relevantes)) / k if k > 0 else 0.0


def recall_at_k(recomendados, relevantes, k=5):
    return len(set(recomendados[:k]) & set(relevantes)) / len(relevantes) if relevantes else 0.0


def ndcg_at_k(recomendados, relevantes, k=5):
    if k <= 0 or not relevantes:
        return 0.0
    relevantes = set(relevantes)
    dcg = sum((1.0 / log2(posicao + 2)) for posicao, filme in enumerate(recomendados[:k])
              if filme in relevantes)
    ideal = sum(1.0 / log2(posicao + 2) for posicao in range(min(k, len(relevantes))))
    return dcg / ideal if ideal else 0.0


def avaliar_algoritmos(g, k=5, seed=42, fracao_teste=0.2, nota_minima=4):
    """Holdout positivo determinístico por usuário; algoritmos recebem só o treino."""
    rng = random.Random(seed)
    treino = type(g)()
    ocultas = defaultdict(set)
    for usuario in g.usuarios():
        positivas = sorted((filme, nota) for filme, nota in g.adj[usuario].items() if nota >= nota_minima)
        quantidade = max(1, round(len(positivas) * fracao_teste)) if positivas else 0
        quantidade = min(quantidade, len(positivas))
        selecionadas = set(rng.sample([filme for filme, _ in positivas], quantidade)) if quantidade else set()
        ocultas[usuario] = selecionadas
        for filme, nota in g.adj[usuario].items():
            if filme not in selecionadas:
                treino.add_aresta(usuario, filme, nota)
    treino.genero.update(g.genero)
    metodos = {"BFS": recomendar_bfs, "Cosseno": recomendar_cosseno,
               "Hibrido": recomendar_hibrido, "Popularidade": None}
    somas = {nome: [0.0, 0.0, 0.0] for nome in metodos}
    usuarios_avaliados = 0
    for usuario, relevantes in ocultas.items():
        if not relevantes:
            continue
        usuarios_avaliados += 1
        for nome, funcao in metodos.items():
            if nome == "Popularidade":
                recomendados = mais_populares(treino, treino.vizinhos(usuario) if usuario in treino.adj else (), k)
            else:
                resultado = funcao(treino, usuario, k)
                recomendados = [item["filme"] for item in resultado] if nome == "Hibrido" else [item[0] for item in resultado]
            valores = (precision_at_k(recomendados, relevantes, k),
                       recall_at_k(recomendados, relevantes, k), ndcg_at_k(recomendados, relevantes, k))
            somas[nome] = [a + b for a, b in zip(somas[nome], valores)]
    if not usuarios_avaliados:
        return {nome: (0.0, 0.0, 0.0) for nome in metodos}
    return {nome: tuple(valor / usuarios_avaliados for valor in valores)
            for nome, valores in somas.items()}


def recomendar(g, usuario, n=5):
    """BFS; se nao houver candidatos (cold start / componente isolada) usa popularidade."""
    rec = recomendar_bfs(g, usuario, n)
    if rec:
        return [(i, s) for i, s, _ in rec], "grafo (BFS)"
    avaliados = g.vizinhos(usuario) if usuario in g.adj else set()
    return [(i, g.grau(i)) for i in mais_populares(g, avaliados, n)], "popularidade (fallback)"


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
