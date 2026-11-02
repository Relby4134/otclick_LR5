function initializeQuestionEditor() {
  const kind = document.getElementById('id_kind');
  if (!kind) return;
  const setVisible = (element, visible) => {
    if (element) element.toggleAttribute('data-kind-hidden', !visible);
  };
  const updateKind = () => {
    setVisible(document.querySelector('.question-puzzle'), kind.value === 'puzzle');
    setVisible(document.querySelector('.question-slider'), kind.value === 'slider');
    setVisible(document.querySelector('.question-audio'), kind.value === 'audio');
    setVisible(document.querySelector('.question-text'), ['text', 'audio'].includes(kind.value));
    setVisible(document.getElementById('choices-group'), ['single', 'multiple', 'image'].includes(kind.value));
    document.querySelectorAll('th.column-image_url, td.field-image_url').forEach(el => setVisible(el, kind.value === 'image'));
  };
  kind.addEventListener('change', updateKind);
  updateKind();

  const editor = document.querySelector('[data-puzzle-editor]');
  if (!editor) return;
  const file = document.getElementById('id_puzzle_image');
  const target = document.getElementById('id_puzzle_target');
  const vertical = document.getElementById('id_puzzle_y');
  const board = editor.querySelector('.editor-board');
  const image = editor.querySelector('.editor-image');
  const selection = editor.querySelector('.editor-selection');
  const content = editor.querySelector('.editor-content');
  const empty = editor.querySelector('.editor-empty');
  const preview = editor.querySelector('[data-puzzle]');
  const trial = preview.querySelector('input[type="range"]');
  const coordinates = editor.querySelector('.editor-coordinates');
  let objectUrl;
  const clamp = value => Math.max(0, Math.min(100, value));
  const refresh = () => {
    const x = clamp(Number(target.value) || 0);
    const y = clamp(Number(vertical.value) || 0);
    selection.style.left = `${x * 0.8}%`;
    selection.style.top = `${y * 0.7}%`;
    coordinates.textContent = `\u041f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u0435: \u043f\u043e \u0433\u043e\u0440\u0438\u0437\u043e\u043d\u0442\u0430\u043b\u0438 ${x}%, \u043f\u043e \u0432\u0435\u0440\u0442\u0438\u043a\u0430\u043b\u0438 ${y}%.`;
    preview.dataset.target = x;
    preview.dataset.y = y;
    preview.dispatchEvent(new Event('puzzle:refresh'));
  };
  const showImage = src => {
    image.src = src;
    preview.querySelector('.puzzle-image').src = src;
    empty.hidden = true;
    content.hidden = false;
    refresh();
  };
  const resetTrial = () => {
    trial.value = Number(target.value) >= 50 ? 0 : 100;
    trial.dispatchEvent(new Event('input', {bubbles: true}));
  };
  file.addEventListener('change', () => {
    if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = undefined; }
    if (!file.files.length) {
      const saved = image.dataset.savedSrc;
      if (saved) showImage(saved);
      else { content.hidden = true; empty.hidden = false; }
      return;
    }
    if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.files[0].type)) {
      empty.textContent = '\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 JPG, PNG, WebP \u0438\u043b\u0438 GIF.';
      empty.hidden = false; content.hidden = true; return;
    }
    objectUrl = URL.createObjectURL(file.files[0]);
    showImage(objectUrl);
    resetTrial();
  });
  target.addEventListener('input', refresh);
  vertical.addEventListener('input', refresh);
  const place = event => {
    const rect = board.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    target.value = Math.round(clamp(((event.clientX - rect.left) / rect.width - 0.1) / 0.8 * 100));
    vertical.value = Math.round(clamp(((event.clientY - rect.top) / rect.height - 0.15) / 0.7 * 100));
    refresh();
  };
  board.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    board.setPointerCapture(event.pointerId);
    place(event);
  });
  board.addEventListener('pointermove', event => {
    if (board.hasPointerCapture(event.pointerId)) place(event);
  });
  board.addEventListener('pointerup', event => {
    if (board.hasPointerCapture(event.pointerId)) board.releasePointerCapture(event.pointerId);
  });
  image.addEventListener('error', () => {
    empty.textContent = '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0439 \u0444\u0430\u0439\u043b.';
    empty.hidden = false; content.hidden = true;
  });
  if (image.getAttribute('src')) {
    image.dataset.savedSrc = image.getAttribute('src');
    showImage(image.getAttribute('src'));
    resetTrial();
  }
  window.addEventListener('pagehide', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeQuestionEditor, {once:true});
else initializeQuestionEditor();
