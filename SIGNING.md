# Signature du code : etat et demarche

## Ce qui est en place

| Mecanisme | Cout | Effet |
| --- | --- | --- |
| `SHA256SUMS.txt` | gratuit | verifier qu'un fichier telecharge est intact |
| Attestation de provenance GitHub | gratuit (depot public) | prouver que le binaire vient de ce depot et de ce workflow |
| Signature Authenticode | certificat requis | supprime l'avertissement « editeur inconnu » de Windows |

Verification de la provenance par un utilisateur :

```bash
gh attestation verify EDAC-Console.exe --repo safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free
```

## Candidature SignPath Foundation (certificat gratuit, open source)

SignPath Foundation offre un certificat de signature de code aux projets open
source, avec signature declenchee depuis GitHub Actions.

Prerequis du projet :

- depot **public** ;
- licence open source (ici : The Unlicense, domaine public) ;
- code source complet et build reproductible depuis la CI ;
- pas de composant proprietaire, pas de telemetrie cachee ;
- un responsable identifiable pour le projet.

Elements a fournir dans le formulaire https://signpath.org/apply :

- nom du projet : Expert Dev Autopilot Console (EDAC Console)
- URL du depot : https://github.com/safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free
- licence : The Unlicense (`LICENSE`)
- description : console de developpement autonome, fenetre Tkinter et CLI,
  configuration en couches, journal avec annotations, garde-fous reseau et Git,
  desinstalleur ; Python pur, sans dependance au runtime.
- artefacts a signer : `EDAC-Console.exe` (portable) et
  `EDAC-Console-Setup-<version>.exe` (installeur Inno Setup)
- build : `.github/workflows/windows-exe.yml`, runner `windows-latest`,
  PyInstaller puis Inno Setup, artefacts et empreintes publies a chaque build.

Une fois la demande acceptee, SignPath fournit un `SIGNPATH_API_TOKEN` et des
identifiants d'organisation/projet : la signature se fait alors via l'action
`signpath/github-action-submit-signing-request`, en remplacement des etapes
`signtool` actuelles (qui restent utilisables avec un certificat commercial via
les secrets `WINDOWS_CERT_PFX_BASE64` et `WINDOWS_CERT_PASSWORD`).
