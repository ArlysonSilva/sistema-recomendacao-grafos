import pytest

from src.grafo import GrafoBipartido
from src.recomendador import (
    recomendar_bfs, recomendar_cosseno, recomendar_hibrido,
    diversificar_recomendacoes, similaridade_cosseno,
    precision_at_k, recall_at_k, ndcg_at_k, avaliar_algoritmos,
    recomendar_estrategia,
)
from src.experimentos import criar_divisao, executar_experimentos


@pytest.fixture
def grafo():
    g = GrafoBipartido()
    g.add_aresta("u1", "f1", 5)
    g.add_aresta("u1", "f2", 4)
    g.add_aresta("u2", "f1", 5)
    g.add_aresta("u2", "f3", 5)
    g.add_aresta("u3", "f4", 3)
    return g


def test_criacao_e_biparticao(grafo):
    assert set(grafo.usuarios()) == {"u1", "u2", "u3"}
    assert set(grafo.itens()) == {"f1", "f2", "f3", "f4"}
    assert grafo.num_arestas() == 5
    assert grafo.eh_bipartido()


def test_adicionar_remover_aresta_e_grau(grafo):
    grafo.add_aresta("u1", "f3", 2)
    assert grafo.grau("u1") == 3
    grafo.remove_aresta("u1", "f3")
    assert grafo.grau("u1") == 2
    assert "u1" not in grafo.vizinhos("f3")


def test_rejeita_tipo_de_vertice_inconsistente(grafo):
    with pytest.raises(ValueError):
        grafo.add_aresta("f1", "outro", 4)


def test_bfs_caminho_e_componentes(grafo):
    dist, _ = grafo.bfs("u1")
    assert dist["f3"] == 3
    assert grafo.caminho_minimo("u1", "f3") == ["u1", "f1", "u2", "f3"]
    assert grafo.caminho_minimo("u1", "u3") is None
    assert len(grafo.componentes_conexas()) == 2


def test_jaccard(grafo):
    assert grafo.jaccard("u1", "u2") == pytest.approx(1 / 3)
    assert grafo.jaccard("u1", "u3") == 0


def test_ranking_bayesiano(grafo):
    resultado = dict(grafo.ranking("bayes", m=2))
    assert resultado["f1"] > resultado["f4"]
    assert list(resultado) == ["f1", "f3", "f2", "f4"]


def test_recomendacoes_excluem_filmes_avaliados(grafo):
    recomendacoes = recomendar_bfs(grafo, "u1", nota_minima=4)
    assert recomendacoes
    assert all(filme not in grafo.vizinhos("u1") for filme, _, _ in recomendacoes)
    assert recomendacoes[0][0] == "f3"


def test_cosseno_identico_semelhante_e_disjunto():
    g = GrafoBipartido()
    for u, f, n in [("a", "x", 5), ("a", "y", 3), ("b", "x", 5), ("b", "y", 3),
                    ("c", "x", 4), ("c", "y", 2), ("d", "z", 5)]:
        g.add_aresta(u, f, n)
    assert similaridade_cosseno(g, "a", "b") == pytest.approx(1.0)
    assert 0.0 < similaridade_cosseno(g, "a", "c") < 1.0
    assert similaridade_cosseno(g, "a", "d") == 0.0
    assert similaridade_cosseno(g, "ausente", "a") == 0.0
    g.adj["vazio"] = {}
    g.tipo["vazio"] = "U"
    assert similaridade_cosseno(g, "vazio", "a") == 0.0


def test_recomendadores_novos_scores_exclusao_e_explicacao(grafo):
    cos = recomendar_cosseno(grafo, "u1")
    hibrido = recomendar_hibrido(grafo, "u1")
    assert cos and hibrido
    assert all(f not in grafo.vizinhos("u1") for f, _, _ in cos)
    assert all(f not in grafo.vizinhos("u1") for f in [r["filme"] for r in hibrido])
    assert all(0 <= r["score"] <= 1 for r in hibrido)
    assert all(r["motivo"] and "filme" in r and "genero" in r for r in hibrido)
    assert recomendar_bfs(grafo, "inexistente") == []


def test_diversidade_prefere_genero_alternativo_sem_excluir_filme(grafo):
    grafo.genero.update({"f1": "A", "f2": "A", "f3": "B"})
    itens = [{"filme": "f1", "score": 0.90, "genero": "A"},
             {"filme": "f2", "score": 0.89, "genero": "A"},
             {"filme": "f3", "score": 0.85, "genero": "B"}]
    resultado = diversificar_recomendacoes(itens, grafo, peso=0.08, n=3)
    assert [r["filme"] for r in resultado] == ["f1", "f3", "f2"]
    assert len(resultado) == 3


def test_metricas_top_k():
    ranking = ["a", "x", "b"]
    relevantes = {"a", "b"}
    assert precision_at_k(ranking, relevantes, 2) == pytest.approx(0.5)
    assert recall_at_k(ranking, relevantes, 2) == pytest.approx(0.5)
    assert ndcg_at_k(ranking, relevantes, 3) == pytest.approx((1 + 1 / 2) / (1 + 1 / 1.5849625007))
    assert recall_at_k([], set(), 5) == 0


def test_avaliacao_deterministica_sem_alterar_grafo(grafo, monkeypatch):
    import src.recomendador as recomendador
    before = {u: dict(grafo.adj[u]) for u in grafo.usuarios()}
    grafos_recebidos = []
    bfs_original = recomendador.recomendar_bfs

    def observar_bfs(g, usuario, n=5, nota_minima=4):
        grafos_recebidos.append(g)
        return bfs_original(g, usuario, n, nota_minima)

    monkeypatch.setattr(recomendador, "recomendar_bfs", observar_bfs)
    primeira = avaliar_algoritmos(grafo, k=2, seed=42)
    segunda = avaliar_algoritmos(grafo, k=2, seed=42)
    assert primeira == segunda
    assert set(primeira) == {"BFS", "Cosseno", "Hibrido", "Popularidade"}
    assert all(len(metricas) == 3 for metricas in primeira.values())
    assert before == {u: dict(grafo.adj[u]) for u in grafo.usuarios()}
    assert grafos_recebidos and all(treino is not grafo for treino in grafos_recebidos)
    assert all(treino.num_arestas() < grafo.num_arestas() for treino in grafos_recebidos)


def test_genero_ausente_e_sem_candidatos():
    g = GrafoBipartido()
    g.add_aresta("u", "f", 5)
    recomendacoes = recomendar_hibrido(g, "u")
    assert recomendacoes == []
    assert diversificar_recomendacoes([{"filme": "sem_genero", "score": 0.5}], g)[0]["filme"] == "sem_genero"


def test_cosseno_centralizado_e_norma_zero():
    g = GrafoBipartido()
    for usuario in ("a", "b"):
        g.add_aresta(usuario, "f1", 4)
        g.add_aresta(usuario, "f2", 4)
    assert similaridade_cosseno(g, "a", "b") == pytest.approx(1)
    assert similaridade_cosseno(g, "a", "b", centralizar=True) == 0
    g.add_aresta("d", "f1", 5)
    g.add_aresta("d", "f2", 1)
    g.add_aresta("c", "f1", 1)
    g.add_aresta("c", "f2", 5)
    assert similaridade_cosseno(g, "d", "c", centralizar=True) == pytest.approx(-1)


def test_estrategias_selecionaveis_e_pesos_validos(grafo):
    for metodo in ("bfs", "cosseno", "hibrido", "popularidade"):
        resultado = recomendar_estrategia(grafo, "u1", metodo, n=2,
                                           pesos=(0.5, 0.3, 0.2), diversidade=0.05)
        assert len(resultado) <= 2
        assert all(item["algoritmo"] == metodo for item in resultado)
        assert all(item["filme"] not in grafo.vizinhos("u1") for item in resultado)
        assert all(0 <= item["score"] <= 1 for item in resultado)
    with pytest.raises(ValueError):
        recomendar_estrategia(grafo, "u1", "hibrido", pesos=(0, 0, 0))


def test_cosseno_sem_sinal_util_usa_fallback_de_popularidade():
    g = GrafoBipartido()
    g.add_aresta("novo", "comum", 5)
    g.add_aresta("outro", "comum", 5)
    g.add_aresta("outro", "popular", 5)
    g.add_aresta("mais_um", "popular", 4)
    recs = recomendar_estrategia(g, "novo", "cosseno", centralizar=True)
    assert recs[0]["filme"] == "popular"
    assert recs[0]["algoritmo"] == "popularidade (fallback)"


def test_experimentos_reutilizam_holdout_e_salvam_macro_e_usuario(grafo, tmp_path):
    treino_a, teste_a = criar_divisao(grafo, seed=19)
    treino_b, teste_b = criar_divisao(grafo, seed=19)
    assert teste_a == teste_b
    assert treino_a.num_arestas() == treino_b.num_arestas()
    saida = tmp_path / "experimentos.csv"
    linhas = executar_experimentos(grafo, saida)
    assert saida.exists()
    assert len(linhas) == 14
    csv = saida.read_text(encoding="utf-8")
    assert "tipo,usuario,algoritmo,configuracao" in csv
    assert "pesos-50-40-10;diversidade-0.08" in csv
    assert "usuario,u1," in csv


def test_endpoints_api(monkeypatch, tmp_path):
    import asyncio
    import httpx
    import backend.api as api
    original = api.grafo_simulacao
    monkeypatch.setattr(api, "grafo_simulacao", __import__("copy").deepcopy(api.grafo_original))
    async def consultar_api():
        transporte = httpx.ASGITransport(app=api.app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://test") as cliente:
            return (
                await cliente.get("/api/estatisticas"),
                await cliente.get("/api/usuarios"),
                await cliente.get("/api/filmes"),
                await cliente.get("/api/recomendacoes/u001"),
                await cliente.get("/api/recomendacoes/user-inexistente"),
                await cliente.get("/api/usuarios/u001/preferencias"),
                await cliente.get("/api/usuarios/u001/similares"),
                await cliente.get("/api/grafo?usuario=u001"),
                await cliente.get("/api/analise"),
                await cliente.post("/api/simulacao/avaliacao", json={"usuario_id":"u001","filme_id":"f007","nota":5}),
                await cliente.post("/api/simulacao/recomendar", json={"usuario_id":"u001"}),
                await cliente.post("/api/simulacao/restaurar"),
            )
    (estatisticas, usuarios, filmes, recomendacoes, inexistente, preferencias,
     similares, dados_grafo, analise, simulacao, comparacao, restaurado) = asyncio.run(consultar_api())
    assert estatisticas.json()["avaliacoes"] == 560
    assert len(usuarios.json()) == 40
    assert len(filmes.json()) == 60
    assert recomendacoes.status_code == 200
    assert inexistente.status_code == 404
    assert preferencias.status_code == similares.status_code == 200
    assert dados_grafo.status_code == analise.status_code == 200
    assert simulacao.json()["alteracao"]["tipo"] in {"adicionada", "alterada"}
    assert comparacao.status_code == 200
    assert restaurado.json()["restaurado"] is True
    assert api.grafo_simulacao is not original
