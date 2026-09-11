# Signature du code : etat et demarche

## Choix du projet

Le projet s'appuie sur les **attestations de provenance** (Sigstore / GitHub) et
sur les empreintes SHA-256. Il n'utilise pas de certificat Authenticode : un tel
certificat publie le nom de son titulaire dans chaque binaire signe, ce que ce
projet, maintenu de maniere anonyme, ne souhaite pas.

Consequence assumee : Windows SmartScreen affiche « editeur inconnu » au premier
lancement. L'origine des binaires reste verifiable publiquement (ci-dessous).

## Ce qui est en place

| Mecanisme | Cout | Effet |
| --- | --- | --- |
| `SHA256SUMS.txt` | gratuit | verifier qu'un fichier telecharge est intact |
| Attestation de provenance GitHub | gratuit (depot public) | prouver que le binaire vient de ce depot et de ce workflow |
| Signature Authenticode | certificat requis, identite publique | supprime l'avertissement « editeur inconnu » de Windows |

Verification de la provenance par un utilisateur :

```bash
gh attestation verify EDAC-Console.exe --repo safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free
```

Les attestations sont produites par `actions/attest-build-provenance` dans
`.github/workflows/windows-exe.yml`, pour l'executable portable et pour
l'installeur, et publiees dans le journal de transparence Rekor.

## Si Authenticode devient necessaire un jour

Deux voies, toutes deux exigeant une identite verifiable (personne physique ou
structure juridique) publiee dans le certificat :

1. **Certificat commercial** (DigiCert, Sectigo, SSL.com...). Le workflow est
   deja pret : deposer `WINDOWS_CERT_PFX_BASE64` et `WINDOWS_CERT_PASSWORD` en
   secrets GitHub, et `tools/sign_windows.ps1` signe, horodate et verifie les
   deux binaires. Sans ces secrets, les etapes sont ignorees.
2. **SignPath Foundation** (https://signpath.org/apply), gratuit pour l'open
   source : depot public, licence open source, build reproductible en CI et
   responsable identifiable. La signature se ferait alors via
   `signpath/github-action-submit-signing-request`, en remplacement des etapes
   `signtool`.

Un certificat auto-signe ne supprime pas l'avertissement SmartScreen : il ne
sert qu'aux tests internes.

## Contact

iSafe_User002@proton.me
