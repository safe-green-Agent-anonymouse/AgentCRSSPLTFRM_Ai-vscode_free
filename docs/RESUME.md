# EDAC Console — résumé commenté

Dépôt : https://github.com/safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free
Release : https://github.com/safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free/releases/tag/v1.0.1

## 1. Ce qui a été construit, et pourquoi ainsi

**Une seule base de code, deux interfaces.** La fenêtre Tkinter et la CLI ne
sont que deux façades : elles partagent la configuration, le journal et le
moteur d'exécution. Conséquence pratique : ce que tu règles dans la fenêtre
s'applique à `edac exec`, et inversement — il n'y a pas deux comportements à
maintenir.

**Python standard library uniquement.** Pas de dépendance au runtime : rien à
installer chez l'utilisateur, et l'`.exe` reste auto-suffisant. Pillow et
PyInstaller ne servent qu'à la construction, pas à l'exécution.

**Configuration en couches** (`edac/config.py`) : défauts < fichier < profil <
variables d'environnement < flags CLI. C'est la règle classique des outils
sérieux : un profil « offline » ou « prod » peut tout figer, et un flag ponctuel
reste prioritaire sans modifier le fichier.

**Journal avec commentaires** (`edac/logging_setup.py`) : fichier rotatif, texte
ou JSON, chaque commande tracée (début, sortie, code de retour, durée) et
annotations horodatées (`Ctrl+M` dans la fenêtre, `edac log annotate` en CLI).
Les secrets sont masqués à l'écriture, pas après coup.

**Garde-fous avant exécution** (`edac/runner.py`) : la commande est analysée
*avant* d'être lancée. Mode hors-ligne, liste blanche d'hôtes, refus des
commandes destructives, refus du `git push` direct sur `main`/`master`. Le mode
autopilot autorise beaucoup, mais ne désactive jamais ces règles — c'est la
différence entre « permissif » et « dangereux ».

**Désinstallation par liste blanche** (`edac/uninstall.py`) : le désinstalleur
ne supprime que des cibles connues, avec `--dry-run`, `--keep-config`,
`--keep-logs`, `--keep-venv` et confirmation obligatoire. Il ne touche pas au
dossier source du projet.

## 2. Chaîne de fabrication

Tout est produit par GitHub Actions, jamais à la main :

1. `tests` sur `ubuntu-latest` : 48 tests unitaires.
2. `build-exe` sur `windows-latest` : icône (7 résolutions), ressource de
   version dérivée de `edac.__version__`, `.exe` PyInstaller, installeur Inno
   Setup, test de démarrage réel de l'exécutable, `SHA256SUMS.txt`.
3. Attestation de provenance (Sigstore) sur les deux binaires.
4. Sur un tag `v*` : release GitHub avec les binaires, les empreintes et
   l'attestation.

Le test de démarrage en CI n'est pas cosmétique : c'est lui qui a révélé le seul
vrai bug de packaging du projet (voir §4).

## 3. Ce qu'apporte chaque mécanisme de confiance

| Mécanisme | Ce que ça prouve | État |
| --- | --- | --- |
| `SHA256SUMS.txt` | le fichier téléchargé est intact | actif |
| Attestation de provenance | le binaire vient bien de ce dépôt et de ce workflow | actif |
| Signature Authenticode | Windows affiche un éditeur identifié | non retenu |

Authenticode est écarté volontairement : le certificat publie le nom de son
titulaire dans chaque binaire, incompatible avec un projet maintenu
anonymement. Le workflow reste prêt à signer si un certificat est fourni un
jour (secrets `WINDOWS_CERT_PFX_BASE64` / `WINDOWS_CERT_PASSWORD`).

Conséquence à assumer : SmartScreen affichera « éditeur inconnu » au premier
lancement.

## 4. Le bug le plus instructif

En CI, l'exécutable Windows ne rendait jamais la main. L'interprétation facile
aurait été « le runner est lent » ; le journal disait autre chose :

```
ImportError: attempted relative import with no known parent package
```

PyInstaller exécutait `edac/__main__.py` directement, donc sans paquet parent,
et ses imports relatifs échouaient ; en mode `--windowed`, l'erreur restait
invisible et le processus survivait. Correction : un point d'entrée `app.py`
qui fait `from edac.cli import main` (import absolu), plus `freeze_support()`.
Leçon : ne jamais passer un `__main__.py` à PyInstaller.

Autre correctif du même ordre : en mode fenêtré, `sys.stdout` et `sys.stderr`
valent `None`, donc le premier `print` d'une commande CLI levait une exception.
`_ensure_streams()` les redirige vers `os.devnull`.

## 5. Historique des livraisons

| PR | Contenu |
| --- | --- |
| #1 | application, configuration, journaux, réseau, désinstalleur, CI `.exe` |
| #2 | signature Authenticode optionnelle + attestations de provenance |
| #3 | version 1.0.1 |
| #4 | décision « provenance seule » + contact public |

## 6. Ce qui reste ouvert (aucun blocage)

- Authenticode, si un jour tu acceptes une identité publique ou une structure.
- Auto-update de l'application depuis les releases GitHub.
- Publication des empreintes d'attestation directement dans les notes de release.
