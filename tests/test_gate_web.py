from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
UI = "http://localhost:3000"
DATA = ROOT / "demo" / "dataset" / "scenario_1_convoy"

TEXT_ROLES = [
    (".call .call-text", "the call"),
    (".call .call-action", "next action"),
    (".eyebrow", "section label"),
    (".trace .why", "step reason"),
    (".trace .skill", "skill name"),
    (".srclist span", "source id"),
    (".trace .claim", "chain claim"),
    (".trace .because", "chain because"),
    (".ev", "evidence finding"),
    (".ev .src", "evidence source"),
    (".ev .stance", "evidence tag"),
    (".note", "escalation"),
    (".runmeta", "run meta"),
    (".trace .num", "rail number"),
    ("#officer-note", "officer note field"),
    (".officer .quiet", "officer accept button"),
    (".officer .quiet-solid", "officer override button"),
    (".rail .eyebrow", "rail label"),
    (".rail .hint", "rail hint"),
    (".audit td", "audit cell"),
]

PROBE = """(sel) => {
  const e = document.querySelector(sel);
  if (!e) return null;
  const cs = getComputedStyle(e);
  let n = e, bg = 'rgba(0, 0, 0, 0)';
  while (n) {
    const c = getComputedStyle(n).backgroundColor;
    if (c && c !== 'rgba(0, 0, 0, 0)') { bg = c; break; }
    n = n.parentElement;
  }
  return {color: cs.color, bg, px: parseFloat(cs.fontSize)};
}"""


def to_hex(rgb: str) -> str | None:
    parts = rgb.replace("rgba", "rgb").split("(")[-1].split(")")[0].split(",")
    if len(parts) < 3:
        return None
    try:
        r, g, b = (int(float(x.strip())) for x in parts[:3])
    except ValueError:
        return None
    return f"#{r:02x}{g:02x}{b:02x}"


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100})

        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        page.goto(UI, wait_until="networkidle")
        page.wait_for_timeout(1200)

        print("C-2  every control is wired")
        page.set_input_files("#file-input", [str(f) for f in sorted(DATA.iterdir())])
        page.wait_for_timeout(500)
        attached = page.locator(".filelist li").count()
        print(f"  {'PASS' if attached == 3 else 'FAIL'}  uploader lists {attached} sources")
        if attached != 3:
            failures.append(f"uploader listed {attached} sources")

        removable = page.locator('.filelist button[aria-label^="Remove"], .filelist button')
        before = page.locator(".filelist li").count()
        removable.first.click()
        page.wait_for_timeout(300)
        after = page.locator(".filelist li").count()
        print(f"  {'PASS' if after == before - 1 else 'FAIL'}  remove button drops a source")
        if after != before - 1:
            failures.append("remove button did not work")
        page.set_input_files("#file-input", [str(f) for f in sorted(DATA.iterdir())])
        page.wait_for_timeout(400)

        page.get_by_role("button", name="Decide now").click()
        page.wait_for_selector(".call .call-text", timeout=60000)
        page.wait_for_timeout(400)

        print("\nR-25  text contrast on the rendered decision view")
        for sel, label in TEXT_ROLES:
            probe = page.evaluate(PROBE, sel)
            if not probe:
                failures.append(f"{label} not rendered ({sel})")
                print(f"  MISSING  {label:<18} {sel}")
                continue
            fg, bg = to_hex(probe["color"]), to_hex(probe["bg"])
            if not fg or not bg:
                failures.append(f"{label} unmeasurable")
                print(f"  SKIP     {label:<18} {probe['color']} on {probe['bg']}")
                continue
            r = ratio(fg, bg)
            need = 3.0 if probe["px"] >= 18 else 4.5
            ok = r >= need
            if not ok:
                failures.append(f"{label} {r:.2f}:1 below {need}")
            print(
                f"  {'PASS' if ok else 'FAIL'}  {label:<18} {r:>6.2f}:1  need {need:<4}"
                f"  {fg} on {bg}  {probe['px']:.0f}px"
            )

        print("\nR-31  the call is the largest text on screen")
        sizes = page.evaluate(
            """() => { const pick = s => { const e=document.querySelector(s);
                 return e ? parseFloat(getComputedStyle(e).fontSize) : 0 };
               return {call: pick('.call .call-text'), claim: pick('.trace .claim'),
                       h1: pick('h1'), eyebrow: pick('.eyebrow'), src: pick('.srclist span')}; }"""
        )
        for name, ok in [
            ("call beats a chain claim", sizes["call"] > sizes["claim"]),
            ("call beats the page title", sizes["call"] > sizes["h1"]),
            ("labels smaller than claims", sizes["eyebrow"] < sizes["claim"]),
            ("source ids smaller than claims", sizes["src"] < sizes["claim"]),
        ]:
            if not ok:
                failures.append(f"hierarchy: {name}")
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(
            f"        call {sizes['call']}px, claim {sizes['claim']}px, "
            f"h1 {sizes['h1']}px, eyebrow {sizes['eyebrow']}px, src {sizes['src']}px"
        )

        print("\nR-26  duty officer can accept and override a run")
        officer = page.locator(".officer")
        panel = "duty officer" in (officer.inner_text() if officer.count() else "").lower()
        print(f"  {'PASS' if panel else 'FAIL'}  officer panel rendered under the decision")
        if not panel:
            failures.append("officer panel missing")
        else:
            page.locator("#officer-note").fill("Gate check: route confirmed.")
            page.get_by_role("button", name="Accept the call").click()
            page.wait_for_timeout(800)
            accepted = "Accepted by the duty officer" in page.locator(".officer").inner_text()
            print(f"  {'PASS' if accepted else 'FAIL'}  accept records and shows a verdict")
            if not accepted:
                failures.append("accept did not record")
            page.get_by_role("button", name="Override the call").click()
            page.wait_for_timeout(800)
            changed = "Overridden by the duty officer" in page.locator(".officer").inner_text()
            print(f"  {'PASS' if changed else 'FAIL'}  latest verdict replaces the earlier one")
            if not changed:
                failures.append("override did not replace accept")

        print("\nR-32  keyboard reaches and operates the controls")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        page.set_input_files("#file-input", [str(f) for f in sorted(DATA.iterdir())])
        page.wait_for_timeout(400)
        page.evaluate("() => document.activeElement.blur()")
        page.keyboard.press("Tab")
        first = page.evaluate(
            "() => ({cls: document.activeElement.className, text: document.activeElement.textContent})"
        )
        ok = "skip-link" in (first["cls"] or "")
        print(f"  {'PASS' if ok else 'FAIL'}  first Tab reaches the skip link ({first})")
        if not ok:
            failures.append("skip link is not the first tab stop")

        ring = page.evaluate(
            """() => { const el = document.activeElement; const cs = getComputedStyle(el);
                 return {w: cs.outlineWidth, style: cs.outlineStyle}; }"""
        )
        ok = ring["style"] != "none" and float(ring["w"].replace("px", "")) >= 2
        print(f"  {'PASS' if ok else 'FAIL'}  focus ring {ring['w']} {ring['style']}")
        if not ok:
            failures.append(f"focus ring weak {ring}")

        for _ in range(12):
            page.keyboard.press("Tab")
            if "Decide now" in (page.evaluate("() => document.activeElement.textContent") or ""):
                break
        ring2 = page.evaluate(
            """() => { const b=document.activeElement;
                  const cs=getComputedStyle(b);
                  return {t:b.textContent.trim(), w:cs.outlineWidth, style:cs.outlineStyle}; }"""
        )
        ok = ring2["style"] != "none" and float(ring2["w"].replace("px", "")) >= 2
        print(f"  {'PASS' if ok else 'FAIL'}  keyboard focus ring on the primary control: "
              f"{ring2['w']} {ring2['style']}")
        if not ok:
            failures.append("primary control focus ring weak")

        print("\nR-27  states")
        body = page.inner_text("body")
        has_mock_notice = "Heuristic output, not a model" in body
        print(f"  {'PASS' if has_mock_notice else 'FAIL'}  engine state is stated in words")
        if not has_mock_notice:
            failures.append("no engine state statement")

        has_audit = page.locator(".audit tbody tr").count() > 0
        print(f"  {'PASS' if has_audit else 'FAIL'}  audit table populated after a run")
        if not has_audit:
            failures.append("audit table still empty after a run")

        print("\nR-03  no horizontal overflow at four widths")
        for width in (390, 768, 1280, 1600):
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(500)
            over = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            ok = over <= 1
            if not ok:
                failures.append(f"overflow {over}px at {width}w")
            print(f"  {'PASS' if ok else 'FAIL'}  {width}px wide, overflow {over}px")
        page.set_viewport_size({"width": 1600, "height": 1100})

        print("\nR-03  tap targets meet 44px")
        small = page.evaluate(
            """() => [...document.querySelectorAll('button, select, a.skip-link, .dropzone')]
                 .map(e => ({t: (e.textContent||'').trim().slice(0,24), h: Math.round(e.getBoundingClientRect().height)}))
                 .filter(x => x.h < 44)"""
        )
        if small:
            failures.append(f"tap targets under 44px: {small}")
            for s in small:
                print(f"  FAIL  {s['t']!r} is {s['h']}px")
        else:
            print("  PASS  every button, select and dropzone is at least 44px tall")

        print("\nC-5  and R-04  no fabricated claims, no emoji")
        banned = ["SOC 2", "ISO 27001", "trusted by", "testimonial", "uptime"]
        hits = [w for w in banned if w.lower() in body.lower()]
        print(f"  {'FAIL' if hits else 'PASS'}  no claim words ({banned})")
        if hits:
            failures.append(f"claim words present: {hits}")

        emoji = page.evaluate(
            """() => { const allowed = new Set([0x2013,0x2014,0x2026,0x2018,0x2019,0x201c,0x201d]);
                 return [...document.body.innerText].filter(c => c.codePointAt(0) > 0x2190 && !allowed.has(c.codePointAt(0))); }"""
        )
        if emoji:
            failures.append(f"emoji rendered: {sorted(set(emoji))}")
        print(f"  {'FAIL' if emoji else 'PASS'}  no emoji ({sorted(set(emoji)) if emoji else 'none'})")

        em = page.evaluate(
            "() => (document.body.innerText.match(/\\u2014/g) || []).length"
        )
        print(f"  {'FAIL' if em else 'PASS'}  no em dash in rendered text ({em})")
        if em:
            failures.append(f"{em} em dashes rendered")

        if console_errors:
            failures.append(f"console errors: {console_errors[:3]}")
        print(f"  {'FAIL' if console_errors else 'PASS'}  console clean ({console_errors[:2]})")

        browser.close()

    print(f"\n{'PASS' if not failures else 'FAIL'}  {len(failures)} issue(s)")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())