#!/usr/bin/env python3
"""Generate SnapByFace application icons.

The source artwork is drawn at high resolution with Pillow, then exported to
PNG, Windows ICO, and macOS ICNS assets used by the packaging scripts.
"""
from __future__ import annotations

import io
import math
import struct
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = ROOT_DIR / "resources"
PNG_PATH = RESOURCES_DIR / "snapbyface.png"
ICO_PATH = RESOURCES_DIR / "snapbyface.ico"
ICNS_PATH = RESOURCES_DIR / "snapbyface.icns"


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def add_gradient(
    image: Image.Image,
    mask: Image.Image,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> None:
    width, height = image.size
    gradient = Image.new("RGBA", image.size)
    pixels = gradient.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        color = mix(top, bottom, t)
        for x in range(width):
            pixels[x, y] = (*color, 255)
    image.alpha_composite(Image.composite(gradient, Image.new("RGBA", image.size), mask))


def radial_overlay(
    image: Image.Image,
    center: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    alpha: int,
    mode: str = "screen",
) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size)
    pixels = overlay.load()
    cx, cy = center
    for y in range(height):
        for x in range(width):
            distance = math.hypot(x - cx, y - cy)
            t = max(0.0, 1.0 - distance / radius)
            if t <= 0:
                continue
            pixels[x, y] = (*color, round(alpha * t * t))
    if mode == "multiply":
        rgb = ImageChops.multiply(image.convert("RGB"), overlay.convert("RGB")).convert("RGBA")
        rgb.putalpha(overlay.getchannel("A"))
        image.alpha_composite(rgb)
    else:
        image.alpha_composite(overlay)


def superellipse_mask(size: int, radius_scale: float = 0.84) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    pixels = mask.load()
    half = size / 2
    exponent = 4.7
    radius = half * radius_scale
    for y in range(size):
        ny = abs((y + 0.5 - half) / radius)
        for x in range(size):
            nx = abs((x + 0.5 - half) / radius)
            if nx**exponent + ny**exponent <= 1:
                pixels[x, y] = 255
    return mask.filter(ImageFilter.GaussianBlur(size * 0.0012))


def rounded_rect_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_shadow(
    canvas: Image.Image,
    mask: Image.Image,
    offset: tuple[int, int],
    blur: int,
    color: tuple[int, int, int, int],
) -> None:
    shadow = Image.new("RGBA", canvas.size)
    shadow_layer = Image.new("RGBA", canvas.size, color)
    shifted = Image.new("L", canvas.size, 0)
    shifted.paste(mask, offset)
    shadow.putalpha(shifted.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(Image.composite(shadow_layer, Image.new("RGBA", canvas.size), shadow.getchannel("A")))


def rounded_panel(
    size: tuple[int, int],
    radius: int,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
    alpha: int = 255,
) -> Image.Image:
    panel = Image.new("RGBA", size)
    mask = rounded_rect_mask(size, radius)
    add_gradient(panel, mask, top, bottom)
    panel.putalpha(ImageChops.multiply(panel.getchannel("A"), mask.point(lambda p: p * alpha // 255)))
    highlight = Image.new("RGBA", size)
    draw = ImageDraw.Draw(highlight)
    inset = max(5, size[0] // 70)
    draw.rounded_rectangle(
        (inset, inset, size[0] - inset, size[1] - inset),
        radius=max(1, radius - inset),
        outline=(255, 255, 255, 120),
        width=max(3, size[0] // 110),
    )
    panel.alpha_composite(highlight)
    return panel


def draw_scan_corner(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    sx: int,
    sy: int,
    length: int,
    width: int,
    color: tuple[int, int, int, int],
) -> None:
    draw.line((x, y, x + sx * length, y), fill=color, width=width)
    draw.line((x, y, x, y + sy * length), fill=color, width=width)


def make_icon(size: int = 1024) -> Image.Image:
    scale = size / 1024
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base_mask = superellipse_mask(size)

    paste_shadow(
        canvas,
        base_mask,
        (round(0.012 * size), round(0.035 * size)),
        round(0.05 * size),
        (19, 34, 57, 85),
    )

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    add_gradient(base, base_mask, (250, 253, 255), (152, 177, 206))
    radial_overlay(base, (size * 0.24, size * 0.12), size * 0.62, (255, 255, 255), 170)
    radial_overlay(base, (size * 0.78, size * 0.86), size * 0.74, (29, 108, 219), 80)
    radial_overlay(base, (size * 0.18, size * 0.86), size * 0.58, (0, 196, 174), 62)
    base.putalpha(base_mask)
    canvas.alpha_composite(base)

    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle(
        (round(0.035 * size), round(0.035 * size), round(0.965 * size), round(0.965 * size)),
        radius=round(0.225 * size),
        outline=(255, 255, 255, 115),
        width=round(0.012 * size),
    )
    border.putalpha(ImageChops.multiply(border.getchannel("A"), base_mask))
    canvas.alpha_composite(border)

    card_size = (round(0.58 * size), round(0.66 * size))
    card = rounded_panel(
        card_size,
        round(0.09 * size),
        (255, 255, 255),
        (222, 232, 243),
        238,
    )
    card_mask = rounded_rect_mask(card_size, round(0.09 * size))
    card_pos = (round(0.21 * size), round(0.18 * size))
    full_card_mask = Image.new("L", (size, size), 0)
    full_card_mask.paste(card_mask, card_pos)
    paste_shadow(canvas, full_card_mask, (round(0.018 * size), round(0.035 * size)), round(0.042 * size), (22, 42, 73, 72))
    canvas.alpha_composite(card, card_pos)

    lens_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    lens_draw = ImageDraw.Draw(lens_layer)
    cx, cy = round(0.5 * size), round(0.505 * size)
    outer = round(0.255 * size)
    ring = round(0.052 * size)
    lens_draw.ellipse(
        (cx - outer, cy - outer, cx + outer, cy + outer),
        fill=(25, 45, 78, 255),
        outline=(255, 255, 255, 150),
        width=round(0.01 * size),
    )
    for i, color in enumerate([(20, 120, 224, 210), (0, 194, 178, 150), (136, 104, 255, 90)]):
        inset = ring + i * round(0.038 * size)
        lens_draw.ellipse(
            (cx - outer + inset, cy - outer + inset, cx + outer - inset, cy + outer - inset),
            outline=color,
            width=round(0.02 * size),
        )

    aperture = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    aperture_draw = ImageDraw.Draw(aperture)
    inner = round(0.16 * size)
    add_gradient(aperture, Image.new("L", (size, size), 0), (0, 0, 0), (0, 0, 0))
    for i in range(7):
        angle = -math.pi / 2 + i * math.tau / 7
        next_angle = angle + math.tau / 7 * 0.72
        p1 = (cx + math.cos(angle) * inner * 0.42, cy + math.sin(angle) * inner * 0.42)
        p2 = (cx + math.cos(angle) * inner * 1.04, cy + math.sin(angle) * inner * 1.04)
        p3 = (cx + math.cos(next_angle) * inner * 1.04, cy + math.sin(next_angle) * inner * 1.04)
        aperture_draw.polygon((p1, p2, p3), fill=(73, 164, 240, 50))
    lens_layer.alpha_composite(aperture)

    face_draw = ImageDraw.Draw(lens_layer)
    face_color = (247, 252, 255, 238)
    head_box = (
        cx - round(0.088 * size),
        cy - round(0.132 * size),
        cx + round(0.088 * size),
        cy + round(0.06 * size),
    )
    face_draw.ellipse(head_box, outline=face_color, width=round(0.014 * size))
    eye_r = round(0.011 * size)
    face_draw.ellipse(
        (
            cx - round(0.048 * size) - eye_r,
            cy - round(0.044 * size) - eye_r,
            cx - round(0.048 * size) + eye_r,
            cy - round(0.044 * size) + eye_r,
        ),
        fill=face_color,
    )
    face_draw.ellipse(
        (
            cx + round(0.048 * size) - eye_r,
            cy - round(0.044 * size) - eye_r,
            cx + round(0.048 * size) + eye_r,
            cy - round(0.044 * size) + eye_r,
        ),
        fill=face_color,
    )
    face_draw.arc(
        (
            cx - round(0.115 * size),
            cy + round(0.062 * size),
            cx + round(0.115 * size),
            cy + round(0.205 * size),
        ),
        200,
        340,
        fill=(247, 252, 255, 215),
        width=round(0.015 * size),
    )

    corner_color = (0, 204, 190, 235)
    corner_w = round(0.018 * size)
    corner_len = round(0.092 * size)
    pad = round(0.142 * size)
    draw_scan_corner(face_draw, cx - pad, cy - pad, 1, 1, corner_len, corner_w, corner_color)
    draw_scan_corner(face_draw, cx + pad, cy - pad, -1, 1, corner_len, corner_w, corner_color)
    draw_scan_corner(face_draw, cx - pad, cy + pad, 1, -1, corner_len, corner_w, corner_color)
    draw_scan_corner(face_draw, cx + pad, cy + pad, -1, -1, corner_len, corner_w, corner_color)

    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    shine_draw.arc(
        (cx - round(0.21 * size), cy - round(0.22 * size), cx + round(0.2 * size), cy + round(0.19 * size)),
        218,
        292,
        fill=(255, 255, 255, 105),
        width=round(0.023 * size),
    )
    lens_layer.alpha_composite(shine)
    canvas.alpha_composite(lens_layer)

    bottom_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(bottom_glow)
    glow_draw.rounded_rectangle(
        (round(0.285 * size), round(0.76 * size), round(0.715 * size), round(0.805 * size)),
        radius=round(0.022 * size),
        fill=(29, 113, 225, 35),
    )
    bottom_glow = bottom_glow.filter(ImageFilter.GaussianBlur(round(0.032 * size)))
    canvas.alpha_composite(bottom_glow)

    return canvas.resize((1024, 1024), Image.Resampling.LANCZOS) if size != 1024 else canvas


def png_bytes(image: Image.Image, side: int) -> bytes:
    buffer = io.BytesIO()
    image.resize((side, side), Image.Resampling.LANCZOS).save(buffer, format="PNG")
    return buffer.getvalue()


def write_icns(source: Image.Image) -> None:
    # ICNS PNG resource types by pixel size. This avoids depending on iconutil,
    # whose behavior differs across macOS command line tool installations.
    entries = [
        ("icp4", png_bytes(source, 16)),
        ("icp5", png_bytes(source, 32)),
        ("icp6", png_bytes(source, 64)),
        ("ic07", png_bytes(source, 128)),
        ("ic08", png_bytes(source, 256)),
        ("ic09", png_bytes(source, 512)),
        ("ic10", png_bytes(source, 1024)),
    ]
    total_size = 8 + sum(8 + len(data) for _, data in entries)
    with ICNS_PATH.open("wb") as file:
        file.write(b"icns")
        file.write(struct.pack(">I", total_size))
        for icon_type, data in entries:
            file.write(icon_type.encode("ascii"))
            file.write(struct.pack(">I", 8 + len(data)))
            file.write(data)


def main() -> int:
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    icon = make_icon(2048)
    icon.save(PNG_PATH)
    icon.save(
        ICO_PATH,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    write_icns(icon)
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")
    if ICNS_PATH.exists():
        print(f"Wrote {ICNS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
