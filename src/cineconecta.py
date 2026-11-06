"""Núcleo usado pela API web do CineConecta.

O módulo carrega os CSVs, representa avaliações em um grafo bipartido e gera
recomendações explicáveis. Os algoritmos centrais são implementados no próprio
projeto para que possam ser estudados diretamente.
"""
from __future__ import annotations

import csv
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dados"
class GrafoFilmes:
    """Grafo bipartido de usuários e filmes armazenado por lista de adjacência.

    ``tipo`` identifica a partição de cada vértice. ``adj`` guarda a mesma
    avaliação nos dois sentidos: ``adj[usuario][filme]`` e
    ``adj[filme][usuario]`` contêm a nota de 1 a 5 da aresta.
    """

    def __init__(self):
        """Inicializa um grafo vazio."""
        self.adj: dict[str, dict[str, int]] = {}
        self.tipo: dict[str, str] = {}

    def add_vertice(self, ident: str, tipo: str) -> None:
        """Inclui um vértice e impede que ele pertença às duas partições."""
        if tipo not in {"usuario", "filme"}:
            raise ValueError("Tipo de vértice deve ser usuario ou filme")
        if ident in self.tipo and self.tipo[ident] != tipo:
            raise ValueError(f"Tipo conflitante para {ident}")
        self.tipo[ident] = tipo
        self.adj.setdefault(ident, {})

    def add_avaliacao(self, usuario: str, filme: str, nota: int) -> None:
        """Cria ou atualiza a aresta usuário-filme com uma nota de 1 a 5."""
        if not 1 <= int(nota) <= 5:
            raise ValueError("A nota deve estar entre 1 e 5")
        self.add_vertice(usuario, "usuario")
        self.add_vertice(filme, "filme")
        self.adj[usuario][filme] = int(nota)
        self.adj[filme][usuario] = int(nota)

    def grau(self, ident: str) -> int:
        """Retorna a quantidade de arestas incidentes no vértice."""
        return len(self.adj.get(ident, {}))

    def vizinhos(self, ident: str) -> set[str]:
        """Retorna os identificadores ligados diretamente ao vértice."""
        return set(self.adj.get(ident, {}))

    def bfs(self, origem: str, max_distancia: int | None = None) -> tuple[dict[str, int], dict[str, str | None]]:
        """Percorre o grafo em largura e retorna distâncias e predecessores.

        A fila visita primeiro todos os vértices de uma distância antes de
        avançar ao próximo nível. ``max_distancia`` limita essa expansão.
        """
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
        """Enumera por BFS caminhos simples que usam somente notas 4 ou 5."""
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
        """Reconstrói um caminho mínimo usando os predecessores da BFS."""
        dist, pai = self.bfs(inicio)
        if fim not in dist:
            return None
        caminho, atual = [], fim
        while atual is not None:
            caminho.append(atual)
            atual = pai[atual]
        return caminho[::-1]

    def componentes(self) -> list[set[str]]:
        """Separa as componentes conexas, da maior para a menor."""
        restantes, resultado = set(self.adj), []
        while restantes:
            origem = next(iter(restantes))
            visitados, _ = self.bfs(origem)
            resultado.append(set(visitados))
            restantes.difference_update(visitados)
        return sorted(resultado, key=len, reverse=True)

    def eh_bipartido(self) -> bool:
        """Confirma que toda aresta liga vértices de partições diferentes."""
        return all(self.tipo[a] != self.tipo[b] for a, viz in self.adj.items() for b in viz)

    def positivos(self, usuario: str) -> set[str]:
        """Retorna os filmes que o usuário avaliou com nota 4 ou 5."""
        return {
            filme
            for filme, nota in self.adj.get(usuario, {}).items()
            if self.tipo.get(filme) == "filme" and nota >= 4
        }

    def jaccard(self, a: str, b: str) -> float:
        """Calcula |A ∩ B| / |A ∪ B| sobre os filmes positivos dos usuários."""
        positivos_a, positivos_b = self.positivos(a), self.positivos(b)
        uniao = positivos_a | positivos_b
        return len(positivos_a & positivos_b) / len(uniao) if uniao else 0.0


def carregar(data_dir: Path = DATA) -> tuple[GrafoFilmes, dict, dict]:
    """Carrega usuários, filmes e avaliações dos três CSVs da aplicação.

    Todos os usuários e filmes são criados mesmo quando não possuem arestas.
    O retorno reúne o grafo e os dicionários de metadados indexados por ID.
    """

    def linhas(nome: str) -> list[dict[str, str]]:
        with (data_dir / nome).open(encoding="utf-8-sig", newline="") as arq:
            return list(csv.DictReader(arq))

    usuarios = {
        registro["id"]: {
            **registro,
            "generos_preferidos": registro["generos_preferidos"].split("|"),
        }
        for registro in linhas("usuarios.csv")
    }
    filmes = {r["id"]: r for r in linhas("filmes.csv")}
    grafo = GrafoFilmes()
    for usuario_id in usuarios:
        grafo.add_vertice(usuario_id, "usuario")
    for filme_id in filmes:
        grafo.add_vertice(filme_id, "filme")
    for registro in linhas("avaliacoes.csv"):
        grafo.add_avaliacao(
            registro["usuario_id"],
            registro["filme_id"],
            int(registro["nota"]),
        )
    return grafo, usuarios, filmes


def recomendacoes(grafo: GrafoFilmes, usuarios: dict, filmes: dict, usuario_id: str, quantidade: int = 20) -> list[dict]:
    """Gera recomendações explicáveis por caminhos positivos U-F-U-F.

    A BFS encontra filmes candidatos a três arestas do usuário inicial. Um
    candidato é descartado quando já foi avaliado. Cada colaborador contribui
    uma única vez por filme, com peso igual ao Jaccard entre os dois usuários.
    A pontuação final é a média ponderada ``Σ(nota × Jaccard) / Σ(Jaccard)``.
    """
    if usuario_id not in usuarios:
        raise KeyError(usuario_id)
    vistos = grafo.vizinhos(usuario_id)
    candidatos: dict[str, dict] = defaultdict(lambda: {"contribuidores": {}, "caminhos": []})
    positivos = grafo.positivos(usuario_id)
    for caminho in grafo.caminhos_positivos(usuario_id, 3):
        _, compartilhado, colaborador, candidato = caminho
        if colaborador == usuario_id or candidato in vistos:
            continue
        similaridade = grafo.jaccard(usuario_id, colaborador)
        if similaridade <= 0:
            continue
        nota = grafo.adj[colaborador][candidato]
        registro = candidatos[candidato]
        registro["contribuidores"].setdefault(
            colaborador,
            {
                "usuario_id": colaborador,
                "nome": usuarios[colaborador]["nome"],
                "nota": nota,
                "similaridade": similaridade,
                "filmes_em_comum": sorted(
                    positivos & grafo.positivos(colaborador)
                ),
            },
        )
        caminho_repetido = any(
            item["usuario_id"] == colaborador
            and item["filme_compartilhado"] == compartilhado
            for item in registro["caminhos"]
        )
        if not caminho_repetido:
            registro["caminhos"].append(
                {
                    "vertices": caminho,
                    "usuario_id": colaborador,
                    "filme_compartilhado": compartilhado,
                    "nota_colaborador": nota,
                    "similaridade": similaridade,
                }
            )

    resultado = []
    for filme_id, info in candidatos.items():
        contrib = list(info["contribuidores"].values())
        peso = sum(c["similaridade"] for c in contrib)
        score = sum(c["nota"] * c["similaridade"] for c in contrib) / peso if peso else 0.0
        resultado.append(
            {
                "filme_id": filme_id,
                "titulo": filmes[filme_id]["titulo"],
                "genero": filmes[filme_id]["genero"],
                "pontuacao": round(score, 3),
                "colaboradores": len(contrib),
                "similaridade_media": sum(
                    c["similaridade"] for c in contrib
                ) / len(contrib),
                "contribuidores": contrib,
                "caminhos": info["caminhos"],
                "motivo": (
                    f"{len(contrib)} usuário(s) com preferências semelhantes "
                    "avaliaram positivamente este filme."
                ),
            }
        )
    return sorted(
        resultado,
        key=lambda item: (
            -item["pontuacao"],
            -item["colaboradores"],
            item["titulo"],
        ),
    )[:quantidade]


def similares(grafo: GrafoFilmes, usuarios: dict, usuario_id: str, limite: int = 8) -> list[dict]:
    """Lista usuários com Jaccard positivo e os filmes positivos em comum."""
    positivos_usuario = grafo.positivos(usuario_id)
    resultado = []
    for outro_id in usuarios:
        if outro_id == usuario_id:
            continue
        similaridade = grafo.jaccard(usuario_id, outro_id)
        if similaridade > 0:
            resultado.append(
                {
                    "id": outro_id,
                    "nome": usuarios[outro_id]["nome"],
                    "similaridade": similaridade,
                    "filmes_em_comum": sorted(
                        positivos_usuario & grafo.positivos(outro_id)
                    ),
                }
            )
    return sorted(
        resultado,
        key=lambda item: (-item["similaridade"], item["nome"]),
    )[:limite]
