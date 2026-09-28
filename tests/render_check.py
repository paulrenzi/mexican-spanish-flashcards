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
        b = pw.chromium.launch()
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
        check(chips == 4, f"4 situation tabs (got {chips})")
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
        clipped = page.evaluate("[...document.querySelectorAll('.chip')].filter(c => c.scrollWidth > c.clientWidth || c.getBoundingClientRect().right > innerWidth).length")
        check(clipped == 0, f"all category chips fit at 360px (clipped {clipped})")
        page.screenshot(path=str(OUT / "5-narrow.png"))
        check(not errors, f"no JS errors {errors}")
        b.close()
finally:
    if server:
        server.terminate()

print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
