#!/usr/bin/env python3
"""Inspección de marcas en texto: codepoints sospechosos (+ estilometría opcional).

    python3 inspect_text.py --stylometry --json INPUT
    python3 inspect_text.py --audit INPUT     # solo detección, nunca reescribe

Nunca modifica nada: lista hallazgos con clase, confianza y posición
(línea:columna). Etiquetas de confianza: confirmed / probable /
informational / likely_false_positive.

Códigos de salida: 0 sin hallazgos accionables; 1 hay hallazgos accionables
(confirmed o probable) o, en modo --audit, el score de estilometría alcanza
el umbral; 2 error de uso.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import _textlib as T  # noqa: E402

MAX_POSITIONS = 12
RUN_PAYLOAD_MIN = 8  # rachas de invisibles = posible payload codificado

CLASS_HINT = {
    "tag_char": "tag characters: canal de texto oculto, nunca legítimo en prosa",
    "invisible_filler": "relleno hangul invisible: usado para ocultar payloads",
    "zero_width": "carácter de ancho cero",
    "interlinear": "anotación interlineal",
    "joiner": "ZWJ/ZWNJ fuera de contexto ortográfico o emoji",
    "soft_hyphen": "guion suave invisible",
    "bidi_control": "control de direccionalidad",
    "variation_selector": "selector de variación fuera de emoji",
    "exotic_space": "espacio no estándar (NBSP, fino, ideográfico...)",
    "typography": "tipografía de modelo (comillas curvas, guion largo, elipsis)",
    "homoglyph": "carácter confusable no latino",
}


def scan(text: str) -> dict:
    mixed = {pos for pos, _c, _w in T.mixed_script_homoglyphs(text)}
    findings = OrderedDict()
    runs, run_len, run_start = [], 0, None

    for i, ch in enumerate(text):
        prev = text[i - 1] if i else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        klass, confidence = T.classify_char(ch, prev, nxt)

        invisible = klass in ("tag_char", "invisible_filler", "zero_width",
                              "joiner", "variation_selector")
        if invisible:
            if run_len == 0:
                run_start = i
            run_len += 1
        else:
            if run_len >= RUN_PAYLOAD_MIN:
                runs.append((run_start, run_len))
            run_len = 0

        if klass is None:
            continue
        if klass == "homoglyph":
            confidence = "confirmed" if i in mixed else "likely_false_positive"

        if klass == "tag_char":
            # se agrupan en un solo hallazgo: un payload son decenas de codepoints
            key = ("tag_char", "U+E0000-E007F")
            entry = findings.setdefault(key, {
                "class": klass,
                "codepoint": "U+E0000-E007F",
                "name": "TAG CHARACTERS (payload invisible)",
                "confidence": "confirmed",
                "count": 0,
                "positions": [],
                "decoded": "",
            })
            cp = ord(ch) - 0xE0000
            entry["decoded"] += chr(cp) if 0x20 <= cp <= 0x7E else "."
        else:
            key = (klass, T.codepoint(ch))
            entry = findings.setdefault(key, {
                "class": klass,
                "codepoint": T.codepoint(ch),
                "name": T.char_name(ch),
                "confidence": confidence,
                "count": 0,
                "positions": [],
            })
        entry["count"] += 1
        # la confianza más alta observada manda
        order = ["likely_false_positive", "informational", "probable", "confirmed"]
        if order.index(confidence) > order.index(entry["confidence"]):
            entry["confidence"] = confidence
        if len(entry["positions"]) < MAX_POSITIONS:
            line, col = T.line_col(text, i)
            entry["positions"].append({"line": line, "col": col, "offset": i})

    if run_len >= RUN_PAYLOAD_MIN:
        runs.append((run_start, run_len))

    out = list(findings.values())
    for f in out:
        f["hint"] = CLASS_HINT.get(f["class"], "")
    out.sort(key=lambda f: (-["likely_false_positive", "informational",
                              "probable", "confirmed"].index(f["confidence"]),
                            -f["count"]))

    payload_runs = []
    for start, length in runs:
        line, col = T.line_col(text, start)
        payload_runs.append({"line": line, "col": col, "offset": start,
                             "length": length,
                             "note": "racha de %d caracteres invisibles: "
                                     "posible payload codificado" % length})
    return {"findings": out, "payload_runs": payload_runs}


def flagged_spans(text: str):
    spans = []
    for phrase, weight, start, _end, frag in T.phrase_hits(text):
        line, col = T.line_col(text, start)
        spans.append({"phrase": phrase, "weight": weight, "text": frag,
                      "line": line, "col": col})
    spans.sort(key=lambda s: (-s["weight"], s["line"]))
    return spans


def render(report: dict, args) -> str:
    lines = ["inspect_text %s — %s" % (T.VERSION, report["path"])]
    lines.append("  sospechoso: %s (%d hallazgos, %d caracteres accionables)"
                 % ("sí" if report["suspicious"] else "no",
                    len(report["findings"]),
                    report["actionable_count"]))
    if not report["findings"]:
        lines.append("  sin caracteres marcados")
    for f in report["findings"]:
        pos = ", ".join("%d:%d" % (p["line"], p["col"]) for p in f["positions"])
        more = "" if f["count"] <= len(f["positions"]) else " (+%d más)" % (
            f["count"] - len(f["positions"]))
        lines.append("  [%s] %s %s x%d — %s" % (
            f["confidence"], f["codepoint"], f["name"], f["count"], f["hint"]))
        if f.get("decoded"):
            lines.append("      payload decodificado: %r" % f["decoded"])
        if pos:
            lines.append("      en %s%s" % (pos, more))
    for r in report["payload_runs"]:
        lines.append("  [confirmed] %d:%d — %s" % (r["line"], r["col"], r["note"]))

    if "stylometry" in report:
        import score_stylometry as S
        lines.append("")
        lines.append(S.render(report["stylometry"], explain=args.audit or args.explain))
    if "flagged_spans" in report:
        lines.append("")
        if report["flagged_spans"]:
            lines.append("  léxico vetado (%d coincidencias):" % len(report["flagged_spans"]))
            for s in report["flagged_spans"][:40]:
                lines.append("    %.2f  %d:%d  %s" % (s["weight"], s["line"], s["col"], s["text"]))
        else:
            lines.append("  léxico vetado: sin coincidencias")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Inspección de marcas de texto (solo lectura).")
    ap.add_argument("input", help="fichero de entrada, o '-' para stdin")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--stylometry", action="store_true",
                    help="añade el score de estilometría")
    ap.add_argument("--audit", action="store_true",
                    help="modo auditoría: hallazgos + estilometría + spans marcados, sin reescribir")
    ap.add_argument("--explain", action="store_true",
                    help="desglose de subscores de estilometría")
    ap.add_argument("--threshold", type=float, default=T.DEFAULT_THRESHOLD)
    args = ap.parse_args(argv)

    text = T.read_input(args.input)
    scanned = scan(text)
    actionable = [f for f in scanned["findings"] if f["confidence"] in T.ACTIONABLE]

    report = {
        "path": args.input,
        "kind": "text",
        "version": T.VERSION,
        "suspicious": bool(actionable or scanned["payload_runs"]),
        "actionable_count": sum(f["count"] for f in actionable),
        "findings": scanned["findings"],
        "payload_runs": scanned["payload_runs"],
    }

    exit_code = 1 if report["suspicious"] else 0

    if args.stylometry or args.audit:
        sty = T.score_text(text, threshold=args.threshold)
        report["stylometry"] = sty
        if args.audit and sty.get("above_threshold"):
            exit_code = 1
    if args.audit:
        report["flagged_spans"] = flagged_spans(T.strip_non_prose(text))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, args))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
