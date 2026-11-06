/** Contratos JSON compartilhados entre as telas e a API do CineConecta. */
export type Stats = {
  usuarios: number
  filmes: number
  avaliacoes: number
  componentes_conexas: number
}

export type User = {
  id: string
  nome: string
  generos_preferidos: string[]
  avaliacoes: number
  grau: number
}

export type Movie = {
  id: string
  titulo: string
  genero: string
  avaliacoes: number
  grau: number
}

export type MovieRating = {
  filme_id: string
  titulo: string
  genero: string
  nota: number
}

export type Preferences = {
  usuario: User
  avaliacoes: MovieRating[]
  generos_preferidos: string[]
  grau: number
}

export type SimilarUser = {
  id: string
  nome: string
  similaridade: number
  filmes_em_comum: string[]
}

export type RecommendationPath = {
  vertices: string[]
  usuario_id: string
  filme_compartilhado: string
  nota_colaborador: number
  similaridade: number
}

export type Contributor = {
  usuario_id: string
  nome: string
  nota: number
  similaridade: number
  filmes_em_comum: string[]
}

export type Recommendation = {
  filme_id: string
  titulo: string
  genero: string
  pontuacao: number
  colaboradores: number
  caminhos: RecommendationPath[]
  contribuidores: Contributor[]
}

export type GraphData = {
  nodes: {
    id: string
    nome: string
    tipo: 'usuario' | 'filme'
    grau: number
    papel: string
    similaridade: number | null
  }[]
  edges: {
    source: string
    target: string
    nota: number
    positiva: boolean
    direta: boolean
    simulada: boolean
    destacado: boolean
    rotas?: number[]
  }[]
  componentes_conexas: number
  caminhos: RecommendationPath[]
  mensagem: string
  modo: string
}

export type Example = {
  disponivel: boolean
  mensagem?: string
  usuario?: { id: string; nome: string }
  filme_compartilhado?: { id: string; titulo: string }
  colaborador?: { id: string; nome: string }
  filme_recomendado?: { id: string; titulo: string }
  nota_usuario?: number
  nota_compartilhada?: number
  nota_colaborador?: number
  positivos_em_comum?: number
  positivos_uniao?: number
  similaridade?: number
  pontuacao?: number
}

export type Analysis = {
  filmes_por_genero: { nome: string; valor: number }[]
  avaliacoes_por_genero: { nome: string; valor: number }[]
  avaliacoes_por_usuario: { id: string; nome: string; valor: number }[]
  filmes_mais_avaliados: { id: string; titulo: string; valor: number }[]
  grau_usuarios: { nome: string; valor: number }[]
  grau_filmes: { titulo: string; valor: number }[]
  similaridade_usuarios: { usuario: string; outro: string; similaridade: number }[]
}

export type SimulationState = {
  ativo: boolean
  usuario: {
    id: string
    nome: string
    avaliacoes: number
    filmes_positivos: number
  } | null
  avaliacoes: MovieRating[]
  similares: SimilarUser[]
  recomendacoes: Recommendation[]
}
