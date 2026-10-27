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
  var toggleBtn = document.getElementById("filters-toggle");
  var badgeEl = document.getElementById("filters-badge");
  var chipsEl = document.getElementById("category-chips");
  var favoritesBtn = document.getElementById("favorites-filter");
  var countEl = document.getElementById("results-count");
  var stories = [];
  var categories = {};
  var counts = null;

  // Filtrele stau în adresa paginii (ex. ?categorie=de-culcare&durata=scurte), ca o listă filtrată să poată fi trimisă.
  var query = new URLSearchParams(location.search);
  var filters = {
    categorie: query.get("categorie") || "",
    durata: query.get("durata") || "",
    favorite: query.get("favorite") === "1"
  };

  function saveFilters() {
    var params = new URLSearchParams();
    if (filters.categorie) params.set("categorie", filters.categorie);
    if (filters.durata) params.set("durata", filters.durata);
    if (filters.favorite) params.set("favorite", "1");
    var search = params.toString();
    try {
      history.replaceState(null, "", search ? "?" + search : location.pathname);
    } catch (e) { /* unele browsere refuză în previzualizări; filtrul merge oricum */ }
  }

  function durationFits(minutes, wanted) {
    if (wanted === "scurte") return minutes <= 4;
    if (wanted === "medii") return minutes >= 5 && minutes <= 7;
    if (wanted === "lungi") return minutes >= 8;
    return true;
  }

  function matches(story) {
    return (!filters.categorie || (story.categories || []).indexOf(filters.categorie) !== -1) &&
      durationFits(story.minutes, filters.durata) &&
      (!filters.favorite || Iamlio.isFavorite(story.id));
  }

  function card(story) {
    var item = el("article", "story-card");
    item.setAttribute("data-id", story.id);
    var link = el("a", "story-link");
    link.href = "poveste.html?id=" + encodeURIComponent(story.id);

    var cover = el("div", "story-cover");
    var img = el("img");
    img.src = story.cover;
    img.alt = "";
    // primele coperți se văd imediat: se încarcă primele, cu prioritate; restul doar când ajungi la ele
    if (grid.children.length < 2) {
      img.loading = "eager";
      img.setAttribute("fetchpriority", "high");
    } else {
      img.loading = "lazy";
    }
    img.decoding = "async";
    cover.appendChild(img);
    var tags = el("div", "story-tags");
    if (story.id === featuredId) tags.appendChild(el("span", "story-tag story-featured", "⭐ Povestea săptămânii"));
    if (isNew(story)) tags.appendChild(el("span", "story-tag story-new", "Nou"));
    var first = categories[(story.categories || [])[0]];
    if (first && story.id !== featuredId) tags.appendChild(el("span", "story-tag", first.emoji + " " + first.label));
    cover.appendChild(tags);
    var page = Iamlio.savedPage(story.id);
    if (page && page < story.pages + 1) cover.appendChild(el("span", "story-resume", "Continuă · pagina " + page));
    cover.appendChild(el("span", "story-play", "▶"));
    link.appendChild(cover);

    // Pe card: copertă, titlu și durată. Restul (contorul, rezumatul) e mic și discret, pentru părinți.
    var body = el("div", "story-body");
    var heading = el("div", "story-heading");
    heading.appendChild(el("h3", null, story.title));
    var minutes = el("span", "story-minutes", "~" + story.minutes + " min");
    minutes.setAttribute("aria-label", "cam " + story.minutes + " minute");
    heading.appendChild(minutes);
    body.appendChild(heading);
    var details = el("p", "story-details");
    if (counts) details.appendChild(el("span", "story-reads", Iamlio.readsLabel(counts[story.id] || 0)));
    body.appendChild(details);
    body.appendChild(el("p", "story-summary", story.summary));
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
      filters = { categorie: "", durata: "", favorite: false };
      syncFilters();
      showStories();
    });
    box.appendChild(reset);
    return box;
  }

  // ---------- „Nou” și „Povestea săptămânii” (după data la care povestea a apărut pe site) ----------

  var NEW_DAYS = 14;
  var MIN_FOR_FEATURED = 3;
  var DAY = 86400000;
  var featuredId = "";

  function daysSincePublished(story) {
    var parts = String(story.published || "").split("-").map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return Infinity;
    var now = new Date();
    return Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(parts[0], parts[1] - 1, parts[2])) / DAY);
  }

  function isNew(story) {
    var days = daysSincePublished(story);
    return days >= 0 && days < NEW_DAYS;
  }

  // Povestea publicată în ultimele 7 zile; dacă nu e niciuna, câte o poveste din bibliotecă pe rând,
  // aceeași pentru toată lumea în aceeași săptămână (de luni până duminică).
  function weeklyStory(list) {
    if (list.length < MIN_FOR_FEATURED) return "";
    var recent = list.filter(function (s) { var d = daysSincePublished(s); return d >= 0 && d < 7; })
      .sort(function (a, b) { return daysSincePublished(a) - daysSincePublished(b); });
    if (recent.length) return recent[0].id;
    var now = new Date();
    var week = Math.floor((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(2024, 0, 1)) / (7 * DAY));
    var byId = list.map(function (s) { return s.id; }).sort();
    return byId[week % byId.length];
  }

  function showStories() {
    saveFilters();
    var shown = stories.filter(matches).sort(function (a, b) {
      return (b.id === featuredId) - (a.id === featuredId); // povestea săptămânii prima
    });
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
    var active = activeFilters();
    badgeEl.textContent = active ? String(active) : "";
    badgeEl.hidden = !active;
    toggleBtn.setAttribute("aria-label", active ? "Filtre (" + active + " alese)" : "Filtre");
  }

  function activeFilters() {
    return [filters.categorie, filters.durata, filters.favorite].filter(Boolean).length;
  }

  // Filtrele stau strânse sub butonul „Filtre”; se deschid singure doar dacă adresa are deja filtre alese.
  function showFilterPanel(open) {
    filtersEl.hidden = !open;
    toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
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
    toggleBtn.addEventListener("click", function () { showFilterPanel(filtersEl.hidden); });
    toggleBtn.hidden = false;
    showFilterPanel(activeFilters() > 0);
  }

  // Lista poveștilor; dacă nu vine în câteva secunde (rețea mobilă care se trezește greu), se cere din nou o dată.
  function loadIndex(retry) {
    return Iamlio.fetchWithTimeout("stories/index.json", { cache: "no-cache" }, 8000).then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    }).catch(function (error) {
      if (retry) return loadIndex(false);
      throw error;
    });
  }

  // Poveștile apar imediat ce vine lista; contorul „citită de X ori” se adaugă după, când (și dacă) răspunde.
  loadIndex(true)
    .then(function (library) {
      stories = library.stories || [];
      featuredId = weeklyStory(stories);
      (library.categories || []).forEach(function (c) { categories[c.id] = c; });
      if (stories.length > 1) buildFilters(library.categories || []); // cu o singură poveste n-ai ce filtra
      if (stories.length >= MIN_FOR_PICK) picksBtn.hidden = false;
      showStories();
      Iamlio.fetchCounts().then(function (result) {
        if (!result) return;
        counts = result;
        // doar numerele se adaugă în carduri, fără să refacem lista (focusul și derularea rămân pe loc)
        Array.prototype.forEach.call(grid.querySelectorAll(".story-card[data-id]"), function (card) {
          var details = card.querySelector(".story-details");
          if (!details || details.querySelector(".story-reads")) return;
          details.appendChild(el("span", "story-reads", Iamlio.readsLabel(counts[card.getAttribute("data-id")] || 0)));
        });
      });
    })
    .catch(function () {
      grid.textContent = "";
      grid.appendChild(el("p", "muted", "Nu am putut încărca poveștile. Încearcă din nou."));
      var again = el("button", "pill", "Încearcă din nou");
      again.type = "button";
      again.addEventListener("click", function () { location.reload(); });
      grid.appendChild(again);
    });

  // ---------- „Lio, alege tu!” ----------

  // Lio alege o poveste la întâmplare (alta decât data trecută) și o deschide gata de citit.
  var MIN_FOR_PICK = 3;
  var LAST_PICK = "iamlio-ales";
  var picksBtn = document.getElementById("lio-picks");
  picksBtn.addEventListener("click", function () {
    var last = Iamlio.readSetting(LAST_PICK, "");
    var choices = stories.filter(function (s) { return s.id !== last; });
    var pick = choices[Math.floor(Math.random() * choices.length)];
    if (!pick) return;
    Iamlio.writeSetting(LAST_PICK, pick.id);
    location.href = "poveste.html?id=" + encodeURIComponent(pick.id) + "&citeste=1";
  });

  // ---------- Lio vorbește când îl atingi ----------

  var lines = [];
  var manifest = null;
  var lastLine = -1;
  var audio = new Audio();

  Iamlio.inlineSvg(heroLio, "assets/img/lio.svg");
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
