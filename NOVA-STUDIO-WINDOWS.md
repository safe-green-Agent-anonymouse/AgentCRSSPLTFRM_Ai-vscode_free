# Nova Studio pour Windows (.exe)

Le workflow **Nova Studio Windows desktop** construit deux versions autonomes de Nova Studio :

- `Nova-Studio-x64.exe` pour Windows 64 bits ;
- `Nova-Studio-x86.exe` pour Windows 32 bits.

## Télécharger

Ouvre l'onglet [Actions du dépôt](https://github.com/safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free/actions/workflows/nova-studio-windows.yml), sélectionne la dernière exécution réussie, puis télécharge l'artefact correspondant à l'architecture de ton Windows. L'artefact est conservé 30 jours.

Pour vérifier l'architecture de Windows : **Paramètres → Système → Informations système → Type du système**.

## Premier démarrage

Le programme affiche l'interface Nova Studio dans une fenêtre desktop et conserve les données du navigateur intégré sous `%LOCALAPPDATA%\NovaStudio\WebView2`. L'application embarque l'interface web : Internet est nécessaire pour la recherche GitHub et les fournisseurs IA distants, mais pas pour ouvrir l'interface et utiliser les fonctions locales disponibles.

Microsoft Edge WebView2 Runtime doit être présent sur l'ordinateur. Il est préinstallé sur la plupart des versions récentes de Windows. Si une fenêtre d'erreur le demande, installer le runtime officiel : <https://developer.microsoft.com/microsoft-edge/webview2/>.

Les projets et conversations de cette version desktop sont stockés localement dans le profil WebView2. Ils ne sont pas automatiquement synchronisés avec le navigateur web ni avec d'autres appareils. Les fournisseurs IA et modèles ne sont pas inclus ; leurs conditions et coûts éventuels restent applicables.

## Recompiler

Depuis la racine du dépôt, sur Windows avec Python 3.12 de la même architecture que la cible :

```powershell
python -m pip install -r requirements-nova.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Nova-Studio-x64 --collect-all webview --collect-all clr_loader --collect-all pythonnet --add-data "web;web" nova_studio.py
```

Pour une version 32 bits, utiliser Python x86 et remplacer `Nova-Studio-x64` par `Nova-Studio-x86`. Le build utilise PyInstaller sur Windows et ne compile pas en croisé depuis Linux ou macOS.
