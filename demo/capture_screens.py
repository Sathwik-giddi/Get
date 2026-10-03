from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://localhost:3000"
DATA = ROOT / "demo" / "dataset"

SCENARIOS = [
    ("01", "landing", None, None),
    ("02", "convoy", "Convoy B / Narmada corridor", "scenario_1_convoy"),
    ("03", "warehouse", "Warehouse cold-chain incident", "scenario_2_warehouse"),
]

SHOTS = ROOT / "demo" / "shots"


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        for index, slug, scenario_name, folder in SCENARIOS:
            page.goto(f"{BASE}/console" if folder else BASE, wait_until="networkidle")
            page.wait_for_timeout(1200)

            if folder:
                page.select_option("#scenario-name", scenario_name)
                page.wait_for_timeout(900)
                paths = [str(f) for f in sorted((DATA / folder).iterdir()) if f.is_file()]
                page.set_input_files("#file-input", paths)
                page.wait_for_timeout(500)
                listed = page.locator(".filelist li").count()
                if listed != len(paths):
                    failures.append(f"{slug}: uploader listed {listed} of {len(paths)}")
                    continue
                page.get_by_role("button", name="Decide now").click()
                page.wait_for_selector(".call .call-text", timeout=60000)
                page.wait_for_timeout(500)

            if page.locator(".stException").count():
                failures.append(f"{slug}: page shows an error state")

            page.screenshot(path=str(SHOTS / f"{index}_{slug}.png"), full_page=(folder is None))
            if folder:
                page.evaluate("() => window.scrollTo(0, 900)")
                page.wait_for_timeout(400)
                page.screenshot(path=str(SHOTS / f"{index}_{slug}_reasoning.png"))

        if errors:
            failures.append(f"console errors: {errors[:3]}")
        browser.close()

    for f in sorted(SHOTS.glob("*.png")):
        print(f"  {f.name}  ({f.stat().st_size / 1024:.0f} KB)")

    if failures:
        print(f"\nFAIL  {len(failures)} issue(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASS  {len(list(SHOTS.glob('*.png')))} screenshots in {SHOTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())