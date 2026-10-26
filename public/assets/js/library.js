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

  var filtersEl = document.getElementById("filters");
  var chipsEl = document.getElementById("category-chips");
  var favoritesBtn = document.getElementById("favorites-filter");
  var countEl = document.getElementById("results-count");
  var stories = [];
  var categories = {};
  var counts = null;

  // Filtrele stau în adresa paginii (ex. ?categorie=de-culcare&varsta=3-5), ca o listă filtrată să poată fi trimisă.
  var query = new URLSearchParams(location.search);
  var filters = {
    categorie: query.get("categorie") || "",
    varsta: query.get("varsta") || "",
    durata: query.get("durata") || "",
    favorite: query.get("favorite") === "1"
  };

  function saveFilters() {
    var params = new URLSearchParams();
    if (filters.categorie) params.set("categorie", filters.categorie);
    if (filters.varsta) params.set("varsta", filters.varsta);
    if (filters.durata) params.set("durata", filters.durata);
    if (filters.favorite) params.set("favorite", "1");
    var search = params.toString();
    try {
      history.replaceState(null, "", search ? "?" + search : location.pathname);
    } catch (e) { /* unele browsere refuză în previzualizări; filtrul merge oricum */ }
  }

  function ageFits(storyAge, wanted) {
    return !wanted || storyAge === wanted || storyAge === "3-7";
  }

  function durationFits(minutes, wanted) {
    if (wanted === "scurte") return minutes <= 4;
    if (wanted === "medii") return minutes >= 5 && minutes <= 7;
    if (wanted === "lungi") return minutes >= 8;
    return true;
  }

  function matches(story) {
    return (!filters.categorie || (story.categories || []).indexOf(filters.categorie) !== -1) &&
      ageFits(story.age, filters.varsta) &&
      durationFits(story.minutes, filters.durata) &&
      (!filters.favorite || Iamlio.isFavorite(story.id));
  }

  function card(story) {
    var item = el("article", "story-card");
    var link = el("a", "story-link");
    link.href = "poveste.html?id=" + encodeURIComponent(story.id);

    var cover = el("div", "story-cover");
    var img = el("img");
    img.src = story.cover;
    img.alt = "";
    img.loading = "lazy";
    cover.appendChild(img);
    var first = categories[(story.categories || [])[0]];
    if (first) cover.appendChild(el("span", "story-tag", first.emoji + " " + first.label));
    var page = Iamlio.savedPage(story.id);
    if (page && page < story.pages + 1) cover.appendChild(el("span", "story-resume", "Continuă · pagina " + page));
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
    item.appendChild(link);
    item.appendChild(Iamlio.favoriteButton(story.id, story.title, function () {
      if (filters.favorite) showStories();
    }));
    return item;
  }

  function emptyState() {
    var box = el("div", "empty-state");
    if (filters.favorite && !stories.some(function (s) { return Iamlio.isFavorite(s.id); })) {
      box.appendChild(el("p", null, "Încă nu ai povești favorite. Apasă pe ♡ la o poveste ca s-o găsești ușor aici."));
    } else {
      box.appendChild(el("p", null, "Nicio poveste nu se potrivește filtrelor alese."));
    }
    var reset = el("button", "pill", "Arată toate poveștile");
    reset.type = "button";
    reset.addEventListener("click", function () {
      filters = { categorie: "", varsta: "", durata: "", favorite: false };
      syncFilters();
      showStories();
    });
    box.appendChild(reset);
    return box;
  }

  function showStories() {
    saveFilters();
    var shown = stories.filter(matches);
    grid.textContent = "";
    if (!stories.length) {
      grid.appendChild(el("p", "muted", "Încă nu avem povești. Revino curând!"));
      return;
    }
    if (!shown.length) grid.appendChild(emptyState());
    shown.forEach(function (story) { grid.appendChild(card(story)); });
    var filtered = shown.length !== stories.length;
    countEl.textContent = filtered ? shown.length + " din " + stories.length + " povești" : "";
  }

  function syncFilters() {
    Array.prototype.forEach.call(chipsEl.children, function (chip) {
      chip.setAttribute("aria-pressed", chip.getAttribute("data-value") === filters.categorie ? "true" : "false");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".segmented"), function (group) {
      var key = group.getAttribute("data-filter");
      Array.prototype.forEach.call(group.children, function (button) {
        button.setAttribute("aria-pressed", button.getAttribute("data-value") === filters[key] ? "true" : "false");
      });
    });
    favoritesBtn.setAttribute("aria-pressed", filters.favorite ? "true" : "false");
  }

  function buildFilters(list) {
    var used = {};
    stories.forEach(function (s) { (s.categories || []).forEach(function (c) { used[c] = (used[c] || 0) + 1; }); });
    var all = el("button", "chip", "Toate");
    all.type = "button";
    all.setAttribute("data-value", "");
    chipsEl.appendChild(all);
    list.forEach(function (category) {
      if (!used[category.id]) return; // doar categoriile care au povești
      var chip = el("button", "chip", category.emoji + " " + category.label);
      chip.type = "button";
      chip.setAttribute("data-value", category.id);
      chipsEl.appendChild(chip);
    });
    Array.prototype.forEach.call(chipsEl.children, function (chip) {
      chip.addEventListener("click", function () {
        filters.categorie = chip.getAttribute("data-value");
        syncFilters();
        showStories();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll(".segmented"), function (group) {
      var key = group.getAttribute("data-filter");
      Array.prototype.forEach.call(group.children, function (button) {
        button.addEventListener("click", function () {
          filters[key] = button.getAttribute("data-value");
          syncFilters();
          showStories();
        });
      });
    });
    favoritesBtn.addEventListener("click", function () {
      filters.favorite = !filters.favorite;
      syncFilters();
      showStories();
    });
    if (filters.categorie && !used[filters.categorie]) filters.categorie = "";
    syncFilters();
    filtersEl.hidden = false;
  }

  var storiesRequest = fetch("stories/index.json", { cache: "no-cache" }).then(function (res) {
    if (!res.ok) throw new Error(res.status);
    return res.json();
  });

  Promise.all([storiesRequest, Iamlio.fetchCounts()])
    .then(function (results) {
      stories = results[0].stories || [];
      counts = results[1];
      (results[0].categories || []).forEach(function (c) { categories[c.id] = c; });
      if (stories.length) buildFilters(results[0].categories || []);
      showStories();
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
