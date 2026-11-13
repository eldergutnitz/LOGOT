# SEAT vehicle brand code style guide

Use this guide for SEAT vehicle-brand interfaces. Do not use it for SEAT S.A. corporate communications.

## Core colours

| Colour | Value | Use |
|---|---|---|
| Liminal Red | `#FF0036` | Main brand colour; accents or backgrounds |
| Nevada White | `#F5F5F5` | Primary light background or accent on red |
| Candy White | `#EBE9E8` | Warm light background or accent on red |
| Midnight Black | `#191919` | Text and primary logo colour |

## Additional colours

| Colour | Value | Pair with |
|---|---|---|
| Violet | `#8B4BE2` | Green |
| Green | `#A4F48A` | Violet |
| Pink | `#E128EF` | Yellow |
| Yellow | `#EEFE42` | Pink |
| Dark Green | `#0A2B2F` | Soft Pink |
| Soft Pink | `#F78BFF` | Dark Green |
| Blue | `#1B0F4D` | Soft Green |
| Soft Green | `#55E4C0` | Blue |

```css
:root {
  --seat-red: #ff0036;
  --seat-nevada-white: #f5f5f5;
  --seat-candy-white: #ebe9e8;
  --seat-midnight-black: #191919;
  --seat-violet: #8b4be2;
  --seat-green: #a4f48a;
  --seat-pink: #e128ef;
  --seat-yellow: #eefe42;
  --seat-dark-green: #0a2b2f;
  --seat-soft-pink: #f78bff;
  --seat-blue: #1b0f4d;
  --seat-soft-green: #55e4c0;
}
```

## Basic rules

- Use Liminal Red as the main identifier, either as a focused accent or a balanced background.
- On Nevada or Candy White, use Liminal Red for the symbol and key headings; use Midnight Black for smaller text.
- On Liminal Red, use Candy or Nevada White for the logo and large headings; use Midnight Black only for small text.
- Never combine Liminal Red with the additional colours.
- Additional colours may be used alone or in the approved pairs shown above. Avoid visual saturation and verify contrast.
- Keep the visual style bold, colourful, youthful and high-energy, with generous open space.
- Use the filled `S` symbol for external campaigns and digital applications when SEAT is already clearly identified. Use the full lockup when brand recognition must be reinforced.
- Reserve the outline symbol for large physical or event applications; do not use it at small digital sizes.
- Use official logo assets only. Midnight Black is the default logo colour; Liminal Red and the two Whites are optional approved alternatives.
