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
      .then(function (res) { return res.text(); })
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
    return fetch("api/citiri.php", { cache: "no-store" }).then(parseCounts).catch(function () { return null; });
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

  function markFinished(id) {
    var list = readList("iamlio-citite");
    if (list.indexOf(id) === -1) {
      list.push(id);
      writeSetting("iamlio-citite", JSON.stringify(list));
    }
  }

  function isFinished(id) { return readList("iamlio-citite").indexOf(id) !== -1; }

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

  // Cele mai potrivite povești după una terminată: categorii comune, etichete comune, vârstă potrivită,
  // iar cele necitite încă au întâietate. Întoarce cel mult `count` povești, fără cea curentă.
  function recommend(stories, current, count) {
    function ageFits(a, b) { return a === b || a === "3-7" || b === "3-7"; }
    return stories
      .filter(function (s) { return s.id !== current.id; })
      .map(function (s, order) {
        var shared = (s.categories || []).filter(function (c) { return (current.categories || []).indexOf(c) !== -1; });
        var tags = (s.tags || []).filter(function (t) { return (current.tags || []).indexOf(t) !== -1; });
        var score = shared.length * 3 + tags.length + (ageFits(s.age, current.age) ? 1 : 0) + (isFinished(s.id) ? 0 : 2);
        return { story: s, score: score, order: order };
      })
      .sort(function (a, b) { return b.score - a.score || a.order - b.order; })
      .slice(0, count)
      .map(function (x) { return x.story; });
  }

  return {
    readSetting: readSetting,
    writeSetting: writeSetting,
    getVoice: getVoice,
    bindVoiceSwitch: bindVoiceSwitch,
    inlineSvg: inlineSvg,
    readsLabel: readsLabel,
    fetchCounts: fetchCounts,
    countRead: countRead,
    speakWithBrowser: speakWithBrowser,
    isFavorite: isFavorite,
    toggleFavorite: toggleFavorite,
    favoriteButton: favoriteButton,
    markFinished: markFinished,
    isFinished: isFinished,
    savedPage: savedPage,
    recommend: recommend
  };
})();
