import re

# --- Include phrases (full-time roles only) ---
_INCLUDE_PHRASES = [
    r"software\s+(?:engineer|developer)",
    r"(?:full[\s-]?stack|frontend|front[\s-]?end|backend|back[\s-]?end)\s+(?:engineer|developer)",
    r"(?:platform|application|systems?)\s+(?:engineer|developer)",
    r"java\s+(?:engineer|developer|software\s+engineer|software\s+developer)",
    r"(?:api|microservices?)\s+developer",
    r"(?:data|analytics)\s+engineer",
    r"(?:business\s+intelligence|bi)\s+(?:engineer|developer)",
    r"etl\s+developer",
    r"data\s+analyst",
    r"business\s+analyst",
    r"data\s+visualization\s+engineer",
    r"cloud\s+(?:engineer|developer|infrastructure\s+engineer)",
    r"devops\s+engineer",,
    r"(?:mlops|machine\s+learning|ml)\s+engineer",
    r"(?:ai|applied)\s+(?:engineer|scientist)",
]

# Combine with word boundaries to avoid partial matches like "engineering"
INCLUDE_RE = re.compile(r"\b(?:" + r"|".join(_INCLUDE_PHRASES) + r")\b", re.I)

# --- Exclude phrases (kill internships/co-ops + optional noise) ---
_EXCLUDE_PHRASES = [
    r"\b(intern|internship|co[ -]?op|campus\s+hire|summer|fall|winter|spring)\b",
    # Add/keep noisy aggregators if you want to filter them out
    r"\b(ripplematch|dice|handshake|wayup|lensa)\b",
    # Optional: uncomment to avoid senior/lead roles
    # r"\b(senior|sr\.?|staff|principal|lead|manager|director|architect|head|vp|chief)\b",
]

EXCLUDE_RE = re.compile(r"|".join(_EXCLUDE_PHRASES), re.I)

def normalize_title(title: str) -> str:
    """
    Normalize for matching: lowercase, collapse whitespace, unify separators.
    """
    t = title.lower()
    t = re.sub(r"[/,_]", " ", t)          # separators to space
    t = re.sub(r"\s+", " ", t).strip()    # collapse spaces
    return t

def is_relevant_title(title: str) -> bool:
    """
    True if the title matches a target phrase and does not hit excludes.
    """
    t = normalize_title(title)
    if EXCLUDE_RE.search(t):
        return False
    return bool(INCLUDE_RE.search(t))
