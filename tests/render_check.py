"""Render the site on an iPhone-sized viewport and drive it. Usage: python tests/render_check.py [url]"""
import sys, subprocess, time, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "shots"
OUT.mkdir(exist_ok=True)

url = sys.argv[1] if len(sys.argv) > 1 else None
server = None
if not url:
    server = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    url = "http://localhost:8765/"

fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)

try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url + ("&" if "?" in url else "?") + "cb=" + str(time.time()))
        page.wait_for_selector(".topic")
        page.evaluate("localStorage.clear()")
        page.reload()

        chips = page.locator(".chip").count()
        check(chips == 13, f"13 situation tabs (got {chips})")
        check(page.is_visible("#listView") and not page.is_visible("#cardsView"), "opens on Phrases, not flashcards")
        check("active" in page.get_attribute(".chip[data-cat=garden]", "class"), "garden tab is the default")
        opened = page.locator(".topic[open]").count()
        check(opened == 2, f"water + light open by default (got {opened})")
        check(page.locator(".topic[data-topic=water][open] .l-es").first.inner_text() == "¿Cada cuánto se riega?", "water topic expands into phrases")
        page.screenshot(path=str(OUT / "1-garden.png"), full_page=True)
        page.click(".topic[data-topic=soil] summary")
        check(page.locator(".topic[data-topic=soil]").get_attribute("open") is not None, "tapping a keyword expands it")
        check(page.locator(".topic[data-topic=soil] .word").count() >= 5, "soil topic has word chips")
        page.reload()
        check(page.locator(".topic[data-topic=soil]").get_attribute("open") is not None, "open topics persist")
        page.click(".topic[data-topic=water] [data-show]")
        check(page.is_visible("#show") and page.inner_text("#showEs") == "¿Cada cuánto se riega?", "show-big overlay")
        page.screenshot(path=str(OUT / "2-show.png"))
        page.click("#show")
        check(not page.is_visible("#show"), "tap closes overlay")

        page.fill("#search", "cuenta")
        n = page.locator("#list .item").count()
        check(n >= 1, f"search 'cuenta' finds restaurant rows from the garden tab (got {n})")
        page.fill("#search", "")

        page.click(".chip[data-cat=gas]")
        check(page.locator(".topic").count() == 7, "gas station has 7 topics")
        check(page.inner_text("#heroName") == "Gas station", "header names the gas station")
        page.click(".topic[data-topic=fill] summary")
        check(page.locator(".topic[data-topic=fill] .item.hear").count() >= 5, "gas fill-up has things you'll hear")
        page.screenshot(path=str(OUT / "3-gas.png"), full_page=True)
        page.click(".topic[data-topic=fill] summary")
        page.click(".chip[data-cat=pharmacy]")
        check(page.locator(".topic").count() == 7, "pharmacy has 7 topics")
        check(page.inner_text("#heroName") == "Pharmacy", "header names the pharmacy")
        check(page.locator(".topic[data-topic=dose] .item.hear").count() >= 5, "pharmacy dosing has things you'll hear")
        page.screenshot(path=str(OUT / "7-pharmacy.png"), full_page=True)
        page.click(".chip[data-cat=clean]")
        check(page.locator(".topic").count() == 7, "house cleaning has 7 topics")
        check(page.inner_text("#heroName") == "House cleaning", "header names house cleaning")
        check(page.locator(".topic[data-topic=supplies] .word").count() >= 10, "cleaning supplies has word chips")
        page.screenshot(path=str(OUT / "8-clean.png"), full_page=True)
        for cid, name, ntop in [("doctor", "Doctor & dentist", 9), ("repair", "Repairs at home", 7), ("taxi", "Taxi & colectivo", 6), ("police", "Police & traffic stop", 6),
                                ("bank", "Bank & money", 7), ("house", "Buying a house", 7)]:
            page.locator(f".chip[data-cat={cid}]").scroll_into_view_if_needed()
            page.click(f".chip[data-cat={cid}]")
            check(page.locator(".topic").count() == ntop, f"{cid} has {ntop} topics")
            check(page.inner_text("#heroName") == name, f"header names {name}")
            check(page.locator(".topic .item, .topic .word").count() >= 50, f"{cid} has 50+ phrases")
            vis = page.evaluate(f"(() => {{ const r = document.querySelector('.chip[data-cat={cid}]').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }})()")
            check(vis, f"{cid} tab stays in view after tapping it")
            if cid == "doctor":
                page.screenshot(path=str(OUT / "10-doctor.png"), full_page=True)
                check(page.locator(".topic[data-topic=dentist] .item").count() >= 10, "doctor has dentist phrases")
        page.screenshot(path=str(OUT / "9-house.png"), full_page=True)
        check(page.locator(".topic[data-topic=finish] .item").count() >= 10, "house has finishing-the-house phrases")
        page.locator(".chip[data-cat=food]").scroll_into_view_if_needed()
        page.click(".chip[data-cat=food]")
        check(page.locator(".topic").count() == 6, "restaurant has 6 topics")
        page.click(".mode[data-mode=cards]")
        check(page.inner_text("#frontText") == "A table for two, please", "practice deck follows the tab")
        page.click("#card"); page.wait_for_timeout(600)
        check("flipped" in page.get_attribute("#card", "class"), "tap flips the card")
        page.click("#gotBtn")
        check(page.inner_text("#progressText").startswith("1 of"), "Got it counts learned")
        page.click("#dirBtn")
        check(page.inner_text("#frontText") != "", "direction toggle works")
        page.click(".mode[data-mode=list]")

        # overflow: every card's back must fit without horizontal scroll
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        check(not overflow, "no horizontal overflow")
        page.set_viewport_size({"width": 360, "height": 740})
        page.click(".chip[data-cat=garden]")
        page.click("#toggleAll")
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        check(not overflow, "no horizontal overflow at 360px with every topic open")
        clipped = page.evaluate("[...document.querySelectorAll('.chip')].filter(c => c.scrollWidth > c.clientWidth || c.offsetWidth < 70).length")
        check(clipped == 0, f"every tab is full size with its whole label (clipped {clipped})")
        scrolls = page.evaluate("(() => { const t = document.querySelector('#cats .track'); return t.scrollWidth > t.clientWidth; })()")
        check(scrolls, "tab bar scrolls sideways instead of squeezing")
        check("more-right" in (page.get_attribute("#cats", "class") or ""), "right edge fades to show more tabs")
        page.screenshot(path=str(OUT / "5-narrow.png"))
        nav_ok = page.evaluate("(() => { const r = document.getElementById('cats').getBoundingClientRect(); return Math.round(r.bottom) === innerHeight; })()")
        check(nav_ok, "situation bar is pinned to the bottom")
        check(not errors, f"no JS errors {errors}")
        dark = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                             has_touch=True, color_scheme="dark")
        dp = dark.new_page()
        dp.goto(url + ("&" if "?" in url else "?") + "cb=" + str(time.time()))
        dp.wait_for_selector(".topic")
        bg = dp.evaluate("getComputedStyle(document.body).backgroundColor")
        check(bg == "rgb(15, 17, 18)", f"dark mode follows the phone (bg {bg})")
        dp.screenshot(path=str(OUT / "6-dark.png"))

        # Talk: the Worker is mocked here; the fake Chromium mic records a tone, the page converts it to WAV.
        tc = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                           has_touch=True, permissions=["microphone"])
        tp = tc.new_page()
        terr = []
        tp.on("pageerror", lambda e: terr.append(str(e)))
        seen = {"stt": [], "translate": []}
        stt_reply = {"body": ""}
        def on_stt(route):
            body = route.request.post_data_buffer or b""
            seen["stt"].append((route.request.url, body[:4], len(body)))
            route.fulfill(status=stt_reply.get("status", 200), content_type="application/json", body=stt_reply["body"])
        def on_translate(route):
            seen["translate"].append(route.request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body='{"text": "¿Me puede hacer un descuento, por favor?", "ms": 2900}')
        tp.route("https://mx-voice.paulmichaelrenzi.workers.dev/stt*", on_stt)
        tp.route("https://mx-voice.paulmichaelrenzi.workers.dev/translate", on_translate)
        tp.goto(url + ("&" if "?" in url else "?") + "cb=" + str(time.time()))
        tp.wait_for_selector(".topic")
        tp.click(".mode[data-mode=talk]")
        check(tp.is_visible("#talkView") and not tp.is_visible("#listView"), "Talk tab opens the talk view")
        check(not tp.is_visible("#cats") and not tp.is_visible("#hero"), "talk view hides the situation bar and header")
        m = tp.evaluate("[matchPhrase('tengo un piquete que se ve infectada', 'es'), matchPhrase('Is there an ATM around here', 'en'), "
                        "matchPhrase('It is spicy', 'en'), matchPhrase('Can you give me a discount please', 'en'), matchPhrase('cloro', 'es')]")
        check(m[0] and m[0]["other"] == "I have a bite that looks infected.", f"phrasebook catches a near-miss transcript of the piquete phrase ({m[0] and m[0]['other']})")
        check(m[1] and m[1]["other"] == "¿Hay un cajero por aquí?", "phrasebook maps English to the curated Spanish")
        check(m[2] is None, "'It is spicy' does not match 'Is it spicy?'")
        check(m[3] is None, "a longer sentence falls through to the translator")
        check(m[4] and "bleach" in m[4]["other"], f"a single word matches its word entry ({m[4] and m[4]['other']})")

        stt_reply["body"] = '{"text": "Tengo un piquete que se ve infectado."}'
        tp.click(".mic[data-from=es]")
        tp.wait_for_selector(".mic.rec")
        check(tp.inner_text(".mic.rec .m-hint") == "Tap to stop", "mic shows it is recording")
        tp.wait_for_timeout(1500)
        tp.click(".mic[data-from=es]")
        tp.wait_for_selector(".turn .t-es")
        check(bool(seen["stt"]) and "lang=es" in seen["stt"][0][0] and seen["stt"][0][1] == b"RIFF" and seen["stt"][0][2] > 30000,
              f"recording is posted to /stt as WAV ({seen['stt'][:1] and seen['stt'][0][1:]})")
        check(tp.inner_text(".turn .t-en") == "I have a bite that looks infected.", "Spanish speech is answered from the phrasebook")
        check(tp.inner_text(".turn .t-src") == "From the phrasebook" and not seen["translate"], "phrasebook match skips the model")

        stt_reply["body"] = '{"text": "Can you give me a discount, please?"}'
        tp.click(".mic[data-from=en]"); tp.wait_for_timeout(1200); tp.click(".mic[data-from=en]")
        tp.wait_for_function("document.querySelectorAll('.turn .t-es').length === 2")
        first = tp.locator(".turn").first
        check(seen["translate"] == [{"text": "Can you give me a discount, please?", "from": "en"}], f"unmatched English goes to /translate ({seen['translate']})")
        check(first.locator(".t-es").inner_text() == "¿Me puede hacer un descuento, por favor?" and first.locator(".t-en").inner_text() == "Can you give me a discount, please?",
              "newest turn is on top, Spanish big with English under")
        check(first.locator(".t-src").inner_text() == "Translated by Claude", "model translations are labelled")

        stt_reply.update(status=503, body='{"error": "stt_quota"}')
        tp.click(".mic[data-from=en]"); tp.wait_for_timeout(800); tp.click(".mic[data-from=en]")
        tp.wait_for_selector(".turn.err")
        check("used up for today" in tp.inner_text(".turn.err .t-err"), "a spent Whisper allowance says so plainly")
        tp.fill("#talkText", "¿Hay un cajero por aquí?")
        tp.click("[data-type-from=es]")
        tp.wait_for_function("document.querySelectorAll('.turn').length === 4")
        check(tp.locator(".turn").first.locator(".t-en").inner_text() == "Is there an ATM around here?", "typed Spanish works through the phrasebook")
        check(not tp.evaluate("document.documentElement.scrollWidth > innerWidth"), "talk view has no horizontal overflow")
        tp.screenshot(path=str(OUT / "11-talk.png"), full_page=True)
        tp.set_viewport_size({"width": 360, "height": 740})
        hdr = tp.evaluate("(() => { const r = document.querySelector('.modes').getBoundingClientRect(); return [innerWidth, Math.round(r.right), document.documentElement.scrollWidth]; })()")
        check(hdr[0] == 360 and hdr[1] <= 360 and hdr[2] <= 360, f"three mode tabs fit at 360px without the page zooming out (innerWidth, tabs right, scrollWidth = {hdr})")
        tp.screenshot(path=str(OUT / "12-talk-narrow.png"))
        check(not terr, f"no JS errors in talk {terr}")
        b.close()
finally:
    if server:
        server.terminate()

print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
