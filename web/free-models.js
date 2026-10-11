(() => {
  const CATALOG_URL = 'https://openrouter.ai/api/v1/models?max_price=0';
  const CHAT_URL = 'https://openrouter.ai/api/v1/chat/completions';
  const KEY_STORAGE = 'nova-free-models-key';
  const MODE_STORAGE = 'nova-free-models-random';
  const CATALOG_STORAGE = 'nova-free-models-catalog';
  const $ = (selector) => document.querySelector(selector);
  const nav = $('.nav');
  const wrap = $('.wrap');
  const chatForm = $('#chatForm');
  if (!nav || !wrap || !chatForm) return;

  let freeModels = [];
  let randomEnabled = sessionStorage.getItem(MODE_STORAGE) === 'true';
  const styles = document.createElement('style');
  styles.textContent = '.fm-list{display:grid;gap:10px;margin-top:16px}.fm-model{padding:14px 16px;border:1px solid var(--line,#292b36);border-radius:14px;background:var(--card,#171820)}.fm-model strong{display:block}.fm-model small{color:var(--muted,#9a9cab)}.fm-toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.fm-toolbar .input{flex:1;min-width:220px}.fm-key{width:100%;margin-top:8px}.fm-check{display:flex;gap:10px;align-items:center;margin:16px 0}.fm-check input{width:auto}.fm-links{display:flex;gap:14px;flex-wrap:wrap;margin-top:14px}.fm-error{color:#ff9292}.fm-ok{color:#80e0b1}';
  document.head.append(styles);

  const navButton = document.createElement('button');
  navButton.type = 'button';
  navButton.dataset.view = 'freeModels';
  navButton.textContent = '🎲 Modèles gratuits';
  nav.append(navButton);

  const section = document.createElement('section');
  section.className = 'view';
  section.id = 'freeModels';
  section.innerHTML = `
    <div class="section-title">
      <div class="eyebrow">CATALOGUE ACTUALISÉ</div>
      <h1>Modèles <span class="grad">gratuits</span></h1>
      <p class="sub">Nova choisit au hasard parmi les modèles OpenRouter dont les tarifs API indiquent 0 $ pour les entrées et les sorties.</p>
    </div>
    <article class="card">
      <label for="fmKey">Clé API OpenRouter</label>
      <input class="input fm-key" id="fmKey" type="password" autocomplete="off" placeholder="Colle ta clé ici (elle reste dans cet onglet)">
      <div class="fm-toolbar" style="margin-top:12px">
        <button class="btn" id="fmSaveKey" type="button">Enregistrer pour cet onglet</button>
        <button class="btn" id="fmRefresh" type="button">Actualiser les modèles</button>
        <span class="small" id="fmStatus" aria-live="polite">Catalogue non chargé</span>
      </div>
      <label class="fm-check"><input type="checkbox" id="fmRandom"><span>Activer le choix aléatoire dans l’assistant</span></label>
      <p class="small">La clé n’est pas incluse dans Nova et n’est conservée qu’en mémoire de session. Les modèles gratuits ont des quotas, peuvent être indisponibles et leurs conditions peuvent changer. Vérifie les conditions d’OpenRouter avant d’envoyer des données sensibles.</p>
      <div class="fm-links">
        <a href="https://openrouter.ai/settings/keys" target="_blank" rel="noopener noreferrer">Créer une clé OpenRouter ↗</a>
        <a href="https://openrouter.ai/models?max_price=0" target="_blank" rel="noopener noreferrer">Voir les modèles gratuits ↗</a>
        <a href="https://openrouter.ai/docs/guides/overview/models" target="_blank" rel="noopener noreferrer">Documentation du catalogue ↗</a>
      </div>
    </article>
    <div class="fm-toolbar" style="margin-top:20px"><input class="input" id="fmSearch" type="search" placeholder="Filtrer les modèles gratuits" aria-label="Filtrer les modèles"><span class="small" id="fmCount"></span></div>
    <div class="fm-list" id="fmList" aria-live="polite"></div>`;
  wrap.append(section);

  const status = $('#fmStatus');
  const list = $('#fmList');
  const count = $('#fmCount');
  const search = $('#fmSearch');
  const keyInput = $('#fmKey');
  const randomCheckbox = $('#fmRandom');
  keyInput.value = sessionStorage.getItem(KEY_STORAGE) || '';
  randomCheckbox.checked = randomEnabled;

  function openSection() {
    document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view === section));
    document.querySelectorAll('[data-view]').forEach((button) => button.classList.toggle('active', button === navButton));
    $('#crumb').textContent = 'Modèles gratuits';
    renderModels();
  }
  navButton.addEventListener('click', openSection);

  function renderModels() {
    const query = search.value.trim().toLowerCase();
    const visible = freeModels.filter((model) => `${model.name} ${model.id}`.toLowerCase().includes(query)).slice(0, 30);
    count.textContent = freeModels.length ? `${freeModels.length} modèles à 0 $ dans le catalogue · ${visible.length} affichés` : '';
    list.replaceChildren();
    for (const model of visible) {
      const card = document.createElement('article');
      card.className = 'fm-model';
      const name = document.createElement('strong');
      name.textContent = model.name || model.id;
      const id = document.createElement('small');
      id.textContent = model.id;
      card.append(name, id);
      list.append(card);
    }
    if (freeModels.length && visible.length === 0) list.textContent = 'Aucun modèle ne correspond à ce filtre.';
    if (!freeModels.length && status.textContent.startsWith('Catalogue actualisé')) list.textContent = 'Aucun modèle gratuit disponible actuellement.';
  }

  async function refreshCatalog() {
    status.className = 'small';
    status.textContent = 'Chargement du catalogue…';
    $('#fmRefresh').disabled = true;
    try {
      const response = await fetch(CATALOG_URL, { headers: { Accept: 'application/json' }, cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (!Array.isArray(payload.data)) throw new Error('Format de catalogue inattendu.');
      freeModels = payload.data.filter((model) => {
        const pricing = model.pricing || {};
        const output = model.architecture?.output_modalities;
        return model.id && Number(pricing.prompt) === 0 && Number(pricing.completion) === 0 && (!Array.isArray(output) || output.includes('text'));
      });
      localStorage.setItem(CATALOG_STORAGE, JSON.stringify(freeModels));
      status.className = 'small fm-ok';
      status.textContent = `Catalogue actualisé · ${freeModels.length} modèles affichés comme gratuits`;
      renderModels();
    } catch (error) {
      status.className = 'small fm-error';
      status.textContent = `Catalogue inaccessible : ${error.message}. Vérifie ta connexion puis réessaie.`;
    } finally {
      $('#fmRefresh').disabled = false;
    }
  }

  try {
    const cached = JSON.parse(localStorage.getItem(CATALOG_STORAGE) || '[]');
    if (Array.isArray(cached)) freeModels = cached;
  } catch (error) {
    console.error('Impossible de lire le catalogue local des modèles gratuits.', error);
  }
  if (freeModels.length) {
    status.textContent = `Catalogue en cache · ${freeModels.length} modèles (actualise pour vérifier les prix)`;
    renderModels();
  } else {
    refreshCatalog();
  }

  $('#fmRefresh').addEventListener('click', refreshCatalog);
  search.addEventListener('input', renderModels);
  $('#fmSaveKey').addEventListener('click', () => {
    const key = keyInput.value.trim();
    if (!key) {
      sessionStorage.removeItem(KEY_STORAGE);
      status.className = 'small';
      status.textContent = 'Clé retirée de cet onglet.';
      return;
    }
    try {
      sessionStorage.setItem(KEY_STORAGE, key);
      status.className = 'small fm-ok';
      status.textContent = 'Clé enregistrée pour cet onglet.';
    } catch (error) {
      status.className = 'small fm-error';
      status.textContent = `Impossible d’enregistrer la clé : ${error.message}`;
    }
  });
  randomCheckbox.addEventListener('change', () => {
    if (randomCheckbox.checked && !sessionStorage.getItem(KEY_STORAGE)) {
      randomCheckbox.checked = false;
      status.className = 'small fm-error';
      status.textContent = 'Ajoute et enregistre d’abord ta clé OpenRouter.';
      return;
    }
    randomEnabled = randomCheckbox.checked;
    sessionStorage.setItem(MODE_STORAGE, String(randomEnabled));
    status.className = 'small fm-ok';
    status.textContent = randomEnabled ? 'Mode aléatoire activé dans l’assistant.' : 'Mode aléatoire désactivé.';
  });

  const standardSubmit = chatForm.onsubmit;
  chatForm.onsubmit = async (event) => {
    if (!randomEnabled) return standardSubmit?.call(chatForm, event);
    event.preventDefault();
    const prompt = $('#prompt').value.trim();
    if (!prompt) return;
    if (!sessionStorage.getItem(KEY_STORAGE)) {
      d.messages.push({ role: 'assistant', content: 'Le mode aléatoire est activé, mais la clé OpenRouter manque. Ajoute-la dans 🎲 Modèles gratuits.' });
      save();
      render();
      return;
    }
    if (!freeModels.length) {
      d.messages.push({ role: 'assistant', content: 'Le catalogue des modèles gratuits est vide ou indisponible. Ouvre 🎲 Modèles gratuits et actualise-le avec une connexion Internet.' });
      save();
      render();
      return;
    }

    d.messages.push({ role: 'user', content: prompt });
    $('#prompt').value = '';
    save();
    render();
    const candidates = [...freeModels];
    for (let i = candidates.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
    }
    const failures = [];
    try {
      for (const model of candidates.slice(0, Math.min(3, candidates.length))) {
        const response = await fetch(CHAT_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${sessionStorage.getItem(KEY_STORAGE)}`,
            'HTTP-Referer': location.origin,
            'X-Title': 'Nova Studio'
          },
          body: JSON.stringify({
            model: model.id,
            messages: [{ role: 'system', content: roles[$('#role').value] }, ...d.messages.slice(-20)],
            stream: false
          })
        });
        if (response.ok) {
          const result = await response.json();
          const answer = result.choices?.[0]?.message?.content;
          if (typeof answer !== 'string' || !answer.trim()) throw new Error(`Réponse vide du modèle ${model.id}`);
          d.messages.push({ role: 'assistant', content: `🎲 ${model.name || model.id}\n\n${answer}` });
          failures.length = 0;
          break;
        }
        const detail = await response.text();
        failures.push(`${model.id} : HTTP ${response.status}`);
        if ([400, 401, 402, 403].includes(response.status)) {
          throw new Error(`OpenRouter a refusé la requête (HTTP ${response.status}). Vérifie la clé et le compte. ${detail.slice(0, 240)}`);
        }
      }
      if (failures.length) throw new Error(`Les modèles essayés sont temporairement indisponibles ou limités : ${failures.join('; ')}`);
    } catch (error) {
      d.messages.push({ role: 'assistant', content: `Échec du mode aléatoire : ${error.message}` });
    }
    save();
    render();
  };
})();
