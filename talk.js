// Talk: say it in English or Spanish, see it in both. Mic -> Parakeet on our server (/stt) -> phrasebook match or Claude (/translate).
(() => {
  const API = "https://mx-voice.paulmichaelrenzi.workers.dev";
  const MAX_SECONDS = 15;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------- Phrasebook match: a curated phrase beats any model (the only thing that gets "piquete" right) ----------
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/\([^)]*\)/g, " ").replace(/[¿?¡!.,;:"“”'’…]/g, " ")
    .replace(/^\s*(el|la|los|las|the|a|an)\s+/, "").replace(/\s+/g, " ").trim();
  function lev(a, b) {
    let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[b.length];
  }
  // One entry per alternative ("seco / húmedo" gives two), skipping fill-in-the-blank phrases.
  const INDEX = { es: [], en: [] };
  PHRASES.forEach((p) => {
    if (/…|\.\.\./.test(p.es + p.en)) return;
    for (const lang of ["es", "en"]) {
      const alts = p[lang].split(" / ");
      const other = p[lang === "es" ? "en" : "es"].split(" / ");
      alts.forEach((a, i) => {
        const n = norm(a);
        if (n) INDEX[lang].push({ n, p, text: a.replace(/\s*\([^)]*\)/g, "").trim(), other: (other.length === alts.length ? other[i] : p[lang === "es" ? "en" : "es"]).replace(/\s*\([^)]*\)/g, "").trim() });
      });
    }
  });
  const MIN_SIMILARITY = 0.88;
  function matchPhrase(text, lang) {
    const n = norm(text);
    if (!n) return null;
    let best = null, bestScore = 0;
    for (const e of INDEX[lang]) {
      if (Math.abs(e.n.length - n.length) > n.length * (1 - MIN_SIMILARITY) + 1) continue;
      const score = 1 - lev(n, e.n) / Math.max(n.length, e.n.length);
      if (score > bestScore) { best = e; bestScore = score; }
    }
    return bestScore >= MIN_SIMILARITY ? { ...best, score: bestScore } : null;
  }
  window.matchPhrase = matchPhrase; // used by tests/render_check.py

  // ---------- Turns ----------
  function addTurn(from) {
    const li = document.createElement("li");
    li.className = "turn from-" + from;
    li.innerHTML = `<div class="t-who">${from === "en" ? "🇺🇸 You said" : "🇲🇽 They said"}</div><div class="t-body"><p class="t-wait">Listening…</p></div>`;
    $("turns").prepend(li);
    $("talkEmpty").classList.add("hidden");
    return li;
  }
  function setWait(li, msg) { li.querySelector(".t-body").innerHTML = `<p class="t-wait">${esc(msg)}</p>`; }
  function setError(li, msg, heard) {
    li.classList.add("err");
    li.querySelector(".t-body").innerHTML = (heard ? `<p class="t-heard">“${esc(heard)}”</p>` : "") + `<p class="t-err">${esc(msg)}</p>`;
  }
  function setResult(li, es, en, source) {
    li.querySelector(".t-body").innerHTML = `
      <p class="t-es">${esc(es)}</p>
      <p class="t-en">${esc(en)}</p>
      <div class="t-foot"><span class="t-src ${source === "phrasebook" ? "book" : ""}">${source === "phrasebook" ? "From the phrasebook" : "Translated by Claude"}</span>
      <button class="t-say" aria-label="Hear it in Spanish"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none"/></svg></button></div>`;
    li.querySelector(".t-say").addEventListener("click", () => window.oraleSpeak(es));
  }
  const MESSAGES = {
    origin_not_connected: "The voice server isn't connected yet. Typed phrasebook phrases still work.",
    origin_unreachable: "The voice server didn't answer. Try again in a moment.",
    rate_limited: "That's a lot of requests at once. Wait a minute and try again.",
    busy: "The translator is busy. Try again in a moment.",
  };
  const why = (d, fallback) => MESSAGES[d && d.error] || fallback;

  async function handleText(text, from, li) {
    const m = matchPhrase(text, from);
    if (m) {
      const [es, en] = from === "en" ? [m.other, text] : [text, m.other];
      setResult(li, es, en, "phrasebook");
      if (from === "en") window.oraleSpeak(es);
      return;
    }
    setWait(li, "Translating…");
    let r, d;
    try {
      r = await fetch(API + "/translate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, from }) });
      d = await r.json();
    } catch { return setError(li, "No connection to the translator.", text); }
    if (!r.ok || !d.text) return setError(li, why(d, "Translation failed. Try again."), text);
    const [es, en] = from === "en" ? [d.text, text] : [text, d.text];
    setResult(li, es, en, "claude");
    if (from === "en") window.oraleSpeak(es);
  }

  // ---------- Recording: sent as the browser made it (Safari mp4, Chrome webm); the server decodes it ----------
  let rec = null;

  function setRecording(from) {
    document.querySelectorAll(".mic").forEach((b) => {
      const on = b.dataset.from === from;
      b.classList.toggle("rec", on);
      b.disabled = !!from && !on;
      b.querySelector(".m-hint").textContent = on ? "Tap to stop" : b.dataset.hint;
    });
  }

  async function start(from) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      const li = addTurn(from);
      return setError(li, "This browser can't record audio. Type it instead.");
    }
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { const li = addTurn(from); return setError(li, "Microphone access was blocked. Allow it in your browser settings, or type instead."); }
    const chunks = [];
    const mr = new MediaRecorder(stream);
    const li = addTurn(from);
    const began = Date.now();
    rec = { mr, from, li, timer: setTimeout(stop, MAX_SECONDS * 1000) };
    mr.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const audio = new Blob(chunks, { type: mr.mimeType || "audio/mp4" });
      if (Date.now() - began < 600 || !audio.size) return setError(li, "That was too short. Tap, speak, then tap again.");
      setWait(li, "Writing it down…");
      let r, d;
      try { r = await fetch(`${API}/stt?lang=${from}`, { method: "POST", headers: { "Content-Type": audio.type }, body: audio }); d = await r.json(); }
      catch { return setError(li, "No connection to speech-to-text."); }
      if (!r.ok) return setError(li, why(d, "Speech-to-text failed. Try again."));
      if (!d.text) return setError(li, d.peak < 0.01
        ? "The microphone sent silence. Check that no other app is using it, then try again."
        : "Didn't catch anything. Try again, a little closer to the phone.");
      await handleText(d.text, from, li);
    };
    mr.start();
    setRecording(from);
  }
  function stop() {
    if (!rec) return;
    clearTimeout(rec.timer);
    if (rec.mr.state !== "inactive") rec.mr.stop();
    rec = null;
    setRecording(null);
  }

  document.querySelectorAll(".mic").forEach((b) =>
    b.addEventListener("click", () => (rec ? (rec.from === b.dataset.from ? stop() : null) : start(b.dataset.from))));

  document.querySelectorAll("[data-type-from]").forEach((b) =>
    b.addEventListener("click", () => {
      const text = $("talkText").value.trim();
      if (!text) return $("talkText").focus();
      $("talkText").value = "";
      handleText(text, b.dataset.typeFrom, addTurn(b.dataset.typeFrom));
    }));
})();
