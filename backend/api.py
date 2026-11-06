"""API HTTP do CineConecta.

Os endpoints convertem o grafo em dados adequados às cinco telas do frontend.
A simulação usa uma cópia em memória e nunca grava os arquivos CSV.
"""
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
usuario_simulado = None


class AvaliacaoSimulada(BaseModel):
    """Dados necessários para adicionar temporariamente uma avaliação."""

    usuario_id: str
    filme_id: str
    nota: int = Field(ge=1, le=5)


class UsuarioSelecionado(BaseModel):
    """Usuário para quem a simulação recalcula recomendações."""

    usuario_id: str


class NovoUsuarioSimulado(BaseModel):
    """Nome da pessoa criada somente durante a simulação."""

    nome: str = Field(min_length=2, max_length=80)


def validar_usuario(usuario_id: str) -> None:
    """Interrompe a requisição quando o ID de usuário não existe."""
    if usuario_id not in usuarios:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")


def generos_preferidos(grafo, usuario_id: str) -> list[str]:
    """Ordena gêneros pela quantidade de avaliações positivas do usuário."""
    contagem = Counter(
        filmes[filme_id]["genero"]
        for filme_id, nota in grafo.adj[usuario_id].items()
        if nota >= 4
    )
    return [genero for genero, _ in contagem.most_common()]


def lista_usuarios(grafo):
    """Serializa os usuários e seus valores derivados no grafo informado."""
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


def usuarios_da_simulacao() -> dict:
    """Combina usuários originais com o único perfil temporário ativo."""
    resultado = dict(usuarios)
    if usuario_simulado:
        resultado[usuario_simulado["id"]] = usuario_simulado
    return resultado


@app.get("/api/estatisticas")
def estatisticas():
    """Retorna os totais reais exibidos no cabeçalho da página inicial."""
    componentes = grafo_original.componentes()
    return {
        "usuarios": len(usuarios),
        "filmes": len(filmes),
        "avaliacoes": sum(grafo_original.grau(uid) for uid in usuarios),
        "componentes_conexas": len(componentes),
        "bipartido": grafo_original.eh_bipartido(),
    }


@app.get("/api/usuarios")
def obter_usuarios():
    return lista_usuarios(grafo_original)


@app.get("/api/filmes")
def obter_filmes():
    return [
        {
            "id": filme_id,
            "titulo": filme["titulo"],
            "genero": filme["genero"],
            "avaliacoes": grafo_original.grau(filme_id),
            "grau": grafo_original.grau(filme_id),
        }
        for filme_id, filme in filmes.items()
    ]


@app.get("/api/usuarios/{usuario_id}/preferencias")
def obter_preferencias(usuario_id: str):
    """Detalha avaliações, grau e preferências positivas de um usuário."""
    validar_usuario(usuario_id)
    avaliacoes = [
        {
            "filme_id": filme_id,
            "titulo": filmes[filme_id]["titulo"],
            "genero": filmes[filme_id]["genero"],
            "nota": nota,
        }
        for filme_id, nota in grafo_original.adj[usuario_id].items()
    ]
    usuario = {**usuarios[usuario_id]}
    usuario["generos_preferidos"] = generos_preferidos(grafo_original, usuario_id)
    return {
        "usuario": usuario,
        "avaliacoes": sorted(avaliacoes, key=lambda item: item["titulo"]),
        "generos_preferidos": usuario["generos_preferidos"],
        "grau": grafo_original.grau(usuario_id),
        "filmes_positivos": len(grafo_original.positivos(usuario_id)),
    }


@app.get("/api/usuarios/{usuario_id}/similares")
def obter_similares(usuario_id: str):
    validar_usuario(usuario_id)
    return similares(grafo_original, usuarios, usuario_id)


@app.get("/api/recomendacoes/{usuario_id}")
def obter_recomendacoes(
    usuario_id: str,
    quantidade: int = Query(default=20, ge=1, le=60),
):
    """Gera o ranking de filmes e os caminhos que justificam cada item."""
    validar_usuario(usuario_id)
    return {
        "usuario_id": usuario_id,
        "recomendacoes": recomendacoes(
            grafo_original, usuarios, filmes, usuario_id, quantidade
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
    """Monta recortes do grafo para a visualização SVG do frontend.

    Os modos retornam o grafo completo, a vizinhança direta, somente arestas
    positivas, uma expansão resumida ou os caminhos de uma recomendação.
    """
    simulacao_ativa = bool(
        usuario_simulado and usuario == usuario_simulado["id"]
    )
    if usuario and not simulacao_ativa:
        validar_usuario(usuario)

    grafo = grafo_simulacao if simulacao_ativa else grafo_original
    usuarios_grafo = usuarios_da_simulacao() if simulacao_ativa else usuarios
    caminhos = []
    mensagem = ""
    recomendacoes_usuario = []

    if usuario and modo in {"expandida", "caminho"}:
        recomendacoes_usuario = recomendacoes(
            grafo, usuarios_grafo, filmes, usuario, quantidade=len(filmes)
        )

    if modo == "todas":
        vertices = set(grafo.adj)
    elif modo == "vizinhos":
        vertices = {usuario} | grafo.vizinhos(usuario) if usuario else set()
    elif modo == "positivas":
        vertices = set(grafo.adj)
    elif modo == "expandida":
        usuarios_semelhantes = similares(
            grafo, usuarios_grafo, usuario, limite=len(usuarios_grafo)
        )[:5] if usuario else []
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
            par = (
                (origem, destino)
                if origem in usuarios_grafo
                else (destino, origem)
            )
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
            "nome": usuarios_grafo[vertice]["nome"] if tipo == "usuario" else filmes[vertice]["titulo"],
            "tipo": tipo,
            "grau": grafo.grau(vertice),
            "papel": papeis.get(vertice, "normal"),
            "similaridade": similaridades.get(vertice),
        }
        for vertice, tipo in grafo.tipo.items()
        if vertice in vertices
    ]
    arestas = []
    for usuario_id in usuarios_grafo:
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


def serializar_exemplo(item: dict, caminho: dict) -> dict:
    """Converte uma recomendação e um de seus caminhos para a tela inicial."""
    inicio, compartilhado, colaborador, candidato = caminho["vertices"]
    positivos_inicio = grafo_original.positivos(inicio)
    positivos_colaborador = grafo_original.positivos(colaborador)
    return {
        "disponivel": True,
        "usuario": {"id": inicio, "nome": usuarios[inicio]["nome"]},
        "filme_compartilhado": {
            "id": compartilhado,
            "titulo": filmes[compartilhado]["titulo"],
        },
        "colaborador": {
            "id": colaborador,
            "nome": usuarios[colaborador]["nome"],
        },
        "filme_recomendado": {
            "id": candidato,
            "titulo": filmes[candidato]["titulo"],
        },
        "nota_usuario": grafo_original.adj[inicio][compartilhado],
        "nota_compartilhada": grafo_original.adj[colaborador][compartilhado],
        "nota_colaborador": caminho["nota_colaborador"],
        "positivos_em_comum": len(positivos_inicio & positivos_colaborador),
        "positivos_uniao": len(positivos_inicio | positivos_colaborador),
        "similaridade": caminho["similaridade"],
        "pontuacao": item["pontuacao"],
    }


@app.get("/api/exemplo")
def obter_exemplo():
    """Seleciona um caminho real e completo para a explicação da página inicial.

    O exemplo conhecido da apresentação é preferido enquanto continuar válido
    na base ou na simulação. Se os dados mudarem, o primeiro caminho disponível
    mantém a seção funcional sem depender de IDs fixos.
    """
    nomes_preferidos = (
        "Mariana Costa",
        "Indiana Jones e os Caçadores da Arca Perdida",
        "Luiza Correia",
        "Seven",
    )
    inicio_preferido = next(
        (uid for uid, usuario in usuarios.items() if usuario["nome"] == nomes_preferidos[0]),
        None,
    )
    compartilhado_preferido = next(
        (fid for fid, filme in filmes.items() if filme["titulo"] == nomes_preferidos[1]),
        None,
    )
    colaborador_preferido = next(
        (uid for uid, usuario in usuarios.items() if usuario["nome"] == nomes_preferidos[2]),
        None,
    )
    candidato_preferido = next(
        (fid for fid, filme in filmes.items() if filme["titulo"] == nomes_preferidos[3]),
        None,
    )
    caminho_preferido = [
        inicio_preferido,
        compartilhado_preferido,
        colaborador_preferido,
        candidato_preferido,
    ]

    if all(caminho_preferido):
        itens = recomendacoes(
            grafo_original,
            usuarios,
            filmes,
            inicio_preferido,
            quantidade=len(filmes),
        )
        item = next(
            (item for item in itens if item["filme_id"] == candidato_preferido),
            None,
        )
        if item:
            caminho = next(
                (
                    caminho
                    for caminho in item["caminhos"]
                    if caminho["vertices"] == caminho_preferido
                ),
                None,
            )
            if caminho:
                return serializar_exemplo(item, caminho)

    for usuario_id in usuarios:
        itens = recomendacoes(
            grafo_original, usuarios, filmes, usuario_id, quantidade=len(filmes)
        )
        for item in itens:
            if item["caminhos"]:
                return serializar_exemplo(item, item["caminhos"][0])
    return {
        "disponivel": False,
        "mensagem": "Não há caminhos positivos para formar um exemplo nesta base.",
    }


@app.get("/api/analise")
def obter_analise():
    """Calcula distribuições descritivas usadas nos gráficos recolhidos."""
    grafo = grafo_original
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


def montar_estado_simulacao() -> dict:
    """Reúne perfil, avaliações e resultados atuais do usuário temporário."""
    if not usuario_simulado:
        return {
            "ativo": False,
            "usuario": None,
            "avaliacoes": [],
            "similares": [],
            "recomendacoes": [],
        }

    usuario_id = usuario_simulado["id"]
    usuarios_ativos = usuarios_da_simulacao()
    avaliacoes = [
        {
            "filme_id": filme_id,
            "titulo": filmes[filme_id]["titulo"],
            "genero": filmes[filme_id]["genero"],
            "nota": nota,
        }
        for filme_id, nota in grafo_simulacao.adj[usuario_id].items()
    ]
    return {
        "ativo": True,
        "usuario": {
            "id": usuario_id,
            "nome": usuario_simulado["nome"],
            "avaliacoes": len(avaliacoes),
            "filmes_positivos": len(grafo_simulacao.positivos(usuario_id)),
        },
        "avaliacoes": sorted(avaliacoes, key=lambda item: item["titulo"]),
        "similares": similares(
            grafo_simulacao, usuarios_ativos, usuario_id, limite=8
        ),
        "recomendacoes": recomendacoes(
            grafo_simulacao,
            usuarios_ativos,
            filmes,
            usuario_id,
            quantidade=20,
        ),
    }


@app.get("/api/simulacao")
def obter_estado_simulacao():
    """Retorna a simulação ativa para permitir recarregar o frontend."""
    return montar_estado_simulacao()


@app.post("/api/simulacao/usuario")
def iniciar_simulacao(pedido: NovoUsuarioSimulado):
    """Cria uma pessoa somente na cópia em memória do grafo."""
    global grafo_simulacao, usuario_simulado
    nome = pedido.nome.strip()
    if len(nome) < 2:
        raise HTTPException(status_code=422, detail="Informe um nome válido.")
    if any(usuario["nome"].casefold() == nome.casefold() for usuario in usuarios.values()):
        raise HTTPException(
            status_code=409,
            detail="Já existe uma pessoa com esse nome na base original.",
        )

    grafo_simulacao = deepcopy(grafo_original)
    alteracoes.clear()
    usuario_simulado = {
        "id": "usuario-simulado",
        "nome": nome,
        "generos_preferidos": [],
    }
    grafo_simulacao.add_vertice(usuario_simulado["id"], "usuario")
    return montar_estado_simulacao()


@app.post("/api/simulacao/avaliacao")
def simular_avaliacao(pedido: AvaliacaoSimulada):
    """Registra uma avaliação do usuário temporário e recalcula os resultados."""
    if not usuario_simulado or pedido.usuario_id != usuario_simulado["id"]:
        raise HTTPException(status_code=404, detail="Inicie uma nova pessoa primeiro.")
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
        "usuario_nome": usuario_simulado["nome"],
        "filme_id": pedido.filme_id,
        "filme_titulo": filmes[pedido.filme_id]["titulo"],
        "nota_nova": pedido.nota,
        "tipo": "adicionada",
    }
    alteracoes.append(alteracao)
    return montar_estado_simulacao()


@app.post("/api/simulacao/recomendar")
def comparar_simulacao(pedido: UsuarioSelecionado):
    """Mantém compatibilidade retornando os resultados atuais da nova pessoa."""
    if not usuario_simulado or pedido.usuario_id != usuario_simulado["id"]:
        raise HTTPException(status_code=404, detail="Simulação não encontrada.")
    return {
        "usuario_id": pedido.usuario_id,
        "antes": [],
        "depois": montar_estado_simulacao()["recomendacoes"],
        "alteracoes": alteracoes,
    }


@app.post("/api/simulacao/restaurar")
def restaurar_simulacao():
    """Descarta todas as avaliações temporárias e restaura a cópia original."""
    global grafo_simulacao, usuario_simulado
    grafo_simulacao = deepcopy(grafo_original)
    usuario_simulado = None
    alteracoes.clear()
    return {"restaurado": True}
