"""Extract structured fields and keywords from job description text."""
import re
from typing import Any

# Common English words that often appear capitalized in job text but are not keywords.
_STOPLIST = frozenset({
    "about", "us", "from", "the", "by", "working", "our", "we", "as", "you", "role",
    "summary", "and", "for", "with", "your", "this", "that", "will", "have", "has",
    "been", "being", "their", "they", "them", "what", "when", "where", "which",
    "who", "how", "all", "each", "every", "both", "some", "such", "than", "into",
    "through", "during", "before", "after", "above", "below", "between", "under",
    "again", "further", "then", "once", "here", "there", "any", "more", "most",
    "other", "just", "also", "only", "same", "than", "too", "very", "can", "may",
    "should", "could", "would", "must", "shall", "need", "dare", "ought", "used",
})

# Known tech/skills terms (lowercase) to always include when present in text.
_KNOWN_TECH = re.compile(
    r"\b(?:"
    r"python|java|javascript|typescript|react|sql|aws|docker|kubernetes|api|ml|machine learning|"
    r"fastapi|django|flask|postgres|redis|linux|git|bash|c\+\+|android|aosp|"
    r"pytest|googletest|espresso|qualcomm|snapdragon|ci/cd|automation|"
    r"hypervisor|kernel|embedded|can bus|ethernet|qxdm|qpst"
    r")\b",
    re.I,
)


def extract_keywords(text: str, max_keywords: int = 50) -> list[str]:
    """Extract likely keywords (tech, skills, role terms) from job text. Filters noise."""
    if not text:
        return []
    text_lower = text.lower()
    seen: set[str] = set()
    result: list[str] = []

    # 1) Known tech terms (case-insensitive)
    for m in _KNOWN_TECH.finditer(text_lower):
        w = m.group(0).strip()
        if w and w not in seen:
            seen.add(w)
            result.append(w)
            if len(result) >= max_keywords:
                return result[:max_keywords]

    # 2) CamelCase / multi-word caps (tech names, frameworks, products)
    for m in re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b", text):
        w = m.strip()
        key = w.lower()
        if len(w) <= 2 or key in _STOPLIST or key in seen:
            continue
        seen.add(key)
        result.append(w)
        if len(result) >= max_keywords:
            return result[:max_keywords]

    # 3) Single capitalized words that look like skills (longer, not stoplist)
    for m in re.findall(r"\b[A-Z][a-z]{2,}\b", text):
        w = m.strip()
        key = w.lower()
        if key in _STOPLIST or key in seen:
            continue
        seen.add(key)
        result.append(w)
        if len(result) >= max_keywords:
            return result[:max_keywords]

    return result[:max_keywords]


def extract_fields_from_html_title(title: str) -> dict[str, str]:
    """Parse a job page title like 'Senior Engineer at Company Name' or 'Company - Role'."""
    out: dict[str, str] = {"company": "", "role": title.strip() if title else ""}
    if not title or not title.strip():
        return out
    t = title.strip()
    # "Role at Company"
    at_match = re.search(r"\s+at\s+(.+)$", t, re.I)
    if at_match:
        out["company"] = at_match.group(1).strip()
        out["role"] = t[: at_match.start()].strip()
        return out
    # "Company - Role" or "Company – Role"
    dash = re.search(r"\s+[-\u2013\u2014]\s+", t)
    if dash:
        out["company"] = t[: dash.start()].strip()
        out["role"] = t[dash.end() :].strip()
        return out
    return out


# Action verbs ATS systems often match; we extract those that appear in the job.
_ATS_ACTION_VERBS = frozenset({
    "develop", "design", "implement", "build", "write", "create", "analyze", "maintain",
    "support", "integrate", "enhance", "collaborate", "debug", "test", "deploy", "improve",
    "optimize", "lead", "manage", "coordinate", "deliver", "drive", "establish", "evaluate",
    "identify", "resolve", "troubleshoot", "document", "automate", "configure", "monitor",
    "review", "refine", "scale", "ship", "architect", "define", "execute", "launch",
})

# Education-related patterns (lowercase) for regex.
_EDUCATION_PATTERN = re.compile(
    r"\b(?:"
    r"BS/MS|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?|"
    r"bachelor(?:'s)?|master(?:'s)?|degree(?:s)?\s+in|"
    r"computer\s+science|electrical\s+engineering|related\s+field"
    r")\b",
    re.I,
)

_YEARS_EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\s*[-+]\s*(\d+)\s*years?|"
    r"(\d+)\+\s*years?|"
    r"(\d+)\s*years?\s*(?:of\s+)?(?:professional\s+)?experience",
    re.I,
)


def extract_ats_signals(text: str) -> dict[str, Any]:
    """
    Extract ATS-friendly signals from job text for resume/cover letter tailoring.
    Returns a dict with action_verbs, years_experience, education, and key_phrases.
    """
    if not text or not text.strip():
        return _empty_ats_signals()
    text_lower = text.lower()
    out: dict[str, Any] = {
        "action_verbs": [],
        "years_experience": None,
        "education": [],
        "key_phrases": [],
    }

    # 1) Action verbs that appear in the job (order preserved by first occurrence)
    seen_verbs: set[str] = set()
    for verb in _ATS_ACTION_VERBS:
        if verb in text_lower and verb not in seen_verbs:
            seen_verbs.add(verb)
            out["action_verbs"].append(verb)

    # 2) Years of experience (first match only)
    for m in _YEARS_EXPERIENCE_PATTERN.finditer(text):
        g = m.groups()
        if g[0] and g[1]:
            out["years_experience"] = f"{g[0]}-{g[1]} years"
            break
        if g[2]:
            out["years_experience"] = f"{g[2]}+ years"
            break
        if g[3]:
            out["years_experience"] = f"{g[3]} years"
            break

    # 3) Education phrases (dedupe by normalized string)
    seen_edu: set[str] = set()
    for m in _EDUCATION_PATTERN.finditer(text):
        raw = m.group(0).strip()
        key = raw.lower()
        if key not in seen_edu:
            seen_edu.add(key)
            out["education"].append(raw)

    # 4) Key phrases: short noun phrases from bullet-like lines (verb + rest)
    # Look for lines that start with a known action verb and take the next few words.
    lines = re.split(r"\n+", text)
    phrase_words = set()
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        first_word = line.split()[0].lower() if line.split() else ""
        if first_word in _ATS_ACTION_VERBS:
            # Take the rest of the line (up to ~50 chars) as a key phrase
            rest = line.split(maxsplit=1)[1] if len(line.split()) > 1 else ""
            rest = re.sub(r"[.:].*", "", rest).strip()[:50]
            if rest and rest.lower() not in phrase_words and len(rest) > 3:
                phrase_words.add(rest.lower())
                out["key_phrases"].append(rest)

    out["key_phrases"] = out["key_phrases"][:15]  # cap for prompt size
    return out


def _empty_ats_signals() -> dict[str, Any]:
    return {
        "action_verbs": [],
        "years_experience": None,
        "education": [],
        "key_phrases": [],
    }


def merge_extracted(job_json: dict[str, Any], title: str, body: str) -> dict[str, Any]:
    """Merge title-derived fields into job_json and add keywords and ATS signals."""
    by_title = extract_fields_from_html_title(title)
    if by_title.get("company") and not job_json.get("company"):
        job_json["company"] = by_title["company"]
    if by_title.get("role") and not job_json.get("role"):
        job_json["role"] = by_title["role"]
    combined = f"{title}\n{body}"
    job_json["keywords"] = extract_keywords(combined)
    job_json["ats"] = extract_ats_signals(combined)
    return job_json
