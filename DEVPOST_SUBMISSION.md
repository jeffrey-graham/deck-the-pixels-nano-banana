# Deck the Pixels 2026 — Devpost Submission Write-Up

## Project Title
**Deck the Pixels: Nano Banana Fair-Isle Holiday Studio & 5-Layer Photoshop Card**

## Tagline
Designing a tactile PCB-and-banana knitted Ugly Holiday Sweater with Google Nano Banana, dressing a 3D coder avatar in the exact garment, and compositing a 5-layer spec-compliant Adobe Photoshop (`.psd`) holiday card.

## Live Links
- **Interactive Showcase & Live 5-Layer PSD Inspector:** [https://jeffrey-graham.github.io/deck-the-pixels-nano-banana/](https://jeffrey-graham.github.io/deck-the-pixels-nano-banana/)
- **GitHub Repository (Source, `.PSD` Binary & Unit Verifier):** [https://github.com/jeffrey-graham/deck-the-pixels-nano-banana](https://github.com/jeffrey-graham/deck-the-pixels-nano-banana)

---

## Inspiration
Holiday cards for software engineers rarely capture both the cozy warmth of traditional winter knitwear and the playful spirit of pixel art and generative AI. When Google launched **Deck the Pixels**, we wanted to treat the challenge like an authentic apparel-to-portrait creative studio: first crafting a genuinely wearable, macro-textured *"DECK THE PIXELS"* Ugly Holiday Sweater using **Nano Banana**, then proving multi-step garment consistency by placing that exact knitted sweater onto a 3D developer avatar inside a snow-lit cabin, and finally structuring the finished card as a clean, non-destructive **5-layer Adobe Photoshop `.psd`** file.

---

## What It Does
Our submission delivers an end-to-end 3-stage holiday card studio and interactive web showcase:

1. **Step 1 — Nano Banana Ugly Holiday Sweater (`assets/ugly_holiday_sweater.jpg`):**
   A `1024×1024` studio flatlay of a royal-blue, crimson, and cream Fair Isle wool sweater featuring knitted *"DECK THE PIXELS"* chest typography, 8-bit Santa-hat Nano Bananas, pixel reindeer, glowing green circuit-board traces along the hem, tactile 3D wool pom-poms, and metallic holiday tinsel.
2. **Step 2 — Developer Avatar Cabin Integration (`assets/developer_avatar_holiday_card.jpg`):**
   Using Nano Banana's reference consistency, our friendly 3D developer avatar wears the exact knitted sweater inside a cozy winter coding cabin—complete with a code monitor on the desk, snow falling past a moonlit window, pixel stockings over a crackling fireplace, and a steaming holiday cocoa mug.
3. **Step 3 — Spec-Compliant 5-Layer Adobe Photoshop Card (`assets/deck_the_pixels_holiday_card.psd`):**
   A genuine multi-layer `.psd` (`8BPS` v1, `896×1200`, 8-bit RGBA channels) containing five named layers that judges can open in Adobe Photoshop, Photopea, GIMP, or toggle live in our browser-based **Interactive 5-Layer PSD Inspector**:
   - `01_Winter_Cabin_Backdrop` — Diffused snowy cabin interior backdrop stage.
   - `02_Nano_Banana_Sweater_Flatlay` — Alpha-isolated Step 1 sweater flatlay aligned directly behind the avatar's torso for instant garment-consistency comparison.
   - `03_Avatar_Wearing_Sweater` — Foreground 3D developer avatar wearing the integrated sweater.
   - `04_Pixel_Banana_Holly_Frame` — Evergreen pine boughs, red holly berries, pixel reindeer, Santa-hat banana crest, and inner gold trim.
   - `05_Holiday_Card_Typography` — Velvet evergreen greeting ribbon with crisp gold serif *"HAPPY HOLIDAYS • DECK THE PIXELS 2026"* typography and removable studio stamp.

---

## How We Built It (Nano Banana + Photoshop Multi-Layer Workflow)
1. **Prompt Engineering for Textile & Pixel Fidelity (Nano Banana):**
   In Step 1, we prompted Nano Banana specifically for macro-photography knit stitch geometry—combining retro pixel-art motifs (Santa-hat bananas, 8-bit CRT monitor, reindeer, and PCB traces) with physical craft embellishments (3D yarn pom-poms and gold/green tinsel) on a neutral studio flatlay so the garment silhouette could be cleanly alpha-masked.
2. **Garment-Consistent Avatar Portrait Synthesis (Nano Banana):**
   In Step 2, we anchored the character portrait on the Step 1 sweater design so the chest lettering (*"DECK THE PIXELS"*), shoulder banana motifs, red-and-green ribbed collar, and pom-pom placements wrapped naturally around the 3D avatar's shoulders and arms while holding a marshmallow-topped cocoa mug.
3. **Multi-Layer Adobe Photoshop `.PSD` Engineering (`scripts/build_psd_and_video.py`):**
   We decomposed the visual elements into 5 distinct `896×1200` RGBA layers—extracting alpha masks for the studio sweater flatlay, cabin portrait window, evergreen pixel-holly frame, and vector-sharp typography ribbon—and wrote a deterministic Adobe Photoshop `8BPS` v1 binary serializer complete with `0x03ED` 72-DPI `ResolutionInfo`, 4-byte padded Pascal-string Layer Records, per-layer RGBA channels (`0, 1, 2, -1`), and merged planar RGB composite data.
4. **Automated PSD Spec Verification & Interactive Web Showcase:**
   We wrote `tests/test_psd_spec.py` to verify every header field, channel length, and layer name against both the Adobe PSD binary specification and Python Pillow's independent `PsdImagePlugin` reader, and built an interactive GitHub Pages showcase + 45-second 1080p walkthrough video (`assets/deck_the_pixels_showcase.mp4`).

---

## Challenges We Ran Into
- **Maintaining Knit Typography & Motif Consistency Across Steps 1 and 2:** Keeping *"DECK THE PIXELS"* legible as actual knitted stitches—while curving naturally across a 3D character's chest behind a steaming mug—required careful composition framing so neither the lettering nor the signature Santa-hat shoulder bananas were occluded.
- **Strict Binary Alignment in Multi-Layer `.PSD` Files:** Adobe Photoshop `.psd` v1 requires exact big-endian byte alignment: Layer Record Pascal strings must be padded to 4-byte multiples, `Layer Info` payloads must be padded to even byte lengths, per-layer channel blocks each carry their own 2-byte compression header while the final merged composite image carries a single shared compression header followed by planar `R`, `G`, `B` arrays. Building an automated binary & `PsdImagePlugin` unit test caught and verified every byte offset.

---

## Accomplishments That We're Proud Of
- Seamless visual continuity from the **Step 1 flatlay sweater** to the **Step 2 cabin portrait**—verified interactively by toggling `03_Avatar_Wearing_Sweater` off in our PSD inspector to reveal `02_Nano_Banana_Sweater_Flatlay` aligned directly underneath.
- Delivering both a **downloadable, Photoshop-ready 5-layer `.psd`** and a **zero-install browser Layer Inspector** so anyone can explore the layer stack instantly.

---

## What We Learned
Combining generative image models like **Google Nano Banana** with structured, non-destructive **Photoshop layer pipelines** unlocks the best of both worlds: Nano Banana excels at rich material textures (knitted wool, warm cabin tungsten lighting, 3D subsurface scattering), while explicit `.psd` layer separation gives designers crisp control over framing, borders, and typography.

---

## What's Next for Deck the Pixels Studio
- Adding customizable greeting text & recipient name presets directly inside the web Layer Inspector with client-side `.psd` and print-ready `300 DPI` PDF export for developer teams sending holiday cards.
