"""Gera um dataset sintetico pequeno (seed fixa) para o projeto.
Nao ha acesso a internet no ambiente, entao em vez do MovieLens usamos
dados simulados no mesmo formato: usuario,filme,nota."""
import csv, random

random.seed(42)

FILMES = {
    "Ficcao": ["Matrix", "Interestelar", "Blade Runner", "A Chegada", "Ex Machina", "Duna", "Inception"],
    "Terror": ["O Exorcista", "Hereditario", "Corra!", "Um Lugar Silencioso", "It: A Coisa", "O Iluminado"],
    "Romance": ["Titanic", "Diario de uma Paixao", "La La Land", "Orgulho e Preconceito", "Questao de Tempo", "Antes do Amanhecer"],
    "Animacao": ["Toy Story", "Procurando Nemo", "Viagem de Chihiro", "Up", "Divertida Mente", "Shrek"],
}
# componente isolada: ninguem do grupo principal viu estes filmes
DOCS = ["Democracia em Vertigem", "Cosmos"]

linhas = []
grupos = list(FILMES)
uid = 1
for g in grupos:                      # 7 usuarios por perfil principal
    for _ in range(7):
        u = f"user{uid:02d}"; uid += 1
        outros = [x for x in grupos if x != g]
        for f in random.sample(FILMES[g], random.randint(4, 6)):
            linhas.append((u, f, random.choice([4, 5, 5])))
        if random.random() < 0.7:     # gosto "secundario" cria pontes entre grupos
            o = random.choice(outros)
            for f in random.sample(FILMES[o], 2):
                linhas.append((u, f, random.choice([2, 3, 4, 5])))
# cold start: usuario com 1 avaliacao
linhas.append(("user29", "Matrix", 5))
# componente isolada
linhas += [("user30", DOCS[0], 5), ("user31", DOCS[0], 4), ("user31", DOCS[1], 5)]

with open("dados/avaliacoes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["usuario", "filme", "nota"]); w.writerows(linhas)
print(len(linhas), "avaliacoes geradas")

with open("dados/filmes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["filme", "genero"])
    for g, fs in FILMES.items():
        for x in fs: w.writerow([x, g])
    for x in DOCS: w.writerow([x, "Documentario"])
