import argparse
import csv
from pathlib import Path

from src.caminhos import ARQUIVO_AVALIACOES, ARQUIVO_FILMES, SAIDA_EXECUCAO
from src.grafo import GrafoBipartido
from src.recomendador import recomendar, recomendar_bfs, avaliar_leave_one_out


def carregar(caminho=ARQUIVO_AVALIACOES, caminho_filmes=ARQUIVO_FILMES):
    g = GrafoBipartido()
    caminho = Path(caminho)
    caminho_filmes = Path(caminho_filmes)
    with caminho.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            g.add_aresta(r["usuario"], r["filme"], int(r["nota"]))
    try:
        with caminho_filmes.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                g.genero[r["filme"]] = r["genero"]
    except FileNotFoundError:
        pass
    return g


def titulo(t):
    print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)


def main(plot=False, salvar_saida=False):
    g = carregar()
    U, I = g.usuarios(), g.itens()

    titulo("1. ESTATISTICAS DO GRAFO")
    print(f"Usuarios: {len(U)} | Itens: {len(I)} | Arestas: {g.num_arestas()}")
    print(f"Grafo bipartido? {g.eh_bipartido()}")
    dens = g.num_arestas() / (len(U) * len(I))
    print(f"Densidade: {dens:.2%}")

    titulo("2. GRAU DOS VERTICES")
    gu = sorted(U, key=lambda u: -g.grau(u))
    gi = sorted(I, key=lambda i: -g.grau(i))
    print("Usuarios mais ativos:", [(u, g.grau(u)) for u in gu[:3]])
    print("Itens mais populares:", [(i, g.grau(i)) for i in gi[:5]])
    print(f"Grau medio usuario: {sum(map(g.grau, U))/len(U):.2f} | item: {sum(map(g.grau, I))/len(I):.2f}")

    titulo("3. CONECTIVIDADE")
    comps = g.componentes_conexas()
    for k, c in enumerate(comps, 1):
        nu = sum(g.tipo[v] == "U" for v in c)
        print(f"Componente {k}: {len(c)} vertices ({nu} usuarios, {len(c)-nu} itens), diametro = {g.diametro_componente(c)}")

    titulo("4. CAMINHO MINIMO")
    for a, b in [("user01", "user15"), ("user01", "Toy Story"), ("user01", "Cosmos")]:
        c = g.caminho_minimo(a, b)
        print(f"{a} -> {b}:", " -> ".join(c) + f"  (distancia {len(c)-1})" if c else "sem caminho (componentes diferentes)")

    titulo("5. VIZINHANCA E SIMILARIDADE")
    u = "user01"
    print(f"Itens de {u}:", sorted(g.vizinhos(u)))
    parecidos = sorted(g.vizinhanca_2(u), key=lambda v: -g.jaccard(u, v))[:3]
    print("Usuarios mais parecidos:", [(v, round(g.jaccard(u, v), 2)) for v in parecidos])

    titulo("6. RECOMENDACOES (BFS ate distancia 3)")
    for u in ["user01", "user10", "user22", "user29", "user30"]:
        rec, metodo = recomendar(g, u)
        print(f"\n{u} [{metodo}]")
        if metodo.startswith("grafo"):
            for i, s, v in recomendar_bfs(g, u):
                print(f"  - {i:25s} score={s:.2f}  (via {v})")
        else:
            for i, s in rec:
                print(f"  - {i:25s} grau={s}")

    titulo("7. AVALIACAO (leave-one-out, top-5)")
    hg, t = avaliar_leave_one_out(g, usar_grafo=True)
    hp, _ = avaliar_leave_one_out(g, usar_grafo=False)
    print(f"Usuarios avaliados: {t}")
    print(f"Hit rate grafo/BFS:    {hg:.1%}")
    print(f"Hit rate popularidade: {hp:.1%}")

    titulo("8. RANKING DE FILMES")
    print("Top 5 pela media bayesiana (considera nota E quantidade de avaliacoes):")
    for k, (i, s) in enumerate(g.ranking("bayes")[:5], 1):
        print(f"  {k}. {i:22s} bayes={s:.2f} media={g.nota_media(i):.2f} avaliacoes={g.grau(i)} [{g.genero.get(i)}]")
    print("\nTop 3 por genero:")
    for gen in sorted(set(g.genero.values())):
        top = ", ".join(f"{i} ({s:.2f})" for i, s in g.ranking("bayes", gen)[:3])
        print(f"  {gen:13s}: {top}")
    print("\nNota media por genero:")
    for gen in sorted(set(g.genero.values())):
        notas = [n for i in g.itens() if g.genero[i] == gen for n in g.adj[i].values()]
        print(f"  {gen:13s}: {sum(notas)/len(notas):.2f} ({len(notas)} avaliacoes)")

    if plot:
        from src.visualizacao import desenhar
        desenhar(g)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analisa o sistema de recomendação de filmes.")
    parser.add_argument("--plot", action="store_true", help="gera as visualizações em outputs/")
    parser.add_argument("--salvar-saida", action="store_true", help="salva a saída textual em docs/saida_execucao.txt")
    argumentos = parser.parse_args()
    if argumentos.salvar_saida:
        import contextlib
        SAIDA_EXECUCAO.parent.mkdir(parents=True, exist_ok=True)
        with SAIDA_EXECUCAO.open("w", encoding="utf-8") as arquivo, contextlib.redirect_stdout(arquivo):
            main(plot=argumentos.plot)
    else:
        main(plot=argumentos.plot)
