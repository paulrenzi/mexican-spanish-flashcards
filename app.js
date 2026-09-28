(() => {
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem("orale:" + k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem("orale:" + k, JSON.stringify(v)); } catch {} },
  };

  const state = {
    cat: store.get("cat", "garden"),
    dir: store.get("dir", "en"), // which language is on the front
    mode: "list",
    open: new Set(store.get("open", ["garden:water", "garden:light"])),
    known: new Set(store.get("known", [])),
    deck: [],
    flipped: false,
  };

  const catById = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));
  const inCat = (p) => p.cat === state.cat;
  const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  // ---------- Speech ----------
  let voice = null;
  function pickVoice() {
    if (!("speechSynthesis" in window)) return;
    const vs = speechSynthesis.getVoices().filter((v) => v.lang && v.lang.toLowerCase().startsWith("es"));
    voice =
      vs.find((v) => /es[-_]mx/i.test(v.lang)) ||
      vs.find((v) => /es[-_]us/i.test(v.lang)) ||
      vs.find((v) => /es[-_]419/i.test(v.lang)) ||
      vs[0] || null;
  }
  if ("speechSynthesis" in window) {
    pickVoice();
    speechSynthesis.addEventListener?.("voiceschanged", pickVoice);
  }
  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/…/g, " ").replace(/\s\/\s/g, ", "));
    u.lang = voice ? voice.lang : "es-MX";
    if (voice) u.voice = voice;
    u.rate = 0.85;
    speechSynthesis.speak(u);
  }

  // ---------- Categories ----------
  function renderCats() {
    $("cats").innerHTML = CATEGORIES
      .map((c) => {
        const n = PHRASES.filter((p) => p.cat === c.id).length;
        return `<button class="chip${c.id === state.cat ? " active" : ""}" data-cat="${c.id}"><span class="ic">${c.icon}</span>${c.name}<span class="n">${n} phrases</span></button>`;
      })
      .join("");
  }
  $("cats").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (!b) return;
    state.cat = b.dataset.cat;
    store.set("cat", state.cat);
    renderCats();
    buildDeck(false);
    renderList();
  });

  // ---------- Deck ----------
  function buildDeck(shuffle) {
    state.deck = PHRASES.map((p, i) => i).filter((i) => inCat(PHRASES[i]) && !state.known.has(PHRASES[i].es));
    if (shuffle) {
      for (let i = state.deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [state.deck[i], state.deck[j]] = [state.deck[j], state.deck[i]];
      }
    }
    showCard();
  }

  function setFlipped(on, animate = true) {
    const card = $("card");
    if (!animate) card.classList.add("no-anim");
    card.classList.toggle("flipped", on);
    state.flipped = on;
    if (!animate) { void card.offsetWidth; card.classList.remove("no-anim"); }
  }

  function showCard() {
    const total = PHRASES.filter(inCat).length;
    const learned = PHRASES.filter((p) => inCat(p) && state.known.has(p.es)).length;
    $("progressText").textContent = `${learned} of ${total} learned · ${state.deck.length} to go`;
    $("barFill").style.width = total ? `${(learned / total) * 100}%` : "0";
    $("dirBtn").textContent = state.dir === "en" ? "EN → ES" : "ES → EN";

    const empty = state.deck.length === 0;
    $("done").classList.toggle("hidden", !empty);
    $("card").classList.toggle("hidden", empty);
    $("actions").style.visibility = empty ? "hidden" : "visible";
    if (empty) {
      const label = `all the ${catById[state.cat].name.toLowerCase()} phrases`;
      $("doneText").textContent = `You've marked ${label} as learned.`;
      return;
    }

    const p = PHRASES[state.deck[0]];
    setFlipped(false, false);
    const tag = `${catById[p.cat].icon} ${catById[p.cat].es}`;
    $("frontTag").textContent = tag;
    $("backTag").textContent = tag;
    const front = $("frontText");
    front.textContent = state.dir === "en" ? p.en : p.es;
    front.classList.toggle("is-es", state.dir === "es");
    $("backEs").textContent = p.es;
    $("backPr").textContent = p.pr;
    $("backEn").textContent = p.en;
    $("backNote").textContent = p.note || "";
  }

  function current() { return state.deck.length ? PHRASES[state.deck[0]] : null; }

  function gotIt() {
    const p = current();
    if (!p) return;
    state.known.add(p.es);
    store.set("known", [...state.known]);
    state.deck.shift();
    showCard();
    renderList();
  }

  function again() {
    if (!state.deck.length) return;
    const i = state.deck.shift();
    state.deck.splice(Math.min(4, state.deck.length), 0, i); // see it again a few cards later
    showCard();
  }

  function flip() { if (current()) setFlipped(!state.flipped); }

  $("gotBtn").addEventListener("click", gotIt);
  $("againBtn").addEventListener("click", again);
  $("speakBtn").addEventListener("click", () => { const p = current(); if (p) speak(p.es); });
  $("shuffleBtn").addEventListener("click", () => buildDeck(true));
  $("dirBtn").addEventListener("click", () => {
    state.dir = state.dir === "en" ? "es" : "en";
    store.set("dir", state.dir);
    showCard();
  });
  function resetCat() {
    PHRASES.filter(inCat).forEach((p) => state.known.delete(p.es));
    store.set("known", [...state.known]);
    buildDeck(false);
    renderList();
  }
  $("resetBtn").addEventListener("click", () => {
    const what = catById[state.cat].name;
    if (confirm(`Reset learned cards for ${what}?`)) resetCat();
  });
  $("doneReset").addEventListener("click", resetCat);

  // ---------- Tap + swipe ----------
  const card = $("card");
  let startX = null, startY = 0, dx = 0;
  card.addEventListener("pointerdown", (e) => {
    startX = e.clientX; startY = e.clientY; dx = 0;
    card.setPointerCapture(e.pointerId);
    card.classList.add("no-anim");
  });
  card.addEventListener("pointermove", (e) => {
    if (startX === null) return;
    dx = e.clientX - startX;
    if (Math.abs(dx) < 6) return;
    card.style.transform = `translateX(${dx}px) rotate(${dx / 25}deg)${state.flipped ? " rotateY(180deg)" : ""}`;
    card.classList.toggle("swipe-right", dx > 80);
    card.classList.toggle("swipe-left", dx < -80);
  });
  function endDrag(e) {
    if (startX === null) return;
    const moved = Math.abs(dx) > 6 || Math.abs(e.clientY - startY) > 10;
    startX = null;
    card.classList.remove("no-anim", "swipe-left", "swipe-right");
    card.style.transform = "";
    if (dx > 80) gotIt();
    else if (dx < -80) again();
    else if (!moved && e.type === "pointerup") flip();
  }
  card.addEventListener("pointerup", endDrag);
  card.addEventListener("pointercancel", endDrag);

  document.addEventListener("keydown", (e) => {
    if (state.mode !== "cards" || e.target.tagName === "INPUT") return;
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); }
    else if (e.key === "ArrowRight") gotIt();
    else if (e.key === "ArrowLeft") again();
    else if (e.key.toLowerCase() === "s") { const p = current(); if (p) speak(p.es); }
  });

  // ---------- Phrases view: topic keywords that expand into phrases ----------
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const topicOf = (p) => catById[p.cat].topics.find((t) => t.id === p.topic);
  const row = (p, where) => `
        <li class="item${p.kind === "hear" ? " hear" : ""}">
          <div class="txt">
            ${where ? `<div class="l-where">${catById[p.cat].icon} ${esc(catById[p.cat].name)} · ${esc(topicOf(p).name)}</div>` : ""}
            <div class="l-es">${esc(p.es)}</div>
            <div class="l-pr">${esc(p.pr)}</div>
            <div class="l-en">${esc(p.en)}</div>
            ${p.note ? `<div class="l-note">${esc(p.note)}</div>` : ""}
          </div>
          <div class="btns">
            <button data-say="${PHRASES.indexOf(p)}" aria-label="Hear it">🔊</button>
            <button data-show="${PHRASES.indexOf(p)}" aria-label="Show it big">⤢</button>
          </div>
        </li>`;
  const word = (p) => `
        <button class="word" data-say="${PHRASES.indexOf(p)}" title="${esc(p.pr)}${p.note ? " · " + esc(p.note) : ""}">
          <span class="w-es">${esc(p.es)}</span><span class="w-en">${esc(p.en)}</span>
        </button>`;

  function renderTopics() {
    const cat = catById[state.cat];
    $("topics").innerHTML = cat.topics.map((t) => {
      const ps = PHRASES.filter((p) => p.cat === cat.id && p.topic === t.id);
      const say = ps.filter((p) => !p.kind), hear = ps.filter((p) => p.kind === "hear"), words = ps.filter((p) => p.kind === "word");
      return `
      <details class="topic" data-topic="${t.id}"${state.open.has(cat.id + ":" + t.id) ? " open" : ""}>
        <summary><span class="t-ic">${t.icon}</span><span class="t-name">${esc(t.name)}<span class="t-es">${esc(t.es)}</span></span><span class="t-n">${ps.length}</span></summary>
        ${say.length ? `<h3>You ask</h3><ul class="list">${say.map((p) => row(p)).join("")}</ul>` : ""}
        ${hear.length ? `<h3>You'll hear</h3><ul class="list">${hear.map((p) => row(p)).join("")}</ul>` : ""}
        ${words.length ? `<h3>Words</h3><div class="words">${words.map(word).join("")}</div>` : ""}
      </details>`;
    }).join("");
    syncToggleAll();
  }
  function syncToggleAll() {
    const ds = [...document.querySelectorAll(".topic")];
    $("toggleAll").textContent = ds.length && ds.every((d) => d.open) ? "Close all" : "Open all";
    $("listCount").textContent = `${ds.length} topics · ${PHRASES.filter(inCat).length} phrases`;
  }
  function saveOpen() {
    state.open = new Set([...state.open].filter((k) => !k.startsWith(state.cat + ":")));
    document.querySelectorAll(".topic[open]").forEach((d) => state.open.add(state.cat + ":" + d.dataset.topic));
    store.set("open", [...state.open]);
    syncToggleAll();
  }
  $("topics").addEventListener("toggle", saveOpen, true);
  $("toggleAll").addEventListener("click", () => {
    const ds = [...document.querySelectorAll(".topic")];
    const open = !ds.every((d) => d.open);
    ds.forEach((d) => (d.open = open));
    saveOpen();
  });

  function renderList() {
    const raw = $("search").value.trim(), q = fold(raw);
    $("topics").classList.toggle("hidden", !!q);
    $("list").classList.toggle("hidden", !q);
    $("toggleAll").classList.toggle("hidden", !!q);
    if (!q) { renderTopics(); return; }
    const rows = PHRASES.filter((p) => fold(p.es + " " + p.en + " " + (p.note || "") + " " + topicOf(p).name + " " + topicOf(p).es).includes(q));
    $("listCount").textContent = `${rows.length} match${rows.length === 1 ? "" : "es"} in all sections`;
    $("list").innerHTML = rows.length ? rows.map((p) => row(p, true)).join("") : `<li class="empty">No phrases match “${esc(raw)}”.</li>`;
  }
  $("search").addEventListener("input", renderList);
  $("listView").addEventListener("click", (e) => {
    const s = e.target.closest("[data-say]");
    if (s) speak(PHRASES[+s.dataset.say].es);
    const b = e.target.closest("[data-show]");
    if (b) {
      const p = PHRASES[+b.dataset.show];
      $("showEs").textContent = p.es;
      $("showEn").textContent = p.en;
      $("show").classList.remove("hidden");
      speak(p.es);
    }
  });
  $("show").addEventListener("click", () => $("show").classList.add("hidden"));

  // ---------- Mode switch ----------
  document.querySelectorAll(".mode").forEach((b) =>
    b.addEventListener("click", () => {
      state.mode = b.dataset.mode;
      document.querySelectorAll(".mode").forEach((x) => {
        x.classList.toggle("active", x === b);
        x.setAttribute("aria-selected", x === b);
      });
      $("cardsView").classList.toggle("hidden", state.mode !== "cards");
      $("listView").classList.toggle("hidden", state.mode !== "list");
    }));

  if (!catById[state.cat]) state.cat = "garden";
  renderCats();
  buildDeck(false);
  renderList();

  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
})();
