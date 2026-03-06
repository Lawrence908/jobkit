"""Markdown -> HTML -> PDF via WeasyPrint."""
import logging
from pathlib import Path

import mistune
from weasyprint import HTML, CSS

from app.core.config import get_settings
from app.utils.files import ensure_safe_relative_path

logger = logging.getLogger(__name__)

_CSS_PATH = Path(__file__).resolve().parent.parent / "templates" / "resume.css"


def md_to_html(md: str) -> str:
    """Convert markdown to HTML body."""
    html_body = mistune.html(md)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
{html_body}
</body>
</html>"""


def render_pdf(html_content: str, output_path: Path, css_path: Path | None = None) -> None:
    """Render HTML to PDF with optional CSS."""
    doc = HTML(string=html_content)
    if css_path and css_path.exists():
        doc.write_pdf(output_path, stylesheets=[CSS(filename=str(css_path))])
    else:
        doc.write_pdf(output_path)
    logger.info("Rendered PDF: %s", output_path)


def render_job_pdfs(job_slug: str, jobs_dir: Path | None = None, outputs_dir: Path | None = None, css_path: Path | None = None) -> list[tuple[str, Path]]:
    """
    Read generated resume.md and cover_letter.md, render to PDFs.
    Returns list of (artifact_type, path) e.g. [("resume_pdf", path), ("cover_letter_pdf", path)].
    """
    settings = get_settings()
    jobs_dir = jobs_dir or settings.jobkit_jobs_dir
    outputs_dir = outputs_dir or settings.jobkit_outputs_dir
    css_path = css_path or _CSS_PATH
    generated = ensure_safe_relative_path(jobs_dir, job_slug, "generated")
    out_dir = ensure_safe_relative_path(outputs_dir, job_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, art_type in [("resume.md", "resume_pdf"), ("cover_letter.md", "cover_letter_pdf")]:
        md_file = generated / name
        if not md_file.exists():
            continue
        md_content = md_file.read_text(encoding="utf-8")
        html_content = md_to_html(md_content)
        pdf_name = name.replace(".md", ".pdf")
        pdf_path = out_dir / pdf_name
        render_pdf(html_content, pdf_path, css_path)
        results.append((art_type, pdf_path))
    return results
