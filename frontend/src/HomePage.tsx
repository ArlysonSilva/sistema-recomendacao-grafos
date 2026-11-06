import type { Analysis, Example, Stats } from './types'

type HomePageProps = {
  stats: Stats | null
  analysis: Analysis | null
  example: Example | null
  onNavigate: (page: string) => void
}

/**
 * Apresentação acadêmica do projeto. Os totais e o exemplo são renderizados
 * exclusivamente com dados retornados pela API.
 */
function HomePage({ stats, analysis, example, onNavigate }: HomePageProps) {
  return <article className="home-page">
    <section className="home-hero" aria-labelledby="project-title">
      <p className="eyebrow">Sistema de recomendação baseado em grafos</p>
      <h1 id="project-title">CineConecta</h1>
      <p className="home-lead">Um sistema de recomendação de filmes que utiliza grafos bipartidos para identificar relações entre usuários e descobrir novos filmes a partir de avaliações compartilhadas.</p>
      <dl className="project-facts" aria-label="Números atuais da base">
        <div><dt>Usuários</dt><dd>{stats?.usuarios ?? '—'}</dd></div>
        <div><dt>Filmes</dt><dd>{stats?.filmes ?? '—'}</dd></div>
        <div><dt>Avaliações</dt><dd>{stats?.avaliacoes ?? '—'}</dd></div>
        <div><dt>Componentes conexas</dt><dd>{stats?.componentes_conexas ?? '—'}</dd></div>
      </dl>
    </section>

    <section className="academic-section split-section" aria-labelledby="graph-model-title">
      <div className="section-copy">
        <p className="section-index">01 · Representação dos dados</p>
        <h2 id="graph-model-title">Um grafo com dois conjuntos de vértices</h2>
        <p>O CineConecta separa os vértices em <strong>usuários</strong> e <strong>filmes</strong>. Um vértice representa uma entidade; uma aresta representa a relação criada quando uma pessoa avalia um filme.</p>
        <p>Cada aresta armazena a nota de 1 a 5. Como não existem ligações entre dois usuários nem entre dois filmes, o grafo é bipartido.</p>
        <div className="concept-legend" aria-label="Legenda do grafo">
          <span><i className="user-dot" />Usuário</span>
          <span><i className="movie-dot" />Filme</span>
          <span><i className="edge-line" />Avaliação</span>
        </div>
      </div>
      <BipartiteModel />
    </section>

    <section className="academic-section similarity-section" aria-labelledby="similarity-title">
      <div className="section-heading">
        <p className="section-index">02 · Interesses em comum</p>
        <h2 id="similarity-title">Avaliações positivas e similaridade de Jaccard</h2>
      </div>
      <div className="similarity-grid">
        <div>
          <h3>Preferência positiva</h3>
          <p>Notas <strong>4 ou 5</strong> indicam uma avaliação positiva. Notas 1, 2 ou 3 permanecem armazenadas no grafo, mas não são usadas para identificar interesses em comum.</p>
          <div className="rating-scale" aria-label="Classificação das notas">
            <span>1</span><span>2</span><span>3</span><span className="positive-rating">4</span><span className="positive-rating">5</span>
          </div>
        </div>
        <div className="formula-explanation">
          <h3>Jaccard</h3>
          <p className="formula" aria-label="J de A B é igual à interseção de A e B dividida pela união de A e B">J(A,B) = |A ∩ B| / |A ∪ B|</p>
          <dl>
            <div><dt>Interseção</dt><dd>filmes positivos em comum.</dd></div>
            <div><dt>União</dt><dd>todos os filmes positivos avaliados por pelo menos um dos usuários.</dd></div>
          </dl>
          <p>Quanto maior o resultado, maior a semelhança entre as preferências. Esse valor não é a nota média dos filmes.</p>
        </div>
      </div>
    </section>

    <section className="academic-section recommendation-section" aria-labelledby="recommendation-title">
      <div className="section-heading">
        <p className="section-index">03 · Busca e cálculo</p>
        <h2 id="recommendation-title">Como nasce uma recomendação</h2>
        <p>A busca em largura (BFS) parte de um usuário e percorre o grafo por níveis. Em três arestas, ela pode chegar a um filme ainda não avaliado pela pessoa inicial.</p>
      </div>
      <ol className="bfs-levels" aria-label="Níveis percorridos pela BFS">
        <li><span>nível 0</span><strong>Usuário inicial</strong></li>
        <li><span>nível 1</span><strong>Filme compartilhado</strong></li>
        <li><span>nível 2</span><strong>Usuário semelhante</strong></li>
        <li><span>nível 3</span><strong>Filme candidato</strong></li>
      </ol>
      <div className="calculation-notes">
        <p><strong>Seleção do candidato.</strong> O último filme do caminho precisa ter avaliação positiva do usuário semelhante e ainda não pode ter sido avaliado pelo usuário inicial.</p>
        <p><strong>Pontuação.</strong> As notas dos colaboradores são combinadas por uma média ponderada pela similaridade Jaccard. O resultado é calculado diretamente a partir das avaliações e relações existentes no grafo.</p>
        <p><strong>Papel dos gêneros.</strong> Eles classificam o catálogo e ajudam na leitura dos dados, mas não participam diretamente do Jaccard, da BFS ou da pontuação atual.</p>
      </div>
    </section>

    <section className="academic-section real-example" aria-labelledby="example-title">
      <div className="section-heading">
        <p className="section-index">04 · Dados da API</p>
        <h2 id="example-title">Exemplo real do funcionamento</h2>
        <p>O caminho abaixo é selecionado pelo backend entre as relações existentes na base atual.</p>
      </div>
      {example?.disponivel ? <>
        <ExampleGraph example={example} />
        <p className="example-explanation"><strong>{example.usuario?.nome}</strong> e <strong>{example.colaborador?.nome}</strong> avaliaram positivamente o mesmo filme. Como {example.colaborador?.nome} também gostou de <strong>{example.filme_recomendado?.titulo}</strong>, sua avaliação pode contribuir para recomendar esse título a {example.usuario?.nome}.</p>
        <dl className="example-results">
          <div><dt>Jaccard</dt><dd>{example.similaridade?.toFixed(3)}</dd><small>{example.positivos_em_comum} em comum / {example.positivos_uniao} na união</small></div>
          <div><dt>Pontuação</dt><dd>{example.pontuacao?.toFixed(3)}</dd><small>retornada pelo recomendador</small></div>
        </dl>
      </> : <p className="empty-message">{example?.mensagem || 'Carregando exemplo da API.'}</p>}
    </section>

    <section className="academic-section application-section" aria-labelledby="application-title">
      <div className="section-heading">
        <p className="section-index">05 · Conhecendo a aplicação</p>
        <h2 id="application-title">Quatro formas de explorar o sistema</h2>
      </div>
      <div className="feature-list">
        <button onClick={() => onNavigate('Usuários')}><strong>Usuários</strong><span>Consulta às avaliações, preferências e usuários semelhantes.</span></button>
        <button onClick={() => onNavigate('Recomendações')}><strong>Recomendações</strong><span>Filmes candidatos e caminhos que justificam cada resultado.</span></button>
        <button onClick={() => onNavigate('Grafo')}><strong>Grafo</strong><span>Exploração das conexões entre pessoas e filmes.</span></button>
        <button onClick={() => onNavigate('Simulação')}><strong>Simulação</strong><span>Inclusão temporária de avaliações para observar as mudanças.</span></button>
      </div>
    </section>

    <details className="home-charts">
      <summary>Gráficos descritivos da base</summary>
      <p>Distribuições complementares calculadas pela API. A seção permanece recolhida para preservar a sequência didática.</p>
      <div className="chart-grid">
        <Bars title="Filmes por gênero" rows={analysis?.filmes_por_genero || []} />
        <Bars title="Avaliações por usuário" rows={analysis?.avaliacoes_por_usuario || []} />
        <Bars title="Grau dos usuários" rows={analysis?.grau_usuarios || []} />
        <Bars title="Grau dos filmes" rows={(analysis?.grau_filmes || []).map(item => ({ nome: item.titulo, valor: item.valor }))} />
        <Bars title="Similaridade entre usuários" rows={(analysis?.similaridade_usuarios || []).slice(0, 12).map(item => ({ nome: `${item.usuario} / ${item.outro}`, valor: item.similaridade }))} />
      </div>
    </details>
  </article>
}

/** Ilustração estática do conceito; os nomes são didáticos, não dados da API. */
function BipartiteModel() {
  return <figure className="concept-figure">
    <svg viewBox="0 0 520 330" role="img" aria-labelledby="model-graph-title model-graph-desc">
      <title id="model-graph-title">Exemplo de grafo bipartido</title>
      <desc id="model-graph-desc">Dois usuários azuis ligados a três filmes verdes por arestas que armazenam notas.</desc>
      <text className="column-title" x="100" y="28">Usuários</text>
      <text className="column-title" x="420" y="28">Filmes</text>
      <g className="model-edges">
        <line x1="105" y1="105" x2="415" y2="75" /><line x1="105" y1="105" x2="415" y2="165" />
        <line x1="105" y1="235" x2="415" y2="165" /><line x1="105" y1="235" x2="415" y2="255" />
      </g>
      <g className="edge-ratings"><text x="250" y="82">5</text><text x="250" y="132">4</text><text x="250" y="210">5</text><text x="250" y="260">3</text></g>
      <g className="model-users"><circle cx="105" cy="105" r="17" /><circle cx="105" cy="235" r="17" /></g>
      <g className="model-movies"><circle cx="415" cy="75" r="17" /><circle cx="415" cy="165" r="17" /><circle cx="415" cy="255" r="17" /></g>
      <g className="model-labels"><text x="75" y="110" textAnchor="end">Pessoa A</text><text x="75" y="240" textAnchor="end">Pessoa B</text><text x="445" y="80">Filme 1</text><text x="445" y="170">Filme 2</text><text x="445" y="260">Filme 3</text></g>
    </svg>
    <figcaption>A nota fica associada à aresta, não ao vértice.</figcaption>
  </figure>
}

/** Desenha o caminho retornado por /api/exemplo como um recorte bipartido. */
function ExampleGraph({ example }: { example: Example }) {
  const usuario = wrapSvgLabel(example.usuario?.nome)
  const colaborador = wrapSvgLabel(example.colaborador?.nome)
  const compartilhado = wrapSvgLabel(example.filme_compartilhado?.titulo)
  const candidato = wrapSvgLabel(example.filme_recomendado?.titulo)

  return <figure className="example-graph">
    <svg viewBox="0 0 920 300" role="img" aria-labelledby="example-graph-title example-graph-desc">
      <title id="example-graph-title">Caminho real de uma recomendação</title>
      <desc id="example-graph-desc">Dois usuários ligados a um filme compartilhado e o usuário colaborador ligado ao filme candidato.</desc>
      <text className="column-title" x="190" y="28">Usuários</text>
      <text className="column-title" x="700" y="28">Filmes</text>
      <g className="example-edges">
        <line x1="205" y1="88" x2="705" y2="88" />
        <line x1="205" y1="222" x2="705" y2="88" />
        <line x1="205" y1="222" x2="705" y2="222" />
      </g>
      <g className="example-ratings">
        <text x="455" y="77">nota {example.nota_usuario}</text>
        <text x="455" y="147">nota {example.nota_compartilhada}</text>
        <text x="455" y="211">nota {example.nota_colaborador}</text>
      </g>
      <g className="example-users"><circle cx="205" cy="88" r="14" /><circle cx="205" cy="222" r="14" /></g>
      <g className="example-movies"><circle cx="705" cy="88" r="14" /><circle className="candidate-node" cx="705" cy="222" r="18" /><circle cx="705" cy="222" r="11" /></g>
      <g className="example-labels">
        <SvgLabel lines={usuario} x={175} y={93} anchor="end" />
        <SvgLabel lines={colaborador} x={175} y={227} anchor="end" />
        <SvgLabel lines={compartilhado} x={735} y={93} />
        <SvgLabel lines={candidato} x={735} y={227} />
        <text className="candidate-label" x="735" y={239 + candidato.length * 15}>filme candidato</text>
      </g>
    </svg>
  </figure>
}

/** Quebra rótulos longos sem conhecer previamente os títulos retornados pela API. */
function wrapSvgLabel(value = '', limit = 24) {
  const lines: string[] = []
  let current = ''
  for (const word of value.split(' ')) {
    const next = current ? `${current} ${word}` : word
    if (next.length > limit && current) {
      lines.push(current)
      current = word
    } else {
      current = next
    }
  }
  if (current) lines.push(current)
  return lines
}

function SvgLabel({ lines, x, y, anchor = 'start' }: { lines: string[]; x: number; y: number; anchor?: 'start' | 'end' }) {
  return <text x={x} y={y} textAnchor={anchor}>
    {lines.map((line, index) => <tspan key={line} x={x} dy={index === 0 ? 0 : 15}>{line}</tspan>)}
  </text>
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

export default HomePage
