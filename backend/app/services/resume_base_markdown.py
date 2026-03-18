"""Resume base dict → markdown for WeasyPrint preview (same pipeline as job PDFs)."""
from __future__ import annotations

from typing import Any


def _esc_line(s: str) -> str:
    s = (s or "").strip()
    return s.replace("\n", " ")


def resume_base_to_markdown(data: dict[str, Any]) -> str:
    """Build markdown from resume_base JSON matching ResumePage / DB shape."""
    lines: list[str] = []
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    name = _esc_line(str(contact.get("name") or ""))
    if name:
        lines.append(f"# {name}")

    meta_parts: list[str] = []
    email = str(contact.get("email") or "").strip()
    if email:
        meta_parts.append(f"[{email}](mailto:{email})")
    phone = str(contact.get("phone") or "").strip()
    if phone:
        meta_parts.append(phone)
    linkedin = str(contact.get("linkedin") or "").strip()
    if linkedin:
        meta_parts.append(f"[LinkedIn]({linkedin})")
    github = str(contact.get("github") or "").strip()
    if github:
        meta_parts.append(f"[GitHub]({github})")
    website = str(contact.get("website") or "").strip()
    if website:
        meta_parts.append(f"[Website]({website})")
    if meta_parts:
        lines.append(" · ".join(meta_parts))

    summary = str(data.get("summary") or "").strip()
    if summary:
        lines.append("")
        lines.append(summary)

    highlights = data.get("highlights_of_qualifications") or data.get("highlights") or []
    if isinstance(highlights, list) and highlights:
        lines.append("")
        lines.append("## Highlights")
        for h in highlights:
            t = _esc_line(str(h))
            if t:
                lines.append(f"- {t}")

    tech = data.get("technical_snapshot") if isinstance(data.get("technical_snapshot"), dict) else {}
    if tech:
        lines.append("")
        lines.append("## Technical snapshot")
        for key, val in tech.items():
            label = str(key).replace("_", " ").strip().title() or str(key)
            if isinstance(val, list) and val:
                items = ", ".join(_esc_line(str(x)) for x in val if x)
                if items:
                    lines.append(f"**{label}:** {items}")
            elif val:
                lines.append(f"**{label}:** {_esc_line(str(val))}")

    experience = data.get("experience") if isinstance(data.get("experience"), list) else []
    if experience:
        lines.append("")
        lines.append("## Experience")
        for exp in experience:
            if not isinstance(exp, dict):
                continue
            role = _esc_line(str(exp.get("role") or ""))
            company = _esc_line(str(exp.get("company") or ""))
            dates = _esc_line(str(exp.get("dates") or ""))
            head = " — ".join(p for p in (role, company) if p) or "Role"
            lines.append("")
            lines.append(f"### {head}")
            if dates:
                lines.append(f"*{dates}*")
            for b in exp.get("bullets") or []:
                bt = _esc_line(str(b))
                if bt:
                    lines.append(f"- {bt}")

    education = data.get("education") if isinstance(data.get("education"), list) else []
    if education:
        lines.append("")
        lines.append("## Education")
        for ed in education:
            if not isinstance(ed, dict):
                continue
            school = _esc_line(str(ed.get("school") or ""))
            degree = _esc_line(str(ed.get("degree") or ""))
            dates = _esc_line(str(ed.get("dates") or ""))
            parts = [p for p in (degree, school) if p]
            line = " — ".join(parts) if parts else "Education"
            if dates:
                line = f"{line} *({dates})*"
            lines.append(f"- {line}")

    certs = data.get("certifications") if isinstance(data.get("certifications"), list) else []
    if certs:
        lines.append("")
        lines.append("## Certifications")
        for c in certs:
            t = _esc_line(str(c))
            if t:
                lines.append(f"- {t}")

    out = "\n".join(lines).strip()
    if not out:
        return (
            "# Resume base\n\n"
            "*Your resume base is empty. Add contact, summary, and experience on the "
            "**Resume base** page — this preview updates automatically.*"
        )
    return out
