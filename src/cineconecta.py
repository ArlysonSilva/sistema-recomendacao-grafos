"""Dados e recomendador do CineConecta. Algoritmos simples e implementados localmente."""
from __future__ import annotations

import csv
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados"
GENRES = ["Ação", "Aventura", "Animação", "Comédia", "Drama", "Romance", "Ficção científica", "Fantasia", "Terror", "Suspense", "Mistério", "Crime", "Documentário", "Musical", "Guerra"]


class GrafoFilmes:
    """Grafo bipartido: adjacência simétrica com nota como peso da aresta."""
    def __init__(self):
        self.adj: dict[str, dict[str, int]] = {}
        self.tipo: dict[str, str] = {}

    def add_vertice(self, ident: str, tipo: str) -> None:
        if tipo not in {"usuario", "filme"}:
            raise ValueError("Tipo de vértice deve ser usuario ou filme")
        if ident in self.tipo and self.tipo[ident] != tipo:
            raise ValueError(f"Tipo conflitante para {ident}")
        self.tipo[ident] = tipo
        self.adj.setdefault(ident, {})

    def add_avaliacao(self, usuario: str, filme: str, nota: int) -> None:
        if not 1 <= int(nota) <= 5:
            raise ValueError("A nota deve estar entre 1 e 5")
        self.add_vertice(usuario, "usuario")
        self.add_vertice(filme, "filme")
        self.adj[usuario][filme] = int(nota)
        self.adj[filme][usuario] = int(nota)

    def grau(self, ident: str) -> int:
        return len(self.adj.get(ident, {}))

    def vizinhos(self, ident: str) -> set[str]:
        return set(self.adj.get(ident, {}))

    def bfs(self, origem: str, max_distancia: int | None = None) -> tuple[dict[str, int], dict[str, str | None]]:
        dist = {origem: 0} if origem in self.adj else {}
        pai: dict[str, str | None] = {origem: None} if origem in self.adj else {}
        fila = deque(dist)
        while fila:
            atual = fila.popleft()
            if max_distancia is not None and dist[atual] >= max_distancia:
                continue
            for vizinho in self.adj[atual]:
                if vizinho not in dist:
                    dist[vizinho], pai[vizinho] = dist[atual] + 1, atual
                    fila.append(vizinho)
        return dist, pai

    def caminhos_positivos(self, origem: str, max_distancia: int = 3) -> list[list[str]]:
        """Enumera com BFS caminhos simples formados apenas por notas >= 4."""
        if origem not in self.adj:
            return []
        fila = deque([[origem]])
        caminhos = []
        while fila:
            caminho = fila.popleft()
            if len(caminho) - 1 == max_distancia:
                if self.tipo[caminho[-1]] == "filme":
                    caminhos.append(caminho)
                continue
            atual = caminho[-1]
            for vizinho, nota in self.adj[atual].items():
                if nota >= 4 and vizinho not in caminho:
                    fila.append(caminho + [vizinho])
        return caminhos

    def caminho_minimo(self, inicio: str, fim: str) -> list[str] | None:
        dist, pai = self.bfs(inicio)
        if fim not in dist:
            return None
        caminho, atual = [], fim
        while atual is not None:
            caminho.append(atual)
            atual = pai[atual]
        return caminho[::-1]

    def componentes(self) -> list[set[str]]:
        restantes, resultado = set(self.adj), []
        while restantes:
            origem = next(iter(restantes))
            visitados, _ = self.bfs(origem)
            resultado.append(set(visitados))
            restantes.difference_update(visitados)
        return sorted(resultado, key=len, reverse=True)

    def eh_bipartido(self) -> bool:
        return all(self.tipo[a] != self.tipo[b] for a, viz in self.adj.items() for b in viz)

    def positivos(self, usuario: str) -> set[str]:
        return {f for f, nota in self.adj.get(usuario, {}).items() if self.tipo.get(f) == "filme" and nota >= 4}

    def jaccard(self, a: str, b: str) -> float:
        x, y = self.positivos(a), self.positivos(b)
        return len(x & y) / len(x | y) if x | y else 0.0


def carregar(data_dir: Path = DATA) -> tuple[GrafoFilmes, dict, dict]:
    def linhas(nome):
        with (data_dir / nome).open(encoding="utf-8-sig", newline="") as arq:
            return list(csv.DictReader(arq))
    usuarios = {r["id"]: {**r, "generos_preferidos": r["generos_preferidos"].split("|")} for r in linhas("usuarios.csv")}
    filmes = {r["id"]: r for r in linhas("filmes.csv")}
    grafo = GrafoFilmes()
    for uid in usuarios: grafo.add_vertice(uid, "usuario")
    for fid in filmes: grafo.add_vertice(fid, "filme")
    for r in linhas("avaliacoes.csv"):
        grafo.add_avaliacao(r["usuario_id"], r["filme_id"], int(r["nota"]))
    return grafo, usuarios, filmes


def recomendacoes(grafo: GrafoFilmes, usuarios: dict, filmes: dict, usuario_id: str, quantidade: int = 20) -> list[dict]:
    """Recomenda filmes com evidência BFS positiva U-F-U-F e Jaccard positivo."""
    if usuario_id not in usuarios:
        raise KeyError(usuario_id)
    vistos = grafo.vizinhos(usuario_id)
    candidatos: dict[str, dict] = defaultdict(lambda: {"contribuidores": {}, "caminhos": []})
    # BFS percorre apenas as arestas positivas e retorna caminhos de três arestas.
    positivos = grafo.positivos(usuario_id)
    for caminho in grafo.caminhos_positivos(usuario_id, 3):
        _, compartilhado, colaborador, candidato = caminho
        if colaborador == usuario_id or candidato in vistos:
            continue
        similaridade = grafo.jaccard(usuario_id, colaborador)
        if similaridade <= 0:
            continue
        nota = grafo.adj[colaborador][candidato]
        reg = candidatos[candidato]
        reg["contribuidores"].setdefault(colaborador, {"usuario_id": colaborador, "nome": usuarios[colaborador]["nome"], "nota": nota, "similaridade": similaridade, "filmes_em_comum": sorted(positivos & grafo.positivos(colaborador))})
        if all(p["usuario_id"] != colaborador or p["filme_compartilhado"] != compartilhado for p in reg["caminhos"]):
            reg["caminhos"].append({"vertices": caminho, "usuario_id": colaborador, "filme_compartilhado": compartilhado, "nota_colaborador": nota, "similaridade": similaridade})
    resultado = []
    for fid, info in candidatos.items():
        contrib = list(info["contribuidores"].values())
        peso = sum(c["similaridade"] for c in contrib)
        score = sum(c["nota"] * c["similaridade"] for c in contrib) / peso if peso else 0.0
        resultado.append({"filme_id": fid, "titulo": filmes[fid]["titulo"], "genero": filmes[fid]["genero"], "pontuacao": round(score, 3), "colaboradores": len(contrib), "similaridade_media": sum(c["similaridade"] for c in contrib) / len(contrib), "contribuidores": contrib, "caminhos": info["caminhos"], "motivo": f"{len(contrib)} usuário(s) com preferências semelhantes avaliaram positivamente este filme."})
    return sorted(resultado, key=lambda x: (-x["pontuacao"], -x["colaboradores"], x["titulo"]))[:quantidade]


def similares(grafo: GrafoFilmes, usuarios: dict, usuario_id: str, limite: int = 8) -> list[dict]:
    return sorted(([{"id": uid, "nome": usuarios[uid]["nome"], "similaridade": grafo.jaccard(usuario_id, uid), "filmes_em_comum": sorted(grafo.positivos(usuario_id) & grafo.positivos(uid))} for uid in usuarios if uid != usuario_id and grafo.jaccard(usuario_id, uid) > 0]), key=lambda x: (-x["similaridade"], x["nome"]))[:limite]
