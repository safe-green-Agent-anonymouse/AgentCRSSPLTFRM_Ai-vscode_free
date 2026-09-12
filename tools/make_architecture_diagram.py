"""Genere docs/architecture.png (schema d'architecture du projet).

Dependance de developpement uniquement : pip install matplotlib
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

BG = "#0f1523"
CARD = "#1b2436"
EDGE = "#55688c"
TXT = "#e6ecf5"
DIM = "#a9bad2"
BLUE = "#4c8dff"
TEAL = "#2bc4b8"
AMBER = "#e0a13a"

TITLE_H = 5.0
LINE_H = 3.6
PAD_B = 2.4

fig, ax = plt.subplots(figsize=(15, 11.8), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 150)
ax.set_ylim(0, 118)
ax.axis("off")


def box(x, y, w, title, lines, accent=BLUE):
    """(x, y) = coin bas-gauche ; hauteur deduite du nombre de lignes."""
    h = TITLE_H + LINE_H * len(lines) + PAD_B
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.6,rounding_size=1.6",
            linewidth=1.6, edgecolor=accent, facecolor=CARD,
        )
    )
    ax.text(x + 1.8, y + h - 1.6, title, color=accent, fontsize=11,
            fontweight="bold", va="top")
    for i, line in enumerate(lines):
        ax.text(x + 1.8, y + h - TITLE_H - 1.2 - i * LINE_H, line,
                color=DIM, fontsize=9.5, va="top")
    return h


def group(x, y, w, h, label):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.8,rounding_size=2",
            linewidth=1.2, edgecolor=EDGE, facecolor="none", linestyle=(0, (5, 4)),
        )
    )
    ax.text(x + 1.5, y + h + 1.8, label, color=EDGE, fontsize=10.5, fontweight="bold")


def arrow(p1, p2, color=DIM, label=None, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(p1, p2, arrowstyle="-|>", color=color, linewidth=1.4,
                        mutation_scale=14, connectionstyle=f"arc3,rad={rad}")
    )
    if label:
        ax.text((p1[0] + p2[0]) / 2 + 0.8, (p1[1] + p2[1]) / 2, label,
                color=color, fontsize=8.5, ha="left", va="center")


ax.text(4, 114, "EDAC Console — architecture", color=TXT, fontsize=20, fontweight="bold")
ax.text(4, 110, "v1.0.1 · Python standard library · .exe et installeur Windows produits par GitHub Actions",
        color=DIM, fontsize=11)

# --- Interfaces -------------------------------------------------------------
group(3, 84, 63, 22.2, "Interfaces utilisateur")
box(6, 86, 27, "GUI  edac/gui.py",
    ["fenetre Tkinter", "console en flux, Ctrl+M", "editeur de configuration"], BLUE)
box(36, 86, 27, "CLI  edac/cli.py",
    ["config / profile / exec / run", "log tail | annotate | list", "uninstall"], BLUE)

# --- Coeur ------------------------------------------------------------------
group(3, 36, 63, 44, "Coeur partage (paquet edac/)")
box(6, 58, 27, "config.py",
    ["schema type + profils", "defauts < fichier < profil", "  < env < flags CLI"], TEAL)
box(36, 58, 27, "runner.py",
    ["execution en flux", "verdict avant execution", "masquage des secrets"], TEAL)
box(6, 38, 27, "logging_setup.py",
    ["journal rotatif texte/JSON", "annotations horodatees", "debut / sortie / code"], TEAL)
box(36, 38, 27, "uninstall.py",
    ["liste blanche de cibles", "--dry-run / --keep-*", "confirmation obligatoire"], TEAL)

box(6, 8, 57, "Garde-fous, appliques avant toute execution",
    ["mode hors-ligne : commandes reseau refusees",
     "network.allowed_hosts : seuls les domaines autorises",
     "git push direct sur main / master bloque",
     "commandes destructives refusees, secrets masques"], AMBER)

# --- CI / publication -------------------------------------------------------
group(74, 36, 72, 70, "Chaine de build et de publication (GitHub Actions)")
box(77, 86, 31, "tests  ubuntu-latest",
    ["python -m unittest", "48 tests verts"], BLUE)
box(112, 86, 31, "build-exe  windows-latest",
    ["PyInstaller (edac.spec)", "Inno Setup (installer.iss)"], BLUE)
box(77, 62, 31, "Artefacts",
    ["EDAC-Console.exe", "EDAC-Console-Setup-1.0.1.exe", "SHA256SUMS.txt"], TEAL)
box(112, 62, 31, "Provenance",
    ["attest-build-provenance", "Sigstore + journal Rekor", "gh attestation verify"], TEAL)
box(77, 38, 66, "Release GitHub (tag v*)",
    ["exe portable + installeur + empreintes + attestation",
     "Authenticode : signe uniquement si les secrets du certificat existent",
     "choix retenu : provenance seule, aucune identite publiee"], AMBER)

# --- Liens ------------------------------------------------------------------
arrow((19.5, 86), (19.5, 77.0), BLUE)
arrow((49.5, 86), (49.5, 77.0), BLUE)
arrow((33, 67), (36, 67), TEAL, label="lit")
arrow((19.5, 58), (19.5, 57.0), TEAL)
arrow((49.5, 58), (49.5, 57.0), TEAL)
arrow((49.5, 38), (49.5, 30.6), AMBER, label="filtre")
arrow((66, 55), (77, 66), DIM, label="app.py + edac.spec", rad=0.14)
arrow((92.5, 86), (92.5, 81.0), BLUE)
arrow((127.5, 86), (127.5, 81.0), BLUE)
arrow((108, 71), (112, 71), TEAL)
arrow((92.5, 62), (92.5, 57.0), TEAL)
arrow((127.5, 62), (127.5, 57.0), TEAL)

fig.savefig("docs/architecture.png", facecolor=BG, bbox_inches="tight")
print("ok")
