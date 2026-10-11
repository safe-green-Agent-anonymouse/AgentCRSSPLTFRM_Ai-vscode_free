# Nova Studio — espace de travail d'agence IA

Nova Studio complète la console existante du dépôt avec une interface web responsive et installable, disponible dans `web/`.

## Fonctions

- Tableau de bord, projets, six rôles d'assistant, chat IA, recherche de dépôts publics GitHub et notes locales exportables.
- Mode hors ligne pour l'interface, les projets et les notes via un service worker/PWA.
- Connexion directe à Ollama ou à un endpoint `/v1/chat/completions` compatible OpenAI ; aucun fournisseur n'est inclus.
- Workflow GitHub Actions pour publier `web/` sur GitHub Pages.

## Utilisation locale

Depuis la racine du dépôt : `py -m http.server 8000 --directory web`, puis ouvrir `http://localhost:8000`. Service worker/PWA nécessite localhost ou HTTPS, pas l'ouverture du fichier en `file://`.

### Ollama

Installer Ollama, télécharger un modèle et démarrer le serveur local. Dans **Connecter un modèle**, configurer `http://localhost:11434/v1` et le nom exact du modèle. Les règles CORS d'Ollama doivent autoriser l'origine de l'application. GitHub Pages est servi en HTTPS ; le navigateur peut bloquer l'accès à Ollama en HTTP. Dans ce cas, utiliser l'application sur localhost ou un proxy HTTPS de confiance.

### API distante

Renseigner l'URL de base, le nom de modèle et éventuellement sa clé. La clé reste dans `sessionStorage` pour l'onglet ; elle n'est pas commise, mais un script chargé sur la page peut la lire tant que l'onglet est ouvert. Ne pas utiliser sur un appareil partagé. Les API distantes peuvent facturer des requêtes : consulter les tarifs, quotas et conditions du fournisseur.

## Gratuité et confidentialité

GitHub Pages et le code sont gratuits dans leurs limites de service. Ollama est gratuit après installation et téléchargement, mais utilise les ressources de l'ordinateur. Nova Studio ne garantit aucun revenu. Les notes, projets et conversations restent dans le navigateur de cet appareil ; aucune synchronisation entre appareils n'est activée. Hors ligne, les API distantes et la recherche GitHub ne fonctionnent pas.

## Publication Pages

Le workflow `.github/workflows/agency-pages.yml` déploie le dossier `web/` sur les push de `main`. Si nécessaire, choisir **Settings → Pages → Build and deployment → Source → GitHub Actions**. Le site sera indiqué dans **Settings → Pages** après le premier déploiement.

Les rôles sont des consignes envoyées au modèle sélectionné, pas des modèles entraînés ni des processus autonomes. L'amélioration se fait par vos retours, vos notes et des modifications versionnées par le propriétaire du dépôt. L'application ne modifie pas elle-même son code.