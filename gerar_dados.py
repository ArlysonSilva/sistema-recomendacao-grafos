"""Gera um dataset sintetico pequeno (seed fixa) para o projeto.
Nao ha acesso a internet no ambiente, entao em vez do MovieLens usamos
dados simulados no mesmo formato: usuario,filme,nota."""
import argparse
import csv
import random
from pathlib import Path

from src.caminhos import ARQUIVO_AVALIACOES, ARQUIVO_FILMES

SEED = 42

FILMES = {
    "Ficcao": ["Matrix", "Interestelar", "Blade Runner", "A Chegada", "Ex Machina", "Duna", "Inception"],
    "Terror": ["O Exorcista", "Hereditario", "Corra!", "Um Lugar Silencioso", "It: A Coisa", "O Iluminado"],
    "Romance": ["Titanic", "Diario de uma Paixao", "La La Land", "Orgulho e Preconceito", "Questao de Tempo", "Antes do Amanhecer"],
    "Animacao": ["Toy Story", "Procurando Nemo", "Viagem de Chihiro", "Up", "Divertida Mente", "Shrek"],
}
# componente isolada: ninguem do grupo principal viu estes filmes
DOCS = ["Democracia em Vertigem", "Cosmos"]

def gerar_dados(arquivo_avaliacoes=ARQUIVO_AVALIACOES, arquivo_filmes=ARQUIVO_FILMES, sobrescrever=False):
    arquivo_avaliacoes, arquivo_filmes = Path(arquivo_avaliacoes), Path(arquivo_filmes)
    existentes = [p for p in (arquivo_avaliacoes, arquivo_filmes) if p.exists()]
    if existentes and not sobrescrever:
        raise FileExistsError("Dados existentes preservados. Use --sobrescrever para substituí-los: " + ", ".join(map(str, existentes)))
    rng = random.Random(SEED)
    linhas = []
    grupos = list(FILMES)
    uid = 1
    for genero in grupos:
        for _ in range(7):
            usuario = f"user{uid:02d}"; uid += 1
            outros = [x for x in grupos if x != genero]
            for filme in rng.sample(FILMES[genero], rng.randint(4, 6)):
                linhas.append((usuario, filme, rng.choice([4, 5, 5])))
            if rng.random() < 0.7:
                outro = rng.choice(outros)
                for filme in rng.sample(FILMES[outro], 2):
                    linhas.append((usuario, filme, rng.choice([2, 3, 4, 5])))
    linhas.append(("user29", "Matrix", 5))
    linhas += [("user30", DOCS[0], 5), ("user31", DOCS[0], 4), ("user31", DOCS[1], 5)]

    arquivo_avaliacoes.parent.mkdir(parents=True, exist_ok=True)
    arquivo_filmes.parent.mkdir(parents=True, exist_ok=True)
    with arquivo_avaliacoes.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["usuario", "filme", "nota"]); w.writerows(linhas)
    with arquivo_filmes.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["filme", "genero"])
        for genero, filmes in FILMES.items():
            for filme in filmes: w.writerow([filme, genero])
        for filme in DOCS: w.writerow([filme, "Documentario"])
    print(len(linhas), "avaliacoes geradas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera os CSVs sintéticos do projeto.")
    parser.add_argument("--sobrescrever", action="store_true", help="substitui dados CSV existentes")
    gerar_dados(sobrescrever=parser.parse_args().sobrescrever)
