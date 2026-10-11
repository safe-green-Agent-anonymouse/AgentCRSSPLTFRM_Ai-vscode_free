(() => {
  const messages = document.querySelector('#messages');
  const chatForm = document.querySelector('#chatForm');
  if (!messages || !chatForm || typeof d === 'undefined' || typeof save !== 'function' || typeof render !== 'function') {
    console.error('Nova Studio message controls could not initialize: chat UI dependencies are missing.');
    return;
  }

  const styles = document.createElement('style');
  styles.textContent = '.message-delete{display:block;margin:10px 0 0 auto;padding:5px 8px;border:1px solid #514653;border-radius:7px;background:#24212a;color:#d7c4c4;font:inherit;font-size:10px;cursor:pointer}.message-delete:hover{background:#3b2930;color:#fff}.message-delete:focus-visible{outline:2px solid var(--purple,#9a7bff);outline-offset:2px}.message-local-note{margin:5px 0 10px;color:var(--muted,#9698a6);font-size:10px;line-height:1.5}';
  document.head.append(styles);

  const note = document.createElement('p');
  note.className = 'message-local-note';
  note.textContent = 'Tu peux retirer chaque message de cet historique local. Cela ne supprime pas les requêtes déjà envoyées à un fournisseur d’IA.';
  chatForm.before(note);

  function addDeleteButtons() {
    const bubbles = messages.querySelectorAll('.bubble');
    for (const [index, bubble] of Array.from(bubbles).entries()) {
      if (index >= d.messages.length || bubble.querySelector('.message-delete')) continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'message-delete';
      button.dataset.messageIndex = String(index);
      button.setAttribute('aria-label', `Supprimer le message ${index + 1} de mon historique local`);
      button.textContent = 'Supprimer pour moi';
      bubble.append(button);
    }
  }

  const originalRender = render;
  render = function (...args) {
    const result = originalRender.apply(this, args);
    addDeleteButtons();
    return result;
  };
  addDeleteButtons();

  messages.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-message-index]');
    if (!button) return;

    const index = Number(button.dataset.messageIndex);
    if (!Number.isInteger(index) || index < 0 || index >= d.messages.length) return;
    if (!window.confirm('Supprimer ce message de ton historique local sur cet appareil ?')) return;

    const [removed] = d.messages.splice(index, 1);
    if (!save()) {
      d.messages.splice(index, 0, removed);
      render();
      return;
    }
    render();
  });
})();
