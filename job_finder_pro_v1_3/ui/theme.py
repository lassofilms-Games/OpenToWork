from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo_trimmed.png"
ICON_PATH = ASSETS_DIR / "icon.ico"

# Colores extraídos del logo #OPENTOWORK
GREEN = "#008600"
GREEN_HOVER = "#046B08"
GRAY = "#BBBBC0"
GRAY_LIGHT = "#F2F2F4"
GRAY_DARK = "#242428"
WHITE = "#FFFFFF"
TEXT_MUTED = ("#5B5B60", "#9B9BA1")

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 11)

SIDEBAR_WIDTH = 280
HEADER_HEIGHT = 60
STATUSBAR_HEIGHT = 30
