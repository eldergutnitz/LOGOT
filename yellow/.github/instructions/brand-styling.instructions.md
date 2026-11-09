---
applyTo: "**/*.{html,htm,css,scss,jsx,tsx}"
---

# Visual style — user-led, brand-aware

## Choose the direction

1. Follow an explicit aesthetic, palette or reference from the user.
2. If the user requests CUPRA, SEAT S.A. corporate, or the SEAT vehicle brand, apply only that
   brand's rules below. Never mix identities unless explicitly requested.
3. With no visual direction, extend the repository's existing design system. For a greenfield UI,
   choose an intentional direction appropriate to its users and content; do not ship a generic
   Bootstrap/dashboard/AI-template look.
4. Explicit overrides win. If an override conflicts with a requested brand, follow it without
   claiming strict brand compliance. Never imply official approval from generated styling.

## Every interface

- Meet WCAG 2.2 AA: body-text contrast at least 4.5:1; large text and UI boundaries at least 3:1.
- Use semantic structure, associated labels, keyboard-operable controls, visible focus and
  reduced-motion support. Never encode meaning in colour alone.
- Define reusable tokens once. Preserve the repository's token naming and component conventions.
- Design hierarchy, spacing and loading/empty/error/disabled/hover/focus states deliberately.
- Use official, licensed logo/font assets already available to the project. Do not redraw, distort,
  recolour or fetch brand assets/fonts from an unapproved public CDN.

## CUPRA

- Base: Black `#000000` and White `#FFFFFF`. Keep the composition dark, sharp and high-contrast.
- Tech Copper is a material treatment, not one flat HEX. Prefer an approved image/texture/render.
  For internal UI only, when no approved asset exists, use this shared fallback sparingly:
  `linear-gradient(90deg,#976F49 0%,#A07850 35%,#855D3B 62%,#52321E 82%,#2B190E 100%)`.
- Supporting colours may include Enceladus Grey `#46525B`, Moonslate `#373B47`, Rio Green `#606652`
  and Tobacco Brown `#836A4E`; they must not dominate or compete with copper.
- Keep body text off copper unless measured contrast passes. Prefer the official white logo; use the
  black version on light backgrounds when required. Use the full logo unless context is unmistakable.

## SEAT S.A. corporate

- Tokens: Matte Black `#2C2A29`, Sand `#B3A097`, Terracote `#E1523D`, Lime `#C8F446`, Petrol
  `#003E51`.
- Use Matte Black text on Sand/Terracote and Sand text on Petrol. Use Lime sparingly for highlights
  or simple line illustration over Sand, Terracote or Petrol. **Never use Lime on White.**
- Prefer structured layouts with large colour fields and clear content separation. Keep photography
  black and white with softened contrast.
- Use only the official combined SEAT S.A. logo, on White, Sand or Black and never directly over a
  photograph. Do not separate its elements.

## SEAT vehicle brand

- Core tokens: Liminal Red `#FF0036`, Midnight Black `#191919`, Candy White `#EBE9E8`, Nevada White
  `#F5F5F5`. Use Liminal Red as a focused identifier or balanced background, not ubiquitous colour.
- On light neutrals, use red for the symbol/key headings and black for smaller text. On red, use a
  white for logo/large headings and black only where measured contrast and brand guidance allow.
- Never combine Liminal Red with the additional palette. Additional colours may be used alone or
  only in these pairs: Violet `#8B4BE2` + Green `#A4F48A`; Pink `#E128EF` + Yellow `#EEFE42`;
  Dark Green `#0A2B2F` + Soft Pink `#F78BFF`; Blue `#1B0F4D` + Soft Green `#55E4C0`.
- Keep the result bold and energetic with open space. Use official logo assets only. Use the filled
  S symbol when SEAT is already clear; otherwise use the full lockup. Reserve the outline symbol for
  large physical/event applications, not small digital UI.
