from __future__ import annotations

import io
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "demo" / "dataset"

DISPATCH = """\
DISPATCH LOG - UNIT 7-KILARA SECTOR
From: J. Menon, Sector Officer
To: Convoy Control, Logistics Cell
Time: 14:20 IST

Convoy B (12 trucks, 84 tonnes of medical stores) is staged at Halipur depot and is
scheduled to clear for the Narmada corridor at 16:00 today. The medical stores are for the
Kolar field hospital, which has asked for them before tomorrow morning.

Two changes since the plan was filed:

1. The district office phoned at 13:55. The road between Halipur and the Kolar turn is
   restricted to light vehicles only. They did not say when it will reopen. Our driver
   confirmed the barricade at the Halipur junction with his own eyes around 14:05.

2. Convoy B does not have the fuel margin for the full detour. Going via Route 7 adds about
   40 minutes on rough road and there is no fuel point between the turn and Kolar on that
   stretch. We can carry 200 extra litres on the second truck if that is approved.

If the convoy does not clear by 18:30 the Kolar hospital starts diverting its own intake
traffic on that corridor, and we will be queued behind them.

Please advise. We are holding until we hear back.
"""

WEATHER_PDF_TITLE = "DISTRICT WEATHER & CIVIL WORKS BULLETIN"
WEATHER_PDF_LINES = [
    "Issued 13:30 IST by District Meteorological Centre, in consultation with",
    "the District Public Works Department.",
    "",
    "1. Rainfall forecast, 15:00 to 21:00 today",
    "   The Narmada catchment is expected to receive 68 mm of rain in this window,",
    "   with intensity peaking between 17:00 and 19:00. This is the second such",
    "   window this week. The 24-hour total since Tuesday is already 94 mm.",
    "",
    "2. Bridge and culvert status",
    "   The culvert at Halipur, chainage 12.4 km on the Narmada corridor, is rated for",
    "   a design flow of 3.2 cumecs. Observed inflow yesterday was 2.9 cumecs and is",
    "   trending upward. PWD has recorded surface cracking on the deck and standing",
    "   water at the second pier in the inspection of 11 September. The structure has",
    "   not been certified since 2022.",
    "",
    "3. Standing advice",
    "   PWD advises that vehicles over 7 tonnes should not use the Halipur culvert",
    "   crossing during or after rainfall until the deck has been re-inspected.",
    "",
    "4. Route 7 condition",
    "   Route 7 (Halipur - Rewa Bypass - Kolar) is open to all vehicle classes. The",
    "   surface is uneven for approximately 6 km and travel speed is restricted to",
    "   25 kmph. No fuel point exists between Halipur and Kolar on Route 7.",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_bridge_photo(path: Path) -> None:
    w, h = 900, 620
    img = Image.new("RGB", (w, h), (108, 116, 122))
    d = ImageDraw.Draw(img)

    horizon = 210
    for y in range(horizon, h):
        t = (y - horizon) / (h - horizon)
        d.line([(0, y), (w, y)], fill=(int(48 + 30 * t), int(54 + 26 * t), int(50 + 22 * t)))

    deck_y = 300
    d.rectangle([0, deck_y, w, deck_y + 54], fill=(96, 97, 93))
    d.rectangle([0, deck_y, w, deck_y + 8], fill=(120, 121, 116))

    for x in range(20, w, 150):
        d.rectangle([x, deck_y - 78, x + 8, deck_y], fill=(84, 86, 82))

    for x in (200, 470, 740):
        d.rectangle([x, deck_y + 54, x + 46, h - 90], fill=(78, 79, 75))
        d.rectangle([x - 14, deck_y + 40, x + 60, deck_y + 58], fill=(88, 89, 85))

    water_y = h - 90
    d.rectangle([0, water_y, w, h], fill=(58, 74, 78))
    for i in range(90):
        x = random.randint(0, w)
        y = random.randint(water_y + 4, h - 6)
        d.ellipse([x, y, x + random.randint(8, 34), y + 3], fill=(72, 90, 95))

    cracks = [
        [(330, deck_y + 4), (372, deck_y + 20), (344, deck_y + 34), (398, deck_y + 50)],
        [(560, deck_y + 2), (596, deck_y + 24), (572, deck_y + 44)],
        [(120, deck_y + 10), (150, deck_y + 26), (138, deck_y + 48)],
    ]
    for path_points in cracks:
        d.line(path_points, fill=(46, 44, 42), width=4)

    d.polygon([(470, deck_y + 54), (516, deck_y + 54), (560, h - 120), (420, h - 120)],
              fill=(64, 80, 84))
    d.ellipse([440, deck_y + 150, 540, deck_y + 250], fill=(58, 76, 82))

    sky = Image.new("RGBA", (w, horizon), (150, 156, 160, 255))
    for _ in range(400):
        x = random.randrange(w)
        y = random.randrange(horizon)
        sky.putpixel((x, y), (162, 168, 172, 255))
    img.paste(sky, (0, 0))

    label_font = _font(26)
    d.rectangle([18, 18, 250, 58], fill=(20, 20, 22))
    d.text((28, 26), "IMG_4471  14:07", font=label_font, fill=(226, 226, 226))

    img = img.rotate(-3.2, expand=False, fillcolor=(96, 100, 104))
    img = img.filter(ImageFilter.GaussianBlur(radius=2.1))
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=3))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=31)
    path.write_bytes(buf.getvalue())


def make_flood_photo(path: Path) -> None:
    w, h = 780, 560
    img = Image.new("RGB", (w, h), (128, 130, 126))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 250], fill=(138, 132, 120))
    for i in range(4):
        x = 60 + i * 190
        d.rectangle([x, 70 + (i % 2) * 40, x + 130, 300], fill=(112, 104, 92))
        for wx in range(x + 20, x + 120, 30):
            for wy in range(100 + (i % 2) * 40, 290, 32):
                d.rectangle([wx, wy, wx + 16, wy + 20], fill=(78, 72, 64))
    d.rectangle([0, 300, w, h], fill=(74, 84, 80))
    for i in range(120):
        x = random.randint(0, w)
        y = random.randint(305, h - 4)
        d.ellipse([x, y, x + random.randint(10, 46), y + 4], fill=(90, 102, 98))
    d.polygon([(300, 300), (470, 300), (620, h), (170, h)], fill=(82, 94, 90))
    d.ellipse([250, 330, 420, 430], fill=(70, 82, 80))
    for cx, cy, r in ((200, 120, 26), (330, 180, 18), (470, 130, 22), (600, 210, 15)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(196, 192, 180))
    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=34)
    path.write_bytes(buf.getvalue())


def make_pdf(path: Path, title: str, lines: list[str]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 25 * mm, title)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, height - 32 * mm, "Ref: DCB/NMD/2026/0914   Page 1 of 1")
    c.line(20 * mm, height - 34 * mm, width - 20 * mm, height - 34 * mm)

    c.setFont("Courier", 9.5)
    y = height - 44 * mm
    for line in lines:
        if line.strip():
            for i in range(0, len(line), 96):
                c.drawString(20 * mm, y, line[i : i + 96])
                y -= 12
        y -= 3
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, 18 * mm, "Generated for hackathon demo. Not an official bulletin.")
    c.showPage()
    c.save()


SCENARIO_1 = (
    "Convoy B must reach Kolar field hospital with medical stores before tomorrow morning. "
    "Decide what happens to Convoy B right now, and say what you need from whom."
)

SCENARIO_2 = (
    "A district warehouse has reported water ingress damaging 40 crates of vaccine stock. "
    "Decide the response and name what must happen in the next 6 hours."
)


def build() -> None:
    random.seed(7)
    s1 = OUT / "scenario_1_convoy"
    s2 = OUT / "scenario_2_warehouse"
    s1.mkdir(parents=True, exist_ok=True)
    s2.mkdir(parents=True, exist_ok=True)

    (s1 / "dispatch_log_7kilara.txt").write_text(DISPATCH)
    make_bridge_photo(s1 / "IMG_4471_bridge.jpg")
    make_pdf(s1 / "bulletin_narmada_rainfall.pdf", WEATHER_PDF_TITLE, WEATHER_PDF_LINES)

    (s2 / "warehouse_report.txt").write_text(
        "WAREHOUSE INCIDENT REPORT - BLOCK C, CENTRAL STORE\n"
        "Reported by: K. Iyer, Store Supervisor, 09:40\n\n"
        "Water entered Block C from the roof vent at about 04:10 during heavy rain. We found\n"
        "standing water about 6 cm deep across roughly 60 percent of the floor when staff\n"
        "arrived. Cold-chain pallets nearest the vent are affected.\n\n"
        "We have moved 22 pallets to the dry bay. 18 pallets are still in place. The generator\n"
        "room is not affected but the main supply has tripped on leakage detection.\n\n"
        "The vaccine stock in the 18 exposed pallets is ours to save. The health department\n"
        "closed office at 17:00 and their officer could not be reached on the mobile.\n"
    )
    make_flood_photo(s2 / "IMG_4488_block_c.jpg")
    make_pdf(
        s2 / "coldchain_sop.pdf",
        "COLD CHAIN STANDARD OPERATING PROCEDURE",
        [
            "Section 4.2 - Exposure and quarantine",
            "Any vaccine pallet exposed to standing water, or to any excursion above 8 C for",
            "more than 60 minutes, must be quarantined and temperature-logged. Quarantined",
            "stock may not be released to service without written sign-off from the district",
            "cold chain officer.",
            "",
            "Section 4.5 - Outage handling",
            "During a mains failure the store must log ambient and pallet temperatures at",
            "15-minute intervals and notify the district cold chain officer within 30 minutes",
            "of confirming the outage.",
            "",
            "Section 4.7 - Reachability",
            "The cold chain officer is considered unreachable only after two contact attempts",
            "at 20-minute intervals. In that case the duty pharmacist may authorise transfer",
            "to an approved alternate store, with retrospective sign-off within 24 hours.",
        ],
    )

    print(f"dataset written to {OUT}")
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(OUT)}  ({p.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    sys.exit(build())