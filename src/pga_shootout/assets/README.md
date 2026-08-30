# UI resources

Source: user-supplied `PGA_Shootout_Graphic_Kit_with_brand_colors.zip`.
Only club PNGs and the nine brand palettes are used. No ability text or numerical
club data from the kit is imported into the engine. Club statistics and identity
remain sourced from the existing official catalogue.

The 88 thumbnails are prepared offline with `scripts/prepare_graphic_kit.py`.
The kit spells one filename `endeavour`; the catalogue uses `endeavor`. This
asset-only spelling reconciliation does not change either the catalogue or rules.
Runtime uses Tk PhotoImage; missing artwork has a text fallback.

Original artwork and brand identities belong to their respective rights holders.
The supplied kit is not treated as a new license grant.
