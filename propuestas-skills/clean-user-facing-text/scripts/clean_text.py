#!/usr/bin/env python3
"""Layer A determinista: limpieza Unicode de texto plano / Markdown / HTML fuente.

Uso típico (según SKILL.md de clean-user-facing-text):

    python3 clean_text.py INPUT -o OUTPUT --stats --no-normalize-spaces

Elimina caracteres invisibles y de control (zero-width, tag characters,
rellenos hangul, controles bidi, soft hyphen, selectores de variación),
normaliza tipografía "de modelo" (comillas curvas, guiones largos, elipsis)
y corrige homóglifos en palabras de escritura mixta.

No toca el contenido semántico: no reescribe, no traduce, no reordena.
Las estadísticas van a stderr; el texto limpio a stdout o a -o.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import _textlib as T  # noqa: E402


def clean(text: str, *, normalize_spaces: bool = True, nfkc: bool = False,
          aggressive_homoglyphs: bool = False, strip_emoji_glue: bool = False,
          keep_typography: bool = False):
    stats = {
        "removed": Counter(),
        "replaced": Counter(),
        "kept_false_positive": Counter(),
        "nfkc": bool(nfkc),
    }

    if nfkc:
        before = text
        text = unicodedata.normalize("NFKC", text)
        stats["nfkc_changed"] = (before != text)

    # --- homóglifos: decidir posiciones antes del barrido ---
    homoglyph_idx = {}
    if aggressive_homoglyphs:
        for i, ch in enumerate(text):
            if ch in T.HOMOGLYPHS:
                homoglyph_idx[i] = T.HOMOGLYPHS[ch]
    else:
        for pos, ch, _word in T.mixed_script_homoglyphs(text):
            homoglyph_idx[pos] = T.HOMOGLYPHS[ch]

    out = []
    n = len(text)
    for i, ch in enumerate(text):
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if T.is_tag_char(ch):
            # se agrupan: un payload son decenas de codepoints distintos
            label = "U+E0000-E007F TAG CHARACTERS (payload invisible)"
        else:
            label = "%s %s" % (T.codepoint(ch), T.char_name(ch))

        if i in homoglyph_idx:
            out.append(homoglyph_idx[i])
            stats["replaced"][label + " -> " + homoglyph_idx[i]] += 1
            continue

        klass, confidence = T.classify_char(ch, prev, nxt)

        if klass in ("tag_char", "invisible_filler", "zero_width",
                     "interlinear", "soft_hyphen", "bidi_control"):
            stats["removed"][label] += 1
            continue

        if klass == "joiner":
            if confidence == "likely_false_positive" and not strip_emoji_glue:
                stats["kept_false_positive"][label] += 1
                out.append(ch)
            else:
                stats["removed"][label] += 1
            continue

        if klass == "variation_selector":
            if confidence == "likely_false_positive" and not strip_emoji_glue:
                stats["kept_false_positive"][label] += 1
                out.append(ch)
            else:
                stats["removed"][label] += 1
            continue

        if klass == "exotic_space":
            if normalize_spaces:
                out.append(" ")
                stats["replaced"][label + " -> SPACE"] += 1
            else:
                stats["kept_false_positive"][label] += 1
                out.append(ch)
            continue

        if klass == "typography":
            if keep_typography:
                stats["kept_false_positive"][label] += 1
                out.append(ch)
            else:
                rep = T.TYPOGRAPHY[ch]
                out.append(rep)
                stats["replaced"][label + " -> " + rep] += 1
            continue

        out.append(ch)

    return "".join(out), stats


def format_stats(stats, as_json: bool = False) -> str:
    payload = {
        "removed": dict(stats["removed"]),
        "replaced": dict(stats["replaced"]),
        "kept_false_positive": dict(stats["kept_false_positive"]),
        "totals": {
            "removed": sum(stats["removed"].values()),
            "replaced": sum(stats["replaced"].values()),
            "kept_false_positive": sum(stats["kept_false_positive"].values()),
        },
        "nfkc": stats.get("nfkc", False),
        "nfkc_changed": stats.get("nfkc_changed"),
        "version": T.VERSION,
    }
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)

    lines = ["clean_text %s" % T.VERSION]
    tot = payload["totals"]
    lines.append("  eliminados: %d | sustituidos: %d | conservados (falso positivo probable): %d"
                 % (tot["removed"], tot["replaced"], tot["kept_false_positive"]))
    for section, title in (("removed", "eliminados"), ("replaced", "sustituidos"),
                           ("kept_false_positive", "conservados")):
        items = payload[section]
        if not items:
            continue
        lines.append("  %s:" % title)
        for key, count in sorted(items.items(), key=lambda kv: -kv[1]):
            lines.append("    %5d  %s" % (count, key))
    if payload["nfkc"]:
        lines.append("  NFKC aplicado (cambió el texto: %s)" % payload["nfkc_changed"])
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Limpieza Unicode determinista (Layer A).")
    ap.add_argument("input", help="fichero de entrada, o '-' para stdin")
    ap.add_argument("-o", "--output", help="fichero de salida (por defecto stdout)")
    ap.add_argument("--in-place", action="store_true",
                    help="sobrescribe el fichero de entrada")
    ap.add_argument("--stats", action="store_true",
                    help="informe de lo eliminado/sustituido (a stderr)")
    ap.add_argument("--json", action="store_true",
                    help="el informe de --stats en JSON")
    ap.add_argument("--no-normalize-spaces", dest="normalize_spaces",
                    action="store_false", default=True,
                    help="conserva NBSP y espacios exóticos (recomendado por defecto en la skill)")
    ap.add_argument("--nfkc", action="store_true",
                    help="normalización NFKC (agresiva: altera ligaduras, anchos, superíndices)")
    ap.add_argument("--aggressive-homoglyphs", action="store_true",
                    help="convierte TODO confusable a ASCII, no solo en palabras mixtas")
    ap.add_argument("--strip-emoji-glue", action="store_true",
                    help="elimina también ZWJ y selectores de variación pegados a emoji")
    ap.add_argument("--keep-typography", action="store_true",
                    help="no toca comillas curvas, guiones largos ni elipsis")
    args = ap.parse_args(argv)

    text = T.read_input(args.input)
    cleaned, stats = clean(
        text,
        normalize_spaces=args.normalize_spaces,
        nfkc=args.nfkc,
        aggressive_homoglyphs=args.aggressive_homoglyphs,
        strip_emoji_glue=args.strip_emoji_glue,
        keep_typography=args.keep_typography,
    )

    target = args.output
    if args.in_place:
        if args.input == "-":
            ap.error("--in-place no es compatible con stdin")
        target = args.input

    if target:
        with open(target, "w", encoding="utf-8", newline="") as fh:
            fh.write(cleaned)
    else:
        sys.stdout.write(cleaned)

    if args.stats:
        sys.stderr.write(format_stats(stats, args.json) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
