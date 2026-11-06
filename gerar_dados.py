"""Atualiza títulos e gêneros sem mexer nas avaliações."""
import argparse
import csv
from pathlib import Path


ARQUIVO_FILMES = Path(__file__).resolve().parent / "dados" / "filmes.csv"

# A ordem acompanha os IDs f001 a f060 já usados em avaliacoes.csv.
CATALOGO = [
    ("Mad Max: Estrada da Fúria", "Ação"),
    ("John Wick", "Ação"),
    ("Duro de Matar", "Ação"),
    ("Gladiador", "Ação"),
    ("Indiana Jones e os Caçadores da Arca Perdida", "Aventura"),
    ("Jurassic Park", "Aventura"),
    ("Piratas do Caribe: A Maldição do Pérola Negra", "Aventura"),
    ("Jumanji", "Aventura"),
    ("Toy Story", "Animação"),
    ("Procurando Nemo", "Animação"),
    ("Shrek", "Animação"),
    ("A Viagem de Chihiro", "Animação"),
    ("As Branquelas", "Comédia"),
    ("O Auto da Compadecida", "Comédia"),
    ("Se Beber, Não Case!", "Comédia"),
    ("Feitiço do Tempo", "Comédia"),
    ("Um Sonho de Liberdade", "Drama"),
    ("À Espera de um Milagre", "Drama"),
    ("Forrest Gump", "Drama"),
    ("O Pianista", "Drama"),
    ("Diário de uma Paixão", "Romance"),
    ("Orgulho e Preconceito", "Romance"),
    ("Titanic", "Romance"),
    ("Como Eu Era Antes de Você", "Romance"),
    ("Interestelar", "Ficção científica"),
    ("Matrix", "Ficção científica"),
    ("Blade Runner 2049", "Ficção científica"),
    ("De Volta para o Futuro", "Ficção científica"),
    ("Harry Potter e a Pedra Filosofal", "Fantasia"),
    ("O Senhor dos Anéis: A Sociedade do Anel", "Fantasia"),
    ("O Hobbit: Uma Jornada Inesperada", "Fantasia"),
    ("A História Sem Fim", "Fantasia"),
    ("O Exorcista", "Terror"),
    ("Invocação do Mal", "Terror"),
    ("Hereditário", "Terror"),
    ("A Bruxa", "Terror"),
    ("Seven", "Suspense"),
    ("Ilha do Medo", "Suspense"),
    ("Garota Exemplar", "Suspense"),
    ("Os Suspeitos", "Suspense"),
    ("Entre Facas e Segredos", "Mistério"),
    ("Assassinato no Expresso do Oriente", "Mistério"),
    ("Zodíaco", "Mistério"),
    ("A Garota no Trem", "Mistério"),
    ("O Poderoso Chefão", "Crime"),
    ("Os Bons Companheiros", "Crime"),
    ("Scarface", "Crime"),
    ("Os Infiltrados", "Crime"),
    ("Free Solo", "Documentário"),
    ("O Dilema das Redes", "Documentário"),
    ("Amy", "Documentário"),
    ("Senna", "Documentário"),
    ("Cantando na Chuva", "Musical"),
    ("Chicago", "Musical"),
    ("Os Miseráveis", "Musical"),
    ("O Rei do Show", "Musical"),
    ("O Resgate do Soldado Ryan", "Guerra"),
    ("1917", "Guerra"),
    ("Até o Último Homem", "Guerra"),
    ("Apocalypse Now", "Guerra"),
]


def atualizar_catalogo(caminho: Path = ARQUIVO_FILMES) -> None:
    if len(CATALOGO) != 60:
        raise ValueError("A lista de catálogo deve conter exatamente 60 filmes.")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        campos = leitor.fieldnames
        filmes = list(leitor)

    ids_esperados = [f"f{i:03}" for i in range(1, 61)]
    if campos is None or [filme["id"] for filme in filmes] != ids_esperados:
        raise ValueError("O catálogo deve conter os IDs f001 a f060 em ordem.")

    for filme, (titulo, genero) in zip(filmes, CATALOGO):
        filme["titulo"] = titulo
        filme["genero"] = genero

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filmes)

    print(f"Catálogo atualizado: {len(filmes)} filmes. Avaliações e usuários não foram alterados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    atualizar_catalogo()
