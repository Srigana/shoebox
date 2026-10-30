"""Render the three demo receipts in web/public/samples/.

They are fictional businesses, and every receipt is printed with
"SAMPLE RECEIPT - NOT A REAL PURCHASE" so it can't pass as a real record.
Run from the repo root:  python scripts/make_samples.py
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "samples"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NOTICE = "SAMPLE RECEIPT - NOT A REAL PURCHASE"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def thermal(lines: list[tuple[str, str]], width_chars: int = 34) -> Image.Image:
    """lines: (style, text). Styles: c=centered, cb=centered bold, l=left, r=two-column 'label|amount', hr=rule, sp=space."""
    f, fb = font(MONO, 22), font(MONO_BOLD, 26)
    cw = f.getbbox("M")[2]
    pad, lh = 34, 32
    w = pad * 2 + cw * width_chars
    h = pad * 2 + lh * len(lines) + 10
    img = Image.new("RGB", (w, h), (250, 249, 244))
    d = ImageDraw.Draw(img)
    ink = (38, 38, 42)
    y = pad
    for style, text in lines:
        if style == "hr":
            d.text((pad, y), "-" * width_chars, font=f, fill=ink)
        elif style in ("c", "cb"):
            ft = fb if style == "cb" else f
            tw = d.textlength(text, font=ft)
            d.text(((w - tw) / 2, y), text, font=ft, fill=ink)
        elif style == "r":
            label, amt = text.split("|")
            d.text((pad, y), label, font=f, fill=ink)
            d.text((w - pad - d.textlength(amt, font=f), y), amt, font=f, fill=ink)
        elif style == "rb":
            label, amt = text.split("|")
            d.text((pad, y), label, font=fb, fill=ink)
            d.text((w - pad - d.textlength(amt, font=fb), y), amt, font=fb, fill=ink)
        elif style == "l":
            d.text((pad, y), text, font=f, fill=ink)
        y += lh
    return img


def photo_look(img: Image.Image, seed: int, angle: float) -> Image.Image:
    """Place the receipt on a desk-gray background with a slight tilt and soft blur, like a phone photo."""
    rnd = random.Random(seed)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    rot = img.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True)
    bg = Image.new("RGB", (rot.width + 120, rot.height + 120), (118, 122, 128))
    px = bg.load()
    for _ in range(bg.width * bg.height // 6):
        x, y = rnd.randrange(bg.width), rnd.randrange(bg.height)
        v = rnd.randint(-10, 10)
        r, g, b = px[x, y]
        px[x, y] = (r + v, g + v, b + v)
    shadow = Image.new("RGBA", rot.size, (0, 0, 0, 90))
    bg.paste(shadow, (66, 70), rot)
    bg.paste(rot, (60, 60), rot)
    return bg


def coffee() -> Image.Image:
    lines = [
        ("cb", "CORNER GRIND COFFEE"), ("c", "212 Harbor Ave"), ("c", "Portland, ME 04101"), ("c", "(207) 555-0142"),
        ("sp", ""), ("l", "10/14/2026            08:42 AM"), ("l", "Order #4471       Server: Dana"), ("hr", ""),
        ("r", "2 Oat Milk Latte 12oz|11.50"), ("r", "1 Almond Croissant|4.25"), ("hr", ""),
        ("r", "Subtotal|15.75"), ("r", "Sales Tax 8.0%|1.26"), ("r", "Tip|3.15"), ("hr", ""),
        ("rb", "TOTAL|$20.16"), ("sp", ""), ("r", "VISA ****4242|20.16"), ("l", "Auth 0391A2"),
        ("sp", ""), ("c", "Thank you!"), ("sp", ""), ("c", NOTICE),
    ]
    return photo_look(thermal(lines), seed=1, angle=-2.2)


def office() -> Image.Image:
    lines = [
        ("cb", "LANTERN OFFICE SUPPLY"), ("c", "880 Mill Street, Suite 3"), ("c", "Burlington, VT 05401"),
        ("sp", ""), ("l", "Date: 10/09/2026   Time: 14:17"), ("l", "Register 2   Trans 18823"), ("hr", ""),
        ("l", "Copy Paper 8.5x11, 5 Ream Case"), ("r", "  1 @ 42.99|42.99"),
        ("l", "Gel Pens, Black, 12 Pack"), ("r", "  1 @ 11.49|11.49"),
        ("l", "Laser Toner Cartridge, Black"), ("r", "  1 @ 64.99|64.99"), ("hr", ""),
        ("r", "Subtotal|119.47"), ("r", "Sales Tax 6.25%|7.47"), ("hr", ""),
        ("rb", "TOTAL|$126.94"), ("sp", ""), ("r", "MASTERCARD ****8810|126.94"),
        ("sp", ""), ("c", "Keep receipt for returns"), ("c", "within 30 days."), ("sp", ""), ("c", NOTICE),
    ]
    return photo_look(thermal(lines, 34), seed=2, angle=1.6)


def invoice() -> Image.Image:
    W, H = 1275, 1650  # US Letter at 150 dpi
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    ink, soft, rule = (24, 30, 44), (96, 104, 120), (210, 214, 222)
    L, R = 110, W - 110
    d.text((L, 120), "Fieldnote Software, Inc.", font=font(SANS_BOLD, 40), fill=ink)
    for i, t in enumerate(["55 Alder Lane", "Madison, WI 53703", "billing@fieldnote.example"]):
        d.text((L, 182 + i * 32), t, font=font(SANS, 24), fill=soft)
    d.text((R - d.textlength("INVOICE", font=font(SANS_BOLD, 44)), 120), "INVOICE", font=font(SANS_BOLD, 44), fill=ink)
    meta = [("Invoice number", "FN-20481"), ("Invoice date", "October 1, 2026"), ("Status", "Paid")]
    for i, (k, v) in enumerate(meta):
        y = 190 + i * 34
        d.text((R - 420, y), k, font=font(SANS, 24), fill=soft)
        d.text((R - d.textlength(v, font=font(SANS_BOLD, 24)), y), v, font=font(SANS_BOLD, 24), fill=ink)
    d.text((L, 340), "Bill to", font=font(SANS, 24), fill=soft)
    d.text((L, 374), "Sample Customer", font=font(SANS_BOLD, 26), fill=ink)
    y = 480
    d.line([(L, y), (R, y)], fill=ink, width=2)
    d.text((L, y + 18), "Description", font=font(SANS_BOLD, 24), fill=ink)
    for x_right, t in [(R - 330, "Qty"), (R - 170, "Price"), (R, "Amount")]:
        d.text((x_right - d.textlength(t, font=font(SANS_BOLD, 24)), y + 18), t, font=font(SANS_BOLD, 24), fill=ink)
    d.line([(L, y + 64), (R, y + 64)], fill=rule, width=2)
    row = y + 84
    d.text((L, row), "Fieldnote Pro, monthly plan", font=font(SANS, 24), fill=ink)
    d.text((L, row + 34), "Oct 1, 2026 to Oct 31, 2026", font=font(SANS, 21), fill=soft)
    for x_right, t in [(R - 330, "1"), (R - 170, "$24.00"), (R, "$24.00")]:
        d.text((x_right - d.textlength(t, font=font(SANS, 24)), row), t, font=font(SANS, 24), fill=ink)
    d.line([(L, row + 90), (R, row + 90)], fill=rule, width=2)
    ty = row + 120
    for k, v, bold in [("Subtotal", "$24.00", False), ("Tax", "$0.00", False), ("Total", "$24.00", True), ("Amount paid", "$24.00", False)]:
        ft = font(SANS_BOLD if bold else SANS, 26 if bold else 24)
        d.text((R - 420, ty), k, font=ft, fill=ink)
        d.text((R - d.textlength(v, font=ft), ty), v, font=ft, fill=ink)
        ty += 44
    d.text((L, ty + 40), "Paid with Visa ending in 4242 on October 1, 2026.", font=font(SANS, 22), fill=soft)
    nt = font(SANS_BOLD, 22)
    d.text(((W - d.textlength(NOTICE, font=nt)) / 2, H - 120), NOTICE, font=nt, fill=soft)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    coffee().save(OUT / "corner-grind-coffee.jpg", quality=88)
    office().save(OUT / "lantern-office-supply.jpg", quality=88)
    invoice().save(OUT / "fieldnote-invoice.pdf", resolution=150)
    for p in sorted(OUT.iterdir()):
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
