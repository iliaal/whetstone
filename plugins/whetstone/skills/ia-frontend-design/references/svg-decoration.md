# SVG decoration

Use this reference for decorative inline SVG. Keep decoration distinct from charts, measured routes, or live connection status; never imply evidence that the illustration does not represent.

1. Give each component instance unique gradient, mask, and clip-path IDs. Derive every matching fragment reference from the same instance prefix. In React, use [`useId`](https://react.dev/reference/react/useId) where supported; pass a unique prefix into async Server Components instead. Render two instances together to catch ID collisions.
2. Inline SVG that needs page custom properties or `currentColor`. Treat SVG loaded through `<img>` or a CSS image URL as a separate image document; page theme tokens do not inherit into it. For fixed-color assets, external image files remain suitable. See [SVG image integration](https://svgwg.org/specs/integration/) and [image property inheritance](https://svgwg.org/svg2-draft/embedded.html).
3. Mark purely decorative inline SVG `aria-hidden="true" focusable="false"`. Set `pointer-events: none` and remove focusable descendants. Keep meaningful graphics out of this hidden decoration path.
4. Size the containing region explicitly. Keep decorative overlays out of content sizing and contain their overflow locally, without clipping content or focus indicators. Check that the narrow layout has no horizontal scrolling caused by the SVG.
5. Choose the `viewBox`, alignment, and [`preserveAspectRatio`](https://svgwg.org/svg2-draft/coords.html#PreserveAspectRatioAttribute) together. Use `meet` to show the whole composition, `slice` to fill the viewport with cropping, and `none` only when non-uniform stretching is intended. Compose a deliberate narrow-viewport crop instead of shrinking an unreadable desktop illustration.

Verify repeated instances, theme changes, narrow/wide crops, and keyboard navigation. Confirm that decorative paths neither intercept controls nor resemble unsupported measurements.
