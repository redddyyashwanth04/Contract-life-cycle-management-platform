"""Generate the Event Management Services Agreement sample PDF.

Run from the project root with any Python that has reportlab installed:
    python scripts/generate_sample_contract.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sample_contracts" / "event-management-agreement.pdf"

INK = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#7a5c1e")
FAINT = colors.HexColor("#666666")


def build() -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleX", parent=styles["Title"], fontName="Times-Bold", fontSize=17,
        leading=21, textColor=INK, spaceAfter=4, alignment=TA_CENTER,
    )
    subtitle = ParagraphStyle(
        "SubtitleX", parent=styles["Normal"], fontName="Times-Italic", fontSize=10,
        leading=13, textColor=FAINT, alignment=TA_CENTER, spaceAfter=10,
    )
    heading = ParagraphStyle(
        "HeadingX", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
        leading=13, textColor=ACCENT, spaceBefore=11, spaceAfter=3,
    )
    body = ParagraphStyle(
        "BodyX", parent=styles["Normal"], fontName="Times-Roman", fontSize=10,
        leading=14, textColor=INK, spaceAfter=4,
    )
    party = ParagraphStyle(
        "PartyX", parent=body, spaceBefore=6, spaceAfter=2,
    )

    def section(num: str, name: str, text: str) -> list:
        return [
            Paragraph(f"{num}. {name}", heading),
            Paragraph(text, body),
        ]

    story: list = [
        Paragraph("EVENT MANAGEMENT SERVICES AGREEMENT", title),
        Paragraph("BrightStage Events - Event Planning and Management", subtitle),
        Paragraph(
            "This Event Management Services Agreement (this &quot;Agreement&quot;) is entered "
            "into as of the date of last signature below by and between <b>BrightStage Events, "
            "LLC</b> (&quot;Vendor&quot;) and <b>Nimbus Labs</b> (&quot;Client&quot;), "
            "collectively the &quot;Parties&quot;.",
            party,
        ),
        *section(
            "1", "SERVICES",
            "Vendor shall plan, coordinate and manage Client's product launch event scheduled "
            "for March 14, 2026 at the Harborview Ballroom, for up to 250 guests. Services "
            "include venue liaison, catering, audiovisual production, staffing, guest "
            "registration, run-of-show management and day-of coordination.",
        ),
        *section(
            "2", "FEES AND PAYMENT",
            "Client shall pay Vendor a total fee of $12,500. A non-refundable deposit of 50% "
            "is due upon execution of this Agreement, and the remaining balance is due seven "
            "(7) days before the event date. Fees not paid when due accrue interest at 1.5% "
            "per month.",
        ),
        *section(
            "3", "CANCELLATION AND POSTPONEMENT",
            "If Client cancels the event within thirty (30) days of the event date, Client "
            "remains liable for 100% of the total fee. Vendor may cancel this Agreement for "
            "convenience upon seven (7) days' written notice, without liability beyond a "
            "refund of the deposit.",
        ),
        *section(
            "4", "LIMITATION OF LIABILITY",
            "TO THE MAXIMUM EXTENT PERMITTED BY LAW, VENDOR'S AGGREGATE LIABILITY ARISING OUT "
            "OF OR RELATED TO THIS AGREEMENT IS UNCAPPED, AND VENDOR SHALL NOT BE LIABLE FOR "
            "ANY LOSS OF PROFITS, DATA OR GOODWILL, OR FOR ANY INDIRECT, INCIDENTAL, SPECIAL "
            "OR CONSEQUENTIAL DAMAGES OF ANY KIND.",
        ),
        *section(
            "5", "INDEMNIFICATION",
            "Client shall indemnify, defend and hold harmless Vendor against any and all "
            "third-party claims, losses and damages arising out of or related to the event, "
            "without limitation, including claims by guests, contractors or venue personnel.",
        ),
        *section(
            "6", "INTELLECTUAL PROPERTY",
            "Client grants Vendor a perpetual, irrevocable, royalty-free, worldwide license to "
            "use, reproduce and display all event recordings, photographs and Client branding "
            "for Vendor's portfolio and marketing purposes.",
        ),
        *section(
            "7", "CONFIDENTIALITY",
            "Each party shall protect the other party's confidential information using "
            "reasonable care and shall use it solely to perform under this Agreement. The "
            "obligations of this Section survive termination for one (1) year.",
        ),
        *section(
            "8", "DATA PROTECTION",
            "Client is solely responsible for the security of guest lists and personal data "
            "collected at the event and for compliance with applicable data protection laws. "
            "Vendor assumes no responsibility for the security, integrity or confidentiality "
            "of such data.",
        ),
        *section(
            "9", "FORCE MAJEURE",
            "Neither party shall be liable for delays or failure to perform caused by events "
            "beyond its reasonable control, including weather, strikes, illness or government "
            "action. Vendor may reschedule the event without refund in such circumstances.",
        ),
        *section(
            "10", "INSURANCE",
            "Vendor shall maintain commercial general liability insurance of at least "
            "$1,000,000 per occurrence and shall provide a certificate of insurance upon "
            "Client's written request.",
        ),
        *section(
            "11", "GOVERNING LAW",
            "This Agreement shall be governed by the laws of the State of Nevada, and the "
            "Parties consent to the exclusive jurisdiction of the courts located in Clark "
            "County, Nevada.",
        ),
        Spacer(1, 18),
        Paragraph("IN WITNESS WHEREOF, the Parties have executed this Agreement.", body),
        Spacer(1, 26),
        Table(
            [
                [
                    Paragraph(
                        "FOR NIMBUS LABS (Client)<br/><br/><br/>____________________________<br/>"
                        "Name: ____________________<br/>Date: ____________________",
                        body,
                    ),
                    Paragraph(
                        "FOR BRIGHTSTAGE EVENTS, LLC (Vendor)<br/><br/><br/>"
                        "____________________________<br/>Name: ____________________<br/>"
                        "Date: ____________________",
                        body,
                    ),
                ]
            ],
            colWidths=[3.05 * inch, 3.05 * inch],
        ),
    ]
    table = story[-1]
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 1), (-1, 1), 24),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ]
        )
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Times-Roman", 8.5)
        canvas.setFillColor(FAINT)
        canvas.drawString(0.75 * inch, 0.5 * inch, "Event Management Services Agreement - Confidential")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.9 * inch,
        title="Event Management Services Agreement",
        author="BrightStage Events",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print("Wrote sample PDF to", str(OUT).encode("ascii", "backslashreplace").decode())


if __name__ == "__main__":
    build()
