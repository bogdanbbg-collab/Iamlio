(function () {
  "use strict";

  var TURN_MS = 750;
  var PAUSE_BEFORE_TURN_MS = 900;

  var params = new URLSearchParams(location.search);
  var storyId = params.get("id") || "";
  var base = "stories/" + encodeURIComponent(storyId) + "/";

  var book = document.getElementById("book");
  var titleEl = document.getElementById("story-title");
  var dotsEl = document.getElementById("dots");
  var prevBtn = document.getElementById("prev-btn");
  var nextBtn = document.getElementById("next-btn");
  var playBtn = document.getElementById("play-btn");
  var autoBtn = document.getElementById("auto-btn");

  var items = [];
  var sheets = [];
  var index = 0;
  var busy = false;

  var reading = false;
  var autoTurn = readSetting("iamlio-autoturn", "1") === "1";
  var manifest = null;
  var audio = new Audio();
  var playToken = 0;
  var speechVoice = null;

  // ---------- utilitare ----------

  function readSetting(key, fallback) {
    try {
      var value = localStorage.getItem(key);
      return value === null ? fallback : value;
    } catch (e) {
      return fallback;
    }
  }

  function writeSetting(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) { /* stocarea poate lipsi; nu e esențială */ }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function image(src, eager) {
    var img = el("img");
    img.src = base + src;
    img.alt = "";
    img.decoding = "async";
    img.loading = eager ? "eager" : "lazy";
    img.draggable = false;
    return img;
  }

  function showError(message) {
    book.textContent = "";
    var box = el("div", "reader-error");
    box.appendChild(el("p", null, message));
    var back = el("a", "pill", "Înapoi la povești");
    back.href = "./";
    box.appendChild(back);
    book.appendChild(box);
    document.querySelector(".reader-controls").hidden = true;
  }

  // ---------- construirea cărții ----------

  function buildItems(story) {
    var list = [{
      kind: "cover",
      image: story.cover.image,
      title: story.title,
      audio: "coperta.mp3",
      speech: "Lio îți citește povestea: " + story.title + "."
    }];
    story.pages.forEach(function (page, i) {
      var number = String(i + 1).padStart(2, "0");
      list.push({
        kind: "page",
        image: page.image,
        text: page.text,
        number: i + 1,
        audio: "pagina-" + number + ".mp3",
        speech: page.text
      });
    });
    list.push({
      kind: "end",
      moral: story.moral,
      audio: "final.mp3",
      speech: "Sfârșit. " + story.moral
    });
    return list;
  }

  function buildSheet(item, i) {
    var sheet = el("article", "sheet");
    var front = el("div", "face face-front");
    sheet.setAttribute("aria-label", item.kind === "page" ? "Pagina " + item.number : item.kind === "cover" ? "Copertă" : "Sfârșit");

    if (item.kind === "cover") {
      var coverArt = el("figure", "sheet-art");
      coverArt.appendChild(image(item.image, true));
      front.appendChild(coverArt);
      var coverText = el("div", "sheet-text cover-text");
      coverText.appendChild(el("h2", null, item.title));
      coverText.appendChild(el("p", "cover-hint", "Dă pagina sau apasă pe Lio ca să-ți citească."));
      front.appendChild(coverText);
    } else if (item.kind === "page") {
      var art = el("figure", "sheet-art");
      art.appendChild(image(item.image, i < 3));
      front.appendChild(art);
      var text = el("div", "sheet-text");
      text.appendChild(el("p", null, item.text));
      text.appendChild(el("span", "page-num", String(item.number)));
      front.appendChild(text);
    } else {
      var end = el("div", "sheet-end");
      var lio = el("img", "end-lio");
      lio.src = "assets/img/lio.svg";
      lio.alt = "";
      end.appendChild(lio);
      end.appendChild(el("h2", null, "Sfârșit"));
      end.appendChild(el("p", "moral", item.moral));
      var actions = el("div", "end-actions");
      var again = el("button", "pill", "Citește din nou");
      again.type = "button";
      again.addEventListener("click", function () {
        stopAudio();
        setReading(false);
        index = 0;
        render();
      });
      var more = el("a", "pill pill-alt", "Alte povești");
      more.href = "./";
      actions.appendChild(again);
      actions.appendChild(more);
      end.appendChild(actions);
      front.appendChild(end);
    }

    front.appendChild(el("div", "shade"));
    sheet.appendChild(front);
    sheet.appendChild(el("div", "face face-back"));
    return sheet;
  }

  function render() {
    sheets.forEach(function (sheet, i) {
      sheet.className = "sheet" + (i === index ? " is-current" : i === index + 1 ? " is-next" : "");
      sheet.style.transition = "";
      sheet.style.transform = "";
      sheet.setAttribute("aria-hidden", i === index ? "false" : "true");
    });
    Array.prototype.forEach.call(dotsEl.children, function (dot, i) {
      dot.classList.toggle("active", i === index);
    });
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === sheets.length - 1;
  }

  // ---------- întoarcerea paginilor ----------

  function animateTo(sheet, angle, done) {
    var finished = false;
    function finish() {
      if (finished) return;
      finished = true;
      sheet.removeEventListener("transitionend", onEnd);
      done();
    }
    function onEnd(event) {
      if (event.target === sheet && event.propertyName === "transform") finish();
    }
    sheet.addEventListener("transitionend", onEnd);
    sheet.style.transition = "";
    sheet.style.transform = "rotateY(" + angle + "deg)";
    setTimeout(finish, TURN_MS + 150);
  }

  function prepareTurn(direction) {
    var sheet = direction > 0 ? sheets[index] : sheets[index - 1];
    sheet.style.transition = "none";
    sheet.className = "sheet is-turning";
    sheet.style.transform = "rotateY(" + (direction > 0 ? 0 : -180) + "deg)";
    void sheet.offsetWidth; // aplică poziția de start înainte de animație
    return sheet;
  }

  function canTurn(direction) {
    return direction > 0 ? index < sheets.length - 1 : index > 0;
  }

  function completeTurn(direction, sheet) {
    animateTo(sheet, direction > 0 ? -180 : 0, function () {
      index += direction;
      render();
      busy = false;
      afterTurn();
    });
  }

  function turn(direction) {
    if (busy || !canTurn(direction)) return;
    busy = true;
    stopAudio();
    completeTurn(direction, prepareTurn(direction));
  }

  function afterTurn() {
    if (reading) playCurrent();
  }

  // Swipe: pagina urmează degetul, apoi se întoarce sau revine.
  var drag = null;

  book.addEventListener("pointerdown", function (event) {
    if (busy || event.button > 0 || event.target.closest("a, button")) return;
    drag = { x: event.clientX, y: event.clientY, t: Date.now(), active: false, direction: 0, sheet: null };
  });

  book.addEventListener("pointermove", function (event) {
    if (!drag) return;
    var dx = event.clientX - drag.x;
    var dy = event.clientY - drag.y;
    if (!drag.active) {
      if (Math.abs(dx) < 10 || Math.abs(dx) < Math.abs(dy)) return;
      var direction = dx < 0 ? 1 : -1;
      if (!canTurn(direction)) {
        drag = null;
        return;
      }
      drag.active = true;
      drag.direction = direction;
      busy = true;
      stopAudio();
      drag.sheet = prepareTurn(direction);
      book.setPointerCapture(event.pointerId);
    }
    var progress = Math.min(1, Math.max(0, (dx * -drag.direction) / (book.clientWidth * 0.85)));
    drag.progress = progress;
    var angle = drag.direction > 0 ? -180 * progress : -180 * (1 - progress);
    drag.sheet.style.transform = "rotateY(" + angle + "deg)";
  });

  function endDrag(event) {
    if (!drag) return;
    var current = drag;
    drag = null;
    if (!current.active) {
      // Atingere simplă: dreapta = înainte, stânga = înapoi.
      if (event.type === "pointerup" && Math.abs(event.clientX - current.x) < 10) {
        var rect = book.getBoundingClientRect();
        turn(event.clientX > rect.left + rect.width / 2 ? 1 : -1);
      }
      return;
    }
    var fast = Date.now() - current.t < 300 && current.progress > 0.08;
    if (current.progress > 0.3 || fast) {
      completeTurn(current.direction, current.sheet);
    } else {
      animateTo(current.sheet, current.direction > 0 ? 0 : -180, function () {
        render();
        busy = false;
        afterTurn();
      });
    }
  }

  book.addEventListener("pointerup", endDrag);
  book.addEventListener("pointercancel", endDrag);

  prevBtn.addEventListener("click", function () { turn(-1); });
  nextBtn.addEventListener("click", function () { turn(1); });

  document.addEventListener("keydown", function (event) {
    if (event.key === "ArrowRight") turn(1);
    else if (event.key === "ArrowLeft") turn(-1);
    else if (event.key === " " && !event.target.closest("button, a")) {
      event.preventDefault();
      setReading(!reading);
    }
  });

  // ---------- vocea lui Lio ----------

  function pickVoice() {
    if (!("speechSynthesis" in window)) return;
    var voices = speechSynthesis.getVoices().filter(function (v) {
      return /^ro/i.test(v.lang);
    });
    var preferred = voices.filter(function (v) {
      return /alina|ioana|emil|google|natural/i.test(v.name);
    });
    speechVoice = preferred[0] || voices[0] || null;
  }

  if ("speechSynthesis" in window) {
    pickVoice();
    speechSynthesis.addEventListener("voiceschanged", pickVoice);
  }

  function stopAudio() {
    playToken++;
    audio.onended = null;
    audio.onerror = null;
    audio.pause();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
  }

  function speak(text, token) {
    if (!("speechSynthesis" in window)) {
      setReading(false);
      return;
    }
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ro-RO";
    if (speechVoice) utterance.voice = speechVoice;
    utterance.rate = 0.9;
    utterance.pitch = 1.05;
    utterance.onend = function () { onReadEnd(token); };
    speechSynthesis.speak(utterance);
  }

  function playCurrent() {
    stopAudio();
    var token = playToken;
    var item = items[index];
    if (manifest && manifest[item.audio]) {
      audio.src = base + "audio/" + item.audio;
      audio.onended = function () { onReadEnd(token); };
      audio.onerror = function () { if (token === playToken) speak(item.speech, token); };
      audio.play().catch(function () {
        if (token === playToken) speak(item.speech, token);
      });
    } else {
      speak(item.speech, token);
    }
  }

  function onReadEnd(token) {
    if (token !== playToken || !reading) return;
    if (index === sheets.length - 1) {
      setReading(false);
      return;
    }
    if (!autoTurn) return; // așteaptă ca cel mic să dea pagina
    setTimeout(function () {
      if (token === playToken && reading) turn(1);
    }, PAUSE_BEFORE_TURN_MS);
  }

  function setReading(on) {
    reading = on;
    playBtn.classList.toggle("is-playing", on);
    playBtn.setAttribute("aria-label", on ? "Oprește citirea" : "Lio citește povestea");
    if (!on) {
      stopAudio();
      return;
    }
    if (index === sheets.length - 1) {
      index = 0;
      render();
    }
    if (!busy) playCurrent();
  }

  playBtn.addEventListener("click", function () { setReading(!reading); });

  function updateAutoBtn() {
    autoBtn.setAttribute("aria-pressed", autoTurn ? "true" : "false");
    autoBtn.title = autoTurn ? "Lio întoarce singur paginile (apasă pentru a opri)" : "Paginile se dau manual (apasă ca Lio să le întoarcă singur)";
  }

  autoBtn.addEventListener("click", function () {
    autoTurn = !autoTurn;
    writeSetting("iamlio-autoturn", autoTurn ? "1" : "0");
    updateAutoBtn();
  });

  // ---------- pornire ----------

  function start(story) {
    document.title = story.title + " — Iamlio";
    titleEl.textContent = story.title;
    items = buildItems(story);
    book.textContent = "";
    dotsEl.textContent = "";
    sheets = items.map(function (item, i) {
      var sheet = buildSheet(item, i);
      book.appendChild(sheet);
      dotsEl.appendChild(el("span", "dot"));
      return sheet;
    });
    updateAutoBtn();
    render();
  }

  if (!/^[a-z0-9-]+$/.test(storyId)) {
    showError("Nu am găsit povestea aceasta.");
    return;
  }

  fetch(base + "audio/manifest.json", { cache: "no-cache" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .catch(function () { return null; })
    .then(function (data) { manifest = data; });

  fetch(base + "story.json", { cache: "no-cache" })
    .then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    })
    .then(start)
    .catch(function () {
      showError("Nu am găsit povestea aceasta.");
    });
})();
