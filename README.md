# Deck the Pixels 2026 — Nano Banana Holiday Sweater Studio & 5-Layer Photoshop `.PSD`

[![Live Showcase](https://img.shields.io/badge/Live_Showcase-GitHub_Pages-F5C85C?style=for-the-badge)](https://jeffrey-graham.github.io/deck-the-pixels-nano-banana/)

Submission package for Google's **$25,000 Deck the Pixels** Hackathon combining **Google Nano Banana** image generation with a spec-compliant **5-Layer Adobe Photoshop (`.psd`)** holiday card pipeline.

## Included Deliverables

- **Step 1 — Ugly Holiday Sweater (`assets/ugly_holiday_sweater.jpg`):** `1024×1024` Nano Banana Fair Isle knitted sweater featuring *"DECK THE PIXELS"*, Santa-hat pixel bananas, reindeer, PCB circuit traces, 3D yarn pom-poms, and metallic tinsel.
- **Step 2 — Developer Avatar Integration (`assets/developer_avatar_holiday_card.jpg`):** Consistent 3D coder avatar wearing the exact Step 1 sweater inside a snow-lit developer cabin.
- **Step 3 — Multi-Layer Adobe Photoshop File (`assets/deck_the_pixels_holiday_card.psd`):** Spec-compliant `8BPS` v1 multi-layer `.psd` (`896×1200`, 8-bit RGBA) with 5 distinct named layers:
  1. `01_Winter_Cabin_Backdrop`
  2. `02_Nano_Banana_Sweater_Flatlay`
  3. `03_Avatar_Wearing_Sweater`
  4. `04_Pixel_Banana_Holly_Frame`
  5. `05_Holiday_Card_Typography`
- **45-Second 1080p Video Showcase (`assets/deck_the_pixels_showcase.mp4`)**
- **Interactive Showcase & Live 5-Layer Browser Inspector (`index.html`)**
- **Devpost Submission Write-Up (`DEVPOST_SUBMISSION.md`)**

## Build & Verify

```bash
# Build the 5-layer .PSD file, layer PNGs, and 45-second 1080p showcase MP4
python3 scripts/build_psd_and_video.py

# Run binary PSD spec & Pillow PsdImagePlugin verification tests
python3 -m unittest discover -s tests -v
```
