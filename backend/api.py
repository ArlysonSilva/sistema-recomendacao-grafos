"""API do CineConecta. A simulação fica somente na memória do processo."""
from collections import Counter
from copy import deepcopy

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.cineconecta import carregar, recomendacoes, similares

app = FastAPI(title="CineConecta")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

grafo_original, usuarios, filmes = carregar()
grafo_simulacao = deepcopy(grafo_original)
alteracoes = []


class AvaliacaoSimulada(BaseModel):
    usuario_id: str
    filme_id: str
    nota: int = Field(ge=1, le=5)


class UsuarioSelecionado(BaseModel):
    usuario_id: str


def validar_usuario(usuario_id: str) -> None:
    if usuario_id not in usuarios:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")


def generos_preferidos(grafo, usuario_id: str) -> list[str]:
    contagem = Counter(
        filmes[filme_id]["genero"]
        for filme_id, nota in grafo.adj[usuario_id].items()
        if nota >= 4
    )
    return [genero for genero, _ in contagem.most_common()]


def lista_usuarios(grafo):
    return [
        {
            "id": usuario_id,
            "nome": usuario["nome"],
            "generos_preferidos": generos_preferidos(grafo, usuario_id),
            "avaliacoes": grafo.grau(usuario_id),
            "grau": grafo.grau(usuario_id),
        }
        for usuario_id, usuario in usuarios.items()
    ]


@app.get("/api/estatisticas")
def estatisticas():
    componentes = grafo_simulacao.componentes()
    return {
        "usuarios": len(usuarios),
        "filmes": len(filmes),
        "avaliacoes": sum(grafo_simulacao.grau(uid) for uid in usuarios),
        "componentes_conexas": len(componentes),
        "bipartido": grafo_simulacao.eh_bipartido(),
    }


@app.get("/api/usuarios")
def obter_usuarios():
    return lista_usuarios(grafo_simulacao)


@app.get("/api/filmes")
def obter_filmes():
    return [
        {
            "id": filme_id,
            "titulo": filme["titulo"],
            "genero": filme["genero"],
            "avaliacoes": grafo_simulacao.grau(filme_id),
            "grau": grafo_simulacao.grau(filme_id),
        }
        for filme_id, filme in filmes.items()
    ]


@app.get("/api/usuarios/{usuario_id}/preferencias")
def obter_preferencias(usuario_id: str):
    validar_usuario(usuario_id)
    avaliacoes = [
        {
            "filme_id": filme_id,
            "titulo": filmes[filme_id]["titulo"],
            "genero": filmes[filme_id]["genero"],
            "nota": nota,
        }
        for filme_id, nota in grafo_simulacao.adj[usuario_id].items()
    ]
    usuario = {**usuarios[usuario_id]}
    usuario["generos_preferidos"] = generos_preferidos(grafo_simulacao, usuario_id)
    return {
        "usuario": usuario,
        "avaliacoes": sorted(avaliacoes, key=lambda item: item["titulo"]),
        "generos_preferidos": usuario["generos_preferidos"],
        "grau": grafo_simulacao.grau(usuario_id),
        "filmes_positivos": len(grafo_simulacao.positivos(usuario_id)),
    }


@app.get("/api/usuarios/{usuario_id}/similares")
def obter_similares(usuario_id: str):
    validar_usuario(usuario_id)
    return similares(grafo_simulacao, usuarios, usuario_id)


@app.get("/api/recomendacoes/{usuario_id}")
def obter_recomendacoes(
    usuario_id: str,
    quantidade: int = Query(default=20, ge=1, le=60),
):
    validar_usuario(usuario_id)
    return {
        "usuario_id": usuario_id,
        "recomendacoes": recomendacoes(
            grafo_simulacao, usuarios, filmes, usuario_id, quantidade
        ),
    }


@app.get("/api/grafo")
def obter_grafo(
    usuario: str | None = None,
    filme_recomendado: str | None = None,
    modo: str = Query(
        default="todas",
        pattern="^(todas|vizinhos|expandida|positivas|caminho)$",
    ),
):
    if usuario:
        validar_usuario(usuario)

    grafo = grafo_simulacao
    caminhos = []
    mensagem = ""
    recomendacoes_usuario = []

    if usuario and modo in {"expandida", "caminho"}:
        recomendacoes_usuario = recomendacoes(
            grafo, usuarios, filmes, usuario, quantidade=len(filmes)
        )

    if modo == "todas":
        vertices = set(grafo.adj)
    elif modo == "vizinhos":
        vertices = {usuario} | grafo.vizinhos(usuario) if usuario else set()
    elif modo == "positivas":
        vertices = set(grafo.adj)
    elif modo == "expandida":
        usuarios_semelhantes = similares(grafo, usuarios, usuario, limite=len(usuarios))[:5] if usuario else []
        ids_semelhantes = {item["id"] for item in usuarios_semelhantes}
        recomendacoes_validas = [
            item for item in recomendacoes_usuario
            if any(caminho["usuario_id"] in ids_semelhantes for caminho in item["caminhos"])
        ][:5]
        filmes_candidatos = {item["filme_id"] for item in recomendacoes_validas}
        caminhos_candidatos = [
            {**caminho, "filme_id": item["filme_id"], "titulo": item["titulo"]}
            for item in recomendacoes_validas
            for caminho in item["caminhos"]
            if caminho["usuario_id"] in ids_semelhantes
        ]
        compartilhados_por_filme = Counter(
            caminho["filme_compartilhado"] for caminho in caminhos_candidatos
        )
        filmes_compartilhados = {
            filme_id for filme_id, _ in sorted(
                compartilhados_por_filme.items(),
                key=lambda item: (-item[1], -grafo.grau(item[0]), item[0]),
            )[:10]
        }
        caminhos = [
            caminho for caminho in caminhos_candidatos
            if caminho["filme_compartilhado"] in filmes_compartilhados
            and caminho["filme_id"] in filmes_candidatos
        ]
        vertices = {vertice for caminho in caminhos for vertice in caminho["vertices"]}
        if usuario:
            vertices.add(usuario)
        if not caminhos:
            mensagem = "Não há caminhos positivos disponíveis para este usuário."
    else:
        if not usuario:
            vertices = set()
            mensagem = "Selecione um usuário e um filme recomendado."
        elif not filme_recomendado:
            vertices = {usuario}
            mensagem = "Selecione um filme recomendado."
        elif filme_recomendado not in filmes:
            raise HTTPException(status_code=404, detail="Filme não encontrado.")
        else:
            recomendado = next(
                (item for item in recomendacoes_usuario if item["filme_id"] == filme_recomendado),
                None,
            )
            if recomendado:
                caminhos = [
                    {**caminho, "filme_id": recomendado["filme_id"], "titulo": recomendado["titulo"]}
                    for caminho in recomendado["caminhos"]
                ][:5]
                vertices = {vertice for caminho in caminhos for vertice in caminho["vertices"]}
            else:
                vertices = {usuario}
                mensagem = "Não há um caminho positivo para esse filme."

    pares_caminho = set()
    rotas_por_aresta = {}
    similaridades = {}
    papeis = {}
    for indice, caminho in enumerate(caminhos):
        rota = caminho["vertices"]
        for origem, destino in zip(rota, rota[1:]):
            par = (origem, destino) if origem in usuarios else (destino, origem)
            pares_caminho.add(par)
            rotas_por_aresta.setdefault(par, []).append(indice)
        papeis[rota[1]] = "compartilhado"
        papeis[rota[2]] = "semelhante"
        papeis[rota[3]] = "candidato"
        similaridades[rota[2]] = caminho["similaridade"]

    if usuario:
        papeis[usuario] = "selecionado"

    nos = [
        {
            "id": vertice,
            "nome": usuarios[vertice]["nome"] if tipo == "usuario" else filmes[vertice]["titulo"],
            "tipo": tipo,
            "grau": grafo.grau(vertice),
            "papel": papeis.get(vertice, "normal"),
            "similaridade": similaridades.get(vertice),
        }
        for vertice, tipo in grafo.tipo.items()
        if vertice in vertices
    ]
    arestas = []
    for usuario_id in usuarios:
        for filme_id, nota in grafo.adj[usuario_id].items():
            if usuario_id not in vertices or filme_id not in vertices:
                continue
            par = (usuario_id, filme_id)
            if modo == "vizinhos" and usuario_id != usuario:
                continue
            if modo in {"expandida", "caminho"} and par not in pares_caminho:
                continue
            if modo == "positivas" and nota < 4:
                continue
            arestas.append({
                "source": usuario_id,
                "target": filme_id,
                "nota": nota,
                "positiva": nota >= 4,
                "direta": usuario_id == usuario,
                "simulada": any(
                    item["usuario_id"] == usuario_id
                    and item["filme_id"] == filme_id
                    for item in alteracoes
                ),
                "destacado": par in pares_caminho,
                "rotas": rotas_por_aresta.get(par, []),
            })
    return {
        "nodes": nos,
        "edges": arestas,
        "componentes_conexas": len(grafo.componentes()),
        "caminhos": caminhos,
        "mensagem": mensagem,
        "modo": modo,
    }


@app.get("/api/exemplo")
def obter_exemplo():
    ordem = list(usuarios)
    mariana = next((uid for uid in ordem if usuarios[uid]["nome"] == "Mariana Costa"), None)
    if mariana:
        ordem.remove(mariana)
        ordem.insert(0, mariana)

    for usuario_id in ordem:
        itens = recomendacoes(
            grafo_simulacao, usuarios, filmes, usuario_id, quantidade=len(filmes)
        )
        for item in itens:
            if not item["caminhos"]:
                continue
            caminho = item["caminhos"][0]
            inicio, compartilhado, colaborador, candidato = caminho["vertices"]
            return {
                "disponivel": True,
                "usuario": {"id": inicio, "nome": usuarios[inicio]["nome"]},
                "filme_compartilhado": {
                    "id": compartilhado,
                    "titulo": filmes[compartilhado]["titulo"],
                },
                "colaborador": {"id": colaborador, "nome": usuarios[colaborador]["nome"]},
                "filme_recomendado": {"id": candidato, "titulo": filmes[candidato]["titulo"]},
                "nota_usuario": grafo_simulacao.adj[inicio][compartilhado],
                "nota_compartilhada": grafo_simulacao.adj[colaborador][compartilhado],
                "nota_colaborador": caminho["nota_colaborador"],
                "similaridade": caminho["similaridade"],
                "pontuacao": item["pontuacao"],
            }
    return {
        "disponivel": False,
        "mensagem": "Não há caminhos positivos para formar um exemplo nesta base.",
    }


@app.get("/api/analise")
def obter_analise():
    grafo = grafo_simulacao
    filmes_por_genero = Counter(filme["genero"] for filme in filmes.values())
    por_genero = Counter()
    por_filme = Counter()
    por_usuario = Counter()

    for usuario_id in usuarios:
        por_usuario[usuario_id] = grafo.grau(usuario_id)
        for filme_id in grafo.adj[usuario_id]:
            por_genero[filmes[filme_id]["genero"]] += 1
            por_filme[filme_id] += 1

    pares = []
    ids = list(usuarios)
    for i, primeiro in enumerate(ids):
        for segundo in ids[i + 1:]:
            valor = grafo.jaccard(primeiro, segundo)
            if valor > 0:
                pares.append({
                    "usuario": usuarios[primeiro]["nome"],
                    "outro": usuarios[segundo]["nome"],
                    "similaridade": valor,
                })
    pares.sort(key=lambda item: item["similaridade"], reverse=True)

    return {
        "filmes_por_genero": [
            {"nome": nome, "valor": total}
            for nome, total in filmes_por_genero.most_common()
        ],
        "avaliacoes_por_genero": [
            {"nome": nome, "valor": total} for nome, total in por_genero.most_common()
        ],
        "avaliacoes_por_usuario": [
            {"id": uid, "nome": usuarios[uid]["nome"], "valor": total}
            for uid, total in por_usuario.items()
        ],
        "filmes_mais_avaliados": [
            {"id": fid, "titulo": filmes[fid]["titulo"], "valor": total}
            for fid, total in por_filme.most_common()
        ],
        "grau_usuarios": [
            {"nome": usuarios[uid]["nome"], "valor": grafo.grau(uid)}
            for uid in usuarios
        ],
        "grau_filmes": [
            {"titulo": filmes[fid]["titulo"], "valor": grafo.grau(fid)}
            for fid in filmes
        ],
        "similaridade_usuarios": pares[:30],
    }


@app.post("/api/simulacao/avaliacao")
def simular_avaliacao(pedido: AvaliacaoSimulada):
    if pedido.usuario_id not in usuarios:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if pedido.filme_id not in filmes:
        raise HTTPException(status_code=404, detail="Filme não encontrado.")
    if pedido.filme_id in grafo_simulacao.adj[pedido.usuario_id]:
        raise HTTPException(
            status_code=409,
            detail="Essa pessoa já avaliou esse filme. Escolha outro filme.",
        )

    grafo_simulacao.add_avaliacao(pedido.usuario_id, pedido.filme_id, pedido.nota)
    alteracao = {
        "usuario_id": pedido.usuario_id,
        "usuario_nome": usuarios[pedido.usuario_id]["nome"],
        "filme_id": pedido.filme_id,
        "filme_titulo": filmes[pedido.filme_id]["titulo"],
        "nota_nova": pedido.nota,
        "tipo": "adicionada",
    }
    alteracoes.append(alteracao)
    return {
        "alteracao": alteracao,
        "alteracoes": alteracoes,
        "recomendacoes": recomendacoes(
            grafo_simulacao, usuarios, filmes, pedido.usuario_id
        ),
    }


@app.post("/api/simulacao/recomendar")
def comparar_simulacao(pedido: UsuarioSelecionado):
    validar_usuario(pedido.usuario_id)
    return {
        "usuario_id": pedido.usuario_id,
        "antes": recomendacoes(
            grafo_original, usuarios, filmes, pedido.usuario_id
        ),
        "depois": recomendacoes(
            grafo_simulacao, usuarios, filmes, pedido.usuario_id
        ),
        "alteracoes": alteracoes,
    }


@app.post("/api/simulacao/restaurar")
def restaurar_simulacao():
    global grafo_simulacao
    grafo_simulacao = deepcopy(grafo_original)
    alteracoes.clear()
    return {"restaurado": True}
