---
name: redaccion-humana
description: >-
  Redacta o reescribe prosa que tiene que sonar natural y humana, evitando los
  patrones formulaicos que delatan a la IA (baja perplejidad y baja
  burstiness): posts, artículos, entradas de blog, cartas, mensajes
  personales, textos divulgativos, guiones y copy. Úsala cuando el usuario
  pida escribir o reescribir un texto en prosa, o que un texto "no parezca de
  IA" o "suene humano", aunque no diga "humanizar". No la uses para la pasada
  final de limpieza de un texto ya terminado (eso es clean-user-facing-text),
  ni para emails y respuestas de trabajo de compras (eso es
  modo-de-respuesta), ni para entregables técnicos, regulatorios o
  contractuales (pliegos, especificaciones/EETT, contratos, cartas de oferta,
  informes normativos, documentación de ingeniería), donde la uniformidad y
  la precisión estandarizada son una virtud.
---

# Redacción humana (anti-huella de IA)

## Qué hace y por qué funciona

Los detectores comerciales (GPTZero, Originality.ai, Turnitin, Copyleaks) no buscan una "lista de palabras prohibidas": calculan dos señales estadísticas y las pasan por un clasificador entrenado sobre millones de muestras humanas y de IA.

1. **Perplejidad** — cómo de predecible es cada palabra para un modelo de referencia. El texto humano puntúa ~20-50 en benchmarks estándar de inglés; los LLM bajan a ~5-10. Esa baja perplejidad (elegir siempre la palabra más probable) es la huella.
2. **Burstiness** — cuánto varía la predecibilidad y la longitud de frase a lo largo del texto. El humano escribe "a ráfagas": agrupa frases cortas y contundentes y luego suelta una larga y subordinada. El modelo regresa a una longitud media, como un metrónomo (sujeto-verbo-objeto, sujeto-verbo-objeto).

Baja perplejidad + baja burstiness = alta probabilidad de marca. El objetivo de esta skill es **subir ambas de forma natural**, sin caer en rareza forzada (que también delata). La burstiness es la prioridad: es la señal más difícil de falsear y la que más pesa.

## Cuándo aplicarla y cuándo NO

**Aplícala** a prosa donde la naturalidad es el objetivo: divulgación, blog, redes, emails personales o comerciales, narrativa, guiones, copy, correspondencia.

**NO la apliques** a entregables técnicos, contractuales o regulatorios. Un pliego, una EETT, un contrato o un informe normativo usan lenguaje estandarizado y predecible **por diseño** para evitar ambigüedad; eso produce baja perplejidad y baja burstiness de forma natural, y los propios detectores admiten que marcan ese registro como "probable IA" aunque lo escriba una persona. Humanizar ahí rompe la precisión: es contraproducente. Ante la duda sobre el registro, pregunta antes de reescribir.

## A. Burstiness (prioritario — romper la uniformidad)

- Varía la longitud de frase de forma **visible y deliberada**. Alterna frases de 3-6 palabras con otras de 25-40. Nunca encadenes 3 o más frases seguidas de longitud parecida.
- Rompe el patrón sujeto-verbo-objeto. Arranca frases con una subordinada, con un complemento circunstancial, con "Y" o "Pero", con una pregunta, o con un fragmento sin verbo.
- **Asimetría de párrafos**: que no midan lo mismo. Uno puede ser una sola línea; el siguiente, siete. Los textos humanos son irregulares por naturaleza; los de IA, simétricos.
- Prohibida la **tríada simétrica** ("rápido, eficiente y escalable"): tres elementos de igual estructura y longitud es un tell clásico. Usa 2, 4 o 5 elementos de extensión desigual, o resuélvelo en prosa.

## B. Perplejidad léxica (elegir la palabra menos predecible)

Veta el léxico inflado. Lista de arranque; la ampliada está en `references/lexico-vetado.md`.

- **EN**: delve, robust, pivotal, meticulous, intricate, groundbreaking, seamless, leverage, foster, underscore, boasts, showcases, testament, myriad, tapestry, realm, elevate, unlock, unleash.
- **ES (uso genérico/comodín)**: crucial, esencial, fundamental, robusto (fuera de ingeniería), clave (como muletilla), sinergia, potenciar, impulsar (relleno), panorama, ecosistema (fuera de biología/tech real), desglosar, sumergirse, explorar (metafórico), abordar, enriquecer, transformador, sólido (metafórico).

Veta muletillas de apertura y cierre, que son el tell más visible:
- "es importante destacar/notar/mencionar que", "cabe señalar que", "en resumen", "en conclusión", "para concluir", "dicho esto", "espero que esto ayude/te sirva", "espero que este mensaje te encuentre bien", "no dudes en preguntar", "¡claro!", "¡aquí tienes!", "en el mundo actual/de hoy", "a medida que X sigue evolucionando".
- **EN**: "when it comes to", "it's worth noting", "in today's fast-paced world", "in the realm of", "firstly/secondly/thirdly".
- Nunca abras reformulando la pregunta ("Cuando hablamos de…"). Nunca cierres con una frase-resumen que repite lo ya dicho.

Prefiere siempre lo concreto sobre el adjetivo inflado: un dato, una cifra, un nombre propio o un ejemplo verificable en lugar de "solución integral y robusta".

## C. Tono y registro

- Usa contracciones y giros coloquiales cuando el idioma y el registro lo admitan. Permite elipsis, incisos y alguna imperfección deliberada. No escribas con gramática de manual todo el rato: los humanos no lo hacen.
- **No sobre-matices** (anti-hedging): evita el "por un lado… por otro lado…" mecánico, el falso equilibrio y el apilar salvedades. Da la conclusión o la opinión directa cuando proceda.
- Iguala el tono del interlocutor. Si escribe directo y sin preámbulo, responde igual: sin introducción de cortesía, sin cierre que resuma.

## D. Formato

- Evita listas con viñetas o numeradas salvo que el usuario las pida o el contenido sea genuinamente secuencial (pasos de un proceso). Por defecto, prosa conectada: la lista fragmentada y simétrica es un patrón de IA.
- Nada de emdashes (—) decorativos ni saturación de dos puntos como recurso estilístico recurrente.

## E. Autocontrol (pasada final obligatoria antes de entregar)

Relee el borrador y verifica, en este orden:
1. ¿Hay 3 o más frases seguidas de longitud similar? Reescribe una para romper el ritmo.
2. ¿Aparece alguna palabra o muletilla de la sección B? Sustitúyela por algo concreto.
3. ¿El texto abre reformulando la pregunta o cierra con un resumen genérico? Elimínalo.
4. ¿Las enumeraciones caen en tríadas o en ítems clónicos? Desiguálalos.

## Regla que no se negocia

No sacrifiques exactitud ni verdad por sonar humano. Si para redactar necesitas un dato que no tienes, dilo explícitamente; **no rellenes el hueco con vaguedad** para dar naturalidad. Un texto humano y falso es peor que uno correcto y algo formulaico.

## Ejemplos (antes → después)

**Ejemplo 1 — apertura y tríada**
- Antes: "En el mundo actual, la inteligencia artificial es una herramienta crucial, robusta y transformadora que está revolucionando múltiples sectores."
- Después: "La IA ya no es promesa. Está metida hasta la cocina en sanidad, banca y logística, y en cada sitio hace algo distinto: en un hospital lee radiografías, en un almacén decide qué camión sale antes."

**Ejemplo 2 — cierre y muletilla**
- Antes: "En conclusión, es importante destacar que estas estrategias pueden ayudarte a mejorar tus resultados. Espero que esto te sirva."
- Después: "Ninguna de estas tácticas es magia. Pero si aplicas dos y mides, en un mes sabrás si te sirven."

**Ejemplo 3 — ritmo (burstiness)**
- Antes: "El proyecto avanza según lo previsto. El equipo ha completado la primera fase. Los resultados son satisfactorios. La segunda fase comenzará pronto."
- Después: "El proyecto va en plazo. La primera fase está cerrada y los números salen bien, mejor de lo que esperábamos en la parte de integración. ¿La segunda? Arranca la semana que viene."

## Aviso honesto (dilo al usuario si el contexto lo pide)

Esta skill mejora la naturalidad y reduce la probabilidad de que un detector marque el texto, pero **no garantiza indetectabilidad**. El paper de la Universidad de Maryland "Can AI-Generated Text be Reliably Detected?" (2023) demostró que estos detectores no son fiables en la práctica, y GPTZero acumula falsos positivos documentados (Futurism midió una tasa que acusaría en falso a ~20% de estudiantes inocentes). Si el uso tiene consecuencias serias (académico, legal), advierte de que ningún método evade la detección de forma garantizada y que conviene cruzar varios detectores.
