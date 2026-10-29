// Fit text to its box, the same way every time: no randomness, no clock, no network.
// Each [data-fit] box scales the font size of its [data-max] children together, in fixed
// steps, from their largest size down to their smallest, and stops at the first size where
// nothing overflows the box and no word is wider than its line. If even the smallest size
// overflows, window.__fitErrors names the box, so the renderer refuses rather than clip.
(function () {
  function overflows(box) {
    if (box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1) return true;
    var kids = box.querySelectorAll('[data-max]');
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].scrollWidth > kids[i].clientWidth + 1) return true;
    }
    return false;
  }
  function fit(box) {
    var kids = Array.prototype.slice.call(box.querySelectorAll('[data-max]'));
    var steps = 60;
    for (var s = 0; s <= steps; s++) {
      kids.forEach(function (k) {
        var max = parseFloat(k.getAttribute('data-max'));
        var min = parseFloat(k.getAttribute('data-min') || String(max * 0.5));
        k.style.fontSize = Math.round(max - (max - min) * s / steps) + 'px';
      });
      if (!overflows(box)) return null;
    }
    return box.getAttribute('data-fit') || 'a text box';
  }
  window.__fit = function () {
    var errors = [];
    document.querySelectorAll('[data-empty-hide]').forEach(function (el) {
      if (!el.textContent.trim()) el.style.display = 'none';
    });
    document.querySelectorAll('[data-fit]').forEach(function (box) {
      var e = fit(box);
      if (e) errors.push(e + ' overflows at its smallest size');
    });
    window.__fitErrors = errors;
    return errors;
  };
})();
