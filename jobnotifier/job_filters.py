import re

# --- Include phrases (full-time roles only) ---
_INCLUDE_PHRASES = [
    r"software\s+(?:engineer|developer)",
    r"software\s+development\s+engineer",
    r"\bsde(?:\s+i)?\b",
    r"(?:associate|junior)\s+(?:software|application|platform|systems?)\s+(?:engineer|developer)",
    r"(?:software|application|platform|systems?)\s+engineer\s+i\b",
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
    r"(?:software|solutions?|cloud|data)\s+architect",
    r"devops\s+engineer",
    r"site\s+reliability\s+engineer",
    r"\bsre\b",
    r"(?:reliability|infrastructure|production|systems?)\s+engineer",
    r"devsecops\s+engineer",
    r"platform\s+reliability\s+engineer",
    r"(?:mlops|machine\s+learning|ml)\s+engineer",
    r"(?:ai|applied)\s+(?:engineer|scientist)",
    r"data\s+scientist",
]

# Combine with word boundaries to avoid partial matches like "engineering"
INCLUDE_RE = re.compile(r"\b(?:" + r"|".join(_INCLUDE_PHRASES) + r")\b", re.I)

# --- Exclude title phrases (kill internships/co-ops + noise + seniority) ---
_EXCLUDE_TITLE_PHRASES = [
    r"\b(intern|internship|co[ -]?op|campus\s+hire|summer|fall|winter|spring)\b",
    r"\b(ripplematch|dice|handshake|wayup|lensa)\b",
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|architect|head|vp|chief)\b",
    r"\b(mid[ -]?level|experienced|manager|supervisor)\b",
    r"\b(ii|iii|iv|v|level\s*[2-9]|l[2-9]|swe\s*[2-9]|sde\s*[2-9])\b",
    r"\b(10\+?\s*years?|[5-9]\+?\s*years?)\b",
]

EXCLUDE_TITLE_RE = re.compile(r"|".join(_EXCLUDE_TITLE_PHRASES), re.I)

_BLOCKED_COMPANY_PHRASES = [
    r"\b(staffing|recruit(?:er|ers|ing|ment)?|placement|headhunt(?:er|ing)?|agency)\b",
    r"\b(jobs?\s+via\b|dice\b|jobot|jobright|revature|cybercoders|motion recruitment|proclinical|goodwin recruiting|beaconfire)\b",
]

BLOCKED_COMPANY_RE = re.compile(r"|".join(_BLOCKED_COMPANY_PHRASES), re.I)

_BLOCKED_CARD_PHRASES = [
    r"\breposted\b",
    r"\bpromoted\b",
]

BLOCKED_CARD_RE = re.compile(r"|".join(_BLOCKED_CARD_PHRASES), re.I)

def normalize_text(text: str) -> str:
    """
    Normalize for matching: lowercase, collapse whitespace, unify separators.
    """
    t = (text or "").lower()
    t = re.sub(r"[/,_]", " ", t)          # separators to space
    t = re.sub(r"[-()]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()    # collapse spaces
    return t

def normalize_title(title: str) -> str:
    return normalize_text(title)

def normalize_company(company: str) -> str:
    return normalize_text(company)

def is_relevant_title(title: str) -> bool:
    """
    True if the title matches a target phrase and does not hit excludes.
    """
    t = normalize_title(title)
    if EXCLUDE_TITLE_RE.search(t):
        return False
    return bool(INCLUDE_RE.search(t))


ENTRY_LEVEL_SIGNAL_RE = re.compile(
    r"\b(junior|associate|entry|entry\s+level|new\s+grad|graduate|early\s+career|apprentice|"
    r"software\s+engineer\s+i|sde\s+i|level\s+1|l1)\b",
    re.I,
)


def is_entry_level_title(title: str) -> bool:
    """
    True for target roles that are not clearly above entry level.
    Generic unlevelled roles are allowed, but explicit higher levels are blocked.
    """
    t = normalize_title(title)
    if not is_relevant_title(title):
        return False
    if EXCLUDE_TITLE_RE.search(t):
        return False
    return True


_US_PHRASES = {
    "united states",
    "united states of america",
    "remote us",
    "remote usa",
    "remote in us",
    "us remote",
    "usa remote",
    "north america",
    "amer",
}

_CANADA_PHRASES = {
    "canada",
    "remote canada",
    "remote in canada",
    "mexico",
    "remote mexico",
    "remote in mexico",
}

_INDIA_PHRASES = {
    "india",
    "remote india",
    "remote in india",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "pune",
    "mumbai",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "delhi",
    "new delhi",
    "ahmedabad",
    "kolkata",
    "kochi",
    "trivandrum",
}

_US_STATE_CODES = {
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","ia","id","il","in","ks",
    "ky","la","ma","md","me","mi","mn","mo","ms","mt","nc","nd","ne","nh","nj","nm",
    "nv","ny","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","va","vt","wa","wi",
    "wv","wy","dc",
}

_US_STATE_NAMES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
    "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
    "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
    "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
    "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming","district of columbia",
}

_CANADA_CODES = {"ab","bc","mb","nb","nl","ns","nt","nu","on","pe","qc","sk","yt"}
_CANADA_NAMES = {
    "alberta","british columbia","manitoba","new brunswick","newfoundland","nova scotia",
    "northwest territories","nunavut","ontario","prince edward island","quebec",
    "saskatchewan","yukon",
}


def classify_job_market(location: str) -> str | None:
    """
    Return one of: india, north_america, or None.
    """
    normalized = normalize_text(location)
    tokens = set(normalized.split())

    if any(phrase in normalized for phrase in _INDIA_PHRASES):
        return "india"

    if any(phrase in normalized for phrase in _US_PHRASES | _CANADA_PHRASES):
        return "north_america"

    if tokens & _US_STATE_CODES or tokens & _CANADA_CODES:
        return "north_america"

    if any(name in normalized for name in _US_STATE_NAMES | _CANADA_NAMES):
        return "north_america"

    return None


def is_allowed_location(location: str, include_india: bool = False) -> bool:
    market = classify_job_market(location)
    if market == "north_america":
        return True
    if market == "india":
        return include_india
    return False

def is_blocked_company(company: str) -> bool:
    """
    True if the company name looks like an agency, staffing firm, or known aggregator.
    """
    return bool(BLOCKED_COMPANY_RE.search(normalize_company(company)))

def is_blocked_card_text(card_text: str) -> bool:
    """
    True if the card metadata suggests a reposted or promoted listing.
    """
    return bool(BLOCKED_CARD_RE.search(normalize_text(card_text)))
