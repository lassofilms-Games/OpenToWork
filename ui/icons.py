"""Iconos monocromos dibujados con PIL.

Los emojis de fuente no se pueden teñir ni siguen el modo claro/oscuro; estos
iconos se dibujan a 4x y se reescalan con LANCZOS para que queden nítidos, con
una variante por tema (recibe tuplas (claro, oscuro) de ui.theme).
"""
from PIL import Image, ImageDraw

import customtkinter as ctk

_SCALE = 4


def _canvas(size):
    s = size * _SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _finish(img, size):
    return img.resize((size, size), Image.LANCZOS)


def _search(size, color):
    img, draw, s = _canvas(size)
    stroke = max(2, round(s * 0.09))
    lens = round(s * 0.62)
    draw.ellipse([stroke, stroke, lens, lens], outline=color, width=stroke)
    start = lens - round(stroke * 0.4)
    end = s - round(stroke * 1.1)
    draw.line([start, start, end, end], fill=color, width=stroke)
    draw.ellipse([end - stroke // 2, end - stroke // 2, end + stroke // 2, end + stroke // 2], fill=color)
    return _finish(img, size)


def _document(size, color):
    img, draw, s = _canvas(size)
    stroke = max(2, round(s * 0.08))
    left, top, right, bottom = round(s * 0.14), round(s * 0.06), round(s * 0.86), round(s * 0.94)
    draw.rounded_rectangle([left, top, right, bottom], radius=round(s * 0.10), outline=color, width=stroke)
    x0, x1 = round(s * 0.30), round(s * 0.70)
    for rel_y in (0.32, 0.50, 0.68):
        y = round(s * rel_y)
        draw.line([x0, y, x1, y], fill=color, width=stroke)
    return _finish(img, size)


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _watermark(logo, height, bg_hex, opacity):
    # Tk no compone alfa parcial de forma fiable, así que la transparencia se
    # hornea: el logo se funde con el color de superficie de la tarjeta.
    width = round(height * logo.width / logo.height)
    scaled = logo.resize((width, height), Image.LANCZOS)
    base = Image.new("RGBA", scaled.size, _hex_to_rgb(bg_hex) + (255,))
    alpha = scaled.getchannel("A").point(lambda a: int(a * opacity))
    scaled.putalpha(alpha)
    return Image.alpha_composite(base, scaled).convert("RGB")


def watermark_logo(logo_path, height, bg_colors, opacity=(0.11, 0.09)):
    """Logo como marca de agua fundida con el fondo (claro, oscuro)."""
    logo = Image.open(logo_path).convert("RGBA")
    light = _watermark(logo, height, bg_colors[0], opacity[0])
    dark = _watermark(logo, height, bg_colors[1], opacity[1])
    return ctk.CTkImage(light_image=light, dark_image=dark, size=light.size)


def search_icon(size, colors):
    return ctk.CTkImage(
        light_image=_search(size, colors[0]), dark_image=_search(size, colors[1]), size=(size, size),
    )


def document_icon(size, colors):
    return ctk.CTkImage(
        light_image=_document(size, colors[0]), dark_image=_document(size, colors[1]), size=(size, size),
    )
