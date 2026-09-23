(() => {
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem("orale:" + k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem("orale:" + k, JSON.stringify(v)); } catch {} },
  };

  const state = {
    cat: store.get("cat", "all"),
    dir: store.get("dir", "en"), // which language is on the front
    mode: "cards",
    known: new Set(store.get("known", [])),
    deck: [],
    flipped: false,
  };

  const catById = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));
  const inCat = (p) => state.cat === "all" || p.cat === state.cat;
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
    const all = [{ id: "all", name: "All", icon: "⭐" }, ...CATEGORIES];
    $("cats").innerHTML = all
      .map((c) => {
        const n = PHRASES.filter((p) => c.id === "all" || p.cat === c.id).length;
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
      const label = state.cat === "all" ? "every phrase" : `all the ${catById[state.cat].name.toLowerCase()} phrases`;
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
    const what = state.cat === "all" ? "all categories" : catById[state.cat].name;
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

  // ---------- List view ----------
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function renderList() {
    const q = fold($("search").value.trim());
    const rows = PHRASES.map((p, i) => [p, i]).filter(([p]) =>
      inCat(p) && (!q || fold(p.es + " " + p.en + " " + (p.note || "")).includes(q)));
    $("list").innerHTML = rows.length
      ? rows.map(([p, i]) => `
        <li class="item${state.known.has(p.es) ? " learned" : ""}">
          <div class="txt">
            <div class="l-es">${esc(p.es)}</div>
            <div class="l-pr">${esc(p.pr)}</div>
            <div class="l-en">${esc(p.en)}</div>
            ${p.note ? `<div class="l-note">${esc(p.note)}</div>` : ""}
          </div>
          <button data-say="${i}" aria-label="Hear it">🔊</button>
        </li>`).join("")
      : `<li class="empty">No phrases match “${esc($("search").value)}”.</li>`;
  }
  $("search").addEventListener("input", renderList);
  $("list").addEventListener("click", (e) => {
    const b = e.target.closest("[data-say]");
    if (b) speak(PHRASES[+b.dataset.say].es);
  });

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

  if (!catById[state.cat] && state.cat !== "all") state.cat = "all";
  renderCats();
  buildDeck(false);
  renderList();

  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
})();
