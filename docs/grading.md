# Grading check (pre-grade estimate)

An **estimate** of the grade a card could get from PSA or similar companies, plus a calculation whether sending it in is worth it. It is not a replacement for the real grading and is not affiliated with PSA.

## What is reliable and what is not

| Part | How | Reliability |
| --- | --- | --- |
| **Centering** | you measure it on a photo with draggable lines, the app applies the published PSA limits | **objective and good** if the lines are placed carefully (a magnifier helps). Modern Pokémon borders are only about 2 to 3 mm wide, so every pixel counts |
| **Corners, edges, surface, print** | the vision AI judges your photos (including corner close-ups) | **rough estimate**: scratches, dents and fine print lines are hard to see on phone photos, sleeves and glare hide a lot |
| **Overall grade** | centering and sub-scores are combined ("the weakest point decides") | shown as a **range** with a confidence level. A 10 is only predicted for clean, sharp photos without sleeve and glare |

## Workflow

1. Open it from the menu (*Grading-Check*) or via the *Grading* button of a card in a card list (name and raw value are filled in).
2. **Photos:** take a photo with the device camera (high resolution) or pick one from the gallery. Front is required, back optional.
3. **Measure centering:** drag the **blue** lines to the outer card edge and the **yellow** lines to the inner border of the frame (where the picture starts). A magnifier shows the area while dragging. Borderless / full-art cards: tick *Zentrierung nicht messbar*.
4. **Estimate:** with the AI help set up (see [ai-scan.md](ai-scan.md)) the photo plus four corner crops per side go to the model; without AI only the centering is evaluated.
5. **Result:** grade with name (for example PSA 8 NM-MT), range, confidence and **what limits the grade most**. The sub-scores (corners, edges, surface, print; 1 to 10, half points) can be edited and recalculated, so you can correct the AI or work without it.
6. **Is it worth it?** Enter the grading cost and market prices for graded copies (PSA 7, 8, 9, 10). The app has no graded prices, use rough values, for example from sold eBay listings. It shows probability, value and profit per grade, the expected profit versus selling raw, the break-even grade and a verdict. The probabilities are a rough assumption around the estimated grade.
7. **Save** the estimate as a grading candidate; the *Gespeichert* list is sorted by grade.

## Centering limits used (published PSA values, approximate)

The worse of left/right and top/bottom counts (percentage of the wider border side).

| Grade | Front | Back |
| --- | --- | --- |
| PSA 10 | up to 55/45 | up to 75/25 |
| PSA 9 | up to 60/40 | up to 90/10 |
| PSA 8 | up to 65/35 | up to 90/10 |
| PSA 7 | up to 70/30 | up to 90/10 |
| PSA 6 | up to 80/20 | |
| PSA 5 | up to 85/15 | |
| PSA 3 | up to 90/10 | |

Check the current limits on the grader's website before submitting; they can change.

## Photo tips

Use the normal camera app (not the scan video), daylight or even light without flash, no glare (tilt the card and shoot several times), a plain background that contrasts with the card, **no sleeve or toploader**, camera straight above the card.

## Which AI?

Judging condition is harder than reading a card number. Google Gemini (Flash) usually gives better results; a local model via Ollama (for example `qwen3-vl:8b`) is rougher and needs longer for many images. See [ai-scan.md](ai-scan.md). With the free Gemini tier Google may use the images to improve its products.
