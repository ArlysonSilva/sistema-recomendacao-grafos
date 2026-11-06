import asyncio
import csv
import hashlib
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from src.cineconecta import DATA, GrafoFilmes, carregar, recomendacoes, similares
from gerar_dados import CATALOGO


def test_grafo_notas_grau_bfs_componentes_e_biparticao():
    g = GrafoFilmes()
    g.add_avaliacao("u1", "f1", 5)
    g.add_avaliacao("u2", "f1", 4)
    g.add_avaliacao("u2", "f2", 3)
    assert g.adj["u1"]["f1"] == 5
    assert g.grau("u2") == 2
    assert g.eh_bipartido()
    assert g.caminho_minimo("u1", "f2") == ["u1", "f1", "u2", "f2"]
    assert len(g.componentes()) == 1


def test_jaccard_positivo_e_usuarios_semelhantes():
    g = GrafoFilmes()
    for u, f, n in [("a", "x", 5), ("a", "y", 2), ("b", "x", 4), ("b", "z", 5), ("c", "y", 5)]:
        g.add_avaliacao(u, f, n)
    assert g.jaccard("a", "b") == pytest.approx(0.5)
    assert g.jaccard("a", "c") == 0
    assert "y" not in g.positivos("a")


def test_recomendacao_real_exibe_caminho_bfs_e_exclui_avaliados():
    g, users, movies = carregar()
    mariana = next(uid for uid, u in users.items() if u["nome"] == "Mariana Costa")
    recs = recomendacoes(g, users, movies, mariana)
    matrix = next(item for item in recs if item["titulo"] == "Matrix")
    assert matrix["caminhos"]
    assert matrix["caminhos"][0]["vertices"] == [mariana, "f005", "u009", "f026"]
    assert users["u009"]["nome"] == "Juliana Carvalho"
    assert movies["f005"]["titulo"] == "Indiana Jones e os Caçadores da Arca Perdida"
    assert "f026" not in g.vizinhos(mariana)
    assert matrix["colaboradores"] >= 1
    assert matrix["pontuacao"] > 0


def test_recomendador_controlado_com_caminho_conhecido():
    g = GrafoFilmes()
    g.add_avaliacao("a", "compartilhado", 5)
    g.add_avaliacao("b", "compartilhado", 4)
    g.add_avaliacao("b", "candidato", 5)
    users = {"a": {"nome": "Ana"}, "b": {"nome": "Bruno"}}
    movies = {
        "compartilhado": {"titulo": "Filme em comum", "genero": "Drama"},
        "candidato": {"titulo": "Novo filme", "genero": "Ação"},
    }
    result = recomendacoes(g, users, movies, "a")
    assert result[0]["caminhos"][0]["vertices"] == ["a", "compartilhado", "b", "candidato"]
    assert result[0]["caminhos"][0]["similaridade"] == pytest.approx(0.5)
    assert result[0]["pontuacao"] == 5


def test_recomendacao_sem_caminho_e_vazio():
    g = GrafoFilmes()
    g.add_avaliacao("u", "f1", 5)
    users = {"u": {"nome": "Pessoa", "generos_preferidos": []}}
    movies = {"f1": {"titulo": "Visto", "genero": "Drama"}}
    assert recomendacoes(g, users, movies, "u") == []


def test_modos_da_api_do_grafo_retorna_recortes_reais():
    import backend.api as api
    from httpx import ASGITransport, AsyncClient

    original = api.grafo_simulacao
    api.grafo_simulacao = deepcopy(api.grafo_original)

    async def calls():
        async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://test") as client:
            all_graph = await client.get("/api/grafo?usuario=u001&modo=todas")
            direct = await client.get("/api/grafo?usuario=u001&modo=vizinhos")
            expanded = await client.get("/api/grafo?usuario=u001&modo=expandida")
            positive = await client.get("/api/grafo?usuario=u001&modo=positivas")
            path = await client.get("/api/grafo?usuario=u001&filme_recomendado=f026&modo=caminho")
            example = await client.get("/api/exemplo")
            return all_graph.json(), direct.json(), expanded.json(), positive.json(), path.json(), example.json()

    try:
        all_graph, direct, expanded, positive, path, example = asyncio.run(calls())
    finally:
        api.grafo_simulacao = original

    assert len(all_graph["nodes"]) == 100
    assert len(all_graph["edges"]) == 560
    assert len({node["id"] for node in all_graph["nodes"]}) == 100

    assert all(node["tipo"] != "usuario" or node["id"] == "u001" for node in direct["nodes"])
    assert {edge["source"] for edge in direct["edges"]} == {"u001"}
    assert len(direct["edges"]) == len(api.grafo_original.adj["u001"])

    assert expanded["caminhos"]
    assert len(expanded["nodes"]) <= 21
    assert len({route["usuario_id"] for route in expanded["caminhos"]}) <= 5
    assert len({route["filme_id"] for route in expanded["caminhos"]}) <= 5
    assert len({route["filme_compartilhado"] for route in expanded["caminhos"]}) <= 10
    assert all(len(route["vertices"]) == 4 for route in expanded["caminhos"])
    assert all(edge["nota"] >= 4 for edge in expanded["edges"])
    valid_pairs = {
        (start, end) if start.startswith("u") else (end, start)
        for route in expanded["caminhos"]
        for start, end in zip(route["vertices"], route["vertices"][1:])
    }
    assert {(edge["source"], edge["target"]) for edge in expanded["edges"]} == valid_pairs
    assert any(node["similaridade"] is not None for node in expanded["nodes"])

    assert len(positive["nodes"]) == 100
    assert positive["edges"]
    assert all(edge["nota"] >= 4 for edge in positive["edges"])

    expected = ["u001", "f005", "u009", "f026"]
    assert any(route["vertices"] == expected for route in path["caminhos"])
    assert len(path["caminhos"]) <= 5
    assert {(edge["source"], edge["target"]) for edge in path["edges"]} == {
        (start, end) if start.startswith("u") else (end, start)
        for route in path["caminhos"]
        for start, end in zip(route["vertices"], route["vertices"][1:])
    }
    assert example["disponivel"]
    assert example["similaridade"] == pytest.approx(
        api.grafo_original.jaccard(example["usuario"]["id"], example["colaborador"]["id"])
    )
    assert example["nota_colaborador"] >= 4


def test_csv_nova_base_integridade_e_seed():
    with (DATA / "usuarios.csv").open(encoding="utf-8-sig", newline="") as f:
        users = list(csv.DictReader(f))
    with (DATA / "filmes.csv").open(encoding="utf-8-sig", newline="") as f:
        movies = list(csv.DictReader(f))
    with (DATA / "avaliacoes.csv").open(encoding="utf-8-sig", newline="") as f:
        ratings = list(csv.DictReader(f))
    assert len(users) == 40 and len({u["id"] for u in users}) == 40 and len({u["nome"] for u in users}) == 40
    assert len(movies) == 60 and len({m["id"] for m in movies}) == 60
    assert len(ratings) == 560
    assert [(m["titulo"], m["genero"]) for m in movies] == CATALOGO
    assert [m["id"] for m in movies] == [f"f{i:03}" for i in range(1, 61)]
    assert {m["genero"] for m in movies} == {"Ação", "Aventura", "Animação", "Comédia", "Drama", "Romance", "Ficção científica", "Fantasia", "Terror", "Suspense", "Mistério", "Crime", "Documentário", "Musical", "Guerra"}
    assert all(1 <= int(r["nota"]) <= 5 for r in ratings)


def test_endpoints_simulacao_nao_altera_csv():
    import backend.api as api
    originals = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*.csv")}
    before = api.grafo_simulacao
    api.grafo_simulacao = deepcopy(api.grafo_original)
    async def calls():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test") as client:
            stats = await client.get("/api/estatisticas")
            graph = await client.get("/api/grafo?usuario=u001&modo=todas")
            result = await client.post("/api/simulacao/avaliacao", json={"usuario_id": "u001", "filme_id": "f026", "nota": 4})
            changed_graph = await client.get("/api/grafo?usuario=u001&modo=vizinhos")
            duplicate = await client.post("/api/simulacao/avaliacao", json={"usuario_id": "u001", "filme_id": "f026", "nota": 4})
            after = await client.post("/api/simulacao/recomendar", json={"usuario_id": "u001"})
            restored = await client.post("/api/simulacao/restaurar")
            bad = await client.post("/api/simulacao/avaliacao", json={"usuario_id": "u001", "filme_id": "f060", "nota": 9})
            return stats, graph, result, changed_graph, duplicate, after, restored, bad
    stats, graph, result, changed_graph, duplicate, after, restored, bad = asyncio.run(calls())
    assert stats.json()["usuarios"] == 40
    assert len(graph.json()["nodes"]) == 100
    assert len(graph.json()["edges"]) == 560
    assert any(edge["simulada"] and edge["target"] == "f026" for edge in changed_graph.json()["edges"])
    assert result.status_code == after.status_code == restored.status_code == 200
    assert duplicate.status_code == 409
    assert bad.status_code == 422
    before_ids = {item["filme_id"] for item in after.json()["antes"]}
    after_ids = {item["filme_id"] for item in after.json()["depois"]}
    assert "f026" in before_ids and "f026" not in after_ids
    assert after.json()["alteracoes"][0]["nota_nova"] == 4
    assert restored.json()["restaurado"]
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("*.csv")} == originals
    api.grafo_simulacao = before
