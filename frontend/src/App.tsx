import { useEffect, useMemo, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

type Stats = {
  usuarios: number
  filmes: number
  avaliacoes: number
  componentes_conexas: number
}

type User = {
  id: string
  nome: string
  generos_preferidos: string[]
  avaliacoes: number
  grau: number
}

type Movie = {
  id: string
  titulo: string
  genero: string
  avaliacoes: number
  grau: number
}

type MovieRating = {
  filme_id: string
  titulo: string
  genero: string
  nota: number
}

type Preferences = {
  usuario: User
  avaliacoes: MovieRating[]
  generos_preferidos: string[]
  grau: number
}

type SimilarUser = {
  id: string
  nome: string
  similaridade: number
  filmes_em_comum: string[]
}

type RecommendationPath = {
  vertices: string[]
  usuario_id: string
  filme_compartilhado: string
  nota_colaborador: number
  similaridade: number
}

type Contributor = {
  usuario_id: string
  nome: string
  nota: number
  similaridade: number
  filmes_em_comum: string[]
}

type Recommendation = {
  filme_id: string
  titulo: string
  genero: string
  pontuacao: number
  colaboradores: number
  caminhos: RecommendationPath[]
  contribuidores: Contributor[]
}

type GraphData = {
  nodes: { id: string; nome: string; tipo: 'usuario' | 'filme'; grau: number; papel: string; similaridade: number | null }[]
  edges: { source: string; target: string; nota: number; positiva: boolean; direta: boolean; simulada: boolean; destacado: boolean; rotas?: number[] }[]
  componentes_conexas: number
  caminhos: RecommendationPath[]
  mensagem: string
  modo: string
}

type Example = {
  disponivel: boolean
  mensagem?: string
  usuario?: { id: string; nome: string }
  filme_compartilhado?: { id: string; titulo: string }
  colaborador?: { id: string; nome: string }
  filme_recomendado?: { id: string; titulo: string }
  nota_usuario?: number
  nota_compartilhada?: number
  nota_colaborador?: number
  similaridade?: number
  pontuacao?: number
}

type Analysis = {
  filmes_por_genero: { nome: string; valor: number }[]
  avaliacoes_por_genero: { nome: string; valor: number }[]
  avaliacoes_por_usuario: { id: string; nome: string; valor: number }[]
  filmes_mais_avaliados: { id: string; titulo: string; valor: number }[]
  grau_usuarios: { nome: string; valor: number }[]
  grau_filmes: { titulo: string; valor: number }[]
  similaridade_usuarios: { usuario: string; outro: string; similaridade: number }[]
}

type SimulationChange = {
  usuario_nome: string
  filme_titulo: string
  nota_nova: number
}

type Comparison = {
  antes: Recommendation[]
  depois: Recommendation[]
  alteracoes: SimulationChange[]
}

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
  const [simUser, setSimUser] = useState('')
  const [simPreferences, setSimPreferences] = useState<Preferences | null>(null)
  const [simMovie, setSimMovie] = useState('')
  const [simRating, setSimRating] = useState(5)
  const [simChanges, setSimChanges] = useState<SimulationChange[]>([])
  const [comparison, setComparison] = useState<Comparison | null>(null)
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
    const mariana = newUsers.find(user => user.nome === 'Mariana Costa')?.id
    const firstUser = mariana || newUsers[0]?.id || ''
    setSelectedUser(current => current || firstUser)
    setSimUser(current => current || firstUser)
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
    if (!simUser) return
    request<Preferences>(`/usuarios/${simUser}/preferencias`)
      .then(newPreferences => {
        setSimPreferences(newPreferences)
        const rated = new Set(newPreferences.avaliacoes.map(item => item.filme_id))
        setSimMovie(current => current && !rated.has(current)
          ? current
          : movies.find(movie => !rated.has(movie.id))?.id || '')
      })
      .catch(reason => setError(reason.message))
  }, [simUser, refreshSimulation, movies])

  useEffect(() => {
    if (page !== 'Grafo' && page !== 'Simulação') return
    const userId = page === 'Grafo' ? selectedUser : simUser
    if (!userId) return
    const selectedMovie = page === 'Grafo' && graphMode === 'caminho' ? selectedRecommendation?.filme_id : undefined
    const query = new URLSearchParams({ usuario: userId, modo: graphMode })
    if (selectedMovie) query.set('filme_recomendado', selectedMovie)
    request<GraphData>(`/grafo?${query}`)
      .then(setGraph)
      .catch(reason => setError(reason.message))
  }, [page, selectedUser, simUser, selectedRecommendation, graphMode, refreshSimulation])

  useEffect(() => {
    if (page !== 'Grafo' || !selectedUser || recommendations.length) return
    request<{ recomendacoes: Recommendation[] }>(`/recomendacoes/${selectedUser}?quantidade=60`)
      .then(result => setRecommendations(result.recomendacoes))
      .catch(reason => setError(reason.message))
  }, [page, selectedUser, recommendations.length, generated])

  function getName(id: string) {
    return users.find(user => user.id === id)?.nome
      || movies.find(movie => movie.id === id)?.titulo
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

  async function prepareExample() {
    const mariana = users.find(user => user.nome === 'Mariana Costa')
    if (!mariana) return
    try {
      const details = await request<Preferences>(`/usuarios/${mariana.id}/preferencias`)
      const rated = new Set(details.avaliacoes.map(item => item.filme_id))
      const matrix = movies.find(movie => movie.titulo === 'Matrix' && !rated.has(movie.id))
      const nextMovie = matrix || movies.find(movie => !rated.has(movie.id))
      if (!nextMovie) {
        setError('Mariana já avaliou todos os filmes.')
        return
      }
      setSimUser(mariana.id)
      setSimPreferences(details)
      setSimMovie(nextMovie.id)
      setSimRating(5)
      setError('')
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  async function applySimulation() {
    if (!simUser || !simMovie) return
    setError('')
    try {
      const result = await request<{ alteracoes: SimulationChange[] }>(
        '/simulacao/avaliacao',
        {
          method: 'POST',
          body: JSON.stringify({
            usuario_id: simUser,
            filme_id: simMovie,
            nota: simRating,
          }),
        },
      )
      const after = await request<Comparison>('/simulacao/recomendar', {
        method: 'POST',
        body: JSON.stringify({ usuario_id: simUser }),
      })
      setSimChanges(result.alteracoes)
      setComparison(after)
      await loadPageData()
      setRefreshSimulation(value => value + 1)
    } catch (reason) {
      setError((reason as Error).message)
    }
  }

  async function restoreSimulation() {
    try {
      await request('/simulacao/restaurar', { method: 'POST' })
      setSimChanges([])
      setComparison(null)
      setError('')
      await loadPageData()
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
              onClick={() => { setPage(name); setError('') }}
            >
              {name}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="header"><h1>{page}</h1></header>
        {error && <div className="error">{error}<button onClick={() => setError('')}>Fechar</button></div>}
        {loading && <p>Carregando…</p>}

        {!loading && page === 'Início' && (
          <Inicio stats={stats} analysis={analysis} example={example} />
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
            users={users}
            movies={movies}
            simUser={simUser}
            setSimUser={setSimUser}
            simPreferences={simPreferences}
            simMovie={simMovie}
            setSimMovie={setSimMovie}
            simRating={simRating}
            setSimRating={setSimRating}
            simChanges={simChanges}
            comparison={comparison}
            graph={graph}
            graphMode={graphMode}
            setGraphMode={setGraphMode}
            getName={getName}
            prepareExample={prepareExample}
            apply={applySimulation}
            restore={restoreSimulation}
          />
        )}
      </main>
    </div>
  )
}

function Inicio({ stats, analysis, example }: { stats: Stats | null; analysis: Analysis | null; example: Example | null }) {
  const componentes = stats?.componentes_conexas
  return <div className="home-content">
    <p className="home-intro">CineConecta é um sistema de recomendação de filmes que utiliza um grafo bipartido para relacionar usuários, filmes e avaliações.</p>
    <p className="home-counts">{stats?.usuarios ?? '—'} usuários · {stats?.filmes ?? '—'} filmes · {stats?.avaliacoes ?? '—'} avaliações · {componentes ?? '—'} componente{componentes === 1 ? '' : 's'} conexa{componentes === 1 ? '' : 's'}</p>
    <section className="home-how"><h2>Como funciona</h2>
      <ul>
        <li><strong>Grafo bipartido:</strong> usuários e filmes são os vértices. Uma avaliação cria uma ligação entre a pessoa e o filme, armazenando a nota.</li>
        <li><strong>Preferência positiva:</strong> avaliações 4 e 5 são consideradas positivas e utilizadas para identificar interesses em comum.</li>
        <li><strong>Jaccard:</strong> mede a semelhança entre dois usuários comparando os filmes que ambos avaliaram positivamente.</li>
        <li><strong>BFS:</strong> percorre as conexões do grafo por níveis para encontrar usuários relacionados e filmes que podem ser recomendados.</li>
        <li><strong>Pontuação:</strong> combina as notas dadas pelos usuários colaboradores, considerando a similaridade entre eles.</li>
        <li><strong>Gêneros:</strong> ajudam a identificar e apresentar as categorias dos filmes, mas não participam diretamente do cálculo atual de Jaccard ou BFS.</li>
      </ul>
    </section>
    <section className="home-example"><h2>Exemplo real</h2>
      {example?.disponivel ? <div className="example-box">
        <p className="example-route">{example.usuario?.nome} &rarr; {example.filme_compartilhado?.titulo} &rarr; {example.colaborador?.nome} &rarr; {example.filme_recomendado?.titulo}</p>
        <p>Esse caminho levou à recomendação: {example.colaborador?.nome} avaliou {example.filme_recomendado?.titulo} com nota {example.nota_colaborador}, similaridade {example.similaridade?.toFixed(3)} e pontuação {example.pontuacao?.toFixed(3)}.</p>
      </div> : <p>{example?.mensagem || 'Carregando exemplo.'}</p>}
    </section>
    <details className="home-charts"><summary>Gráficos</summary><div className="chart-grid">
      <Bars title="Filmes por gênero" rows={analysis?.filmes_por_genero || []} />
      <Bars title="Avaliações por usuário" rows={analysis?.avaliacoes_por_usuario || []} />
      <Bars title="Grau dos usuários" rows={analysis?.grau_usuarios || []} />
      <Bars title="Grau dos filmes" rows={(analysis?.grau_filmes || []).map(item => ({ nome: item.titulo, valor: item.valor }))} />
      <Bars title="Similaridade entre usuários" rows={(analysis?.similaridade_usuarios || []).slice(0, 12).map(item => ({ nome: `${item.usuario} / ${item.outro}`, valor: item.similaridade }))} />
    </div></details>
  </div>
}


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
                  <td>{user.generos_preferidos.join(', ') || '?'}</td>
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
          <p><b>Preferências:</b> {props.preferences.generos_preferidos.join(', ') || '?'}</p>
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
                    {vertexIndex > 0 && <b>â†’</b>}{props.getName(id)}
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
          <span className="path-swatch" />{collaborator} ? {shared} ? nota {path.nota_colaborador} ? Jaccard {path.similaridade.toFixed(3)}
        </button>
      })}
    </div>}
    <div className="graph-legend"><span><i className="user-color" />Usuários</span><span><i className="movie-color" />Filmes</span><span><i className="graph-edge-key" />Avaliação</span><span>Vértices {props.graph?.nodes.length ?? 0}</span><span>Arestas {props.graph?.edges.length ?? 0}</span></div>
  </section>
}

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

function Simulacao(props: {
  users: User[]
  movies: Movie[]
  simUser: string
  setSimUser: (id: string) => void
  simPreferences: Preferences | null
  simMovie: string
  setSimMovie: (id: string) => void
  simRating: number
  setSimRating: (value: number) => void
  simChanges: SimulationChange[]
  comparison: Comparison | null
  graph: GraphData | null
  graphMode: string
  setGraphMode: (mode: string) => void
  getName: (id: string) => string
  prepareExample: () => void
  apply: () => void
  restore: () => void
}) {
  const rated = new Set(props.simPreferences?.avaliacoes.map(item => item.filme_id) || [])
  const availableMovies = props.movies.filter(movie => !rated.has(movie.id))
  const beforeIds = new Set(props.comparison?.antes.map(item => item.filme_id) || [])
  const afterIds = new Set(props.comparison?.depois.map(item => item.filme_id) || [])
  const removed = props.comparison?.antes.filter(item => !afterIds.has(item.filme_id)) || []
  const added = props.comparison?.depois.filter(item => !beforeIds.has(item.filme_id)) || []

  return <>
    <div className="steps">
      <section className="panel">
        <h2>1. Escolher pessoa</h2>
        <label>Pessoa
          <select value={props.simUser} onChange={event => props.setSimUser(event.target.value)}>
            {props.users.map(user => <option key={user.id} value={user.id}>{user.nome}</option>)}
          </select>
        </label>
        <button className="button" onClick={props.prepareExample}>Exemplo</button>
      </section>
      <section className="panel">
        <h2>2. Avaliar filme</h2>
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
        <button className="button primary" disabled={!props.simMovie} onClick={props.apply}>Aplicar</button>
      </section>
      <section className="panel">
        <h2>3. Ver resultado</h2>
        <p>Você adicionou uma avaliação. Veja como as conexões e recomendações mudaram.</p>
        <button className="button" onClick={props.restore}>Restaurar</button>
      </section>
    </div>

    {props.simChanges.length > 0 && <section className="panel">
      <h2>Avaliações adicionadas</h2>
      <table>
        <thead><tr><th>Pessoa</th><th>Filme</th><th>Nota</th></tr></thead>
        <tbody>{props.simChanges.map((change, index) => (
          <tr key={`${change.usuario_nome}-${change.filme_titulo}-${index}`}>
            <td>{change.usuario_nome}</td><td>{change.filme_titulo}</td><td>{change.nota_nova}</td>
          </tr>
        ))}</tbody>
      </table>
    </section>}

    {props.comparison && <section className="panel">
      <h2>Recomendações antes e depois</h2>
      <p className="difference">
        Saíram: {removed.map(item => item.titulo).join(', ') || 'nenhum filme'}.
        {' '}Entraram: {added.map(item => item.titulo).join(', ') || 'nenhum filme'}.
      </p>
      <div className="comparison">
        <div><h3>Antes</h3><RecommendationList items={props.comparison.antes} /></div>
        <div><h3>Depois</h3><RecommendationList items={props.comparison.depois} /></div>
      </div>
    </section>}

    <section className="panel">
      <div className="graph-controls">
        <h2>Grafo atualizado</h2>
        <label>Conexões
          <select value={props.graphMode} onChange={event => props.setGraphMode(event.target.value)}>
            <option value="vizinhos">Vizinhança</option>
            <option value="positivas">Avaliações positivas</option>
            <option value="todos">Todas</option>
          </select>
        </label>
      </div>
      {props.graph && <GraphView graph={props.graph} selectedPath={null} />}
      <div className="legend"><span><i className="simulated-color" />Nova avaliação simulada</span></div>
    </section>
  </>
}

function RecommendationList({ items }: { items: Recommendation[] }) {
  if (!items.length) return <p className="muted">Sem recomendações por conexões positivas.</p>
  return <table>
    <thead><tr><th>Filme</th><th>Pontuação</th></tr></thead>
    <tbody>{items.slice(0, 8).map(item => (
      <tr key={item.filme_id}><td>{item.titulo}</td><td>{item.pontuacao.toFixed(2)}</td></tr>
    ))}</tbody>
  </table>
}

function Bars({ title, rows }: { title: string; rows: { nome: string; valor: number }[] }) {
  const max = Math.max(1, ...rows.map(row => row.valor))
  return <section className="chart">
    <h3>{title}</h3>
    {rows.map((row, index) => (
      <div className="bar-row" key={`${row.nome}-${index}`}>
        <span title={row.nome}>{row.nome}</span>
        <div><i style={{ width: `${Math.max(2, row.valor / max * 100)}%` }} /></div>
        <b>{Number.isInteger(row.valor) ? row.valor : row.valor.toFixed(2)}</b>
      </div>
    ))}
  </section>
}

export default App

