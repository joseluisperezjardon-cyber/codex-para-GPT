# scripts/ para la skill `clean-user-facing-text`

Reconstrucción de los tres scripts que el `SKILL.md` invoca y que no venían en
el paquete sincronizado. Sin dependencias externas, sin red, Python 3.8+.

| Fichero | Papel |
| --- | --- |
| `_textlib.py` | Núcleo compartido: tablas Unicode, homóglifos, léxico vetado, métricas. **Los otros tres lo importan: no lo separes de ellos.** |
| `clean_text.py` | Layer A determinista (limpieza Unicode) |
| `score_stylometry.py` | Estimador de estilometría sin LLM |
| `inspect_text.py` | Inspección de marcas + auditoría (solo lectura) |

## Instalación

Copia los cuatro ficheros en `clean-user-facing-text/scripts/` dentro de tu
paquete de skill y vuelve a subirla. El `SKILL.md` resuelve `$SCRIPTS` a esa
carpeta, así que las llamadas que ya documenta funcionan tal cual:

```bash
python3 "$SCRIPTS/inspect_text.py" --stylometry --json INPUT
python3 "$SCRIPTS/inspect_text.py" --audit INPUT
python3 "$SCRIPTS/clean_text.py" INPUT -o OUTPUT --stats --no-normalize-spaces
python3 "$SCRIPTS/score_stylometry.py" INPUT --explain
```

## `clean_text.py`

Elimina, por defecto: tag characters (U+E0000–E007F, el canal de texto oculto
más usado), rellenos hangul invisibles, zero-width (U+200B, U+2060–2064,
U+FEFF, U+180E), anotación interlineal, soft hyphen, controles bidi y
selectores de variación sueltos. Sustituye tipografía de modelo (comillas
curvas → rectas, guion largo/corto → `-`, elipsis → `...`) y homóglifos
cirílicos/griegos **solo dentro de palabras mayoritariamente latinas**.

Conserva ZWJ/ZWNJ pegados a emoji o a escrituras que los necesitan (árabe,
hebreo, índicas, tailandés): ahí no son una marca, son ortografía.

| Flag | Efecto |
| --- | --- |
| `--no-normalize-spaces` | Deja NBSP y espacios exóticos como están (lo que recomienda el SKILL.md por defecto) |
| `--keep-typography` | No toca comillas curvas ni guiones largos |
| `--aggressive-homoglyphs` | Convierte **todo** confusable a ASCII. Destroza texto en cirílico o griego real: úsalo solo sobre texto que sabes que es latino |
| `--nfkc` | Normalización NFKC. Altera ligaduras, anchos y superíndices |
| `--strip-emoji-glue` | Quita también ZWJ y selectores de variación de los emoji (rompe emojis compuestos) |
| `--in-place` | Sobrescribe la entrada |
| `--stats` / `--json` | Informe de lo eliminado y sustituido, a stderr |

No protege bloques de código: si el fichero es Markdown con `​```fences```​`,
inspecciona primero las posiciones y limpia solo los tramos de prosa, como
indica el propio SKILL.md.

## `score_stylometry.py` / estimador

Cuatro señales sobre el texto en prosa (se descartan antes bloques de código,
código inline, URLs, tablas y ruido Markdown):

- **burstiness**: coeficiente de variación de la longitud de frase (peso 0,45)
- **cadencia IA**: densidad ponderada de léxico y coletillas vetadas por 100
  palabras, lista alineada con `redaccion-humana/references/lexico-vetado.md`
  (peso 0,30)
- **uniformidad**: fracción de frases dentro de rachas de longitud similar
  (peso 0,15)
- **diversidad léxica**: MATTR con ventana 50 (peso 0,10)

El compuesto se amortigua por longitud (factor 0,70–1,00 entre 30 y 250
palabras), porque en textos cortos cualquier métrica de dispersión es ruido.

| Tier | Rango | Qué hacer |
| --- | --- | --- |
| `high` | ≥ 0,65 | Reescribir (Layer B) |
| `medium` | 0,45–0,65 | Verificar a mano; no reescribir por sistema |
| `low` | < 0,45 | No tocar |
| `uncalibrated` | < 30 palabras | `status: insufficient_length` |

Códigos de salida: `score_stylometry.py` devuelve 1 si el score alcanza el
umbral (`--threshold`, 0,65 por defecto). `inspect_text.py` devuelve 1 si hay
hallazgos accionables (`confirmed` o `probable`) o, en `--audit`, si además el
score alcanza el umbral. 0 en caso contrario, 2 en error de uso.

Calibración de referencia con los textos de prueba usados al construirlo:
prosa tipo IA con coletillas 0,73 (`high`); prosa técnica real con frases
irregulares 0,00 (`low`); prosa correcta pero metronómica, sin léxico vetado,
0,47 (`medium`).

## Límites (dilos siempre)

Esto mide la familia de detectores **estadísticos** (perplejidad y burstiness).
No es GPTZero, Turnitin, Originality ni Pangram; no detecta marcas de agua con
clave secreta; no dice nada sobre autoría. Un score bajo significa que las
señales medibles se han movido, no que un detector concreto vaya a aceptar el
texto. `inspect_text.py` no reescribe nunca y `clean_text.py` no cambia el
contenido: no reordena, no traduce, no añade ni quita afirmaciones.
