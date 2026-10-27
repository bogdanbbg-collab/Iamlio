/* Panoul de administrare: autentificare, statistici, povești de rezolvat, erori și starea site-ului. */
(function () {
  "use strict";

  var API = "api/admin.php";
  var DAY = 86400000;
  var loginForm = document.getElementById("login");
  var panel = document.getElementById("panel");
  var logoutBtn = document.getElementById("logout");
  var clearBtn = document.getElementById("clear-errors");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function number(value) {
    return Number(value || 0).toLocaleString("ro-RO");
  }

  function dateLabel(iso, withYear) {
    var parts = String(iso).slice(0, 10).split("-").map(Number);
    var months = ["ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct", "noi", "dec"];
    return parts[2] + " " + months[parts[1] - 1] + (withYear ? " " + parts[0] : "");
  }

  function timeLabel(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return "—";
    return d.toLocaleString("ro-RO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  // Ultimele n zile, până azi inclusiv (azi = ziua serverului, în România), ca „AAAA-LL-ZZ”.
  function lastDays(today, n) {
    var parts = today.split("-").map(Number);
    var end = Date.UTC(parts[0], parts[1] - 1, parts[2]);
    var days = [];
    for (var i = n - 1; i >= 0; i--) days.push(new Date(end - i * DAY).toISOString().slice(0, 10));
    return days;
  }

  // 1 tip, 2 tipuri, 20 de tipuri (forma românească după număr)
  function plural(n, one, few, many) {
    var rest = n % 100;
    return number(n) + " " + (n === 1 ? one : n === 0 || (rest > 0 && rest < 20) ? few : "de " + many);
  }

  function sum(list) {
    return list.reduce(function (a, b) { return a + b; }, 0);
  }

  // ---------- autentificare ----------

  function showLogin(message) {
    panel.hidden = true;
    logoutBtn.hidden = true;
    loginForm.hidden = false;
    document.getElementById("login-message").textContent = message || "";
    document.getElementById("password").focus();
  }

  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    var data = new FormData(loginForm);
    data.append("actiune", "intrare");
    var button = loginForm.querySelector("button");
    button.disabled = true;
    fetch(API, { method: "POST", body: data, credentials: "same-origin" })
      .then(function (res) {
        button.disabled = false;
        if (res.ok) {
          loginForm.reset();
          load();
        } else {
          showLogin(res.status === 429 ? "Prea multe încercări. Mai încearcă peste o oră." : "Parola nu este corectă.");
        }
      })
      .catch(function () {
        button.disabled = false;
        showLogin("Serverul nu răspunde. Mai încearcă.");
      });
  });

  function post(action) {
    var data = new FormData();
    data.append("actiune", action);
    return fetch(API, { method: "POST", body: data, credentials: "same-origin" });
  }

  logoutBtn.addEventListener("click", function () {
    // chiar dacă serverul nu răspunde, ecranul revine la intrare (cookie-ul expiră oricum în 12 ore)
    post("iesire").catch(function () {}).then(function () { showLogin("Te-ai deconectat."); });
  });

  clearBtn.addEventListener("click", function () {
    if (!window.confirm("Ștergi lista de erori? Fă asta după ce le-ai rezolvat.")) return;
    post("sterge-erori")
      .then(function (res) {
        if (res.status === 401) showLogin("Sesiunea a expirat. Intră din nou.");
        else load();
      })
      .catch(function () { window.alert("Nu am putut șterge erorile. Încearcă din nou."); });
  });

  document.getElementById("refresh").addEventListener("click", load);

  function load() {
    fetch(API, { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        if (res.status === 401) return showLogin();
        if (!res.ok) throw new Error(res.status);
        return res.json().then(render);
      })
      .catch(function () { showLogin("Datele nu au putut fi încărcate. Reîncearcă."); });
  }

  // ---------- panoul ----------

  function render(data) {
    loginForm.hidden = true;
    panel.hidden = false;
    logoutBtn.hidden = false;
    document.getElementById("updated").textContent = "Actualizat la " + timeLabel(data.acum);

    var site = data.site || {};
    var stories = site.stories || [];
    var titles = {};
    stories.forEach(function (s) { titles[s.id] = s.title; });
    var days30 = lastDays(data.azi, 30);
    var visits = data.vizite || {};
    var readsByDay = (data.citiri && data.citiri.zile) || {};
    var totals = (data.citiri && data.citiri.totaluri) || {};

    var visitors = days30.map(function (d) { return visits[d] ? Number(visits[d].vizitatori || 0) : 0; });
    var reads = days30.map(function (d) {
      var day = readsByDay[d] || {};
      return sum(Object.keys(day).map(function (id) { return Number(day[id]); }));
    });
    var views = days30.map(function (d) {
      var shown = (visits[d] && visits[d].afisari) || {};
      return sum(Object.keys(shown).map(function (k) { return Number(shown[k]); }));
    });
    var since = Date.now() - DAY;
    var recentErrors = (data.erori || []).filter(function (g) { return new Date(g.ultima).getTime() >= since; });

    renderTiles([
      ["Vizitatori azi", visitors[29], "ieri: " + number(visitors[28])],
      ["Vizitatori · 7 zile", sum(visitors.slice(-7)), "30 de zile: " + number(sum(visitors))],
      ["Pagini afișate · 7 zile", sum(views.slice(-7)), "30 de zile: " + number(sum(views))],
      ["Povești deschise · 7 zile", sum(reads.slice(-7)), "azi: " + number(reads[29])],
      ["Povești deschise · total", sum(Object.keys(totals).map(function (k) { return Number(totals[k]); })), "de la început"],
      ["Povești publicate", stories.length, plural((site.personal || []).length, "personalizată", "personalizate", "personalizate")],
      ["Erori · 24 de ore", sum(recentErrors.map(function (g) { return Number(g.numar); })),
        plural((data.erori || []).length, "tip", "tipuri", "tipuri") + " în 14 zile", recentErrors.length ? "warn" : "ok"]
    ]);
    renderBars(document.getElementById("chart-visits"), days30, visitors, "vizitatori");
    renderBars(document.getElementById("chart-reads"), days30, reads, "povești deschise");
    renderTop(stories, totals, readsByDay, days30);
    renderLibrary(site, stories);
    renderTodo(site);
    renderErrors(data.erori || []);
    renderSystem(data, site);
  }

  function renderTiles(tiles) {
    var box = document.getElementById("tiles");
    box.textContent = "";
    tiles.forEach(function (tile) {
      var card = el("div", "admin-tile" + (tile[3] ? " is-" + tile[3] : ""));
      card.appendChild(el("p", "admin-tile-label", tile[0]));
      card.appendChild(el("p", "admin-tile-value", number(tile[1])));
      card.appendChild(el("p", "admin-tile-note", tile[2]));
      box.appendChild(card);
    });
  }

  // Grafic cu bare (o singură serie): fiecare bară are eticheta ei pentru hover/focus și pentru cititoarele de ecran;
  // sub grafic, același lucru ca tabel.
  function renderBars(box, days, values, unit) {
    box.textContent = "";
    var max = Math.max.apply(null, values.concat([1]));
    var chart = el("div", "admin-bars");
    chart.setAttribute("role", "list");
    days.forEach(function (day, i) {
      var label = dateLabel(day) + ": " + number(values[i]) + " " + unit;
      var bar = el("div", "admin-bar");
      bar.setAttribute("role", "listitem");
      bar.setAttribute("tabindex", "0");
      bar.setAttribute("aria-label", label);
      bar.setAttribute("data-tip", label);
      var fill = el("span", "admin-bar-fill");
      fill.style.height = (values[i] ? Math.max(3, values[i] / max * 100) : 0) + "%";
      bar.appendChild(fill);
      chart.appendChild(bar);
    });
    var axis = el("div", "admin-bars-axis");
    axis.appendChild(el("span", null, dateLabel(days[0])));
    axis.appendChild(el("span", null, "maxim " + number(max === 1 && !values.some(Boolean) ? 0 : max) + " pe zi"));
    axis.appendChild(el("span", null, "azi"));
    box.appendChild(chart);
    box.appendChild(axis);

    var details = el("details", "admin-details");
    details.appendChild(el("summary", null, "Vezi ca tabel"));
    var table = el("table", "admin-table");
    var head = table.createTHead().insertRow();
    head.appendChild(el("th", null, "Ziua"));
    head.appendChild(el("th", "num", unit.charAt(0).toUpperCase() + unit.slice(1)));
    var body = table.createTBody();
    days.slice().reverse().forEach(function (day, i) {
      var row = body.insertRow();
      row.appendChild(el("td", null, dateLabel(day, true)));
      row.appendChild(el("td", "num", number(values[days.length - 1 - i])));
    });
    details.appendChild(table);
    box.appendChild(details);
  }

  function renderTop(stories, totals, readsByDay, days30) {
    var box = document.getElementById("top");
    box.textContent = "";
    var ids = Object.keys(totals);
    stories.forEach(function (s) { if (ids.indexOf(s.id) === -1) ids.push(s.id); });
    if (!ids.length) {
      box.appendChild(el("p", "admin-muted", "Încă nu există citiri."));
      return;
    }
    function inDays(id, days) {
      return sum(days.map(function (d) { return Number((readsByDay[d] || {})[id] || 0); }));
    }
    var byId = {};
    stories.forEach(function (s) { byId[s.id] = s; });
    var rows = ids.map(function (id) {
      return { id: id, story: byId[id], total: Number(totals[id] || 0), week: inDays(id, days30.slice(-7)), month: inDays(id, days30) };
    }).sort(function (a, b) { return b.total - a.total || b.month - a.month; });

    var table = el("table", "admin-table");
    var head = table.createTHead().insertRow();
    ["#", "Povestea", "Total", "7 zile", "30 de zile", "Publicată"].forEach(function (h, i) {
      head.appendChild(el("th", i >= 2 && i <= 4 ? "num" : null, h));
    });
    var body = table.createTBody();
    rows.forEach(function (r, i) {
      var row = body.insertRow();
      row.appendChild(el("td", "num", String(i + 1)));
      var cell = el("td");
      if (r.story) {
        var link = el("a", null, r.story.title);
        link.href = "poveste.html?id=" + encodeURIComponent(r.id);
        cell.appendChild(link);
      } else {
        cell.appendChild(el("span", "admin-muted", r.id + " (nu mai e pe site)"));
      }
      row.appendChild(cell);
      row.appendChild(el("td", "num", number(r.total)));
      row.appendChild(el("td", "num", number(r.week)));
      row.appendChild(el("td", "num", number(r.month)));
      row.appendChild(el("td", null, r.story && r.story.published ? dateLabel(r.story.published, true) : "—"));
    });
    box.appendChild(table);
  }

  function renderLibrary(site, stories) {
    var box = document.getElementById("library");
    box.textContent = "";
    var minutes = stories.map(function (s) { return Number(s.minutes || 0); });
    var thisMonth = (site.built || "").slice(0, 7);
    var list = el("dl", "admin-facts");
    function fact(label, value) {
      list.appendChild(el("dt", null, label));
      list.appendChild(el("dd", null, value));
    }
    fact("Povești publicate", number(stories.length));
    fact("Noi luna aceasta", number(stories.filter(function (s) { return (s.published || "").slice(0, 7) === thisMonth; }).length));
    fact("Durata medie", minutes.length ? "~" + Math.round(sum(minutes) / minutes.length) + " min" : "—");
    box.appendChild(list);

    // câte povești are fiecare categorie: arată unde mai e loc de povești noi
    box.appendChild(el("h3", null, "Pe categorii"));
    var categories = site.categories || {};
    var counts = {};
    stories.forEach(function (s) { (s.categories || []).forEach(function (c) { counts[c] = (counts[c] || 0) + 1; }); });
    var max = Math.max.apply(null, Object.keys(counts).map(function (k) { return counts[k]; }).concat([1]));
    var rows = el("div", "admin-hbars");
    Object.keys(categories).forEach(function (key) {
      var row = el("div", "admin-hbar");
      row.appendChild(el("span", "admin-hbar-label", categories[key].emoji + " " + categories[key].label));
      var track = el("span", "admin-hbar-track");
      var fill = el("span", "admin-hbar-fill");
      fill.style.width = ((counts[key] || 0) / max * 100) + "%";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "admin-hbar-value", number(counts[key] || 0)));
      rows.appendChild(row);
    });
    box.appendChild(rows);
  }

  function renderTodo(site) {
    var box = document.getElementById("todo");
    box.textContent = "";
    var problems = site.problems || [];
    var waiting = (site.personal || []).filter(function (p) { return !p.approved; });
    if (!problems.length && !waiting.length) {
      box.appendChild(el("p", "admin-ok", "✓ Nimic de rezolvat: toate poveștile sunt publicate."));
      return;
    }
    problems.forEach(function (p) {
      var item = el("div", "admin-todo is-problem");
      item.appendChild(el("strong", null, p.title + " — nepublicată (" + plural(p.count, "problemă", "probleme", "probleme") + ")"));
      var list = el("ul");
      p.errors.forEach(function (e) { list.appendChild(el("li", null, e)); });
      item.appendChild(list);
      item.appendChild(el("p", "admin-muted", "Detalii: rapoarte/" + p.id + ".md în repository"));
      box.appendChild(item);
    });
    waiting.forEach(function (p) {
      var item = el("div", "admin-todo");
      item.appendChild(el("strong", null, p.title + " — personalizată pentru " + p["for"] + ", așteaptă aprobarea"));
      var link = el("a", null, "Previzualizează");
      link.href = "poveste.html?previzualizare=" + encodeURIComponent(p.id);
      var line = el("p");
      line.appendChild(link);
      item.appendChild(line);
      box.appendChild(item);
    });
  }

  var ERROR_TYPES = { js: "JavaScript", promisiune: "JavaScript", imagine: "Imagine", audio: "Audio", server: "Server", alta: "Fișier" };

  function renderErrors(groups) {
    var box = document.getElementById("errors");
    box.textContent = "";
    clearBtn.hidden = !groups.length;
    if (!groups.length) {
      box.appendChild(el("p", "admin-ok", "✓ Nicio eroare în ultimele 14 zile."));
      return;
    }
    var table = el("table", "admin-table admin-errors");
    var head = table.createTHead().insertRow();
    ["Tip", "Eroarea", "De câte ori", "Ultima dată", "Unde"].forEach(function (h, i) {
      head.appendChild(el("th", i === 2 ? "num" : null, h));
    });
    var body = table.createTBody();
    groups.slice().sort(function (a, b) { return String(b.ultima).localeCompare(String(a.ultima)); }).forEach(function (g) {
      var row = body.insertRow();
      row.appendChild(el("td", null, ERROR_TYPES[g.tip] || g.tip));
      var what = el("td");
      what.appendChild(el("span", "admin-error-message", g.mesaj));
      if (g.sursa) what.appendChild(el("span", "admin-muted admin-error-source", g.sursa + (g.linie ? ":" + g.linie : "")));
      row.appendChild(what);
      row.appendChild(el("td", "num", number(g.numar)));
      row.appendChild(el("td", null, timeLabel(g.ultima)));
      var where = el("td");
      var browsers = Object.keys(g.browsere || {}).map(function (b) { return b + " (" + g.browsere[b] + ")"; });
      where.appendChild(el("span", null, browsers.join(", ")));
      if ((g.pagini || []).length) where.appendChild(el("span", "admin-muted admin-error-source", g.pagini.join(", ")));
      row.appendChild(where);
    });
    var wrap = el("div", "admin-table-wrap");
    wrap.appendChild(table);
    box.appendChild(wrap);
  }

  function renderSystem(data, site) {
    var box = document.getElementById("system");
    box.textContent = "";
    var list = el("dl", "admin-facts");
    function fact(label, value) {
      list.appendChild(el("dt", null, label));
      list.appendChild(el("dd", null, value));
    }
    fact("Versiunea publicată", site.commit ? site.commit.slice(0, 7) : "—");
    fact("Publicată la", site.built ? timeLabel(site.built) : "—");
    var server = data.server || {};
    fact("Ultima copie a contorului", server.ultima_copie ? timeLabel(server.ultima_copie) + " (" + plural(server.copii, "zi păstrată", "zile păstrate", "zile păstrate") + ")" : "încă nu există");
    var month = (data.azi || "").slice(0, 7);
    var budget = (site.image_budget || {})[month];
    if (budget && typeof budget === "object") {
      fact("Imagini generate luna aceasta", number(budget.imagini) + " (~" + Number(budget.lei || 0).toFixed(2) + " lei)");
    } else {
      fact("Imagini generate luna aceasta", "0");
    }
    fact("PHP pe server", server.php || "—");
    box.appendChild(list);
  }

  load();
})();
