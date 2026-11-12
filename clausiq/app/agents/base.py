"""Shared helpers for clause segmentation and type inference."""
import re

CLAUSE_TYPES = [
    "Indemnification",
    "Liability Cap",
    "Termination",
    "Confidentiality",
    "IP Ownership",
    "Data Protection",
    "Payment Terms",
    "Governing Law",
    "Warranty",
    "Insurance",
    "Force Majeure",
    "Entire Agreement",
    "Severability",
    "Notice",
    "Dispute Resolution",
    "Renewal",
    "Non-Solicitation",
    "Assignment",
    "Compliance",
    "General",
]

TYPE_KEYWORDS: dict[str, list[str]] = {
    "Indemnification": ["indemnif", "hold harmless", "defend against"],
    "Liability Cap": ["limitation of liability", "aggregate liability", "liability of either party", "shall not be liable", "total liability", "liable for any"],
    "Termination": ["termination", "terminate", "cancellation", "cancel"],
    "Confidentiality": ["confidential", "non-disclosure", "trade secret"],
    "IP Ownership": ["intellectual property", "ownership", "work product", "license", "proprietary rights"],
    "Data Protection": ["customer data", "personal data", "personal information", "privacy", "gdpr", "data protection", "security of"],
    "Payment Terms": ["fees", "payment", "invoice", "payable", "compensation"],
    "Governing Law": ["governing law", "jurisdiction", "laws of the state"],
    "Warranty": ["warrant", "as is", "as-is", "representation"],
    "Insurance": ["insurance", "policy of", "coverage"],
    "Force Majeure": ["force majeure", "act of god", "beyond reasonable control"],
    "Entire Agreement": ["entire agreement", "integration", "supersedes all prior"],
    "Severability": ["severab"],
    "Notice": ["notices shall", "notice shall be", "written notice"],
    "Dispute Resolution": ["dispute", "arbitration", "mediation"],
    "Renewal": ["renew", "renewal", "automatic extension"],
    "Non-Solicitation": ["solicit", "non-solicitation", "hire any employee"],
    "Assignment": ["assign", "assignment", "successors"],
    "Compliance": ["compliance", "applicable law", "regulatory"],
}

HEADING_RE = re.compile(
    r"^\s*("
    r"(?:ARTICLE\s+[IVXLCDM]+)"
    r"|(?:Section\s+\d+(?:\.\d+)*)"
    r"|(?:\d+(?:\.\d+)*\.?)"
    r")\s*[-–—:.)]?\s*(.*)$",
    re.IGNORECASE,
)


def infer_clause_type(text: str) -> str:
    lowered = text.lower()
    best_type, best_score = "General", 0
    for clause_type, keywords in TYPE_KEYWORDS.items():
        score = sum(lowered.count(kw) for kw in keywords)
        # Require at least two keyword hits so stray words in footers or
        # preamble text cannot hijack the classification.
        if score >= 2 and score > best_score:
            best_type, best_score = clause_type, score
    return best_type


def split_sections(text: str) -> list[dict]:
    """Split contract text into headed sections; falls back to paragraph
    chunking when the document has no recognizable headings."""
    lines = text.split("\n")
    sections: list[dict] = []
    current: dict | None = None
    heading_count = 0

    for line in lines:
        stripped = line.strip()
        match = HEADING_RE.match(stripped)
        is_all_caps = bool(re.fullmatch(r"[A-Z][A-Z0-9 ,&'/\-]{4,60}", stripped))
        is_heading = bool(match) or is_all_caps
        if is_heading and stripped and len(stripped) <= 90:
            if match:
                heading = match.group(1).strip()
                title = match.group(2).strip() or heading
            else:
                heading = stripped
                title = stripped
            heading_count += 1
            if current:
                sections.append(current)
            current = {"heading": heading, "title": title, "body": []}
        elif current is not None:
            if stripped:
                current["body"].append(stripped)
        elif stripped:
            # Preamble text before any heading.
            current = {"heading": "", "title": "Preamble", "body": [stripped]}
    if current:
        sections.append(current)

    if heading_count >= 2:
        out = []
        for section in sections:
            body = " ".join(section["body"]).strip()
            if body:
                out.append(
                    {
                        "title": section["title"][:120],
                        "text": body,
                        "source_ref": section["heading"] or section["title"],
                    }
                )
        if out:
            return out

    # Paragraph-chunk fallback.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out, buffer, buf_len = [], [], 0
    for block in blocks:
        buffer.append(block)
        buf_len += len(block)
        if buf_len >= 350:
            merged = " ".join(buffer)
            out.append(
                {
                    "title": (buffer[0].split(".")[0] + ".")[:120],
                    "text": merged,
                    "source_ref": f"Paragraph {len(out) + 1}",
                }
            )
            buffer, buf_len = [], 0
    if buffer:
        merged = " ".join(buffer)
        out.append(
            {
                "title": (buffer[0].split(".")[0] + ".")[:120],
                "text": merged,
                "source_ref": f"Paragraph {len(out) + 1}",
            }
        )
    return out
