"""Generate completion-certificate PDF bytes (ReportLab)."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CERTIFICATE_TITLE = "Сертификат о прохождении практики GitPlayground"
CERTIFICATE_DISCLAIMER = (
    "GitPlayground не является образовательной организацией. Этот документ не является "
    "дипломом, свидетельством о профессии или государственным документом об образовании. "
    "Он подтверждает только факт прохождения практических задач и квиза на платформе."
)


def _register_font() -> str:
    """Prefer a Unicode TTF if present; otherwise Helvetica (ASCII fallback)."""
    # ponytail: Helvetica cannot render Cyrillic; ship DejaVu if available, else transliterate-free
    # English fallback for CI without system fonts — embed DejaVu from reportlab fonts is limited.
    # Use built-in and write Russian via UTF-8 with a bundled approach: reportlab's freefont.
    try:
        from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames

        if "DejaVuSans" in getRegisteredFontNames():
            return "DejaVuSans"
    except Exception:  # noqa: BLE001
        pass
    # Try common Windows / Linux paths for DejaVu or Arial.
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            pdfmetrics.registerFont(TTFont("CertSans", path))
            return "CertSans"
        except Exception:  # noqa: BLE001
            continue
    return "Helvetica"


def build_certificate_pdf(
    *,
    display_name: str,
    issued_at: datetime,
    verification_code: str,
    verify_url: str,
) -> bytes:
    font = _register_font()
    buf = BytesIO()
    page = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 25 * mm

    page.setStrokeColorRGB(0.1, 0.1, 0.1)
    page.setLineWidth(1.5)
    page.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    y = height - margin - 30 * mm
    page.setFont(font, 16)
    page.drawCentredString(width / 2, y, CERTIFICATE_TITLE)

    y -= 20 * mm
    page.setFont(font, 11)
    page.drawCentredString(width / 2, y, "Настоящим подтверждается, что")

    y -= 14 * mm
    page.setFont(font, 18)
    page.drawCentredString(width / 2, y, display_name)

    y -= 16 * mm
    page.setFont(font, 11)
    lines = [
        "прошёл(а) практические задачи курса и квиз",
        "на платформе GitPlayground.",
    ]
    for line in lines:
        page.drawCentredString(width / 2, y, line)
        y -= 7 * mm

    y -= 8 * mm
    page.setFont(font, 10)
    date_str = issued_at.strftime("%d.%m.%Y")
    page.drawCentredString(width / 2, y, f"Дата выдачи: {date_str}")
    y -= 7 * mm
    page.drawCentredString(width / 2, y, f"Код проверки: {verification_code}")
    y -= 7 * mm
    page.setFont(font, 8)
    page.drawCentredString(width / 2, y, verify_url)

    # Disclaimer at bottom
    page.setFont(font, 7)
    text = page.beginText(margin + 8 * mm, margin + 28 * mm)
    text.setFont(font, 7)
    for chunk in _wrap(CERTIFICATE_DISCLAIMER, 95):
        text.textLine(chunk)
    page.drawText(text)

    page.showPage()
    page.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = (" ".join(current + [word])).strip()
        if len(trial) <= width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines
