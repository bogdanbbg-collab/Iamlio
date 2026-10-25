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

  return {
    readSetting: readSetting,
    writeSetting: writeSetting,
    getVoice: getVoice,
    bindVoiceSwitch: bindVoiceSwitch,
    inlineSvg: inlineSvg,
    readsLabel: readsLabel,
    fetchCounts: fetchCounts,
    countRead: countRead,
    speakWithBrowser: speakWithBrowser
  };
})();
