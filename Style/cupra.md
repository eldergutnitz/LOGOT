# CUPRA code style guide

Use this guide when generating CUPRA-styled digital interfaces.

## Colours

### Primary

| Colour | Value | Use |
|---|---|---|
| Black | `#000000` | Main backgrounds and dark surfaces |
| White | `#FFFFFF` | Text, icons and light surfaces |
| Tech Copper | Internal gradient | Material accents only; see rule below |

### Secondary

| Colour | Value |
|---|---|
| Enceladus Grey | `#46525B` |
| Moonslate | `#373B47` |
| Rio Green | `#606652` |
| Tobacco Brown | `#836A4E` |

Black and White should form the visual base. Use secondary colours as supporting accents, never as the dominant palette.

Tech Copper is a metallic material effect, not a flat colour. For internal interfaces, use the
gradient below when an approved copper image, texture or render is unavailable. Do not replace it
with a single sampled HEX.

```css
:root {
  --cupra-black: #000000;
  --cupra-white: #ffffff;
  --cupra-tech-copper-gradient: linear-gradient(
    90deg,
    #976f49 0%,
    #a07850 35%,
    #855d3b 62%,
    #52321e 82%,
    #2b190e 100%
  );
  --cupra-enceladus-grey: #46525b;
  --cupra-moonslate: #373b47;
  --cupra-rio-green: #606652;
  --cupra-tobacco-brown: #836a4e;
}
```

## Basic rules

- Prefer dark, high-contrast compositions based on Black and White.
- Use the Tech Copper gradient sparingly for material accents, highlights and selected surfaces in
  internal interfaces. Keep body text off the gradient unless contrast is verified.
- Keep secondary colours restrained and purposeful.
- Maintain readable contrast for text, icons and interactive states.
- Use official CUPRA logo assets; never redraw, distort or recolour them.
- Use the white logo by default and the black version only on light backgrounds where required for contrast.
- Use the complete logo by default. Use the symbol alone only when the surrounding context is unmistakably CUPRA.
- Do not invent additional brand colours, logo lockups or graphic treatments.
