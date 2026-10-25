(function () {
  "use strict";

  var grid = document.getElementById("stories");
  var heroLio = document.getElementById("hero-lio");
  var lioSays = document.getElementById("lio-says");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  // ---------- biblioteca ----------

  function card(story, counts) {
    var link = el("a", "story-card");
    link.href = "poveste.html?id=" + encodeURIComponent(story.id);

    var cover = el("div", "story-cover");
    var img = el("img");
    img.src = story.cover;
    img.alt = "";
    img.loading = "lazy";
    cover.appendChild(img);
    cover.appendChild(el("span", "story-play", "▶"));
    link.appendChild(cover);

    var body = el("div", "story-body");
    body.appendChild(el("h3", null, story.title));
    if (counts) {
      body.appendChild(el("p", "story-reads", Iamlio.readsLabel(counts[story.id] || 0)));
    }
    body.appendChild(el("p", "story-summary", story.summary));
    var meta = el("p", "story-meta");
    meta.appendChild(el("span", null, story.pages + " pagini"));
    meta.appendChild(el("span", null, "~" + story.minutes + " min"));
    meta.appendChild(el("span", null, story.age + " ani"));
    body.appendChild(meta);
    link.appendChild(body);
    return link;
  }

  var storiesRequest = fetch("stories/index.json", { cache: "no-cache" }).then(function (res) {
    if (!res.ok) throw new Error(res.status);
    return res.json();
  });

  Promise.all([storiesRequest, Iamlio.fetchCounts()])
    .then(function (results) {
      var data = results[0];
      var counts = results[1];
      grid.textContent = "";
      if (!data.stories.length) {
        grid.appendChild(el("p", "muted", "Încă nu avem povești. Revino curând!"));
        return;
      }
      data.stories.forEach(function (story) {
        grid.appendChild(card(story, counts));
      });
    })
    .catch(function () {
      grid.textContent = "";
      grid.appendChild(el("p", "muted", "Nu am putut încărca poveștile. Încearcă din nou."));
    });

  // ---------- Lio vorbește când îl atingi ----------

  var lines = [];
  var manifest = null;
  var lastLine = -1;
  var audio = new Audio();

  Iamlio.inlineSvg(heroLio, "assets/img/lio.svg");
  Iamlio.bindVoiceSwitch(document.querySelector(".voice-picker"), function () { sayHello(); });

  fetch("assets/lio-replici.json").then(function (r) { return r.json(); }).then(function (d) { lines = d.replici; }).catch(function () {});
  fetch("assets/audio/manifest.json", { cache: "no-cache" }).then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { manifest = d; }).catch(function () {});

  function talking(on) {
    heroLio.classList.toggle("is-talking", on);
  }

  audio.addEventListener("playing", function () { talking(true); });
  audio.addEventListener("pause", function () { talking(false); });
  audio.addEventListener("ended", function () { talking(false); });

  function sayHello() {
    if (!lines.length) return;
    var n;
    do { n = Math.floor(Math.random() * lines.length); } while (lines.length > 1 && n === lastLine);
    lastLine = n;
    var text = lines[n];
    lioSays.textContent = text;

    heroLio.classList.remove("is-jumping");
    void heroLio.offsetWidth;
    heroLio.classList.add("is-jumping");

    audio.pause();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    var voice = Iamlio.getVoice();
    var file = "replica-" + String(n + 1).padStart(2, "0") + ".mp3";
    if (manifest && manifest[voice] && manifest[voice][file]) {
      audio.src = "assets/audio/" + voice + "/" + file + "?v=" + String(manifest[voice][file]).slice(0, 10);
      audio.play().catch(function () { talking(false); });
    } else {
      Iamlio.speakWithBrowser(text, voice, {
        onstart: function () { talking(true); },
        onend: function () { talking(false); }
      });
    }
  }

  heroLio.addEventListener("click", sayHello);
})();
