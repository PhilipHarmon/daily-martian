// Gallery lightbox — click a photo card to view it large.
(function () {
  var lightbox = document.getElementById('lightbox');
  if (!lightbox) return;

  var img = document.getElementById('lb-img');
  var title = document.getElementById('lb-title');
  var date = document.getElementById('lb-date');
  var desc = document.getElementById('lb-desc');
  var full = document.getElementById('lb-full');

  function open(card) {
    img.src = card.getAttribute('data-large');
    img.alt = card.getAttribute('data-title') || '';
    title.textContent = card.getAttribute('data-title') || '';
    date.textContent = card.getAttribute('data-date') || '';
    desc.textContent = card.getAttribute('data-desc') || '';
    full.href = card.getAttribute('data-large');
    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lightbox.hidden = true;
    document.body.style.overflow = '';
    img.src = '';
  }

  document.querySelectorAll('.photo-card').forEach(function (card) {
    card.addEventListener('click', function () { open(card); });
  });

  lightbox.querySelectorAll('[data-close]').forEach(function (el) {
    el.addEventListener('click', close);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !lightbox.hidden) close();
  });
})();
