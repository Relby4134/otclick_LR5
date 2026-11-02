function initializeSurveyInteractions() {
  document.querySelectorAll('input[type="range"]').forEach(input => {
    const output = input.parentElement.querySelector('output');
    if (!output) return;
    const update = () => { output.textContent = input.value; };
    input.addEventListener('input', update);
    update();
  });
  // Keep geometry proportional to the image: resize needs no pixel calculations.
  document.querySelectorAll('[data-puzzle]').forEach(puzzle => {
    const image = puzzle.querySelector('.puzzle-image');
    const input = puzzle.querySelector('input[type="range"]');
    if (!image || !input) return;
    const piece = puzzle.querySelector('.puzzle-piece');
    const hole = puzzle.querySelector('.puzzle-hole');
    const error = puzzle.querySelector('.puzzle-error');

    const update = () => { piece.style.left = `${Number(input.value) * 0.8}%`; };
    const ready = () => {
      if (!image.naturalWidth) return;
      const target = Number(puzzle.dataset.target);
      const y = Number(puzzle.dataset.y);
      hole.style.left = `${target * 0.8}%`;
      hole.style.top = piece.style.top = `${y * 0.7}%`;
      piece.style.backgroundImage = `url("${image.currentSrc || image.src}")`;
      piece.style.backgroundPosition = `${target}% ${y}%`;
      error.hidden = true;
      puzzle.classList.add('puzzle-ready');
      update();
    };
    const failed = () => { puzzle.classList.remove('puzzle-ready'); error.hidden = false; };
    puzzle.addEventListener('puzzle:refresh', ready);
    image.addEventListener('load', ready);
    image.addEventListener('error', failed);
    const help = puzzle.querySelector('.puzzle-help');
    if (help) input.setAttribute('aria-describedby', help.id);
    input.addEventListener('input', update);
    if (image.complete) image.naturalWidth ? ready() : failed();
  });
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSurveyInteractions, {once: true});
} else {
  initializeSurveyInteractions();
}
