#!/usr/bin/env python3
"""Estimador de estilometría sin LLM (burstiness + cadencia IA + MATTR).

    python3 score_stylometry.py INPUT [--json] [--explain] [--threshold 0.65]

Salida: score compuesto 0-1 amortiguado por longitud, density_tier
(low / medium / high / uncalibrated) y las métricas que lo componen.
Código de salida 1 si el score alcanza el umbral (0.65 por defecto).

Límites (dilos siempre al usuario): esto calibra contra la familia de
detectores estadísticos (perplejidad/burstiness). No es GPTZero, Turnitin,
Originality ni Pangram, no detecta marcas de agua con clave secreta y no
dice nada sobre autoría. Un score bajo significa que las señales medibles
se han movido, no que un detector concreto vaya a aceptar el texto.
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import _textlib as T  # noqa: E402

TIER_HINT = {
    "high": "reescribir (Layer B): la huella estadística es alta",
    "medium": "verificar a mano; no reescribir por sistema",
    "low": "no reescribir: las señales medibles son débiles",
    "uncalibrated": "texto demasiado corto para puntuar",
}


def render(report: dict, explain: bool = False, path: str = "") -> str:
    if report["status"] == "insufficient_length":
        return ("estilometría: insufficient_length (%d palabras, mínimo %d) — tier %s"
                % (report["words"], report["min_words"], report["density_tier"]))

    m = report["metrics"]
    lines = [
        "estilometría %s%s" % (T.VERSION, (" — " + path) if path else ""),
        "  score          %.3f  (umbral %.2f, %s)" % (
            report["score"], report["threshold"],
            "POR ENCIMA" if report["above_threshold"] else "por debajo"),
        "  density_tier   %s  -> %s" % (report["density_tier"],
                                        TIER_HINT[report["density_tier"]]),
        "  confianza      %s  (%d palabras, %d frases)" % (
            report["confidence"], report["words"], report["sentences"]),
        "  burstiness CV  %.3f  (frase media %.1f palabras, sd %.1f)" % (
            m["burstiness_cv"], m["sentence_len_mean"], m["sentence_len_sd"]),
        "  cadencia IA    %.2f por 100 palabras  (%d coincidencias)" % (
            m["ai_phrase_density_per_100w"], m["ai_phrase_hits"]),
        "  MATTR-50       %.3f" % m["mattr_50"],
        "  uniformidad    %.0f%% de las frases en rachas de longitud similar" % (
            m["uniform_run_fraction"] * 100),
    ]
    if explain:
        s = report["subscores"]
        lines.append("  subscores (1.0 = máxima huella):")
        lines.append("    burstiness %.2f x0.45 | cadencia %.2f x0.30 | "
                     "uniformidad %.2f x0.15 | léxico %.2f x0.10"
                     % (s["burstiness"], s["ai_phrases"], s["uniformity"],
                        s["lexical_diversity"]))
        lines.append("    raw %.3f -> amortiguado por longitud -> %.3f"
                     % (report["raw_score"], report["score"]))
        if m["uniform_runs"]:
            runs = ", ".join("%d-%d" % (r["from_sentence"], r["to_sentence"])
                             for r in m["uniform_runs"])
            lines.append("    rachas uniformes (frases): " + runs)
        if report["top_phrases"]:
            lines.append("  coincidencias de léxico vetado:")
            for h in report["top_phrases"]:
                lines.append("    %.2f  %s" % (h["weight"], h["text"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Estimador de estilometría sin LLM.")
    ap.add_argument("input", help="fichero de entrada, o '-' para stdin")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--explain", action="store_true",
                    help="desglose de subscores y coincidencias")
    ap.add_argument("--threshold", type=float, default=T.DEFAULT_THRESHOLD,
                    help="umbral de score para el código de salida (por defecto 0.65)")
    args = ap.parse_args(argv)

    text = T.read_input(args.input)
    report = T.score_text(text, threshold=args.threshold)
    report["path"] = args.input

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, args.explain, args.input))

    return 1 if report.get("above_threshold") else 0


if __name__ == "__main__":
    raise SystemExit(main())
