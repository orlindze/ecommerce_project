"""Генерация PDF-счёта (reportlab). Реквизиты компании берутся из settings.COMPANY."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
ACCENT = colors.HexColor('#7c4dff')
GREEN = colors.HexColor('#00b386')


def _register_fonts():
    if 'DejaVu' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('DejaVu', str(FONT_DIR / 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', str(FONT_DIR / 'DejaVuSans-Bold.ttf')))


class Logo(Flowable):
    """Векторный логотип компании (круглый диск + название)."""
    width, height = 60 * mm, 14 * mm

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(ACCENT)
        c.circle(7 * mm, 7 * mm, 6.5 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.circle(7 * mm, 7 * mm, 2.2 * mm, stroke=0, fill=1)
        c.setFillColor(ACCENT)
        c.circle(7 * mm, 7 * mm, 0.8 * mm, stroke=0, fill=1)
        c.setFont('DejaVu-Bold', 16)
        c.setFillColor(colors.black)
        c.drawString(17 * mm, 4.5 * mm, 'Disc')
        c.setFillColor(GREEN)
        c.drawString(17 * mm + c.stringWidth('Disc', 'DejaVu-Bold', 16), 4.5 * mm, 'Zone')


def _money(value):
    return f'{value:,.2f} ₴'.replace(',', ' ')


def build_invoice_pdf(order):
    """Возвращает bytes с PDF-счётом для заказа."""
    _register_fonts()
    company = settings.COMPANY
    base = ParagraphStyle('base', fontName='DejaVu', fontSize=9, leading=12)
    bold = ParagraphStyle('bold', parent=base, fontName='DejaVu-Bold')
    title = ParagraphStyle('title', parent=base, fontName='DejaVu-Bold', fontSize=15, leading=19, spaceAfter=4)
    right = ParagraphStyle('right', parent=base, alignment=2)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f'Рахунок №{order.pk}', author=company['name'])
    story = []

    requisites = [
        Paragraph(f"<b>{company['name']}</b>", base),
        Paragraph(f"Адреса: {company['address']}", base),
        Paragraph(f"{company['tax_id_label']}: {company['tax_id']}", base),
        Paragraph(f"IBAN: {company['iban']}", base),
        Paragraph(f"Банк: {company['bank']}", base),
        Paragraph(f"{company['email']} · {company['phone']}", base),
    ]
    header = Table([[Logo(), requisites]], colWidths=[70 * mm, 104 * mm])
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story += [header, Spacer(1, 8 * mm)]

    story.append(Paragraph(f'Рахунок №{order.pk} від {order.created_at:%d.%m.%Y}', title))
    story.append(Paragraph(f'Статус замовлення: {order.get_status_display()}', base))
    story.append(Spacer(1, 4 * mm))

    addr = getattr(order, 'shipping_address', None)
    buyer = [Paragraph('<b>Покупець / доставка</b>', base)]
    if addr:
        buyer += [Paragraph(addr.full_name, base),
                  Paragraph(f'Тел.: {addr.phone}', base),
                  Paragraph(f'{addr.country}, {addr.city}, {addr.address} {addr.postal_code}'.strip(), base)]
    buyer.append(Paragraph(f'Email: {order.email}', base))
    story += [*buyer, Spacer(1, 6 * mm)]

    rows = [[Paragraph(h, bold) for h in ('№', 'Товар', 'Ціна', 'К-сть', 'Сума')]]
    for i, item in enumerate(order.items.all(), 1):
        rows.append([str(i), Paragraph(item.product_name, base), _money(item.price),
                     str(item.quantity), _money(item.get_cost())])
    table = Table(rows, colWidths=[10 * mm, 82 * mm, 28 * mm, 20 * mm, 34 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ece8ff')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c9c9d9')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story += [table, Spacer(1, 5 * mm)]

    totals = [['Сума:', _money(order.get_subtotal())]]
    if order.discount_percent:
        code = order.coupon.code if order.coupon else ''
        totals.append([f'Знижка {order.discount_percent}% {code}:', '− ' + _money(order.get_discount())])
    totals.append(['Разом до сплати:', _money(order.get_total())])
    tt = Table(totals, colWidths=[120 * mm, 54 * mm], hAlign='RIGHT')
    tt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'), ('FONTNAME', (0, -1), (-1, -1), 'DejaVu-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, ACCENT),
    ]))
    story += [tt, Spacer(1, 12 * mm),
              Paragraph('Дякуємо за покупку в DiscZone!', right)]
    doc.build(story)
    return buf.getvalue()