"""Grafo bipartido usuario-item com lista de adjacencia (implementado do zero)."""
from collections import deque


class GrafoBipartido:
    def __init__(self):
        self.adj = {}      # vertice -> {vizinho: nota}
        self.tipo = {}     # vertice -> 'U' (usuario) ou 'I' (item)
        self.genero = {}   # item -> genero

    # ---------- construcao ----------
    def add_aresta(self, usuario, item, nota=1):
        for v, t in ((usuario, "U"), (item, "I")):
            if v not in self.adj:
                self.adj[v] = {}
                self.tipo[v] = t
            elif self.tipo[v] != t:
                raise ValueError(f"'{v}' ja existe como tipo {self.tipo[v]}")
        self.adj[usuario][item] = nota
        self.adj[item][usuario] = nota

    def remove_aresta(self, usuario, item):
        self.adj[usuario].pop(item, None)
        self.adj[item].pop(usuario, None)

    def usuarios(self):
        return [v for v, t in self.tipo.items() if t == "U"]

    def itens(self):
        return [v for v, t in self.tipo.items() if t == "I"]

    def num_arestas(self):
        return sum(len(self.adj[u]) for u in self.usuarios())

    # ---------- grau e vizinhanca ----------
    def grau(self, v):
        return len(self.adj[v])

    def vizinhos(self, v):
        return set(self.adj[v])

    def vizinhanca_2(self, u):
        """Usuarios a distancia 2 de u (compartilham ao menos 1 item)."""
        res = set()
        for i in self.adj[u]:
            res |= self.adj[i].keys()
        res.discard(u)
        return res

    def jaccard(self, u1, u2):
        a, b = self.vizinhos(u1), self.vizinhos(u2)
        uniao = a | b
        return len(a & b) / len(uniao) if uniao else 0.0

    # ---------- BFS, caminhos, conectividade ----------
    def bfs(self, origem, limite=None):
        """Retorna (dist, pai). Se 'limite' for dado, nao expande alem dele."""
        dist, pai = {origem: 0}, {origem: None}
        fila = deque([origem])
        while fila:
            v = fila.popleft()
            if limite is not None and dist[v] >= limite:
                continue
            for w in self.adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    pai[w] = v
                    fila.append(w)
        return dist, pai

    def caminho_minimo(self, a, b):
        dist, pai = self.bfs(a)
        if b not in dist:
            return None
        caminho, v = [], b
        while v is not None:
            caminho.append(v)
            v = pai[v]
        return caminho[::-1]

    def componentes_conexas(self):
        visitado, comps = set(), []
        for v in self.adj:
            if v not in visitado:
                dist, _ = self.bfs(v)
                visitado |= dist.keys()
                comps.append(set(dist))
        return sorted(comps, key=len, reverse=True)

    def eh_bipartido(self):
        """Verifica por 2-coloracao com BFS (todas as arestas ligam U a I)."""
        cor = {}
        for s in self.adj:
            if s in cor:
                continue
            cor[s] = 0
            fila = deque([s])
            while fila:
                v = fila.popleft()
                for w in self.adj[v]:
                    if w not in cor:
                        cor[w] = 1 - cor[v]
                        fila.append(w)
                    elif cor[w] == cor[v]:
                        return False
        return True

    def diametro_componente(self, comp):
        """Maior menor-distancia entre dois vertices da componente (BFS de cada vertice)."""
        return max(max(self.bfs(v)[0].values()) for v in comp)

    # ---------- notas e ranking ----------
    def nota_media(self, item):
        notas = self.adj[item].values()
        if not notas:
            return 0.0
        return sum(notas) / len(notas)

    def ranking(self, metodo="bayes", genero=None, m=4):
        """Ranking dos filmes. metodos:
        'media'  -> nota media simples
        'grau'   -> popularidade (qtd de avaliacoes)
        'bayes'  -> media ponderada: (v*R + m*C)/(v+m), onde v = grau do filme,
                    R = media do filme, C = media global, m = peso do prior.
                    Evita que um filme com 1 nota 5 fique em 1o lugar."""
        itens = [i for i in self.itens() if genero is None or self.genero.get(i) == genero]
        total = self.num_arestas()
        if not total:
            return []
        C = sum(nt for i in self.itens() for nt in self.adj[i].values()) / total
        def chave(i):
            v, R = self.grau(i), self.nota_media(i)
            if metodo == "media": return R
            if metodo == "grau": return v
            return (v * R + m * C) / (v + m)
        return sorted(((i, chave(i)) for i in itens), key=lambda x: (-x[1], x[0]))
