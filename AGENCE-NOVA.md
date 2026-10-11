# Nova Studio — espace de travail d'agence IA

Nova Studio complète la console existante du dépôt avec une interface web responsive et installable, disponible dans `web/`.

## Fonctions

- Tableau de bord, projets, six rôles d'assistant, chat IA, recherche de dépôts publics GitHub et notes locales exportables.
- Suppression message par message dans l'historique local de l'appareil. La suppression ne révoque pas les requêtes déjà envoyées au fournisseur IA.
- Mode hors ligne pour l'interface, les projets et les notes via un service worker/PWA.
- Connexion directe à Ollama ou à un endpoint `/v1/chat/completions` compatible OpenAI ; aucun fournisseur n'est inclus.
- Mode aléatoire OpenRouter : sélection aléatoire parmi son catalogue en direct, limitée aux modèles déclarant un tarif d'entrée et de sortie nul.
- Workflow GitHub Actions pour publier `web/` sur GitHub Pages.

## Utilisation locale

Depuis la racine du dépôt : `py -m http.server 8000 --directory web`, puis ouvrir `http://localhost:8000`. Service worker/PWA nécessite localhost ou HTTPS, pas l'ouverture du fichier en `file://`.

### Ollama

Installer Ollama, télécharger un modèle et démarrer le serveur local. Dans **Connecter un modèle**, configurer `http://localhost:11434/v1` et le nom exact du modèle. Les règles CORS d'Ollama doivent autoriser l'origine de l'application. GitHub Pages est servi en HTTPS ; le navigateur peut bloquer l'accès à Ollama en HTTP. Dans ce cas, utiliser l'application sur localhost ou un proxy HTTPS de confiance.

### Mode aléatoire gratuit

Dans **Modèles gratuits**, Nova charge le catalogue public OpenRouter avec `max_price=0` et filtre les modèles dont l'API déclare à la fois un tarif d'entrée et de sortie égal à zéro. Le catalogue peut changer et l'accès reste soumis aux quotas, à la disponibilité, aux règles d'inscription et aux conditions du fournisseur. Confirme les conditions en vigueur chez OpenRouter avant toute utilisation; « gratuit » ne garantit ni un quota illimité ni une disponibilité permanente.

Crée ta clé sur [OpenRouter](https://openrouter.ai/settings/keys), colle-la dans Nova Studio et enregistre-la pour l'onglet. Aucune clé n'est intégrée à l'application ou stockée dans `localStorage`; elle est gardée dans `sessionStorage` pendant la session du navigateur. Les scripts exécutés par la page peuvent lire cette clé, donc ne l'utilise pas sur un appareil partagé et ne colle pas de données sensibles dans le chat.

Le mode aléatoire ne fonctionne pas hors ligne. Si un modèle échoue ou est limité, Nova essaie jusqu'à deux autres modèles de la liste gratuite chargée, puis indique explicitement l'erreur.

### API distante

Renseigner l'URL de base, le nom de modèle et éventuellement sa clé. La clé reste dans `sessionStorage` pour l'onglet ; elle n'est pas commise, mais un script chargé sur la page peut la lire tant que l'onglet est ouvert. Ne pas utiliser sur un appareil partagé. Les API distantes peuvent facturer des requêtes : consulter les tarifs, quotas et conditions du fournisseur.

## Gratuité et confidentialité

GitHub Pages et le code sont gratuits dans leurs limites de service. Ollama est gratuit après installation et téléchargement, mais utilise les ressources de l'ordinateur. Nova Studio ne garantit aucun revenu. Les notes, projets et conversations restent dans le navigateur de cet appareil ; aucune synchronisation entre appareils n'est activée. Hors ligne, les API distantes et la recherche GitHub ne fonctionnent pas.

Nova Studio n'a pas de comptes utilisateurs ni de rôle administrateur intégré : « pour moi » désigne l'historique de l'appareil et du profil de navigateur utilisé. Les données ne sont pas partagées entre appareils.

## Publication Pages

Le workflow `.github/workflows/agency-pages.yml` déploie le dossier `web/` sur les push de `main`. Si nécessaire, choisir **Settings → Pages → Build and deployment → Source → GitHub Actions**. Le site sera indiqué dans **Settings → Pages** après le premier déploiement.

Les rôles sont des consignes envoyées au modèle sélectionné, pas des modèles entraînés ni des processus autonomes. L'amélioration se fait par vos retours, vos notes et des modifications versionnées par le propriétaire du dépôt. L'application ne modifie pas elle-même son code.
