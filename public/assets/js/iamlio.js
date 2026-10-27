/* Funcții comune pentru toate paginile Iamlio. */
window.Iamlio = (function () {
  "use strict";

  var VOICE_KEY = "iamlio-voce";
  var VOICES = ["feminin", "masculin"];

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

  function getVoice() {
    var voice = readSetting(VOICE_KEY, "feminin");
    return VOICES.indexOf(voice) === -1 ? "feminin" : voice;
  }

  function setVoice(voice) {
    writeSetting(VOICE_KEY, voice);
  }

  // Leagă butoanele [data-voice] dintr-un container de vocea salvată.
  function bindVoiceSwitch(container, onChange) {
    var buttons = container.querySelectorAll("[data-voice]");
    function sync() {
      var current = getVoice();
      Array.prototype.forEach.call(buttons, function (btn) {
        btn.setAttribute("aria-pressed", btn.getAttribute("data-voice") === current ? "true" : "false");
      });
    }
    Array.prototype.forEach.call(buttons, function (btn) {
      btn.addEventListener("click", function () {
        var voice = btn.getAttribute("data-voice");
        if (voice === getVoice()) return;
        setVoice(voice);
        sync();
        if (onChange) onChange(voice);
      });
    });
    sync();
  }

  // Inserează un SVG ca element (nu <img>), ca să poată fi animat din CSS.
  function inlineSvg(container, src) {
    return fetch(src)
      .then(function (res) {
        if (!res.ok) throw new Error(res.status); // o pagină de eroare nu ajunge în locul lui Lio
        return res.text();
      })
      .then(function (text) {
        container.innerHTML = text;
        var svg = container.querySelector("svg");
        // „mișcare redusă”: Lio nu mai clipește și nu mai face cu mâna
        if (svg && svg.pauseAnimations && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
          svg.pauseAnimations();
        }
        return svg;
      })
      .catch(function () {
        var img = document.createElement("img");
        img.src = src;
        img.alt = "";
        container.textContent = "";
        container.appendChild(img);
        return null;
      });
  }

  // „citită o dată”, „citită de 5 ori”, „citită de 20 de ori”, „citită de 101 ori”.
  function readsLabel(count) {
    if (!count) return "Fii primul care o citește!";
    if (count === 1) return "Citită o dată";
    var lastTwo = count % 100;
    var withDe = count >= 20 && (lastTwo === 0 || lastTwo >= 20);
    return "Citită de " + count.toLocaleString("ro-RO") + (withDe ? " de ori" : " ori");
  }

  function parseCounts(res) {
    if (!res.ok) throw new Error(res.status);
    return res.json().then(function (data) {
      if (!data || typeof data.citiri !== "object") throw new Error("format");
      return data.citiri;
    });
  }

  // Întoarce {id: număr} sau null dacă hostul nu are contorul (ex. previzualizare locală).
  function fetchCounts() {
    return fetchWithTimeout("api/citiri.php", { cache: "no-store" }, 6000).then(parseCounts).catch(function () { return null; });
  }

  // fetch care renunță după `ms` milisecunde, ca o cerere blocată să nu țină pagina în „Se încarcă…”.
  function fetchWithTimeout(url, options, ms) {
    var controller = window.AbortController ? new AbortController() : null;
    var timer = null;
    var request = fetch(url, controller ? Object.assign({ signal: controller.signal }, options) : options);
    var timeout = new Promise(function (resolve, reject) {
      timer = setTimeout(function () {
        if (controller) controller.abort();
        reject(new Error("timeout"));
      }, ms);
    });
    return Promise.race([request, timeout]).then(function (res) { clearTimeout(timer); return res; },
      function (error) { clearTimeout(timer); throw error; });
  }

  // Numără o citire o singură dată pe sesiune pentru fiecare poveste.
  function countRead(storyId) {
    var key = "iamlio-citit-" + storyId;
    var counted = false;
    try { counted = sessionStorage.getItem(key) === "1"; } catch (e) { /* fără sesiune: numărăm */ }
    if (counted) return fetchCounts();
    return fetch("api/citiri.php?id=" + encodeURIComponent(storyId), { method: "POST", cache: "no-store" })
      .then(parseCounts)
      .then(function (counts) {
        try { sessionStorage.setItem(key, "1"); } catch (e) { /* ignorăm */ }
        return counts;
      })
      .catch(function () { return null; });
  }

  // Alege o voce românească din browser, potrivită cu genul cerut (rezervă când lipsește mp3-ul).
  function browserVoice(gender) {
    if (!("speechSynthesis" in window)) return null;
    var voices = speechSynthesis.getVoices().filter(function (v) { return /^ro/i.test(v.lang); });
    var pattern = gender === "masculin" ? /emil|andrei|male|bărbat/i : /alina|ioana|female|femeie/i;
    return voices.filter(function (v) { return pattern.test(v.name); })[0] || voices[0] || null;
  }

  if ("speechSynthesis" in window) {
    speechSynthesis.getVoices();
    speechSynthesis.addEventListener("voiceschanged", function () { speechSynthesis.getVoices(); });
  }

  function speakWithBrowser(text, gender, handlers) {
    if (!("speechSynthesis" in window)) return false;
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ro-RO";
    var voice = browserVoice(gender);
    if (voice) utterance.voice = voice;
    utterance.rate = 0.9 * (handlers.speed || 1);
    utterance.pitch = gender === "masculin" ? 0.9 : 1.1;
    utterance.onstart = handlers.onstart || null;
    utterance.onend = handlers.onend || null;
    utterance.onerror = handlers.onend || null;
    speechSynthesis.speak(utterance);
    return true;
  }

  // ---------- favorite, povești terminate, reluare (doar pe dispozitiv) ----------

  function readList(key) {
    try {
      var list = JSON.parse(readSetting(key, "[]"));
      return Array.isArray(list) ? list.filter(function (x) { return typeof x === "string"; }) : [];
    } catch (e) {
      return [];
    }
  }

  function isFavorite(id) { return readList("iamlio-favorite").indexOf(id) !== -1; }

  function toggleFavorite(id) {
    var list = readList("iamlio-favorite");
    var at = list.indexOf(id);
    if (at === -1) list.unshift(id); else list.splice(at, 1);
    writeSetting("iamlio-favorite", JSON.stringify(list));
    return at === -1;
  }


  function savedPage(id) {
    var value = Number(readSetting("iamlio-pagina-" + id, "0"));
    return value > 0 ? value : 0;
  }

  // Buton de favorit (inimioară) care rămâne sincronizat cu lista salvată.
  function favoriteButton(id, title, onChange) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "fav-btn";
    function sync() {
      var on = isFavorite(id);
      button.setAttribute("aria-pressed", on ? "true" : "false");
      button.setAttribute("aria-label", (on ? "Scoate de la favorite: " : "Adaugă la favorite: ") + title);
      button.textContent = on ? "♥" : "♡";
    }
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleFavorite(id);
      sync();
      button.classList.remove("pop");
      void button.offsetWidth;
      button.classList.add("pop");
      if (onChange) onChange();
    });
    sync();
    return button;
  }

  // ---------- statistici pentru administrator (doar totaluri, fără cookie-uri; vezi api/vizita.php) ----------

  function reportVisit() {
    var body = document.body;
    if (!body || body.classList.contains("admin") || !window.fetch) return;
    var page = body.classList.contains("home") ? "acasa" : body.classList.contains("reader") ? "poveste" : "altele";
    // răspunsul se citește până la capăt, ca cererea să se încheie (altfel browserul o poate ține deschisă)
    fetch("api/vizita.php?pagina=" + page, { method: "POST" }).then(function (r) { return r.text(); }).catch(function () {});
  }

  // Erorile din pagină ajung în panoul de administrare (api/erori.php): mesajul, fișierul și pagina,
  // fără date personale; cel mult 10 rapoarte pe pagină, fiecare eroare o singură dată.
  var reported = {};
  var reportsLeft = 10;

  function reportError(type, message, source, line) {
    var key = type + "|" + message + "|" + source + "|" + line;
    if (reported[key] || reportsLeft <= 0 || !window.fetch) return;
    reported[key] = true;
    reportsLeft--;
    var report = { tip: type, mesaj: String(message).slice(0, 300), sursa: String(source || "").slice(0, 200),
      linie: line || 0, pagina: location.pathname + location.search };
    fetch("api/erori.php", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report) }).then(function (r) { return r.text(); }).catch(function () {});
  }

  window.addEventListener("error", function (event) {
    var target = event.target;
    if (target && target !== window && (target.tagName === "IMG" || target.tagName === "SOURCE" || target.tagName === "SCRIPT" ||
        target.tagName === "LINK")) {
      reportError(target.tagName === "IMG" ? "imagine" : "alta", "nu s-a încărcat", target.src || target.href || "", 0);
      return;
    }
    // „Script error.” vine din scripturi de pe alte site-uri (extensii ale browserului): nu ne spune nimic util
    if (!event.message || event.message === "Script error.") return;
    reportError("js", event.message, event.filename, event.lineno);
  }, true);

  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason;
    reportError("promisiune", reason && reason.message ? reason.message : String(reason), "", 0);
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", reportVisit);
  else reportVisit();

  return {
    reportError: reportError,
    readSetting: readSetting,
    writeSetting: writeSetting,
    getVoice: getVoice,
    bindVoiceSwitch: bindVoiceSwitch,
    inlineSvg: inlineSvg,
    readsLabel: readsLabel,
    fetchCounts: fetchCounts,
    fetchWithTimeout: fetchWithTimeout,
    countRead: countRead,
    speakWithBrowser: speakWithBrowser,
    isFavorite: isFavorite,
    toggleFavorite: toggleFavorite,
    favoriteButton: favoriteButton,
    savedPage: savedPage
  };
})();
