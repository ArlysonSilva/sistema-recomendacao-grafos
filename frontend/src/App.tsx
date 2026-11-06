import { useEffect, useMemo, useState } from 'react'

import HomePage from './HomePage'
import type {
  Analysis,
  Example,
  GraphData,
  Movie,
  Preferences,
  Recommendation,
  SimilarUser,
  SimulationState,
  Stats,
  User,
} from './types'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

/** Executa chamadas à API e uniformiza as mensagens de erro da interface. */
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Não foi possível carregar os dados.')
  }
  return response.json() as Promise<T>
}

/** Coordena a navegação entre as cinco telas e seus estados compartilhados. */
function App() {
  const pages = ['Início', 'Usuários', 'Recomendações', 'Grafo', 'Simulação']
  const [page, setPage] = useState('Início')
  const [stats, setStats] = useState<Stats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [movies, setMovies] = useState<Movie[]>([])
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [example, setExample] = useState<Example | null>(null)
  const [selectedUser, setSelectedUser] = useState('')
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [similarUsers, setSimilarUsers] = useState<SimilarUser[]>([])
  const [search, setSearch] = useState('')
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null)
  const [generated, setGenerated] = useState(false)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [graphMode, setGraphMode] = useState('todas')
  const [simName, setSimName] = useState('')
  const [simulation, setSimulation] = useState<SimulationState | null>(null)
  const [simMovie, setSimMovie] = useState('')
  const [simRating, setSimRating] = useState(5)
  const [simSelectedRecommendation, setSimSelectedRecommendation] = useState<Recommendation | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshSimulation, setRefreshSimulation] = useState(0)

  async function loadPageData() {
    const [newStats, newUsers, newMovies, newAnalysis] = await Promise.all([
      request<Stats>('/estatisticas'),
      request<User[]>('/usuarios'),
      request<Movie[]>('/filmes'),
      request<Analysis>('/analise'),
    ])
    setStats(newStats)
    setUsers(newUsers)
    setMovies(newMovies)
    setAnalysis(newAnalysis)

    request<Example>('/exemplo').then(setExample).catch(reason => setError(reason.message))
    const firstUser = newUsers[0]?.id || ''
    setSelectedUser(current => current || firstUser)
  }

  useEffect(() => {
    loadPageData()
      .catch(reason => setError(reason.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedUser) return
    Promise.all([
      request<Preferences>(`/usuarios/${selectedUser}/preferencias`),
      request<SimilarUser[]>(`/usuarios/${selectedUser}/similares`),
    ])
      .then(([newPreferences, newSimilarUsers]) => {
        setPreferences(newPreferences)
        setSimilarUsers(newSimilarUsers)
      })
      .catch(reason => setError(reason.message))
  }, [selectedUser, refreshSimulation])

  useEffect(() => {
    if (page !== 'Simulação') return
    request<SimulationState>('/simulacao')
      .then(state => {
        setSimulation(state)
        const rated = new Set(state.avaliacoes.map(item => item.filme_id))
        setSimMovie(current => current && !rated.has(current)
          ? current
          : movies.find(movie => !rated.has(movie.id))?.id || '')
      })
      .catch(reason => setError(reason.message))
  }, [page, movies])

  useEffect(() => {
    if (page !== 'Grafo' && page !== 'Simulação') return
    const userId = page === 'Grafo' ? selectedUser : simulation?.usuario?.id
    if (!userId) {
      setGraph(null)
      return
    }
    const selectedMovie = graphMode === 'caminho'
      ? (page === 'Grafo' ? selectedRecommendation : simSelectedRecommendation)?.filme_id
      : undefined
    const query = new URLSearchParams({ usuario: userId, modo: graphMode })
    if (selectedMovie) query.set('filme_recomendado', selectedMovie)
    request<GraphData>(`/grafo?${query}`)
      .then(setGraph)
      .catch(reason => setError(reason.message))
  }, [page, selectedUser, simulation?.usuario?.id, selectedRecommendation, simSelectedRecommendation, graphMode, refreshSimulation])

  useEffect(() => {
    if (page !== 'Grafo' || !selectedUser || recommendations.length) return
    request<{ recomendacoes: Recommendation[] }>(`/recomendacoes/${selectedUser}?quantidade=60`)
      .then(result => setRecommendations(result.recomendacoes))
      .catch(reason => setError(reason.message))
  }, [page, selectedUser, recommendations.length, generated])

  function getName(id: string) {
    return users.find(user => user.id === id)?.nome
      || movies.find(movie => movie.id === id)?.titulo
      || (simulation?.usuario?.id === id ? simulation.usuario.nome : undefined)
      || id
  }

  async function generateRecommendations() {
    if (!selectedUser) return
    setError('')
    setGenerated(true)
    setSelectedRecommendation(null)
    try {
      const result = await request<{ recomendacoes: Recommendation[] }>(
        `/recomendacoes/${selectedUser}?quantidade=60`,
      )
      setRecommendations(result.recomendacoes)
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  async function startSimulation() {
    if (!simName.trim()) return
    try {
      const state = await request<SimulationState>('/simulacao/usuario', {
        method: 'POST',
        body: JSON.stringify({ nome: simName.trim() }),
      })
      setSimulation(state)
      setSimMovie(movies[0]?.id || '')
      setSimRating(5)
      setSimSelectedRecommendation(null)
      setGraphMode('vizinhos')
      setRefreshSimulation(value => value + 1)
      setError('')
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  async function applySimulation() {
    if (!simulation?.usuario || !simMovie) return
    setError('')
    try {
      const state = await request<SimulationState>(
        '/simulacao/avaliacao',
        {
          method: 'POST',
          body: JSON.stringify({
            usuario_id: simulation.usuario.id,
            filme_id: simMovie,
            nota: simRating,
          }),
        },
      )
      setSimulation(state)
      const rated = new Set(state.avaliacoes.map(item => item.filme_id))
      setSimMovie(movies.find(movie => !rated.has(movie.id))?.id || '')
      setSimSelectedRecommendation(null)
      setGraphMode('vizinhos')
      setRefreshSimulation(value => value + 1)
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  async function restoreSimulation() {
    try {
      await request('/simulacao/restaurar', { method: 'POST' })
      setSimulation({ ativo: false, usuario: null, avaliacoes: [], similares: [], recomendacoes: [] })
      setSimName('')
      setSimMovie('')
      setSimSelectedRecommendation(null)
      setGraph(null)
      setError('')
      setRefreshSimulation(value => value + 1)
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  function selectUser(usuarioId: string) {
    setSelectedUser(usuarioId)
    setRecommendations([])
    setSelectedRecommendation(null)
    setGenerated(false)
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">CineConecta</div>
        <nav>
          {pages.map(name => (
            <button
              className={page === name ? 'selected' : ''}
              key={name}
              onClick={() => {
                setPage(name)
                if (name === 'Simulação') setGraphMode('vizinhos')
                setError('')
              }}
            >
              {name}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        {page !== 'Início' && <header className="header"><h1>{page}</h1></header>}
        {error && <div className="error">{error}<button onClick={() => setError('')}>Fechar</button></div>}
        {loading && <p>Carregando…</p>}

        {!loading && page === 'Início' && (
          <HomePage stats={stats} analysis={analysis} example={example} onNavigate={setPage} />
        )}
        {!loading && page === 'Usuários' && (
          <Usuarios
            users={users}
            selectedUser={selectedUser}
            preferences={preferences}
            similarUsers={similarUsers}
            search={search}
            setSearch={setSearch}
            selectUser={selectUser}
            getName={getName}
          />
        )}
        {!loading && page === 'Recomendações' && (
          <Recomendacoes
            users={users}
            selectedUser={selectedUser}
            setSelectedUser={selectUser}
            generated={generated}
            recommendations={recommendations}
            selectedRecommendation={selectedRecommendation}
            setSelectedRecommendation={setSelectedRecommendation}
            getName={getName}
            openGraph={() => { setGraphMode('caminho'); setPage('Grafo') }}
            generate={generateRecommendations}
          />
        )}
        {!loading && page === 'Grafo' && (
          <Grafo
            users={users}
            movies={movies}
            recommendations={recommendations}
            selectedUser={selectedUser}
            setSelectedUser={selectUser}
            selectedRecommendation={selectedRecommendation}
            setSelectedRecommendation={setSelectedRecommendation}
            graphMode={graphMode}
            setGraphMode={setGraphMode}
            graph={graph}
          />
        )}
        {!loading && page === 'Simulação' && (
          <Simulacao
            movies={movies}
            simName={simName}
            setSimName={setSimName}
            simulation={simulation}
            simMovie={simMovie}
            setSimMovie={setSimMovie}
            simRating={simRating}
            setSimRating={setSimRating}
            selectedRecommendation={simSelectedRecommendation}
            setSelectedRecommendation={setSimSelectedRecommendation}
            graph={graph}
            graphMode={graphMode}
            setGraphMode={setGraphMode}
            getName={getName}
            start={startSimulation}
            apply={applySimulation}
            restore={restoreSimulation}
          />
        )}
      </main>
    </div>
  )
}

/** Tela de consulta às avaliações, preferências e similaridades de cada usuário. */
function Usuarios(props: {
  users: User[]
  selectedUser: string
  preferences: Preferences | null
  similarUsers: SimilarUser[]
  search: string
  setSearch: (value: string) => void
  selectUser: (id: string) => void
  getName: (id: string) => string
}) {
  const visible = props.users.filter(user =>
    user.nome.toLocaleLowerCase('pt-BR').includes(props.search.toLocaleLowerCase('pt-BR')),
  )

  return (
    <div className="users-layout">
      <section className="panel">
        <input
          className="search"
          aria-label="Buscar usuário"
          placeholder="Buscar nome"
          value={props.search}
          onChange={event => props.setSearch(event.target.value)}
        />
        <div className="table-scroll">
          <table>
            <thead><tr><th>Nome</th><th>Avaliações</th><th>Gêneros</th><th>Grau</th></tr></thead>
            <tbody>
              {visible.map(user => (
                <tr
                  className={user.id === props.selectedUser ? 'selected-row clickable-row' : 'clickable-row'}
                  key={user.id}
                  onClick={() => props.selectUser(user.id)}
                >
                  <td>{user.nome}</td>
                  <td>{user.avaliacoes}</td>
                  <td>{user.generos_preferidos.join(', ') || 'Nenhum'}</td>
                  <td>{user.grau}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel user-detail">
        {props.preferences && <>
          <h2>{props.preferences.usuario.nome}</h2>
          <p><b>Preferências:</b> {props.preferences.generos_preferidos.join(', ') || 'Nenhuma'}</p>
          <h3>Filmes avaliados</h3>
          <table>
            <thead><tr><th>Filme</th><th>Gênero</th><th>Nota</th></tr></thead>
            <tbody>{props.preferences.avaliacoes.map(item => (
              <tr key={item.filme_id}><td>{item.titulo}</td><td>{item.genero}</td><td>{item.nota}</td></tr>
            ))}</tbody>
          </table>
          <h3>Usuários semelhantes</h3>
          {props.similarUsers.length ? (
            <table>
              <thead><tr><th>Nome</th><th>Jaccard</th><th>Filmes em comum</th></tr></thead>
              <tbody>{props.similarUsers.map(user => (
                <tr key={user.id}>
                  <td>{user.nome}</td>
                  <td>{user.similaridade.toFixed(3)}</td>
                  <td>{user.filmes_em_comum.map(props.getName).join(', ')}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p className="muted">Não há filmes positivos em comum.</p>}
        </>}
      </section>
    </div>
  )
}

/** Tela que apresenta o ranking e os caminhos U-F-U-F que explicam cada item. */
function Recomendacoes(props: {
  users: User[]
  selectedUser: string
  setSelectedUser: (id: string) => void
  generated: boolean
  recommendations: Recommendation[]
  selectedRecommendation: Recommendation | null
  setSelectedRecommendation: (item: Recommendation | null) => void
  getName: (id: string) => string
  openGraph: () => void
  generate: () => void
}) {
  const [search, setSearch] = useState('')
  const visible = props.recommendations.filter(item =>
    item.titulo.toLocaleLowerCase('pt-BR').includes(search.toLocaleLowerCase('pt-BR')),
  )

  return (
    <>
      <section className="panel controls">
        <label>Usuário
          <select value={props.selectedUser} onChange={event => props.setSelectedUser(event.target.value)}>
            {props.users.map(user => <option key={user.id} value={user.id}>{user.nome}</option>)}
          </select>
        </label>
        <button className="button primary" onClick={props.generate}>Gerar</button>
      </section>
      {props.generated && props.recommendations.length === 0 && (
        <p className="panel">Ainda não há conexões suficientes para recomendar filmes.</p>
      )}
      {props.recommendations.length > 0 && <section className="panel">
        <input
          className="search rec-search"
          aria-label="Buscar filme recomendado"
          placeholder="Buscar filme"
          value={search}
          onChange={event => setSearch(event.target.value)}
        />
        <table>
          <thead><tr><th>Filme</th><th>Gênero</th><th>Pontuação</th><th>Colaboradores</th><th></th></tr></thead>
          <tbody>{visible.map(item => (
            <tr key={item.filme_id} className={props.selectedRecommendation?.filme_id === item.filme_id ? 'selected-row' : ''}>
              <td>{item.titulo}</td>
              <td>{item.genero}</td>
              <td>{item.pontuacao.toFixed(2)} / 5</td>
              <td>{item.colaboradores}</td>
              <td><button className="link-button" onClick={() => props.setSelectedRecommendation(item)}>Ver caminho</button></td>
            </tr>
          ))}</tbody>
        </table>
      </section>}
      {props.selectedRecommendation && <section className="panel path-info">
        <div className="section-title">
          <h2>{props.selectedRecommendation.titulo}</h2>
          <button className="button" onClick={() => props.setSelectedRecommendation(null)}>Fechar</button>
        </div>
        {props.selectedRecommendation.caminhos.map(path => {
          const contributor = props.selectedRecommendation!.contribuidores.find(user => user.usuario_id === path.usuario_id)
          const sharedTitle = props.getName(path.filme_compartilhado)
          return (
            <div className="path-explanation" key={`${path.usuario_id}-${path.filme_compartilhado}`}>
              <div className="path-row">
                {path.vertices.map((id, vertexIndex) => (
                  <span className="path-part" key={`${id}-${vertexIndex}`}>
                    {vertexIndex > 0 && <b>→</b>}{props.getName(id)}
                  </span>
                ))}
              </div>
              <p>
                {contributor?.nome} e o usuário selecionado avaliaram {sharedTitle} positivamente.
                {' '}{contributor?.nome} deu nota {path.nota_colaborador} a {props.selectedRecommendation!.titulo}.
                {' '}Jaccard: {path.similaridade.toFixed(3)}.
              </p>
            </div>
          )
        })}
        <button className="button primary" onClick={props.openGraph}>Ver no grafo</button>
      </section>}
    </>
  )
}

const PATH_COLORS = ['#315F82', '#39785B', '#9A7044', '#76628F', '#4F7771']

function Grafo(props: {
  users: User[]; movies: Movie[]; recommendations: Recommendation[]; selectedUser: string; setSelectedUser: (id: string) => void
  selectedRecommendation: Recommendation | null; setSelectedRecommendation: (item: Recommendation | null) => void
  graphMode: string; setGraphMode: (mode: string) => void; graph: GraphData | null
}) {
  const needsMovie = props.graphMode === 'caminho'
  const [selectedPath, setSelectedPath] = useState<number | null>(null)
  useEffect(() => setSelectedPath(null), [props.graph, props.graphMode, props.selectedUser, props.selectedRecommendation])

  return <section className="panel graph-panel">
    <div className="graph-controls">
      <label>Usuário<select value={props.selectedUser} onChange={event => props.setSelectedUser(event.target.value)}>{props.users.map(user => <option key={user.id} value={user.id}>{user.nome}</option>)}</select></label>
      <label>Modo<select value={props.graphMode} onChange={event => props.setGraphMode(event.target.value)}>
        <option value="todas">Todas</option><option value="vizinhos">Vizinhan&#231;a</option><option value="expandida">Vizinhan&#231;a expandida</option><option value="positivas">Avalia&#231;&#245;es positivas</option><option value="caminho">Caminho da recomenda&#231;&#227;o</option>
      </select></label>
      {needsMovie && <label>Filme recomendado<select value={props.selectedRecommendation?.filme_id || ''} onChange={event => props.setSelectedRecommendation(props.recommendations.find(item => item.filme_id === event.target.value) || null)}>
        <option value="">Selecione</option>{props.recommendations.map(item => <option key={item.filme_id} value={item.filme_id}>{item.titulo}</option>)}
      </select></label>}
    </div>
    {props.graph?.mensagem && <p className="muted">{props.graph.mensagem}</p>}
    {props.graph && <GraphView graph={props.graph} onSelectUser={props.setSelectedUser} selectedPath={selectedPath} />}
    {props.graphMode === 'caminho' && !!props.graph?.caminhos.length && <div className="path-choices">
      {props.graph.caminhos.map((path, index) => {
        const collaborator = props.users.find(user => user.id === path.usuario_id)?.nome || path.usuario_id
        const shared = props.movies.find(movie => movie.id === path.filme_compartilhado)?.titulo || path.filme_compartilhado
        return <button key={`${path.usuario_id}-${path.filme_compartilhado}-${index}`} className={selectedPath === index ? 'path-choice selected-path' : 'path-choice'} style={{ '--path-color': PATH_COLORS[index % PATH_COLORS.length] } as React.CSSProperties} onClick={() => setSelectedPath(index)}>
          <span className="path-swatch" />{collaborator} · {shared} · nota {path.nota_colaborador} · Jaccard {path.similaridade.toFixed(3)}
        </button>
      })}
    </div>}
    <div className="graph-legend"><span><i className="user-color" />Usuários</span><span><i className="movie-color" />Filmes</span><span><i className="graph-edge-key" />Avaliação</span><span>Vértices {props.graph?.nodes.length ?? 0}</span><span>Arestas {props.graph?.edges.length ?? 0}</span></div>
  </section>
}

/**
 * Desenha o grafo em SVG sem biblioteca externa. A vizinhança usa disposição
 * radial, os caminhos usam as duas partições em colunas e o modo completo usa
 * uma simulação de forças determinística.
 */
function GraphView({ graph, onSelectUser, selectedPath }: { graph: GraphData; onSelectUser?: (id: string) => void; selectedPath: number | null }) {
  const [hoverNode, setHoverNode] = useState<string | null>(null)
  const [screenWidth, setScreenWidth] = useState(() => window.innerWidth)
  useEffect(() => {
    const updateWidth = () => setScreenWidth(window.innerWidth)
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])
  const sideSpace = screenWidth <= 650 ? 44 : screenWidth <= 760 ? 68 : screenWidth <= 900 ? 228 : 278
  const width = Math.max(320, Math.min(1200, screenWidth - sideSpace))
  const nodes = graph.nodes
  const edges = graph.edges
  const selectedUser = nodes.find(node => node.papel === 'selecionado')?.id
  const selectedNeighbors = new Set(edges.filter(edge => edge.source === selectedUser).map(edge => edge.target))
  const layout = useMemo(() => {
    const positions = new Map<string, { x: number; y: number }>()
    if (graph.modo === 'vizinhos') {
      const center = nodes.find(node => node.tipo === 'usuario')
      const movies = nodes.filter(node => node.tipo === 'filme')
      const height = Math.max(320, Math.min(420, 250 + movies.length * 12))
      if (center) positions.set(center.id, { x: width / 2, y: height / 2 })
      const radiusX = Math.min(width * 0.31, 125 + movies.length * 9)
      const radiusY = Math.min(height * 0.36, 110 + movies.length * 3)
      movies.forEach((node, index) => {
        const angle = -Math.PI / 2 + index * 2 * Math.PI / Math.max(1, movies.length)
        positions.set(node.id, { x: width / 2 + Math.cos(angle) * radiusX, y: height / 2 + Math.sin(angle) * radiusY })
      })
      return { positions, height }
    }

    if (graph.modo === 'expandida' || graph.modo === 'caminho') {
      let left = nodes.filter(node => node.tipo === 'usuario').sort((a, b) => (a.papel === 'selecionado' ? -1 : b.papel === 'selecionado' ? 1 : a.nome.localeCompare(b.nome)))
      let right = nodes.filter(node => node.tipo === 'filme').sort((a, b) => a.nome.localeCompare(b.nome))
      const height = Math.max(360, Math.min(520, Math.max(nodes.length, 12) * 27))
      const neighbors = (id: string, list: typeof nodes) => edges.filter(edge => edge.source === id || edge.target === id).map(edge => edge.source === id ? edge.target : edge.source).filter(other => list.some(node => node.id === other))
      for (let pass = 0; pass < 2; pass++) {
        const rightRank = new Map(right.map((node, i) => [node.id, i]))
        left = [...left].sort((a, b) => {
          const average = (node: typeof a) => { const values = neighbors(node.id, right).map(id => rightRank.get(id) ?? 0); return values.length ? values.reduce((x, y) => x + y, 0) / values.length : right.length }
          return (a.papel === 'selecionado' ? -100 : average(a)) - (b.papel === 'selecionado' ? -100 : average(b))
        })
        const leftRank = new Map(left.map((node, i) => [node.id, i]))
        right = [...right].sort((a, b) => {
          const average = (node: typeof a) => { const values = neighbors(node.id, left).map(id => leftRank.get(id) ?? 0); return values.length ? values.reduce((x, y) => x + y, 0) / values.length : left.length }
          return average(a) - average(b)
        })
      }
      const place = (column: typeof nodes, x: number) => column.forEach((node, i) => positions.set(node.id, { x, y: 28 + i * (height - 56) / Math.max(1, column.length - 1) }))
      place(left, width * 0.34); place(right, width * 0.66)
      return { positions, height }
    }

    const height = Math.max(420, Math.min(600, 320 + nodes.length * 2.8))
    const coords = nodes.map((node, index) => {
      const seed = [...node.id].reduce((sum, char) => sum + char.charCodeAt(0), 0)
      const angle = index * 2.399963 + seed * 0.013
      const spread = Math.sqrt((index + 1) / Math.max(1, nodes.length))
      return { id: node.id, x: width / 2 + Math.cos(angle) * width * 0.39 * spread, y: height / 2 + Math.sin(angle) * height * 0.39 * spread, vx: 0, vy: 0 }
    })
    const byId = new Map(coords.map(node => [node.id, node]))
    const springEdges = edges.map(edge => [byId.get(edge.source), byId.get(edge.target)] as const).filter(pair => pair[0] && pair[1])
    for (let step = 0; step < 140; step++) {
      for (let i = 0; i < coords.length; i++) for (let j = i + 1; j < coords.length; j++) {
        const a = coords[i], b = coords[j], dx = a.x - b.x || (i - j) * 0.01, dy = a.y - b.y || (i + j + 1) * 0.01
        const distance2 = Math.max(100, dx * dx + dy * dy), force = 40 / distance2
        a.vx += dx * force; a.vy += dy * force; b.vx -= dx * force; b.vy -= dy * force
      }
      for (const [a, b] of springEdges) {
        const dx = b!.x - a!.x, dy = b!.y - a!.y, distance = Math.max(1, Math.hypot(dx, dy)), force = (distance - 145) * 0.002
        a!.vx += dx / distance * force; a!.vy += dy / distance * force; b!.vx -= dx / distance * force; b!.vy -= dy / distance * force
      }
      for (const point of coords) {
        point.vx = Math.max(-7, Math.min(7, point.vx * 0.72)); point.vy = Math.max(-7, Math.min(7, point.vy * 0.72))
        point.x = Math.max(45, Math.min(width - 45, point.x + point.vx + (width / 2 - point.x) * 0.002)); point.y = Math.max(45, Math.min(height - 45, point.y + point.vy + (height / 2 - point.y) * 0.002))
      }
    }
    coords.forEach(point => positions.set(point.id, point))
    return { positions, height }
  }, [graph.modo, nodes, edges, width])

  const topIds = new Set([...nodes].sort((a, b) => b.grau - a.grau).slice(0, 10).map(node => node.id))
  const positiveOrAll = graph.modo === 'todas' || graph.modo === 'positivas'
  const visibleLabels = new Set(nodes.filter(node => node.id === selectedUser || selectedNeighbors.has(node.id) || topIds.has(node.id)).map(node => node.id))
  const labelPositions = new Map<string, { x: number; y: number; anchorEnd: boolean; lines: string[] }>()
  const usedLabelAreas: { left: number; right: number; top: number; bottom: number }[] = []
  const labelNodes = nodes.filter(node => !positiveOrAll || visibleLabels.has(node.id)).sort((a, b) => {
    const priority = (node: GraphData['nodes'][number]) => node.id === selectedUser ? -100 : selectedNeighbors.has(node.id) ? -50 : -node.grau
    return priority(a) - priority(b)
  })
  for (const node of labelNodes) {
    const point = layout.positions.get(node.id)
    if (!point) continue
    const suffix = graph.modo === 'expandida' && node.papel === 'semelhante' && node.similaridade !== null ? ` (${node.similaridade.toFixed(3)})` : ''
    const text = node.nome + suffix
    const columnMode = graph.modo === 'expandida' || graph.modo === 'caminho'
    const maxChars = Math.max(12, Math.floor(width * (columnMode ? 0.28 : 0.42) / 6.3))
    const lines: string[] = []
    let current = ''
    for (const word of text.split(' ')) {
      const next = current ? `${current} ${word}` : word
      if (next.length > maxChars && current) { lines.push(current); current = word }
      else current = next
    }
    if (current) lines.push(current)
    const estimatedWidth = Math.max(...lines.map(line => line.length)) * 6.3 + 8
    const anchorEnd = columnMode ? node.tipo === 'usuario' : point.x > width - estimatedWidth - 24
    const x = anchorEnd ? point.x - 14 : point.x + 14
    const labelWidth = Math.min(width - 30, estimatedWidth)
    const offsets = [0, ...Array.from({ length: 20 }, (_, index) => (index % 2 ? 1 : -1) * Math.ceil((index + 1) / 2) * 16)]
    let chosenY = point.y + 4
    for (const offset of offsets) {
      const y = Math.max(14, Math.min(layout.height - 8, point.y + 4 + offset))
      const area = { left: anchorEnd ? x - labelWidth : x, right: anchorEnd ? x : x + labelWidth, top: y - 11, bottom: y + lines.length * 14 }
      if (!usedLabelAreas.some(other => area.left < other.right + 3 && area.right + 3 > other.left && area.top < other.bottom + 2 && area.bottom + 2 > other.top)) {
        chosenY = y
        usedLabelAreas.push(area)
        break
      }
    }
    labelPositions.set(node.id, { x, y: chosenY, anchorEnd, lines })
  }
  const hoveredNeighbors = new Set(edges.filter(edge => edge.source === hoverNode || edge.target === hoverNode).flatMap(edge => [edge.source, edge.target]))
  const svgEdges = graph.modo === 'caminho'
    ? graph.caminhos.flatMap((path, index) => path.vertices.slice(0, -1).map((id, step) => {
      const target = path.vertices[step + 1]
      const edge = edges.find(item => (item.source === id && item.target === target) || (item.source === target && item.target === id))
      return edge ? { edge, from: id, to: target, route: index } : null
    }).filter((item): item is { edge: GraphData['edges'][number]; from: string; to: string; route: number } => item !== null))
    : edges.map(edge => ({ edge, from: edge.source, to: edge.target, route: -1 }))

  return <svg className="graph-svg" viewBox={`0 0 ${width} ${layout.height}`} role="img" aria-label="Grafo bipartido de usu&#225;rios e filmes">
    {svgEdges.map((item, index) => {
      const start = layout.positions.get(item.from), end = layout.positions.get(item.to)
      if (!start || !end) return null
      const key = `${item.edge.source}-${item.edge.target}-${item.route}-${index}`
      const hovered = hoverNode ? item.edge.source === hoverNode || item.edge.target === hoverNode : false
      const selected = selectedUser && positiveOrAll ? item.edge.source === selectedUser : false
      const fadedPath = graph.modo === 'caminho' && selectedPath !== null && selectedPath !== item.route
      const opacity = hoverNode ? (hovered ? 1 : 0.05) : fadedPath ? 0.05 : positiveOrAll && selectedUser ? (selected ? 0.85 : 0.05) : graph.modo === 'todas' ? 0.18 : graph.modo === 'positivas' ? 0.3 : graph.modo === 'expandida' ? 0.72 : 0.9
      return <line key={key} x1={start.x} y1={start.y} x2={end.x} y2={end.y}
        className="graph-edge" style={item.route >= 0 ? { stroke: PATH_COLORS[item.route % PATH_COLORS.length] } : undefined}
        strokeWidth={item.route >= 0 ? 2.5 : (selected || item.edge.destacado ? 2 : 1)} opacity={opacity}
        >
        <title>{(nodes.find(node => node.id === item.edge.source)?.nome || item.edge.source)} - {(nodes.find(node => node.id === item.edge.target)?.nome || item.edge.target)}, nota {item.edge.nota}</title>
      </line>
    })}
    {nodes.map(node => {
      const point = layout.positions.get(node.id); if (!point) return null
      const radius = Math.min(14, 5 + node.grau * 0.18)
      const isVisibleLabel = !positiveOrAll || visibleLabels.has(node.id)
      const hovered = hoverNode ? hoveredNeighbors.has(node.id) : false
      const selectedFade = positiveOrAll && selectedUser && node.id !== selectedUser && !selectedNeighbors.has(node.id)
      const fadedPath = graph.modo === 'caminho' && selectedPath !== null && !graph.caminhos[selectedPath]?.vertices.includes(node.id)
      const opacity = hoverNode ? (hovered ? 1 : 0.05) : fadedPath ? 0.45 : selectedFade ? 0.05 : 1
      const anchorEnd = point.x > width - 210
      const show = isVisibleLabel || hoverNode === node.id || (graph.modo === 'caminho' && nodes.length < 20)
      const labelPosition = labelPositions.get(node.id) || { x: anchorEnd ? point.x - radius - 7 : point.x + radius + 7, y: point.y + 4, anchorEnd, lines: [node.nome] }
      return <g key={node.id} opacity={opacity} onMouseEnter={() => setHoverNode(node.id)} onMouseLeave={() => setHoverNode(null)}>
        <circle data-node-id={node.id} cx={point.x} cy={point.y} r={radius} className={`graph-node ${node.tipo === 'usuario' ? 'user-node' : 'movie-node'} role-${node.papel}`} onClick={() => node.tipo === 'usuario' && onSelectUser?.(node.id)}>
          <title>{node.nome} - {node.tipo === 'usuario' ? 'Usuario' : 'Filme'} - grau {node.grau}{node.similaridade !== null ? ` - Jaccard ${node.similaridade.toFixed(3)}` : ''}</title>
        </circle>
        {show && <text className="graph-label" x={labelPosition.x} y={labelPosition.y} textAnchor={labelPosition.anchorEnd ? 'end' : 'start'}>{labelPosition.lines.map((line, index) => <tspan key={index} x={labelPosition.x} dy={index === 0 ? 0 : 14}>{line}</tspan>)}</text>}
      </g>
    })}
  </svg>
}

/** Tela de simulação: adiciona arestas somente na cópia em memória do backend. */
function Simulacao(props: {
  movies: Movie[]
  simName: string
  setSimName: (name: string) => void
  simulation: SimulationState | null
  simMovie: string
  setSimMovie: (id: string) => void
  simRating: number
  setSimRating: (value: number) => void
  selectedRecommendation: Recommendation | null
  setSelectedRecommendation: (item: Recommendation | null) => void
  graph: GraphData | null
  graphMode: string
  setGraphMode: (mode: string) => void
  getName: (id: string) => string
  start: () => void
  apply: () => void
  restore: () => void
}) {
  const active = Boolean(props.simulation?.ativo && props.simulation.usuario)
  const rated = new Set(props.simulation?.avaliacoes.map(item => item.filme_id) || [])
  const availableMovies = props.movies.filter(movie => !rated.has(movie.id))

  return <>
    <div className="simulation-layout">
      <section className="panel simulation-profile">
        <div className="section-title">
          <div><h2>Perfil e avaliações</h2><p>Cadastre uma pessoa temporária e registre suas notas.</p></div>
          {active && <button className="button" onClick={props.restore}>Restaurar</button>}
        </div>

        {!active ? <div className="simulation-start">
          <label>Nome da nova pessoa
            <input
              className="search"
              value={props.simName}
              maxLength={80}
              placeholder="Ex.: Gabriel Oliveira"
              onChange={event => props.setSimName(event.target.value)}
              onKeyDown={event => { if (event.key === 'Enter') props.start() }}
            />
          </label>
          <button className="button primary" disabled={props.simName.trim().length < 2} onClick={props.start}>Iniciar simulação</button>
        </div> : <>
          <dl className="simulation-summary">
            <div><dt>Nome</dt><dd>{props.simulation?.usuario?.nome}</dd></div>
            <div><dt>Avaliações</dt><dd>{props.simulation?.usuario?.avaliacoes}</dd></div>
            <div><dt>Positivas</dt><dd>{props.simulation?.usuario?.filmes_positivos}</dd></div>
          </dl>

          <div className="simulation-form">
            <label>Filme ainda não avaliado
              <select value={props.simMovie} onChange={event => props.setSimMovie(event.target.value)}>
                {availableMovies.map(movie => <option key={movie.id} value={movie.id}>{movie.titulo}</option>)}
              </select>
            </label>
            <label>Nota
              <select value={props.simRating} onChange={event => props.setSimRating(Number(event.target.value))}>
                {[1, 2, 3, 4, 5].map(value => <option key={value} value={value}>{value}</option>)}
              </select>
            </label>
            <button className="button primary" disabled={!props.simMovie} onClick={props.apply}>Registrar avaliação</button>
          </div>

          <div className="simulation-history">
            <h3>Histórico</h3>
            {props.simulation?.avaliacoes.length ? <table>
              <thead><tr><th>Filme</th><th>Gênero</th><th>Nota</th><th>Uso</th></tr></thead>
              <tbody>{props.simulation.avaliacoes.map(item => (
                <tr key={item.filme_id}>
                  <td>{item.titulo}</td><td>{item.genero}</td><td>{item.nota}</td>
                  <td className={item.nota >= 4 ? 'positive-note' : 'neutral-note'}>{item.nota >= 4 ? 'Preferência positiva' : 'Apenas registrada'}</td>
                </tr>
              ))}</tbody>
            </table> : <p className="muted">Nenhuma avaliação registrada.</p>}
          </div>
        </>}
      </section>

      <section className="panel simulation-results">
        <h2>Resultados</h2>
        {!active ? <p className="muted">Inicie uma nova pessoa para calcular similaridades e recomendações.</p> : <>
          <h3>Usuários semelhantes</h3>
          {props.simulation?.similares.length ? <table>
            <thead><tr><th>Usuário</th><th>Jaccard</th><th>Filmes positivos em comum</th></tr></thead>
            <tbody>{props.simulation.similares.map(user => (
              <tr key={user.id}><td>{user.nome}</td><td>{user.similaridade.toFixed(3)}</td><td>{user.filmes_em_comum.map(props.getName).join(', ')}</td></tr>
            ))}</tbody>
          </table> : <p className="muted">Ainda não há interesses positivos em comum. Registre notas 4 ou 5 para criar conexões.</p>}

          <h3>Recomendações</h3>
          {props.simulation?.recomendacoes.length ? <table>
            <thead><tr><th>Filme</th><th>Pontuação</th><th>Colaboradores</th><th>Caminho</th></tr></thead>
            <tbody>{props.simulation.recomendacoes.slice(0, 10).map(item => (
              <tr key={item.filme_id} className={props.selectedRecommendation?.filme_id === item.filme_id ? 'selected-row' : ''}>
                <td>{item.titulo}</td><td>{item.pontuacao.toFixed(3)}</td><td>{item.colaboradores}</td>
                <td><button className="link-button" onClick={() => { props.setSelectedRecommendation(item); props.setGraphMode('caminho') }}>Ver caminho</button></td>
              </tr>
            ))}</tbody>
          </table> : <p className="muted">Não há conexões positivas suficientes para recomendar filmes neste momento.</p>}

          {props.selectedRecommendation && <div className="simulation-paths">
            <h3>Caminhos para {props.selectedRecommendation.titulo}</h3>
            {props.selectedRecommendation.caminhos.map((path, index) => (
              <p key={`${path.usuario_id}-${path.filme_compartilhado}-${index}`}>
                {path.vertices.map(props.getName).join(' → ')} · Jaccard {path.similaridade.toFixed(3)} · nota {path.nota_colaborador}
              </p>
            ))}
          </div>}
        </>}
      </section>
    </div>

    <section className="panel">
      <div className="graph-controls">
        <h2>Grafo atualizado</h2>
        <label>Conexões
          <select disabled={!active} value={props.graphMode} onChange={event => props.setGraphMode(event.target.value)}>
            <option value="vizinhos">Vizinhança</option>
            <option value="positivas">Avaliações positivas</option>
            {props.selectedRecommendation && <option value="caminho">Caminho selecionado</option>}
          </select>
        </label>
      </div>
      {!active && <p className="muted">O grafo aparecerá após iniciar a simulação.</p>}
      {active && props.graph && <GraphView graph={props.graph} selectedPath={null} />}
      <div className="legend"><span><i className="simulated-color" />Nova avaliação simulada</span></div>
    </section>
  </>
}

export default App

