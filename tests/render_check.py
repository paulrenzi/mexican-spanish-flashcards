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
        page.wait_for_selector("#frontText")
        page.evaluate("localStorage.clear()")
        page.reload()

        chips = page.locator(".chip").count()
        check(chips == 4, f"4 category chips (got {chips})")
        front = page.inner_text("#frontText")
        check(front == "Hello", f"first card front is 'Hello' (got {front!r})")
        page.screenshot(path=str(OUT / "1-front.png"))

        page.click("#card")
        page.wait_for_timeout(600)
        check("flipped" in page.get_attribute("#card", "class"), "tap flips the card")
        check(page.inner_text("#backEs") == "Hola", "back shows Spanish")
        page.screenshot(path=str(OUT / "2-back.png"))

        page.click("#gotBtn")
        check(page.inner_text("#frontText") == "Good morning", "Got it advances to next card")
        check(page.inner_text("#progressText").startswith("1 of"), "progress counts 1 learned")

        # swipe right = got it
        box = page.locator("#card").bounding_box()
        y = box["y"] + box["height"] / 2
        page.mouse.move(box["x"] + 100, y); page.mouse.down()
        page.mouse.move(box["x"] + 300, y, steps=8); page.mouse.up()
        check(page.inner_text("#progressText").startswith("2 of"), "swipe right marks learned")

        # swipe left = again (no learned change)
        page.mouse.move(box["x"] + 300, y); page.mouse.down()
        page.mouse.move(box["x"] + 80, y, steps=8); page.mouse.up()
        check(page.inner_text("#progressText").startswith("2 of"), "swipe left does not mark learned")

        page.click(".chip[data-cat=food]")
        check(page.inner_text("#frontText") == "A table for two, please", "restaurant deck starts at table phrase")
        page.click(".chip[data-cat=food]")
        page.click("#card"); page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "3-food-back.png"))

        page.click("#dirBtn")
        check(page.inner_text("#frontText") == "Una mesa para dos, por favor", "ES→EN direction shows Spanish first")

        page.reload()
        check(page.inner_text("#progressText").startswith("0 of"), "category + direction persist; food has 0 learned")

        page.click(".mode[data-mode=list]")
        page.fill("#search", "cuenta")
        n = page.locator(".item").count()
        check(n >= 1, f"list search 'cuenta' finds rows (got {n})")
        page.fill("#search", "")
        page.click(".chip[data-cat=all]")
        page.screenshot(path=str(OUT / "4-list.png"))
        total = page.locator(".item").count()
        check(total > 100, f"list shows all phrases (got {total})")

        # overflow: every card's back must fit without horizontal scroll
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        check(not overflow, "no horizontal overflow")
        page.set_viewport_size({"width": 360, "height": 740})
        page.click(".mode[data-mode=cards]")
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
