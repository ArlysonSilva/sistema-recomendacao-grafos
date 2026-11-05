import pytest

from src.grafo import GrafoBipartido
from src.recomendador import recomendar_bfs


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
