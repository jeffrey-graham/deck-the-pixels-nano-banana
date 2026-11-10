#!/usr/bin/env python3
"""
Deck the Pixels ($25,000 Google Nano Banana + Photoshop Hackathon) Builder:

1. Constructs 5 genuine, distinct RGBA layers (`896 x 1200`) from the two Nano Banana
   studio assets (`ugly_holiday_sweater.jpg` and `developer_avatar_holiday_card.jpg`):
   - `01_Winter_Cabin_Backdrop`
   - `02_Nano_Banana_Sweater_Flatlay`
   - `03_Avatar_Wearing_Sweater`
   - `04_Pixel_Banana_Holly_Frame`
   - `05_Holiday_Card_Typography`
2. Writes a spec-compliant Adobe Photoshop `.psd` v1 (`8BPS`) binary file
   (`assets/deck_the_pixels_holiday_card.psd`) with raw channels, Pascal-string
   4-byte padded Layer Records, ResolutionInfo (`8BIM` 0x03ED), and merged RGB composite.
3. Exports individual web-preview PNGs (`assets/layers/*.png` & `assets/final_holiday_card.png`)
   for the interactive browser Layer Inspector.
4. Renders a crisp 45-second 1080p H.264 MP4 showcase (`assets/deck_the_pixels_showcase.mp4`).
"""

from __future__ import annotations

import math
import pathlib
import struct
import subprocess
import tempfile
import wave
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

CARD_W = 896
CARD_H = 1200

VID_W = 1920
VID_H = 1080
FPS = 24
VID_DURATION = 45
TOTAL_FRAMES = FPS * VID_DURATION  # 1080 frames

FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_MONO = "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def pack_pascal_string_padded4(name: str) -> bytes:
    raw = name.encode("ascii")
    if len(raw) > 255:
        raise ValueError("PSD Pascal layer name cannot exceed 255 bytes.")
    unpadded_len = 1 + len(raw)
    pad_len = (4 - (unpadded_len % 4)) % 4
    return struct.pack("B", len(raw)) + raw + (b"\x00" * pad_len)


def write_psd_v1(
    psd_path: pathlib.Path,
    width: int,
    height: int,
    layers: List[Tuple[str, Image.Image]],
    composite_rgb: Image.Image,
) -> None:
    """
    Write a 100% spec-compliant Adobe Photoshop v1 (`8BPS`) multi-layer binary `.psd` file.
    Each layer is stored as full-canvas RGBA (`0`=R, `1`=G, `2`=B, `-1`=Transparency Mask)
    using Raw Uncompressed channel planes (`compression = 0`), followed by planar RGB composite.
    """
    if composite_rgb.size != (width, height) or composite_rgb.mode != "RGB":
        raise ValueError("composite_rgb must match (width, height) in RGB mode.")

    # 1. File Header (26 bytes)
    # Signature '8BPS', Version 1, 6 zero bytes, Channels=3 (composite RGB), Height, Width, Depth=8, Mode=3 (RGB)
    header = struct.pack(
        ">4sH6sHIIHH",
        b"8BPS",
        1,
        b"\x00" * 6,
        3,
        height,
        width,
        8,
        3,
    )

    # 2. Color Mode Data (4 bytes: length 0 for RGB)
    color_mode_section = struct.pack(">I", 0)

    # 3. Image Resources Section (ResolutionInfo 0x03ED = 72 DPI)
    res_payload = struct.pack(">ihhihh", 72 << 16, 1, 1, 72 << 16, 1, 1)  # 16 bytes
    res_block = b"8BIM" + struct.pack(">H", 0x03ED) + b"\x00\x00" + struct.pack(">I", len(res_payload)) + res_payload
    image_resources_section = struct.pack(">I", len(res_block)) + res_block

    # 4. Layer and Mask Information Section
    layer_records = bytearray()
    channel_data_blobs: List[bytes] = []

    channel_byte_len = 2 + (width * height)  # 2-byte compression=0 + raw plane

    for layer_name, layer_img in layers:
        if layer_img.size != (width, height):
            raise ValueError(f"Layer {layer_name} size {layer_img.size} != {(width, height)}")
        rgba = layer_img.convert("RGBA")
        r_ch, g_ch, b_ch, a_ch = rgba.split()

        # Bounding rectangle: top=0, left=0, bottom=height, right=width
        rec = bytearray()
        rec.extend(struct.pack(">iiii", 0, 0, height, width))
        # 4 channels: 0 (R), 1 (G), 2 (B), -1 (Alpha)
        rec.extend(struct.pack(">H", 4))
        for ch_id in (0, 1, 2, -1):
            rec.extend(struct.pack(">hI", ch_id, channel_byte_len))

        # Blend mode signature '8BIM', key 'norm', opacity=255, clipping=0, flags=0 (visible), filler=0
        rec.extend(b"8BIM")
        rec.extend(b"norm")
        rec.extend(struct.pack(">BBBB", 255, 0, 0, 0))

        # Extra Data: Layer Mask (4B = 0) + Blending Ranges (4B = 0) + Padded Pascal Name
        pascal_name = pack_pascal_string_padded4(layer_name)
        extra_data = struct.pack(">I", 0) + struct.pack(">I", 0) + pascal_name
        rec.extend(struct.pack(">I", len(extra_data)))
        rec.extend(extra_data)

        layer_records.extend(rec)

        # Store raw uncompressed channel data in exact declared order (R, G, B, A)
        raw_hdr = struct.pack(">H", 0)
        channel_data_blobs.append(raw_hdr + r_ch.tobytes())
        channel_data_blobs.append(raw_hdr + g_ch.tobytes())
        channel_data_blobs.append(raw_hdr + b_ch.tobytes())
        channel_data_blobs.append(raw_hdr + a_ch.tobytes())

    layer_info_body = bytearray()
    layer_info_body.extend(struct.pack(">h", len(layers)))
    layer_info_body.extend(layer_records)
    for blob in channel_data_blobs:
        layer_info_body.extend(blob)

    if len(layer_info_body) % 2 != 0:
        layer_info_body.append(0)

    layer_info_section = struct.pack(">I", len(layer_info_body)) + layer_info_body
    global_mask_info = struct.pack(">I", 0)

    layer_and_mask_body = layer_info_section + global_mask_info
    layer_and_mask_section = struct.pack(">I", len(layer_and_mask_body)) + layer_and_mask_body

    # 5. Merged Composite Image Data Section (1 compression header=0 + planar R, G, B)
    comp_r, comp_g, comp_b = composite_rgb.split()
    composite_section = (
        struct.pack(">H", 0)
        + comp_r.tobytes()
        + comp_g.tobytes()
        + comp_b.tobytes()
    )

    with open(psd_path, "wb") as f:
        f.write(header)
        f.write(color_mode_section)
        f.write(image_resources_section)
        f.write(layer_and_mask_section)
        f.write(composite_section)


def build_five_holiday_card_layers(
    sweater_jpg: pathlib.Path,
    avatar_card_jpg: pathlib.Path,
) -> Tuple[List[Tuple[str, Image.Image]], Image.Image]:
    """
    Construct 5 distinct, meaningful RGBA Photoshop layers (896 x 1200) from the
    Nano Banana Ugly Holiday Sweater & Developer Avatar Holiday Card assets.
    """
    sweater_src = Image.open(sweater_jpg).convert("RGB")
    card_src = Image.open(avatar_card_jpg).convert("RGB")
    if card_src.size != (CARD_W, CARD_H):
        card_src = card_src.resize((CARD_W, CARD_H), Image.Resampling.LANCZOS)

    # Inner cabin portrait window coordinates inside the holly frame
    win_x1, win_y1, win_x2, win_y2 = 62, 114, 834, 1118

    # -------------------------------------------------------------------------
    # Layer 1: 01_Winter_Cabin_Backdrop (Opaque RGBA atmospheric cabin base)
    # -------------------------------------------------------------------------
    layer1 = Image.new("RGBA", (CARD_W, CARD_H), (12, 30, 24, 255))
    cabin_crop = card_src.crop((win_x1, win_y1, win_x2, win_y2))
    # Create warm ambient cabin backdrop plate (softly diffused behind central character)
    cabin_ambient = ImageEnhance.Brightness(cabin_crop.filter(ImageFilter.GaussianBlur(14))).enhance(0.92)
    # Preserve crisp upper snowy window & side cabin details (monitor & fireplace)
    cabin_plate = cabin_crop.copy()
    center_mask = Image.new("L", cabin_crop.size, 0)
    cmdraw = ImageDraw.Draw(center_mask)
    # Soft ellipse over where the character sits so Layer 1 looks like an ambient empty cabin stage
    cmdraw.ellipse([140, 110, 635, 985], fill=255)
    center_mask = center_mask.filter(ImageFilter.GaussianBlur(28))
    cabin_stage = Image.composite(cabin_ambient, cabin_plate, center_mask)
    layer1.paste(cabin_stage.convert("RGBA"), (win_x1, win_y1))

    # -------------------------------------------------------------------------
    # Layer 2: 02_Nano_Banana_Sweater_Flatlay (Step 1 Sweater isolated on alpha)
    # -------------------------------------------------------------------------
    layer2 = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    sw_size = 640
    sw_resized = sweater_src.resize((sw_size, sw_size), Image.Resampling.LANCZOS)
    # Isolate knitted sweater from light studio grey background (RGB > ~198 neutral)
    sw_rgba = sw_resized.convert("RGBA")
    sw_pixels = sw_rgba.load()
    sw_alpha = Image.new("L", (sw_size, sw_size), 0)
    sa_px = sw_alpha.load()
    for y in range(sw_size):
        for x in range(sw_size):
            r, g, b, _ = sw_pixels[x, y]
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            sat = max_c - min_c
            lum = (r + g + b) / 3.0
            # Studio backdrop is neutral light grey (low saturation, high luminance)
            if sat < 22 and lum > 178:
                sa_px[x, y] = 0
            elif sat < 30 and lum > 165:
                sa_px[x, y] = 110
            else:
                sa_px[x, y] = 255
    sw_alpha = sw_alpha.filter(ImageFilter.GaussianBlur(1.5))
    sw_rgba.putalpha(sw_alpha)
    # Align right at the avatar torso region so toggling Layer 3 off reveals Step 1 flatlay!
    layer2.paste(sw_rgba, ((CARD_W - sw_size) // 2, 455), sw_rgba)

    # -------------------------------------------------------------------------
    # Layer 3: 03_Avatar_Wearing_Sweater (Step 2 Character & Cabin Foreground)
    # -------------------------------------------------------------------------
    layer3 = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    win_alpha = Image.new("L", (CARD_W, CARD_H), 0)
    wadraw = ImageDraw.Draw(win_alpha)
    wadraw.rounded_rectangle([win_x1, win_y1, win_x2, win_y2], radius=8, fill=255)
    layer3_rgb = card_src.copy().convert("RGBA")
    layer3_rgb.putalpha(win_alpha)
    layer3 = Image.alpha_composite(layer3, layer3_rgb)

    # -------------------------------------------------------------------------
    # Layer 4: 04_Pixel_Banana_Holly_Frame (Evergreen & Pixel-Banana Border)
    # -------------------------------------------------------------------------
    layer4 = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    frame_alpha = Image.new("L", (CARD_W, CARD_H), 255)
    fadraw = ImageDraw.Draw(frame_alpha)
    # Transparent inner window + transparent bottom typography ribbon
    fadraw.rounded_rectangle([win_x1 + 4, win_y1 + 4, win_x2 - 4, win_y2 - 4], radius=6, fill=0)
    fadraw.rectangle([0, 1126, CARD_W, CARD_H], fill=0)
    frame_alpha = frame_alpha.filter(ImageFilter.GaussianBlur(0.8))

    frame_rgba = card_src.copy().convert("RGBA")
    frame_rgba.putalpha(frame_alpha)
    # Add crisp festive gold inner trim accent on Layer 4
    fdraw = ImageDraw.Draw(frame_rgba)
    fdraw.rounded_rectangle(
        [win_x1 + 3, win_y1 + 3, win_x2 - 3, win_y2 - 3],
        radius=6,
        outline=(232, 194, 102, 235),
        width=2,
    )
    layer4 = frame_rgba

    # -------------------------------------------------------------------------
    # Layer 5: 05_Holiday_Card_Typography (Crisp Festive Greeting & Studio Stamp)
    # -------------------------------------------------------------------------
    layer5 = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(layer5)
    # Deep evergreen velvet footer ribbon + crisp gold serif greeting
    tdraw.rectangle([0, 1124, CARD_W, CARD_H], fill=(11, 29, 23, 255))
    tdraw.line([(56, 1126), (CARD_W - 56, 1126)], fill=(232, 194, 102, 220), width=2)

    greeting = "HAPPY HOLIDAYS • DECK THE PIXELS 2026"
    f_greet = load_font(FONT_SERIF, 32)
    bbox = tdraw.textbbox((0, 0), greeting, font=f_greet)
    tw = bbox[2] - bbox[0]
    tx = (CARD_W - tw) // 2
    ty = 1144
    # Subtle drop shadow + warm gold lettering
    tdraw.text((tx + 2, ty + 2), greeting, font=f_greet, fill=(0, 0, 0, 190))
    tdraw.text((tx, ty), greeting, font=f_greet, fill=(246, 224, 158, 255))

    # Subtle removable Studio Layer Pill at top of inner window (demonstrating non-destructive PSD text layer)
    pill_box = (258, 128, 638, 162)
    tdraw.rounded_rectangle(pill_box, radius=17, fill=(12, 28, 24, 205), outline=(246, 224, 158, 210), width=1)
    tag_txt = "NANO BANANA  ×  PHOTOSHOP 5-LAYER PSD"
    f_tag = load_font(FONT_MONO, 14)
    tb = tdraw.textbbox((0, 0), tag_txt, font=f_tag)
    tdraw.text(
        (pill_box[0] + (pill_box[2] - pill_box[0] - (tb[2] - tb[0])) // 2, pill_box[1] + 8),
        tag_txt,
        font=f_tag,
        fill=(246, 224, 158, 255),
    )

    named_layers = [
        ("01_Winter_Cabin_Backdrop", layer1),
        ("02_Nano_Banana_Sweater_Flatlay", layer2),
        ("03_Avatar_Wearing_Sweater", layer3),
        ("04_Pixel_Banana_Holly_Frame", layer4),
        ("05_Holiday_Card_Typography", layer5),
    ]

    # Compute exact merged composite bottom-to-top
    comp = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 255))
    for _, lyr in named_layers:
        comp = Image.alpha_composite(comp, lyr)

    return named_layers, comp.convert("RGB")


def make_video_canvas() -> Image.Image:
    img = Image.new("RGB", (VID_W, VID_H), (10, 20, 18))
    draw = ImageDraw.Draw(img)
    for y in range(VID_H):
        t = y / VID_H
        r = int(10 + 8 * (1.0 - t))
        g = int(24 + 14 * (1.0 - t))
        b = int(20 + 12 * (1.0 - t))
        draw.line([(0, y), (VID_W, y)], fill=(r, g, b))

    for x in range(0, VID_W, 96):
        draw.line([(x, 0), (x, VID_H)], fill=(18, 36, 30), width=1)
    for y in range(0, VID_H, 96):
        draw.line([(0, y), (VID_W, y)], fill=(18, 36, 30), width=1)

    draw.rectangle([0, 0, VID_W, 6], fill=(245, 200, 92))
    return img


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), cand, font=font)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_vid_chrome(draw: ImageDraw.ImageDraw, step_badge: str) -> None:
    GOLD = (245, 200, 92)
    CREAM = (248, 244, 232)
    MUTED = (172, 194, 182)

    draw.rounded_rectangle([72, 34, 595, 82], radius=24, fill=(18, 38, 31), outline=GOLD, width=2)
    draw.ellipse([92, 48, 112, 68], fill=GOLD)
    draw.text((126, 43), "DECK THE PIXELS • NANO BANANA STUDIO", font=load_font(FONT_BOLD, 21), fill=CREAM)

    draw.rounded_rectangle([1380, 34, 1848, 82], radius=24, fill=(16, 32, 27), outline=(48, 82, 68), width=2)
    draw.text((1412, 45), step_badge, font=load_font(FONT_MONO, 19), fill=GOLD)

    draw.rounded_rectangle([72, 984, 1848, 1042], radius=14, fill=(12, 25, 21), outline=(42, 72, 60), width=1)
    draw.text(
        (100, 998),
        "Google Nano Banana Image Generation  +  5-Layer Spec-Compliant Adobe Photoshop (.PSD) Compositing",
        font=load_font(FONT_MONO, 21),
        fill=MUTED,
    )


def build_showcase_slides(
    sweater_jpg: pathlib.Path,
    named_layers: List[Tuple[str, Image.Image]],
    final_rgb: Image.Image,
) -> List[Tuple[Image.Image, int]]:
    GOLD = (245, 200, 92)
    RED_FEST = (239, 68, 68)
    MINT = (74, 222, 128)
    CREAM = (248, 244, 232)
    MUTED = (176, 198, 186)

    sweater_img = Image.open(sweater_jpg).convert("RGB")

    # Slide 1 (11s): Step 1 — Ugly Holiday Sweater Generation with Nano Banana
    s1 = make_video_canvas()
    d1 = ImageDraw.Draw(s1)
    draw_vid_chrome(d1, "STEP 01 / 04 • SWEATER DESIGN")
    d1.text((72, 136), "STEP 1 • NANO BANANA TEXTILE SYNTHESIS", font=load_font(FONT_MONO, 23), fill=GOLD)
    d1.text((72, 182), "Designing the Ultimate", font=load_font(FONT_BOLD, 54), fill=CREAM)
    d1.text((72, 250), "\"Deck the Pixels\" Sweater", font=load_font(FONT_BOLD, 54), fill=GOLD)

    desc1 = (
        "Generated with Google's Nano Banana model: tactile macro-knitted Fair Isle wool featuring "
        "8-bit pixel reindeer, Santa-hat Nano Bananas, PCB circuit traces, 3D yarn pom-poms, and metallic tinsel."
    )
    y = 345
    f_b = load_font(FONT_REG, 25)
    for line in wrap_lines(d1, desc1, f_b, 860):
        d1.text((72, y), line, font=f_b, fill=MUTED)
        y += 38

    specs1 = [
        ("Prompt Focus", "Macro knit stitch fidelity + 3D pom-poms + circuit-board Fair Isle"),
        ("Center Motif", "Knitted 'DECK THE PIXELS' lettering flanked by pixel reindeer & bananas"),
        ("Resolution", "1024 x 1024 studio flatlay ready for character reference & PSD isolation"),
    ]
    sy = 540
    for k, v in specs1:
        d1.rounded_rectangle([72, sy, 940, sy + 112], radius=16, fill=(16, 34, 28), outline=(48, 84, 70), width=2)
        d1.text((100, sy + 18), k.upper(), font=load_font(FONT_MONO, 19), fill=MINT)
        d1.text((100, sy + 54), v, font=load_font(FONT_REG, 22), fill=CREAM)
        sy += 130

    # Right showcase frame for Step 1 sweater
    d1.rounded_rectangle([1018, 128, 1848, 958], radius=24, fill=(18, 36, 30), outline=GOLD, width=3)
    sw_disp = sweater_img.resize((786, 786), Image.Resampling.LANCZOS)
    s1.paste(sw_disp, (1040, 150))

    # Slide 2 (11s): Step 2 — Avatar Integration Wearing the Exact Sweater
    s2 = make_video_canvas()
    d2 = ImageDraw.Draw(s2)
    draw_vid_chrome(d2, "STEP 02 / 04 • AVATAR INTEGRATION")
    d2.text((72, 136), "STEP 2 • CHARACTER & GARMENT CONSISTENCY", font=load_font(FONT_MONO, 23), fill=MINT)
    d2.text((72, 182), "Bringing Our Developer", font=load_font(FONT_BOLD, 54), fill=CREAM)
    d2.text((72, 250), "Avatar Into the Cabin", font=load_font(FONT_BOLD, 54), fill=MINT)

    desc2 = (
        "Using Nano Banana's multi-modal reference consistency, our 3D developer avatar wears the exact "
        "knitted 'DECK THE PIXELS' banana sweater inside a cozy snow-lit coder cabin with hot cocoa."
    )
    y = 345
    for line in wrap_lines(d2, desc2, f_b, 920):
        d2.text((72, y), line, font=f_b, fill=MUTED)
        y += 38

    # Side-by-side mini sweater -> arrow -> full portrait
    d2.rounded_rectangle([72, 520, 462, 930], radius=18, fill=(16, 34, 28), outline=GOLD, width=2)
    d2.text((98, 540), "SOURCE GARMENT", font=load_font(FONT_MONO, 18), fill=GOLD)
    s2.paste(sweater_img.resize((338, 338), Image.Resampling.LANCZOS), (98, 574))

    d2.line([(485, 725), (565, 725)], fill=GOLD, width=6)
    d2.polygon([(572, 725), (550, 710), (550, 740)], fill=GOLD)

    d2.rounded_rectangle([595, 520, 1020, 930], radius=18, fill=(16, 34, 28), outline=MINT, width=2)
    d2.text((622, 544), "CONSISTENCY WINS", font=load_font(FONT_MONO, 19), fill=MINT)
    pts2 = [
        "Identical 'DECK THE PIXELS' knit chest typography",
        "Matching shoulder Santa-hat Nano Bananas",
        "Preserved 3D red/green/white wool pom-poms",
        "Natural drape around arms holding cocoa mug",
    ]
    py = 594
    f_sm = load_font(FONT_REG, 21)
    for pt in pts2:
        for ln in wrap_lines(d2, f"• {pt}", f_sm, 375):
            d2.text((622, py), ln, font=f_sm, fill=CREAM)
            py += 30
        py += 10

    d2.rounded_rectangle([1188, 126, 1824, 958], radius=24, fill=(18, 36, 30), outline=MINT, width=3)
    card_disp = final_rgb.resize((604, 808), Image.Resampling.LANCZOS)
    s2.paste(card_disp, (1204, 138))

    # Slide 3 (13s): Step 3 — 5-Layer Adobe Photoshop (.PSD) Breakdown
    s3 = make_video_canvas()
    d3 = ImageDraw.Draw(s3)
    draw_vid_chrome(d3, "STEP 03 / 04 • 5-LAYER PHOTOSHOP PSD")
    d3.text((72, 122), "NON-DESTRUCTIVE MULTI-LAYER COMPOSITING (`deck_the_pixels_holiday_card.psd`)", font=load_font(FONT_MONO, 22), fill=GOLD)
    d3.text((72, 162), "5 Distinct Named RGBA Layers in Spec-Compliant .PSD", font=load_font(FONT_BOLD, 44), fill=CREAM)

    checker_bg = (28, 46, 40)
    card_w = 324
    gap = 30
    for idx, (lname, limg) in enumerate(named_layers):
        cx1 = 72 + idx * (card_w + gap)
        cx2 = cx1 + card_w
        cy1, cy2 = 248, 938
        d3.rounded_rectangle([cx1, cy1, cx2, cy2], radius=18, fill=(16, 32, 27), outline=GOLD if idx == 4 else (54, 92, 76), width=2)
        d3.text((cx1 + 18, cy1 + 18), f"LAYER 0{idx + 1}", font=load_font(FONT_MONO, 18), fill=GOLD)

        # Checkerboard preview behind RGBA layer thumbnail
        thumb_w, thumb_h = 288, 386
        tx1, ty1 = cx1 + 18, cy1 + 58
        thumb_canvas = Image.new("RGBA", (thumb_w, thumb_h), checker_bg + (255,))
        tc_draw = ImageDraw.Draw(thumb_canvas)
        for gy in range(0, thumb_h, 16):
            for gx in range(0, thumb_w, 16):
                if ((gx // 16) + (gy // 16)) % 2 == 0:
                    tc_draw.rectangle([gx, gy, gx + 16, gy + 16], fill=(38, 60, 52, 255))
        l_thumb = limg.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        thumb_comp = Image.alpha_composite(thumb_canvas, l_thumb).convert("RGB")
        s3.paste(thumb_comp, (tx1, ty1))
        d3.rectangle([tx1, ty1, tx1 + thumb_w, ty1 + thumb_h], outline=(68, 108, 90), width=1)

        # Layer Name & role
        ny = cy1 + 464
        for ln in wrap_lines(d3, lname.replace("_", " "), load_font(FONT_BOLD, 21), card_w - 36):
            d3.text((cx1 + 18, ny), ln, font=load_font(FONT_BOLD, 21), fill=CREAM)
            ny += 28

        roles = [
            "Diffused snow-lit cabin backdrop stage (RGBA base).",
            "Isolated Step 1 Nano Banana sweater flatlay on alpha.",
            "3D coder avatar wearing sweater with cocoa mug.",
            "Evergreen pine, holly berries & pixel banana border.",
            "Editable gold serif greeting & studio edition badge.",
        ]
        ry = cy1 + 544
        f_r = load_font(FONT_REG, 18)
        for ln in wrap_lines(d3, roles[idx], f_r, card_w - 36):
            d3.text((cx1 + 18, ry), ln, font=f_r, fill=MUTED)
            ry += 26

    # Slide 4 (10s): Step 4 — Final Holiday Card Showcase & Downloadable PSD
    s4 = make_video_canvas()
    d4 = ImageDraw.Draw(s4)
    draw_vid_chrome(d4, "STEP 04 / 04 • FINISHED HOLIDAY CARD")
    d4.rounded_rectangle([72, 128, 1130, 956], radius=26, fill=(16, 34, 28), outline=GOLD, width=3)
    d4.text((120, 184), "GOOGLE DECK THE PIXELS • FINAL SUBMISSION", font=load_font(FONT_MONO, 22), fill=GOLD)
    d4.text((120, 232), "Happy Holidays from", font=load_font(FONT_BOLD, 58), fill=CREAM)
    d4.text((120, 306), "Deck the Pixels 2026!", font=load_font(FONT_BOLD, 58), fill=RED_FEST if False else GOLD)

    pts4 = [
        "Step 1: Custom Nano Banana Ugly Holiday Sweater (1024x1024)",
        "Step 2: Consistent 3D Developer Avatar Cabin Integration",
        "Step 3: Multi-Layer Adobe Photoshop .PSD (8BPS v1, 5 RGBA Layers)",
        "Interactive Browser Layer Inspector + Direct .PSD Download",
    ]
    py = 426
    for pt in pts4:
        d4.ellipse([120, py + 9, 138, py + 27], fill=MINT)
        d4.text((158, py), pt, font=load_font(FONT_REG, 26), fill=CREAM)
        py += 58

    d4.rounded_rectangle([120, 704, 1080, 818], radius=18, fill=GOLD)
    d4.text(
        (152, 740),
        "jeffrey-graham.github.io/deck-the-pixels-nano-banana",
        font=load_font(FONT_MONO, 27),
        fill=(10, 22, 18),
    )
    d4.text(
        (120, 854),
        "Includes full source scripts, PSD spec verifier & Devpost write-up.",
        font=load_font(FONT_REG, 23),
        fill=MUTED,
    )

    d4.rounded_rectangle([1184, 126, 1828, 958], radius=24, fill=(18, 36, 30), outline=GOLD, width=3)
    s4.paste(final_rgb.resize((612, 818), Image.Resampling.LANCZOS), (1200, 134))

    return [
        (s1, 11 * FPS),
        (s2, 11 * FPS),
        (s3, 13 * FPS),
        (s4, 10 * FPS),
    ]


def generate_festive_chime_wav(wav_path: pathlib.Path, duration_s: int) -> None:
    sample_rate = 22050
    total_samples = sample_rate * duration_s
    # Warm Fmaj7 holiday bell-pad harmonics
    freqs = [174.61, 220.00, 261.63, 329.63, 523.25]

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        chunk = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            env = 1.0
            if t < 1.8:
                env = t / 1.8
            elif t > duration_s - 2.2:
                env = max(0.0, (duration_s - t) / 2.2)
            shimmer = 0.84 + 0.16 * math.sin(2.0 * math.pi * 0.35 * t)
            val = sum(math.sin(2.0 * math.pi * f * t) * (0.30 / (idx + 1.1)) for idx, f in enumerate(freqs))
            sample = int(max(-32767, min(32767, val * env * shimmer * 4100)))
            chunk.extend(struct.pack("<h", sample))
            if len(chunk) >= 44100:
                wf.writeframes(chunk)
                chunk.clear()
        if chunk:
            wf.writeframes(chunk)


def render_showcase_mp4(mp4_path: pathlib.Path, schedule: List[Tuple[Image.Image, int]]) -> None:
    fade_frames = 14
    GOLD = (245, 200, 92)

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = pathlib.Path(tmpdir) / "holiday.wav"
        generate_festive_chime_wav(wav_path, VID_DURATION)

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{VID_W}x{VID_H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(wav_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(mp4_path),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdin is not None

        gf = 0
        for idx, (cur_img, fcount) in enumerate(schedule):
            prev_img = schedule[idx - 1][0] if idx > 0 else cur_img
            for lf in range(fcount):
                if lf < fade_frames and idx > 0:
                    frame = Image.blend(prev_img, cur_img, lf / float(fade_frames))
                else:
                    frame = cur_img.copy()

                draw = ImageDraw.Draw(frame)
                prog_w = int(VID_W * ((gf + 1) / float(TOTAL_FRAMES)))
                draw.rectangle([0, VID_H - 8, VID_W, VID_H], fill=(18, 36, 30))
                draw.rectangle([0, VID_H - 8, prog_w, VID_H], fill=GOLD)

                proc.stdin.write(frame.tobytes())
                gf += 1

        proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg failed ({ret}):\n{stderr_out}")


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    assets = root / "assets"
    layers_dir = assets / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)

    sweater_jpg = assets / "ugly_holiday_sweater.jpg"
    avatar_card_jpg = assets / "developer_avatar_holiday_card.jpg"
    psd_out = assets / "deck_the_pixels_holiday_card.psd"
    final_png = assets / "final_holiday_card.png"
    mp4_out = assets / "deck_the_pixels_showcase.mp4"

    named_layers, final_rgb = build_five_holiday_card_layers(sweater_jpg, avatar_card_jpg)

    # Export individual RGBA PNGs for interactive browser Layer Inspector + final PNG
    for lname, limg in named_layers:
        limg.save(layers_dir / f"{lname}.png", format="PNG")
    final_rgb.save(final_png, format="PNG")

    # Write genuine multi-layer Adobe Photoshop .psd v1 file
    write_psd_v1(psd_out, CARD_W, CARD_H, named_layers, final_rgb)

    # Render 45-second 1080p MP4 showcase
    schedule = build_showcase_slides(sweater_jpg, named_layers, final_rgb)
    render_showcase_mp4(mp4_out, schedule)

    print(f"Saved PSD: {psd_out} ({psd_out.stat().st_size / (1024 * 1024):.2f} MB)")
    print(f"Saved MP4: {mp4_out} ({mp4_out.stat().st_size / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
