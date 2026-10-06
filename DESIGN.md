# Launcher design

## Theme

Two palettes share one structure and switch live from the header button; the initial
choice follows the Windows apps preference (AppsUseLightTheme). Tk needs sRGB hex values,
so the tokens are sRGB approximations of low-chroma neutrals.

- Dark (primary): background #14161a, surface #1c2026, field #22262d, tab #191c21,
  border #30353d, ink #e9e6dd, muted #9ba1a9, accent (hunter gold) #c9a227,
  accent hover #dcb63c, on-accent #17130a, summary tint #2a2517.
- Light: background #f2f1ec, surface #fbfaf6, field #ffffff, tab #e9e7dd,
  border #d8d4c8, ink #24201a, muted #6b6558, accent #8a6d1f, on-accent #fffdf4,
  summary tint #efe9d6.

The accent marks primary actions, the selected tab and the brand only; red stays reserved
for errors. Body text keeps at least 4.5:1 contrast against its background in both themes.

## Typography

One family: Microsoft YaHei UI (10pt body, 12pt bold section headings, 24pt bold title),
plus a Georgia "BLOODBORNE" wordmark in the accent colour. No display fonts in controls.

## Layout

All pixel sizes run through px(), a scale factor from the monitor DPI: per-monitor DPI
awareness is enabled before Tk starts and tk scaling is set so point sizes follow the same
DPI. The window measures the tallest tab and sizes itself so nothing is clipped. Form rows
align on a shared label column with consistent control widths. Save and launch stay at the
bottom, launch visually primary.

## Images

tools/build_launcher_assets.py generates launcher_assets/hero_{dark,light}[@2x].png from
the poster artwork (skyline crop, rounded corners, fade into the theme background). The
launcher loads them with plain Tk and falls back to a text-only header when absent; these
files stay out of git like the other artwork (*.png and *.jpg are ignored).

## Components

Native ttk controls only. Checkbuttons render as solid-filled boxes when on (clam's
X-shaped mark is painted in the fill colour so a checked box never reads as "canceled").
Comboboxes are readonly with themed dropdown lists. Keyboard focus stays visible, and the
combobox listboxes re-theme when the palette switches.
