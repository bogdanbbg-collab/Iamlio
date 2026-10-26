(function () {
  "use strict";

  // Cine a cerut „mișcare redusă” în sistem vede paginile schimbându-se fără animație.
  var REDUCED_MOTION = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var TURN_MS = REDUCED_MOTION ? 1 : 1300;    // o întoarcere completă de pagină, ca într-o carte adevărată
  var MIN_TURN_MS = REDUCED_MOTION ? 1 : 450; // după un swipe, restul întoarcerii nu e mai scurt de atât
  var TAP_MAX_MOVE = 10;
  var TAP_MAX_MS = 600;
  var PAUSE_BEFORE_TURN_MS = 1200;

  var params = new URLSearchParams(location.search);
  var storyId = params.get("id") || "";
  var base = "stories/" + encodeURIComponent(storyId) + "/";

  var book = document.getElementById("book");
  var titleEl = document.getElementById("story-title");
  var dotsEl = document.getElementById("dots");
  var prevBtn = document.getElementById("prev-btn");
  var nextBtn = document.getElementById("next-btn");
  var playBtn = document.getElementById("play-btn");
  var readsEl = document.getElementById("story-reads");
  var settingsEl = document.getElementById("settings");
  var settingsBtn = document.getElementById("settings-btn");
  var autoInput = document.getElementById("auto-turn");
  var bedtimeInput = document.getElementById("bedtime");
  var fullscreenBtn = document.getElementById("fullscreen-btn");

  var SPEEDS = [0.8, 0.9, 1, 1.1];
  var BEDTIME_VOLUME = 0.7;
  var RESUME_KEY = "iamlio-pagina-" + (new URLSearchParams(location.search).get("id") || "");

  var items = [];
  var sheets = [];
  var index = 0;
  var busy = false;

  var reading = false;
  var autoTurn = Iamlio.readSetting("iamlio-autoturn", "1") === "1";
  var speed = Number(Iamlio.readSetting("iamlio-viteza", "1"));
  if (SPEEDS.indexOf(speed) === -1) speed = 1;
  var bedtime = Iamlio.readSetting("iamlio-culcare", "0") === "1";
  var manifest = null;
  var audio = new Audio();
  audio.preload = "auto";
  audio.hidden = true;
  document.body.appendChild(audio);
  var playToken = 0;
  var timing = null;      // [[început, sfârșit], …] pentru replicile paginii citite acum
  var spoken = -1;        // replica evidențiată acum

  // ---------- utilitare ----------

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
    var lio = story.lio || {};
    var list = [{
      kind: "cover",
      image: story.cover.image,
      title: story.title,
      intro: lio.intro || "",
      audio: "coperta.mp3",
      speech: "Lio îți citește povestea: " + story.title + "."
    }];
    story.pages.forEach(function (page, i) {
      var number = String(i + 1).padStart(2, "0");
      list.push({
        kind: "page",
        image: page.image,
        text: page.text,
        narration: Array.isArray(page.narration) ? page.narration.map(function (n) { return n.text; }) : [],
        number: i + 1,
        audio: "pagina-" + number + ".mp3",
        speech: page.text
      });
    });
    list.push({
      kind: "end",
      moral: story.moral,
      outro: lio.outro || "",
      questions: Array.isArray(story.questions) ? story.questions : [],
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
      if (item.intro) {
        var says = el("p", "lio-bubble");
        var face = el("img", "lio-bubble-face");
        face.src = "assets/img/lio-cap.svg";
        face.alt = "";
        says.appendChild(face);
        says.appendChild(el("span", null, item.intro));
        coverText.appendChild(says);
      }
      coverText.appendChild(el("h2", null, item.title));
      coverText.appendChild(el("p", "cover-reads"));
      coverText.appendChild(el("p", "cover-hint", "Dă pagina sau apasă pe Lio ca să-ți citească."));
      coverText.appendChild(resumeBox());
      front.appendChild(coverText);
    } else if (item.kind === "page") {
      var art = el("figure", "sheet-art");
      art.appendChild(image(item.image, i < 3));
      front.appendChild(art);
      var text = el("div", "sheet-text");
      text.appendChild(pageText(item));
      text.appendChild(el("span", "page-num", String(item.number)));
      front.appendChild(text);
    } else {
      var end = el("div", "sheet-end");
      var lio = el("img", "end-lio");
      lio.src = REDUCED_MOTION ? "assets/img/lio-static.svg" : "assets/img/lio.svg";
      lio.alt = "";
      lio.setAttribute("data-awake", lio.src);
      end.appendChild(lio);
      end.appendChild(el("h2", null, "Sfârșit"));
      end.appendChild(el("p", "moral", item.moral));
      if (item.outro) end.appendChild(el("p", "end-outro", item.outro));
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
      if (item.questions.length) {
        var quiz = el("button", "pill pill-quiz", "🎲 Întrebările lui Lio");
        quiz.type = "button";
        quiz.addEventListener("click", function () { openQuiz(item.questions); });
        actions.appendChild(quiz);
      }
      actions.appendChild(again);
      actions.appendChild(more);
      end.appendChild(actions);
      var recs = el("div", "end-recs");
      recs.hidden = true;
      end.appendChild(recs);
      front.appendChild(end);
    }

    front.appendChild(el("div", "shade"));
    sheet.appendChild(front);
    sheet.appendChild(el("div", "face face-back"));
    return sheet;
  }

  // Textul paginii, cu fiecare replică din regia de voce într-un <span>, ca să poată fi evidențiată când e citită.
  function pageText(item) {
    var p = el("p");
    var cursor = 0;
    var ranges = [];
    for (var i = 0; i < item.narration.length; i++) {
      var at = item.text.indexOf(item.narration[i], cursor);
      if (at === -1) { ranges = null; break; }
      ranges.push([at, at + item.narration[i].length]);
      cursor = at + item.narration[i].length;
    }
    if (!item.narration.length) {
      p.textContent = item.text;
      return p;
    }
    if (!ranges) { // textul și regia diferă doar prin punctuație: afișăm replicile, una după alta
      item.narration.forEach(function (part, n) {
        if (n) p.appendChild(document.createTextNode(" "));
        p.appendChild(el("span", "seg", part));
      });
      return p;
    }
    var last = 0;
    ranges.forEach(function (range) {
      if (range[0] > last) p.appendChild(document.createTextNode(item.text.slice(last, range[0])));
      p.appendChild(el("span", "seg", item.text.slice(range[0], range[1])));
      last = range[1];
    });
    if (last < item.text.length) p.appendChild(document.createTextNode(item.text.slice(last)));
    return p;
  }

  // Reluarea: dacă cel mic a rămas la mijlocul poveștii, coperta îi oferă să continue de acolo.
  function savedPage() {
    var value = Number(Iamlio.readSetting(RESUME_KEY, "0"));
    return value > 0 && value < items.length - 1 ? value : 0;
  }

  function resumeBox() {
    var box = el("div", "resume");
    box.hidden = true;
    box.appendChild(el("p", "resume-text"));
    var go = el("button", "pill resume-continue", "Continuă");
    go.type = "button";
    go.addEventListener("click", function () {
      var page = savedPage();
      if (page) jumpTo(page);
    });
    var restart = el("button", "pill pill-alt resume-restart", "De la început");
    restart.type = "button";
    restart.addEventListener("click", function () {
      Iamlio.writeSetting(RESUME_KEY, "0");
      box.hidden = true;
    });
    var actions = el("div", "resume-actions");
    actions.appendChild(go);
    actions.appendChild(restart);
    box.appendChild(actions);
    return box;
  }

  function updateResume() {
    var box = book.querySelector(".resume");
    var page = savedPage();
    if (!box) return;
    box.hidden = !page;
    if (page) box.querySelector(".resume-text").textContent = "Ai rămas la pagina " + page + ".";
  }

  function jumpTo(target) {
    stopAudio();
    index = target;
    render();
    if (reading) playCurrent();
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
    if (index > 0) Iamlio.writeSetting(RESUME_KEY, index < sheets.length - 1 ? String(index) : "0");
    if (index === sheets.length - 1) Iamlio.markFinished(storyId);
    clearSpoken();
    preloadNext();
  }

  // Pagina următoare e pregătită dinainte: imaginea se încarcă, iar vocea se descarcă dacă Lio citește.
  var preloaded = {};
  function preloadNext() {
    var next = sheets[index + 1];
    if (!next) return;
    var img = next.querySelector("img");
    if (img && img.loading === "lazy") img.loading = "eager";
    var url = reading && audioUrl(items[index + 1]);
    if (url && !preloaded[url]) {
      preloaded[url] = true;
      fetch(url).catch(function () { delete preloaded[url]; });
    }
  }

  // ---------- întoarcerea paginilor ----------

  function animateTo(sheet, angle, done, duration) {
    var ms = duration || TURN_MS;
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
    sheet.style.transition = "transform " + ms + "ms cubic-bezier(.3, .1, .2, 1)";
    sheet.style.transform = "rotateY(" + angle + "deg)";
    setTimeout(finish, ms + 150);
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

  // remaining = cât mai are pagina de parcurs (1 = toată întoarcerea), ca după swipe să nu „sară”.
  function completeTurn(direction, sheet, remaining) {
    var share = remaining === undefined ? 1 : remaining;
    animateTo(sheet, direction > 0 ? -180 : 0, function () {
      index += direction;
      render();
      busy = false;
      afterTurn();
    }, Math.max(MIN_TURN_MS, TURN_MS * share));
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

  // Un singur deget contează: al doilea deget pus pe ecran în timpul unui gest e ignorat.
  book.addEventListener("pointerdown", function (event) {
    if (drag || busy || event.button > 0 || event.target.closest("a, button")) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY, t: Date.now(), moved: 0,
             active: false, direction: 0, sheet: null, progress: 0 };
  });

  book.addEventListener("pointermove", function (event) {
    if (!drag || event.pointerId !== drag.id) return;
    var dx = event.clientX - drag.x;
    var dy = event.clientY - drag.y;
    drag.moved = Math.max(drag.moved, Math.abs(dx), Math.abs(dy));
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
    if (!drag || event.pointerId !== drag.id) return;
    var current = drag;
    drag = null;
    if (!current.active) {
      // Atingere scurtă, fără mișcare (nu derularea textului): dreapta = înainte, stânga = înapoi.
      var isTap = event.type === "pointerup" && current.moved < TAP_MAX_MOVE && Date.now() - current.t < TAP_MAX_MS;
      if (isTap) {
        var rect = book.getBoundingClientRect();
        turn(event.clientX > rect.left + rect.width / 2 ? 1 : -1);
      }
      return;
    }
    var cancelled = event.type === "pointercancel"; // gest întrerupt de browser: pagina revine
    var fast = Date.now() - current.t < 300 && current.progress > 0.08;
    if (!cancelled && (current.progress > 0.3 || fast)) {
      completeTurn(current.direction, current.sheet, 1 - current.progress);
    } else {
      animateTo(current.sheet, current.direction > 0 ? 0 : -180, function () {
        render();
        busy = false;
        afterTurn();
      }, Math.max(MIN_TURN_MS, TURN_MS * current.progress));
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

  function talking(on) {
    playBtn.classList.toggle("is-talking", on);
  }

  // Evidențierea: replica citită acum se colorează, iar Lio mișcă gura doar cât vorbește (nu și în pauze).
  function segments() {
    var sheet = sheets[index];
    return sheet ? sheet.querySelectorAll(".seg") : [];
  }

  function clearSpoken() {
    spoken = -1;
    Array.prototype.forEach.call(book.querySelectorAll(".seg.is-spoken"), function (span) {
      span.classList.remove("is-spoken");
    });
  }

  function showMoment(seconds) {
    var current = -1;
    for (var i = 0; timing && i < timing.length; i++) {
      if (seconds >= timing[i][0] && seconds < timing[i][1]) { current = i; break; }
    }
    talking(current !== -1);
    if (current === spoken) return;
    clearSpoken();
    spoken = current;
    var span = segments()[current];
    if (span) {
      span.classList.add("is-spoken");
      if (span.scrollIntoView) span.scrollIntoView({ block: "nearest" });
    }
  }

  function followAudio() {
    if (audio.paused || !timing) return;
    showMoment(audio.currentTime);
    requestAnimationFrame(followAudio);
  }

  audio.addEventListener("playing", function () {
    if (timing) followAudio();
    else talking(true);
  });
  audio.addEventListener("timeupdate", function () { if (timing) showMoment(audio.currentTime); });
  audio.addEventListener("pause", function () { talking(false); });
  audio.addEventListener("ended", function () { talking(false); clearSpoken(); });

  function stopAudio() {
    playToken++;
    audio.onended = null;
    audio.onerror = null;
    audio.pause();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    timing = null; // altfel, actualizarea de timp care vine după pauză ar evidenția din nou replica
    talking(false);
    clearSpoken();
  }

  function speak(text, token) {
    var started = Iamlio.speakWithBrowser(text, Iamlio.getVoice(), {
      speed: speed,
      onstart: function () { if (token === playToken) talking(true); },
      onend: function () {
        if (token !== playToken) return;
        talking(false);
        onReadEnd(token);
      }
    });
    if (!started) setReading(false);
  }

  // Adresa include amprenta din manifest: după ce vocea e regenerată, browserul nu mai redă varianta veche.
  function audioUrl(item) {
    var voice = Iamlio.getVoice();
    var digest = manifest && manifest[voice] && manifest[voice][item.audio];
    return digest ? base + "audio/" + voice + "/" + item.audio + "?v=" + String(digest).slice(0, 10) : "";
  }

  function playCurrent() {
    stopAudio();
    var token = playToken;
    var item = items[index];
    var url = audioUrl(item);
    var voiceTiming = manifest && manifest.timing && manifest.timing[Iamlio.getVoice()];
    timing = voiceTiming && voiceTiming[item.audio] || null;
    if (url) {
      audio.src = url;
      applyAudioSettings();
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
    preloadNext();
  }

  playBtn.addEventListener("click", function () { setReading(!reading); });

  // ---------- setări de citire ----------

  // Schimbarea sursei readuce viteza la normal, așa că viteza și volumul se aplică la fiecare redare.
  function applyAudioSettings() {
    audio.defaultPlaybackRate = speed;
    audio.playbackRate = speed;
    if ("preservesPitch" in audio) audio.preservesPitch = true;
    audio.volume = bedtime ? BEDTIME_VOLUME : 1;
  }

  function openSettings() {
    settingsEl.hidden = false;
    settingsBtn.setAttribute("aria-expanded", "true");
    document.getElementById("settings-close").focus();
  }

  function closeSettings() {
    settingsEl.hidden = true;
    settingsBtn.setAttribute("aria-expanded", "false");
    settingsBtn.focus();
  }

  settingsBtn.addEventListener("click", openSettings);
  document.getElementById("settings-close").addEventListener("click", closeSettings);
  settingsEl.addEventListener("click", function (event) { if (event.target === settingsEl) closeSettings(); });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !settingsEl.hidden) closeSettings();
  });

  var speedButtons = document.querySelectorAll("[data-speed]");
  function syncSpeed() {
    Array.prototype.forEach.call(speedButtons, function (button) {
      button.setAttribute("aria-pressed", Number(button.getAttribute("data-speed")) === speed ? "true" : "false");
    });
  }
  Array.prototype.forEach.call(speedButtons, function (button) {
    button.addEventListener("click", function () {
      speed = Number(button.getAttribute("data-speed"));
      Iamlio.writeSetting("iamlio-viteza", String(speed));
      syncSpeed();
      applyAudioSettings();
    });
  });

  autoInput.checked = autoTurn;
  autoInput.addEventListener("change", function () {
    autoTurn = autoInput.checked;
    Iamlio.writeSetting("iamlio-autoturn", autoTurn ? "1" : "0");
  });

  function applyBedtime() {
    document.body.classList.toggle("bedtime", bedtime);
    var endLio = book.querySelector(".end-lio");
    if (endLio) endLio.src = bedtime ? "assets/img/lio-somnoros.svg" : endLio.getAttribute("data-awake");
    bedtimeInput.checked = bedtime;
    applyAudioSettings();
  }
  bedtimeInput.addEventListener("change", function () {
    bedtime = bedtimeInput.checked;
    Iamlio.writeSetting("iamlio-culcare", bedtime ? "1" : "0");
    applyBedtime();
  });

  // Ecran complet unde browserul îl permite; pe iPhone se explică varianta „Adaugă pe ecranul principal”.
  var root = document.documentElement;
  var canFullscreen = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
  function isFullscreen() { return !!(document.fullscreenElement || document.webkitFullscreenElement); }
  function syncFullscreen() {
    fullscreenBtn.textContent = isFullscreen() ? "Ieși din ecranul complet" : "Ecran complet";
  }
  fullscreenBtn.hidden = !canFullscreen;
  document.getElementById("fullscreen-hint").hidden = canFullscreen || window.navigator.standalone === true;
  fullscreenBtn.addEventListener("click", function () {
    if (isFullscreen()) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    } else {
      var request = root.requestFullscreen || root.webkitRequestFullscreen;
      var result = request.call(root);
      if (result && result.catch) result.catch(function () {});
    }
    closeSettings();
  });
  document.addEventListener("fullscreenchange", syncFullscreen);
  document.addEventListener("webkitfullscreenchange", syncFullscreen);

  syncSpeed();
  applyBedtime();

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
    render();
    updateResume();
    applyBedtime();
    Iamlio.countRead(story.id).then(showReads);
    if (story.personalized) markPersonal(story);
    var bar = document.querySelector(".reader-bar");
    bar.insertBefore(Iamlio.favoriteButton(story.id, story.title), settingsBtn);
    fetch("stories/index.json", { cache: "no-cache" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) { if (data) showRecommendations(data.stories || [], story); })
      .catch(function () {});
  }

  // Povești personalizate: nu se indexează; până la aprobare se văd doar ca „Previzualizare”.
  function markPersonal(story) {
    var robots = document.createElement("meta");
    robots.name = "robots";
    robots.content = "noindex, nofollow";
    document.head.appendChild(robots);
    if (story.approved !== true) {
      var banner = el("p", "preview-banner",
        "Previzualizare: povestea pentru " + (story.personalized.for || "copil") + " așteaptă aprobarea. Nu trimite încă link-ul.");
      banner.setAttribute("role", "status");
      document.querySelector(".stage").prepend(banner);
    }
  }

  // ---------- Întrebările lui Lio (după poveste, fără punctaj) ----------

  var quizEl = null;
  var lioManifest = null;
  var quizAudio = new Audio();
  quizAudio.hidden = true;
  document.body.appendChild(quizAudio);

  fetch("assets/audio/manifest.json", { cache: "no-cache" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) { lioManifest = data; })
    .catch(function () {});

  function voiceUrl(folder, list, file) {
    var voice = Iamlio.getVoice();
    var digest = list && list[voice] && list[voice][file];
    return digest ? folder + voice + "/" + file + "?v=" + String(digest).slice(0, 10) : "";
  }

  // Redă un fișier al poveștii sau al lui Lio; dacă lipsește, citește textul cu vocea browserului.
  function sayQuiz(url, text, done) {
    quizAudio.pause();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    if (url) {
      quizAudio.src = url;
      quizAudio.defaultPlaybackRate = speed;
      quizAudio.playbackRate = speed;
      quizAudio.volume = bedtime ? BEDTIME_VOLUME : 1;
      quizAudio.onended = done || null;
      quizAudio.play().catch(function () { Iamlio.speakWithBrowser(text, Iamlio.getVoice(), { speed: speed, onend: done }); });
    } else {
      Iamlio.speakWithBrowser(text, Iamlio.getVoice(), { speed: speed, onend: done });
    }
  }

  function lioLine(group, texts) {
    var count = lioManifest && lioManifest[Iamlio.getVoice()]
      ? Object.keys(lioManifest[Iamlio.getVoice()]).filter(function (f) { return f.indexOf(group + "-") === 0; }).length : 0;
    var n = Math.floor(Math.random() * Math.max(count, 1)) + 1;
    var file = group + "-" + String(n).padStart(2, "0") + ".mp3";
    return { url: voiceUrl("assets/audio/", lioManifest, file), text: texts[(n - 1) % texts.length] };
  }

  function optionsSentence(options) {
    var texts = options.map(function (o) { return String(o.text).replace(/[.!?]+$/, ""); });
    return texts.length > 1 ? texts.slice(0, -1).join(", ") + " sau " + texts[texts.length - 1] + "?" : texts[0] + "?";
  }

  function openQuiz(questions) {
    setReading(false);
    if (!quizEl) {
      quizEl = el("div", "quiz");
      quizEl.setAttribute("role", "dialog");
      quizEl.setAttribute("aria-modal", "true");
      quizEl.setAttribute("aria-label", "Întrebările lui Lio");
      document.body.appendChild(quizEl);
      quizEl.addEventListener("click", function (event) { if (event.target === quizEl) closeQuiz(); });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && quizEl && !quizEl.hidden) closeQuiz();
      });
    }
    quizEl.hidden = false;
    showQuestion(questions, 0);
  }

  function closeQuiz() {
    quizAudio.pause();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    quizEl.hidden = true;
    var button = book.querySelector(".pill-quiz");
    if (button) button.focus();
  }

  function showQuestion(questions, number) {
    var question = questions[number];
    quizEl.textContent = "";
    var panel = el("div", "quiz-panel");
    var head = el("div", "quiz-head");
    head.appendChild(el("span", "quiz-progress", "Întrebarea " + (number + 1) + " din " + questions.length));
    var close = el("button", "icon-btn quiz-close");
    close.type = "button";
    close.setAttribute("aria-label", "Închide întrebările");
    close.textContent = "✕";
    close.addEventListener("click", closeQuiz);
    head.appendChild(close);
    panel.appendChild(head);

    var face = el("img", "quiz-lio");
    face.src = "assets/img/lio-cap.svg";
    face.alt = "";
    panel.appendChild(face);
    var text = el("p", "quiz-question", question.text);
    panel.appendChild(text);
    var feedback = el("p", "quiz-feedback");
    feedback.setAttribute("aria-live", "polite");

    var file = "intrebare-" + (number + 1) + ".mp3";
    function askAloud() { sayQuiz(voiceUrl(base + "audio/", manifest, file), question.text + " " + optionsSentence(question.options)); }

    var grid = el("div", "quiz-options");
    question.options.forEach(function (option, n) {
      var card = el("button", "quiz-option");
      card.type = "button";
      if (option.image) {
        var img = el("img");
        img.src = base + option.image;
        img.alt = "";
        card.appendChild(img);
      } else {
        card.appendChild(el("span", "quiz-emoji", option.emoji));
      }
      card.appendChild(el("span", "quiz-option-text", option.text));
      card.addEventListener("click", function () {
        if (panel.classList.contains("is-solved")) return;
        if (n === question.answer) {
          panel.classList.add("is-solved");
          card.classList.add("is-right");
          face.src = REDUCED_MOTION ? "assets/img/lio-bravo-static.svg" : "assets/img/lio-bravo.svg";
          var praise = lioLine("bravo", ["Bravo! Ai ascultat cu mare atenție!"]);
          feedback.textContent = praise.text + (question.explanation ? " " + question.explanation : "");
          sayQuiz(praise.url, praise.text, function () {
            if (question.explanation) {
              sayQuiz(voiceUrl(base + "audio/", manifest, "raspuns-" + (number + 1) + ".mp3"), question.explanation);
            }
          });
          next.hidden = false;
          next.focus();
        } else {
          card.classList.remove("is-wrong");
          void card.offsetWidth;
          card.classList.add("is-wrong");
          var retry = lioLine("incearca", ["Hmm, aproape! Mai încearcă o dată."]);
          feedback.textContent = retry.text;
          sayQuiz(retry.url, retry.text);
        }
      });
      grid.appendChild(card);
    });
    panel.appendChild(grid);
    panel.appendChild(feedback);

    var actions = el("div", "quiz-actions");
    var again = el("button", "pill pill-alt", "🔊 Ascultă din nou");
    again.type = "button";
    again.addEventListener("click", askAloud);
    var last = number === questions.length - 1;
    var next = el("button", "pill", last ? "Gata!" : "Următoarea întrebare");
    next.type = "button";
    next.hidden = true;
    next.addEventListener("click", function () {
      if (last) closeQuiz(); else showQuestion(questions, number + 1);
    });
    actions.appendChild(again);
    actions.appendChild(next);
    panel.appendChild(actions);
    quizEl.appendChild(panel);
    close.focus();
    askAloud();
  }

  // Pe pagina de final: două povești asemănătoare (necitite încă, dacă există), nu o listă nesfârșită.
  function showRecommendations(all, story) {
    var current = all.filter(function (s) { return s.id === story.id; })[0] ||
      { id: story.id, categories: story.categories, tags: story.tags, age: story.age };
    var picks = Iamlio.recommend(all, current, 2);
    var box = book.querySelector(".end-recs");
    if (!box || !picks.length) return;
    box.appendChild(el("p", "end-recs-title", "Mai ascultă o poveste:"));
    var list = el("div", "end-recs-list");
    picks.forEach(function (pick) {
      var link = el("a", "rec-card");
      link.href = "poveste.html?id=" + encodeURIComponent(pick.id);
      var img = el("img");
      img.src = pick.cover;
      img.alt = "";
      img.loading = "lazy";
      link.appendChild(img);
      var info = el("span", "rec-info");
      info.appendChild(el("span", "rec-title", pick.title));
      info.appendChild(el("span", "rec-meta", "~" + pick.minutes + " min"));
      link.appendChild(info);
      list.appendChild(link);
    });
    box.appendChild(list);
    box.hidden = false;
    box.parentNode.classList.add("has-recs");
  }

  function showReads(counts) {
    if (!counts) return;
    var label = Iamlio.readsLabel(counts[storyId] || 0);
    readsEl.textContent = label;
    readsEl.hidden = false;
    var cover = book.querySelector(".cover-reads");
    if (cover) cover.textContent = label;
  }

  Iamlio.bindVoiceSwitch(document.querySelector("#settings .voice-switch"), function () {
    if (reading && !busy) playCurrent();
  });
  Iamlio.inlineSvg(document.getElementById("play-lio"), "assets/img/lio-cap.svg");

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
