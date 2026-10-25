(function () {
  "use strict";

  var grid = document.getElementById("stories");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function card(story) {
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
    body.appendChild(el("p", null, story.summary));
    var meta = el("p", "story-meta");
    meta.appendChild(el("span", null, story.pages + " pagini"));
    meta.appendChild(el("span", null, "~" + story.minutes + " min"));
    meta.appendChild(el("span", null, story.age + " ani"));
    body.appendChild(meta);
    link.appendChild(body);
    return link;
  }

  fetch("stories/index.json", { cache: "no-cache" })
    .then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    })
    .then(function (data) {
      grid.textContent = "";
      if (!data.stories.length) {
        grid.appendChild(el("p", "muted", "Încă nu avem povești. Revino curând!"));
        return;
      }
      data.stories.forEach(function (story) {
        grid.appendChild(card(story));
      });
    })
    .catch(function () {
      grid.textContent = "";
      grid.appendChild(el("p", "muted", "Nu am putut încărca poveștile. Încearcă din nou."));
    });
})();
