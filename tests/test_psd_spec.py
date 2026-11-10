#!/usr/bin/env python3
"""
Unit test suite verifying spec-compliance of `assets/deck_the_pixels_holiday_card.psd`
against both the Adobe Photoshop v1 (`8BPS`) binary file specification AND Pillow's
independent `PsdImagePlugin` reader.
"""

import pathlib
import struct
import unittest

from PIL import Image

EXPECTED_LAYERS = [
    "01_Winter_Cabin_Backdrop",
    "02_Nano_Banana_Sweater_Flatlay",
    "03_Avatar_Wearing_Sweater",
    "04_Pixel_Banana_Holly_Frame",
    "05_Holiday_Card_Typography",
]


class TestDeckThePixelsPsdSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = pathlib.Path(__file__).resolve().parent.parent
        cls.psd_path = cls.root / "assets" / "deck_the_pixels_holiday_card.psd"
        cls.mp4_path = cls.root / "assets" / "deck_the_pixels_showcase.mp4"

    def test_psd_binary_header_and_five_named_layer_records(self) -> None:
        self.assertTrue(self.psd_path.exists(), f"Missing {self.psd_path}")
        data = self.psd_path.read_bytes()

        # 1. File Header (26 bytes)
        sig, ver, reserved, channels, height, width, depth, color_mode = struct.unpack(
            ">4sH6sHIIHH", data[:26]
        )
        self.assertEqual(sig, b"8BPS")
        self.assertEqual(ver, 1)
        self.assertEqual(reserved, b"\x00" * 6)
        self.assertEqual(channels, 3)
        self.assertEqual(width, 896)
        self.assertEqual(height, 1200)
        self.assertEqual(depth, 8)
        self.assertEqual(color_mode, 3)  # RGB

        offset = 26
        # 2. Color Mode Data
        (cm_len,) = struct.unpack(">I", data[offset : offset + 4])
        self.assertEqual(cm_len, 0)
        offset += 4

        # 3. Image Resources
        (ir_len,) = struct.unpack(">I", data[offset : offset + 4])
        offset += 4 + ir_len

        # 4. Layer and Mask Info
        (lmi_len,) = struct.unpack(">I", data[offset : offset + 4])
        self.assertGreater(lmi_len, 0)
        lmi_end = offset + 4 + lmi_len
        offset += 4

        (layer_info_len,) = struct.unpack(">I", data[offset : offset + 4])
        self.assertEqual(layer_info_len % 2, 0, "Layer info length must be even per PSD spec")
        offset += 4

        (layer_count,) = struct.unpack(">h", data[offset : offset + 2])
        self.assertEqual(layer_count, 5)
        offset += 2

        parsed_names = []
        channel_specs = []
        for _ in range(layer_count):
            top, left, bottom, right, num_ch = struct.unpack(">iiiiH", data[offset : offset + 18])
            self.assertEqual((top, left, bottom, right), (0, 0, height, width))
            self.assertEqual(num_ch, 4)
            offset += 18

            ch_list = []
            for _ in range(num_ch):
                ch_id, ch_len = struct.unpack(">hI", data[offset : offset + 6])
                ch_list.append((ch_id, ch_len))
                offset += 6
            channel_specs.append(ch_list)

            blend_sig, blend_key, opacity, clipping, flags, filler, extra_len = struct.unpack(
                ">4s4sBBBBI", data[offset : offset + 16]
            )
            self.assertEqual(blend_sig, b"8BIM")
            self.assertEqual(blend_key, b"norm")
            self.assertEqual(opacity, 255)
            self.assertEqual(filler, 0)
            offset += 16

            extra_start = offset
            (mask_len,) = struct.unpack(">I", data[offset : offset + 4])
            offset += 4 + mask_len
            (br_len,) = struct.unpack(">I", data[offset : offset + 4])
            offset += 4 + br_len

            name_len = data[offset]
            name = data[offset + 1 : offset + 1 + name_len].decode("ascii")
            parsed_names.append(name)

            # Verify 4-byte Pascal padding alignment
            pascal_padded_len = extra_len - (offset - extra_start)
            self.assertEqual(pascal_padded_len % 4, 0)
            offset = extra_start + extra_len

        self.assertEqual(parsed_names, EXPECTED_LAYERS)

        # Verify Channel Image Data planes match exact byte counts
        for ch_list in channel_specs:
            for ch_id, ch_len in ch_list:
                self.assertIn(ch_id, {0, 1, 2, -1})
                (comp_method,) = struct.unpack(">H", data[offset : offset + 2])
                self.assertEqual(comp_method, 0)
                self.assertEqual(ch_len, 2 + width * height)
                offset += ch_len

        # Jump to Section 5: Merged Composite Image Data
        offset = lmi_end
        (comp_compression,) = struct.unpack(">H", data[offset : offset + 2])
        self.assertEqual(comp_compression, 0)
        remaining_bytes = len(data) - (offset + 2)
        self.assertEqual(remaining_bytes, 3 * width * height)

    def test_independent_pillow_psd_reader_parses_all_five_layers(self) -> None:
        with Image.open(self.psd_path) as psd_img:
            self.assertEqual(psd_img.format, "PSD")
            self.assertEqual(psd_img.size, (896, 1200))
            self.assertEqual(psd_img.mode, "RGB")
            self.assertTrue(hasattr(psd_img, "layers"))
            self.assertEqual(len(psd_img.layers), 5)
            pil_layer_names = [
                lyr[0].decode("ascii") if isinstance(lyr[0], bytes) else str(lyr[0])
                for lyr in psd_img.layers
            ]
            self.assertEqual(pil_layer_names, EXPECTED_LAYERS)

    def test_showcase_video_and_layer_pngs_exist(self) -> None:
        self.assertTrue(self.mp4_path.exists())
        self.assertGreater(self.mp4_path.stat().st_size, 500_000)
        for lname in EXPECTED_LAYERS:
            p = self.root / "assets" / "layers" / f"{lname}.png"
            self.assertTrue(p.exists(), f"Missing exported layer PNG {p}")


if __name__ == "__main__":
    unittest.main()
