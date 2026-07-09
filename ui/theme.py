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

# Pares (claro, oscuro) para elementos que no son widgets CTk nativos
# (ttk.Treeview no sigue customtkinter.set_appearance_mode automáticamente).
TABLE_BG = (WHITE, "#1E1E22")
TABLE_FG = ("#1A1A1A", "#E8E8EA")
TABLE_HEADING_BG = (GRAY_LIGHT, "#2A2A2E")
ROW_API_BG = ("#E9F7EC", "#123319")
ROW_SEARCH_BG = ("#F4F4F6", "#2A2A2E")
MATCH_HIGH = ("#0F7B2E", "#4ADE80")
MATCH_MID = ("#9A6B00", "#F5C451")
MATCH_LOW = ("#6B6B70", "#9B9BA1")
SELECTION_BG = ("#D7EFDC", "#1F4B2C")
SELECTION_FG = ("#0A3D14", "#BEE8C8")
DESCRIPTION_BG = (GRAY_LIGHT, "#2A2A2E")
# Fondo de los divisores arrastrables (tk.PanedWindow tampoco sigue el modo CTk).
WINDOW_BG = ("#EBEBEB", "#242424")

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_SMALL = (FONT_FAMILY, 11)

SIDEBAR_WIDTH = 280
SIDEBAR_MIN_WIDTH = 230
MAIN_AREA_MIN_WIDTH = 420
TABLE_MIN_HEIGHT = 200
DETAIL_HEIGHT = 220
DETAIL_MIN_HEIGHT = 150
HEADER_HEIGHT = 60
STATUSBAR_HEIGHT = 30
