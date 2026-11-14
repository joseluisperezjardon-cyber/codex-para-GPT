"""Núcleo compartido de la skill clean-user-facing-text.

Reconstrucción del pipeline vendorizado: clases de marcas Unicode, mapa
conservador de homóglifos, tokenización de frases ES/EN y estimador de
estilometría sin LLM (burstiness, densidad de cadencia IA, MATTR y
compuesto amortiguado 0-1).

Sin red, sin dependencias externas. Python 3.8+.

Nota de diseño: los caracteres invisibles se declaran por punto de código
(chr(0x...)) y nunca literalmente, para que el fichero sobreviva a copias,
editores que normalizan y a la propia limpieza de esta skill.
"""

from __future__ import annotations

import re
import statistics
import unicodedata

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# 1. Clases de marcas Unicode
# ---------------------------------------------------------------------------
# confianza: confirmed | probable | informational | likely_false_positive


def _t(pairs):
    return {chr(cp): name for cp, name in pairs}


ZERO_WIDTH = _t([
    (0x200B, "ZERO WIDTH SPACE"),
    (0x2060, "WORD JOINER"),
    (0x2061, "FUNCTION APPLICATION"),
    (0x2062, "INVISIBLE TIMES"),
    (0x2063, "INVISIBLE SEPARATOR"),
    (0x2064, "INVISIBLE PLUS"),
    (0xFEFF, "ZERO WIDTH NO-BREAK SPACE (BOM)"),
    (0x180E, "MONGOLIAN VOWEL SEPARATOR"),
])

JOINERS = _t([
    (0x200C, "ZERO WIDTH NON-JOINER"),
    (0x200D, "ZERO WIDTH JOINER"),
])

SOFT_HYPHEN = _t([(0x00AD, "SOFT HYPHEN")])

BIDI_CONTROLS = _t([
    (0x200E, "LEFT-TO-RIGHT MARK"),
    (0x200F, "RIGHT-TO-LEFT MARK"),
    (0x061C, "ARABIC LETTER MARK"),
    (0x202A, "LEFT-TO-RIGHT EMBEDDING"),
    (0x202B, "RIGHT-TO-LEFT EMBEDDING"),
    (0x202C, "POP DIRECTIONAL FORMATTING"),
    (0x202D, "LEFT-TO-RIGHT OVERRIDE"),
    (0x202E, "RIGHT-TO-LEFT OVERRIDE"),
    (0x2066, "LEFT-TO-RIGHT ISOLATE"),
    (0x2067, "RIGHT-TO-LEFT ISOLATE"),
    (0x2068, "FIRST STRONG ISOLATE"),
    (0x2069, "POP DIRECTIONAL ISOLATE"),
])

INTERLINEAR = _t([
    (0xFFF9, "INTERLINEAR ANNOTATION ANCHOR"),
    (0xFFFA, "INTERLINEAR ANNOTATION SEPARATOR"),
    (0xFFFB, "INTERLINEAR ANNOTATION TERMINATOR"),
])

# Rellenos invisibles usados para ocultar payloads en texto plano.
INVISIBLE_FILLERS = _t([
    (0x115F, "HANGUL CHOSEONG FILLER"),
    (0x1160, "HANGUL JUNGSEONG FILLER"),
    (0x3164, "HANGUL FILLER"),
    (0xFFA0, "HALFWIDTH HANGUL FILLER"),
])

EXOTIC_SPACES = _t([
    (0x00A0, "NO-BREAK SPACE"),
    (0x2000, "EN QUAD"),
    (0x2001, "EM QUAD"),
    (0x2002, "EN SPACE"),
    (0x2003, "EM SPACE"),
    (0x2004, "THREE-PER-EM SPACE"),
    (0x2005, "FOUR-PER-EM SPACE"),
    (0x2006, "SIX-PER-EM SPACE"),
    (0x2007, "FIGURE SPACE"),
    (0x2008, "PUNCTUATION SPACE"),
    (0x2009, "THIN SPACE"),
    (0x200A, "HAIR SPACE"),
    (0x202F, "NARROW NO-BREAK SPACE"),
    (0x205F, "MEDIUM MATHEMATICAL SPACE"),
    (0x3000, "IDEOGRAPHIC SPACE"),
])

# Tipografía "de modelo" -> ASCII. Visible, se declara por punto de código
# para evitar sorpresas de codificación.
TYPOGRAPHY = {
    chr(0x2018): "'", chr(0x2019): "'", chr(0x201A): "'", chr(0x201B): "'",
    chr(0x201C): '"', chr(0x201D): '"', chr(0x201E): '"', chr(0x201F): '"',
    chr(0x2032): "'", chr(0x2033): '"',
    chr(0x2013): "-", chr(0x2014): "-", chr(0x2015): "-", chr(0x2212): "-",
    chr(0x2026): "...",
    chr(0x00B4): "'", chr(0x02BC): "'",
}

TYPOGRAPHY_NAMES = _t([
    (0x2018, "LEFT SINGLE QUOTATION MARK"),
    (0x2019, "RIGHT SINGLE QUOTATION MARK"),
    (0x201A, "SINGLE LOW-9 QUOTATION MARK"),
    (0x201B, "SINGLE HIGH-REVERSED-9 QUOTATION MARK"),
    (0x201C, "LEFT DOUBLE QUOTATION MARK"),
    (0x201D, "RIGHT DOUBLE QUOTATION MARK"),
    (0x201E, "DOUBLE LOW-9 QUOTATION MARK"),
    (0x201F, "DOUBLE HIGH-REVERSED-9 QUOTATION MARK"),
    (0x2032, "PRIME"),
    (0x2033, "DOUBLE PRIME"),
    (0x2013, "EN DASH"),
    (0x2014, "EM DASH"),
    (0x2015, "HORIZONTAL BAR"),
    (0x2212, "MINUS SIGN"),
    (0x2026, "HORIZONTAL ELLIPSIS"),
    (0x00B4, "ACUTE ACCENT"),
    (0x02BC, "MODIFIER LETTER APOSTROPHE"),
])

# Homóglifos cirílicos / griegos / otros hacia ASCII.
_HOMOGLYPH_PAIRS = [
    # cirílico minúscula
    (0x0430, "a"), (0x0435, "e"), (0x043E, "o"), (0x0440, "p"), (0x0441, "c"),
    (0x0443, "y"), (0x0445, "x"), (0x0456, "i"), (0x0455, "s"), (0x0458, "j"),
    (0x04BB, "h"), (0x0501, "d"), (0x051B, "q"), (0x0433, "r"), (0x0431, "b"),
    # cirílico mayúscula
    (0x0410, "A"), (0x0412, "B"), (0x0415, "E"), (0x041A, "K"), (0x041C, "M"),
    (0x041D, "H"), (0x041E, "O"), (0x0420, "P"), (0x0421, "C"), (0x0422, "T"),
    (0x0423, "Y"), (0x0425, "X"), (0x0405, "S"), (0x0408, "J"), (0x0406, "I"),
    # griego
    (0x03B1, "a"), (0x03B5, "e"), (0x03B9, "i"), (0x03BA, "k"), (0x03BD, "v"),
    (0x03BF, "o"), (0x03C1, "p"), (0x03C4, "t"), (0x03C5, "u"), (0x03C7, "x"),
    (0x0391, "A"), (0x0392, "B"), (0x0395, "E"), (0x0396, "Z"), (0x0397, "H"),
    (0x0399, "I"), (0x039A, "K"), (0x039C, "M"), (0x039D, "N"), (0x039F, "O"),
    (0x03A1, "P"), (0x03A4, "T"), (0x03A5, "Y"), (0x03A7, "X"),
    # otros confusables frecuentes
    (0x0131, "i"), (0x04CF, "l"), (0x2010, "-"), (0x2011, "-"),
]
HOMOGLYPHS = {chr(cp): rep for cp, rep in _HOMOGLYPH_PAIRS}

VARIATION_SELECTORS = [(0xFE00, 0xFE0F), (0xE0100, 0xE01EF)]
TAG_CHARS = (0xE0000, 0xE007F)  # payloads invisibles (tag characters)

EMOJI_RANGES = [
    (0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2B00, 0x2BFF),
    (0xFE0F, 0xFE0F), (0x2190, 0x21FF), (0x24C2, 0x24C2),
    (0x203C, 0x2049), (0x1F1E6, 0x1F1FF),
]

# Scripts donde ZWJ/ZWNJ son ortográficamente necesarios.
JOINER_SCRIPT_RANGES = [
    (0x0590, 0x08FF),   # hebreo, árabe, siríaco, thaana, N'Ko
    (0x0900, 0x0DFF),   # índicas
    (0x0E00, 0x0EFF),   # tailandés/lao
    (0xFB1D, 0xFDFF), (0xFE70, 0xFEFF),
]


def _in_ranges(cp: int, ranges) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def is_emoji(ch: str) -> bool:
    return _in_ranges(ord(ch), EMOJI_RANGES)


def needs_joiner(ch: str) -> bool:
    return _in_ranges(ord(ch), JOINER_SCRIPT_RANGES)


def is_variation_selector(ch: str) -> bool:
    return _in_ranges(ord(ch), VARIATION_SELECTORS)


def is_tag_char(ch: str) -> bool:
    return TAG_CHARS[0] <= ord(ch) <= TAG_CHARS[1]


def char_name(ch: str) -> str:
    for table in (ZERO_WIDTH, JOINERS, SOFT_HYPHEN, BIDI_CONTROLS, INTERLINEAR,
                  INVISIBLE_FILLERS, EXOTIC_SPACES, TYPOGRAPHY_NAMES):
        if ch in table:
            return table[ch]
    if is_tag_char(ch):
        return "TAG CHARACTER (payload invisible)"
    if is_variation_selector(ch):
        return "VARIATION SELECTOR"
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "UNNAMED"


def codepoint(ch: str) -> str:
    return "U+%04X" % ord(ch)


def classify_char(ch: str, prev: str = "", nxt: str = ""):
    """(clase, confianza) o (None, None) si el carácter es normal."""
    if is_tag_char(ch):
        return "tag_char", "confirmed"
    if ch in INVISIBLE_FILLERS:
        return "invisible_filler", "confirmed"
    if ch in ZERO_WIDTH:
        return "zero_width", "confirmed"
    if ch in INTERLINEAR:
        return "interlinear", "confirmed"
    if ch in JOINERS:
        if (prev and (needs_joiner(prev) or is_emoji(prev))) or \
           (nxt and (needs_joiner(nxt) or is_emoji(nxt))):
            return "joiner", "likely_false_positive"
        return "joiner", "probable"
    if ch in SOFT_HYPHEN:
        return "soft_hyphen", "probable"
    if ch in BIDI_CONTROLS:
        return "bidi_control", "probable"
    if is_variation_selector(ch):
        if prev and is_emoji(prev):
            return "variation_selector", "likely_false_positive"
        return "variation_selector", "probable"
    if ch in EXOTIC_SPACES:
        return "exotic_space", "informational"
    if ch in TYPOGRAPHY:
        return "typography", "informational"
    if ch in HOMOGLYPHS:
        return "homoglyph", "informational"  # se recalifica por palabra mixta
    return None, None


ACTIONABLE = {"confirmed", "probable"}


# ---------------------------------------------------------------------------
# 2. Homóglifos: detección conservadora por palabra mixta
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def mixed_script_homoglyphs(text: str):
    """[(posición, carácter, palabra)] de homóglifos en palabras latinas."""
    hits = []
    for m in _WORD_RE.finditer(text):
        word = m.group(0)
        latin = sum(1 for c in word if "a" <= c.lower() <= "z")
        conf = [(i, c) for i, c in enumerate(word) if c in HOMOGLYPHS]
        if latin and conf and latin >= len(conf):
            for i, c in conf:
                hits.append((m.start() + i, c, word))
    return hits


# ---------------------------------------------------------------------------
# 3. Léxico vetado (alineado con redaccion-humana/references/lexico-vetado.md)
# ---------------------------------------------------------------------------
# peso 1.0 = coletilla o frase hecha; <=0.5 = palabra comodín aislada.

AI_PHRASES = {
    # --- español: coletillas y frases ---
    "es importante destacar": 1.0, "es importante señalar": 1.0,
    "es importante mencionar": 1.0, "es importante notar": 1.0,
    "es importante recordar": 0.9,
    "cabe señalar": 1.0, "cabe mencionar": 1.0, "cabe destacar": 1.0,
    "en resumen": 1.0, "en conclusión": 1.0, "para concluir": 1.0,
    "en definitiva": 0.8, "dicho esto": 0.8, "dicho todo esto": 1.0,
    "por un lado": 0.5, "por otro lado": 0.5,
    "en el mundo actual": 1.0, "en el mundo de hoy": 1.0,
    "en la era digital": 1.0, "en el panorama actual": 1.0,
    "sigue evolucionando": 0.8, "no dudes en preguntar": 1.0,
    "no dudes en contactar": 1.0, "no dudes en consultar": 1.0,
    "espero que esto ayude": 1.0, "espero que te sirva": 1.0,
    "espero que esto te sirva": 1.0,
    "espero que este mensaje te encuentre bien": 1.0,
    "claro que sí": 0.6, "aquí tienes": 0.6, "vamos a ello": 0.8,
    "sin más preámbulos": 1.0, "en el ámbito de": 0.8,
    "juega un papel": 0.9, "desempeña un papel": 0.9,
    "papel fundamental": 0.9, "papel crucial": 1.0,
    "una solución integral": 0.9, "solución robusta": 0.9,
    "es fundamental entender": 1.0, "vale la pena mencionar": 1.0,
    "en última instancia": 0.8, "de la mano de": 0.4,
    "a día de hoy": 0.4, "en este sentido": 0.5,
    "por su parte": 0.35, "en pocas palabras": 0.7,
    # --- español: palabras comodín ---
    "crucial": 0.4, "esencial": 0.35, "fundamental": 0.35,
    "imprescindible": 0.3, "robusto": 0.3, "robusta": 0.3,
    "sinergia": 0.5, "sinergias": 0.5, "potenciar": 0.4, "impulsar": 0.3,
    "fomentar": 0.35, "panorama": 0.35, "ecosistema": 0.35,
    "desglosar": 0.35, "sumergirse": 0.5, "adentrarse": 0.5,
    "enriquecer": 0.35, "transformador": 0.45, "transformadora": 0.45,
    "revolucionario": 0.45, "revolucionaria": 0.45, "disruptivo": 0.45,
    "holístico": 0.5, "holística": 0.5, "versátil": 0.35,
    "dinámico": 0.3, "innovador": 0.35, "innovadora": 0.35,
    "optimizar": 0.3, "profundizar": 0.3, "matizar": 0.25,
    "sólido": 0.25, "clave": 0.2, "abordar": 0.25, "integral": 0.25,
    # --- inglés: frases ---
    "it is important to note": 1.0, "it's important to note": 1.0,
    "it is worth noting": 1.0, "it's worth noting": 1.0,
    "when it comes to": 0.9, "in today's fast-paced world": 1.0,
    "in the realm of": 1.0, "at the end of the day": 0.8,
    "needless to say": 0.8, "a testament to": 1.0,
    "plays a crucial role": 1.0, "plays a pivotal role": 1.0,
    "in the ever-evolving landscape": 1.0, "in conclusion": 1.0,
    "to sum up": 0.9, "i hope this helps": 1.0,
    "i hope this email finds you well": 1.0, "let's dive in": 1.0,
    "dive deep into": 0.9, "unlock the potential": 1.0,
    "to the next level": 0.9, "firstly": 0.4, "secondly": 0.3,
    "moreover": 0.3, "furthermore": 0.3,
    # --- inglés: palabras ---
    "delve": 0.6, "robust": 0.3, "pivotal": 0.5, "meticulous": 0.5,
    "intricate": 0.45, "groundbreaking": 0.5, "seamless": 0.5,
    "leverage": 0.4, "foster": 0.4, "underscore": 0.45, "underscores": 0.45,
    "boasts": 0.5, "showcases": 0.45, "testament": 0.5, "myriad": 0.5,
    "tapestry": 0.6, "realm": 0.4, "elevate": 0.4, "unleash": 0.5,
    "harness": 0.4, "embark": 0.45, "cultivate": 0.35, "nuanced": 0.35,
    "holistic": 0.45, "streamline": 0.4, "utilize": 0.35, "plethora": 0.5,
    "paramount": 0.45, "vibrant": 0.35, "bustling": 0.45, "resonate": 0.35,
    "empower": 0.45, "spearhead": 0.4, "bolster": 0.4, "garner": 0.4,
}

_PHRASE_PATTERNS = [
    (p, w, re.compile(r"(?<!\w)" + re.escape(p).replace(r"\ ", r"\s+") + r"(?!\w)",
                      re.IGNORECASE | re.UNICODE))
    for p, w in AI_PHRASES.items()
]


def phrase_hits(text: str):
    """[(frase, peso, inicio, fin, fragmento)] sin solapes: gana la más larga."""
    raw = []
    for phrase, weight, pat in _PHRASE_PATTERNS:
        for m in pat.finditer(text):
            raw.append((phrase, weight, m.start(), m.end(), m.group(0)))
    raw.sort(key=lambda h: (h[2], -(h[3] - h[2])))
    out, last_end = [], -1
    for hit in raw:
        if hit[2] >= last_end:
            out.append(hit)
            last_end = hit[3]
    return out


# ---------------------------------------------------------------------------
# 4. Segmentación y métricas
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MD_NOISE_RE = re.compile(r"^\s{0,3}(#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s+)", re.MULTILINE)
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)

_ABBREV = {"sr", "sra", "dr", "dra", "ee", "uu", "etc", "vs", "art", "fig",
           "núm", "no", "pág", "aprox", "ud", "uds", "mr", "mrs", "inc", "vol",
           "ing", "ref", "cap", "ap", "op", "ss", "ej"}

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+|\n{2,}")


def strip_non_prose(text: str) -> str:
    """Quita código, URLs, tablas y ruido Markdown antes de medir."""
    text = _CODE_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _TABLE_RE.sub(" ", text)
    text = _MD_NOISE_RE.sub("", text)
    return text


def split_sentences(text: str):
    parts, buf = [], ""
    for chunk in _SENT_SPLIT_RE.split(text):
        if not chunk:
            continue
        piece = chunk.strip()
        if not piece:
            continue
        candidate = (buf + " " + piece).strip() if buf else piece
        toks = candidate.split()
        tail = re.sub(r"[^\w]", "", toks[-1]).lower() if toks else ""
        if tail in _ABBREV or (len(tail) == 1 and tail.isalpha()):
            buf = candidate
            continue
        parts.append(candidate)
        buf = ""
    if buf:
        parts.append(buf)
    return [p for p in parts if re.search(r"\w", p)]


def words_of(text: str):
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text, re.UNICODE)


def mattr(tokens, window: int = 50) -> float:
    toks = [t.lower() for t in tokens]
    if not toks:
        return 0.0
    if len(toks) <= window:
        return len(set(toks)) / len(toks)
    ratios = [len(set(toks[i:i + window])) / window
              for i in range(len(toks) - window + 1)]
    return sum(ratios) / len(ratios)


def uniform_runs(lengths, tol: float = 0.30, min_run: int = 3):
    """Rachas de >=min_run frases cuya longitud varía menos de tol (relativo)."""
    runs, i = [], 0
    n = len(lengths)
    while i < n:
        j = i
        while j + 1 < n:
            window = lengths[i:j + 2]
            lo, hi = min(window), max(window)
            if lo <= 0 or (hi - lo) / lo > tol:
                break
            j += 1
        if j - i + 1 >= min_run:
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def _ramp(value, best, worst):
    """1.0 en 'worst' (máxima huella IA), 0.0 en 'best'."""
    if best > worst:
        if value >= best:
            return 0.0
        if value <= worst:
            return 1.0
        return (best - value) / (best - worst)
    if value <= best:
        return 0.0
    if value >= worst:
        return 1.0
    return (value - best) / (worst - best)


def tier_of(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


DEFAULT_THRESHOLD = 0.65
MIN_WORDS = 30


def score_text(text: str, threshold: float = DEFAULT_THRESHOLD) -> dict:
    prose = strip_non_prose(text)
    tokens = words_of(prose)
    n_words = len(tokens)

    if n_words < MIN_WORDS:
        return {
            "status": "insufficient_length",
            "words": n_words,
            "min_words": MIN_WORDS,
            "density_tier": "uncalibrated",
            "threshold": threshold,
        }

    sentences = split_sentences(prose)
    lengths = [n for n in (len(words_of(s)) for s in sentences) if n > 0]
    mean_len = statistics.fmean(lengths) if lengths else 0.0
    sd = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    cv = (sd / mean_len) if mean_len else 0.0

    hits = phrase_hits(prose)
    weighted = sum(h[1] for h in hits)
    density = weighted * 100.0 / n_words

    lex = mattr(tokens)
    runs = uniform_runs(lengths)
    covered = sum(b - a + 1 for a, b in runs)
    uniform_frac = covered / len(lengths) if lengths else 0.0

    s_burst = _ramp(cv, best=0.60, worst=0.20)
    s_phrase = _ramp(density, best=0.0, worst=2.5)
    s_lex = _ramp(lex, best=0.82, worst=0.62)
    s_uniform = _ramp(uniform_frac, best=0.0, worst=0.70)

    # La burstiness pesa más que el léxico: es la señal más difícil de falsear
    # y la que más discrimina en la familia de detectores estadísticos.
    raw = 0.45 * s_burst + 0.30 * s_phrase + 0.15 * s_uniform + 0.10 * s_lex
    conf_factor = min(1.0, n_words / 250.0)
    score = round(raw * (0.70 + 0.30 * conf_factor), 4)
    confidence = "high" if n_words >= 250 else ("medium" if n_words >= 80 else "low")

    return {
        "status": "scored",
        "score": score,
        "raw_score": round(raw, 4),
        "threshold": threshold,
        "above_threshold": score >= threshold,
        "density_tier": tier_of(score),
        "confidence": confidence,
        "words": n_words,
        "sentences": len(lengths),
        "metrics": {
            "sentence_len_mean": round(mean_len, 2),
            "sentence_len_sd": round(sd, 2),
            "burstiness_cv": round(cv, 4),
            "ai_phrase_density_per_100w": round(density, 3),
            "ai_phrase_hits": len(hits),
            "mattr_50": round(lex, 4),
            "uniform_run_fraction": round(uniform_frac, 3),
            "uniform_runs": [{"from_sentence": a + 1, "to_sentence": b + 1}
                             for a, b in runs],
        },
        "subscores": {
            "burstiness": round(s_burst, 3),
            "ai_phrases": round(s_phrase, 3),
            "uniformity": round(s_uniform, 3),
            "lexical_diversity": round(s_lex, 3),
        },
        "top_phrases": [
            {"phrase": p, "weight": w, "text": frag}
            for p, w, _s, _e, frag in sorted(hits, key=lambda h: -h[1])[:15]
        ],
    }


def line_col(text: str, index: int):
    line = text.count("\n", 0, index) + 1
    last_nl = text.rfind("\n", 0, index)
    return line, index - last_nl


def read_input(path: str) -> str:
    import sys
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as fh:
            data = fh.read()
    return data.decode("utf-8", errors="replace")
