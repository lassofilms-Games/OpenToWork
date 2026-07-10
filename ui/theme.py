from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo_trimmed.png"
ICON_PATH = ASSETS_DIR / "icon.ico"

# =============================================================================
# DESIGN SYSTEM — OPentowork_app
# Todos los valores de color/tipografía/espaciado/radio de la UI viven aquí.
# Los widgets no-CTk (ttk.Treeview, tk.PanedWindow) no siguen el modo de
# apariencia automáticamente, por eso casi todo se define como par
# (claro, oscuro) e main_window.py resuelve el índice con _dark_mode_index().
# Los widgets CTk sí aceptan estos mismos pares directamente como fg_color/
# text_color/hover_color/border_color.
# =============================================================================

# ---------------------------------------------------------------------------
# Color · superficies y neutros
# ---------------------------------------------------------------------------
BG_MAIN = ("#F1F2F4", "#1C1D20")          # fondo de ventana / paneles divisores
SURFACE = ("#FFFFFF", "#232428")           # tarjetas: sidebar, header, tabla, detalle
SURFACE_ALT = ("#F6F7F8", "#2A2B30")       # filas alternas, inputs, chips neutros
SURFACE_SUNKEN = ("#EDEEF1", "#242529")    # zonas "hundidas": descripción, badges de match
BORDER = ("#E4E5E9", "#333438")            # bordes sutiles de tarjetas/inputs
BORDER_STRONG = ("#D4D6DB", "#45464C")     # bordes de botones outline / foco

WHITE = "#FFFFFF"
GRAY = "#BBBBC0"
GRAY_LIGHT = "#F2F2F4"
GRAY_DARK = "#242428"

# ---------------------------------------------------------------------------
# Color · texto
# ---------------------------------------------------------------------------
TEXT_PRIMARY = ("#23252A", "#E8E8EA")      # títulos, valores importantes (gris oscuro, no negro puro)
TEXT_SECONDARY = ("#6B6C74", "#9B9BA1")    # subtítulos, metadatos
TEXT_MUTED = ("#5B5B60", "#9B9BA1")        # alias retrocompatible de TEXT_SECONDARY
TEXT_DISABLED = ("#B4B5BB", "#5A5B60")

# ---------------------------------------------------------------------------
# Color · marca (verde OPENTOWORK, se conserva)
# ---------------------------------------------------------------------------
GREEN = "#008600"
GREEN_HOVER = "#046B08"
GREEN_PRESSED = "#035907"
GREEN_SOFT = ("#E7F5E9", "#123319")        # fondo suave de acento (chips, badges "real")
GREEN_SOFT_TEXT = ("#0F7B2E", "#4ADE80")

# ---------------------------------------------------------------------------
# Color · estados semánticos por oferta
# ---------------------------------------------------------------------------
STATE_FAVORITE = "#D08700"
STATE_APPLIED = GREEN
STATE_DISCARDED = "#6B6B70"
ROW_DISCARDED_FG = ("#A6A6AC", "#5E5E64")

# ---------------------------------------------------------------------------
# Color · tabla de resultados
# ---------------------------------------------------------------------------
TABLE_BG = SURFACE
TABLE_FG = TEXT_PRIMARY
TABLE_HEADING_BG = (GRAY_LIGHT, "#2A2A2E")
TABLE_ROW_ALT_BG = SURFACE_ALT
TABLE_ROW_HOVER_BG = ("#EFF6F0", "#22301F")
ROW_API_BG = ("#EEF8F0", "#152A17")
ROW_SEARCH_BG = (SURFACE_ALT[0], "#2A2A2E")
MATCH_HIGH = ("#0F7B2E", "#4ADE80")
MATCH_MID = ("#9A6B00", "#F5C451")
MATCH_LOW = ("#6B6B70", "#9B9BA1")
SELECTION_BG = ("#D7EFDC", "#1F4B2C")
SELECTION_FG = ("#0A3D14", "#BEE8C8")
DESCRIPTION_BG = SURFACE_SUNKEN

# Fondo de los divisores arrastrables (tk.PanedWindow no sigue el modo CTk).
WINDOW_BG = BG_MAIN

# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 14, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_CAPTION = (FONT_FAMILY, 10)
FONT_BADGE = (FONT_FAMILY, 11, "bold")

# ---------------------------------------------------------------------------
# Espaciado (escala 4px)
# ---------------------------------------------------------------------------
SPACE_XXS = 2
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

# ---------------------------------------------------------------------------
# Radios de borde
# ---------------------------------------------------------------------------
RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16
RADIUS_PILL = 999

# ---------------------------------------------------------------------------
# Bordes / grosor
# ---------------------------------------------------------------------------
BORDER_WIDTH = 1

# ---------------------------------------------------------------------------
# Dimensiones de layout
# ---------------------------------------------------------------------------
SIDEBAR_WIDTH = 280
SIDEBAR_MIN_WIDTH = 240
MAIN_AREA_MIN_WIDTH = 420
TABLE_MIN_HEIGHT = 200
DETAIL_HEIGHT = 220
DETAIL_MIN_HEIGHT = 150
HEADER_HEIGHT = 64
STATUSBAR_HEIGHT = 32

# ---------------------------------------------------------------------------
# Helpers de estilo por componente — devuelven kwargs listos para pasar a
# los constructores de CTk, para no repetir combinaciones de color en cada
# call site. No crean widgets ni contienen lógica de negocio.
# ---------------------------------------------------------------------------


def card_style(radius=RADIUS_LG):
    """Tarjeta de superficie: fondo blanco/oscuro, radio grande, sin borde propio."""
    return dict(fg_color=SURFACE, corner_radius=radius, border_width=0)


def bordered_card_style(radius=RADIUS_LG):
    """Igual que card_style pero con borde sutil, para tarjetas sobre BG_MAIN."""
    return dict(fg_color=SURFACE, corner_radius=radius, border_width=BORDER_WIDTH, border_color=BORDER)


def primary_button_style():
    """Botón de acción principal (verde) — ej. 'Search jobs'."""
    return dict(
        fg_color=GREEN, hover_color=GREEN_HOVER, text_color=WHITE,
        corner_radius=RADIUS_SM, font=FONT_SECTION, border_width=0,
    )


def secondary_button_style():
    """Botón outline neutro — ej. 'Export', 'Save configuration'."""
    return dict(
        fg_color="transparent", hover_color=SURFACE_ALT, text_color=TEXT_SECONDARY,
        corner_radius=RADIUS_SM, border_width=BORDER_WIDTH, border_color=BORDER_STRONG,
    )


def ghost_button_style():
    """Botón sin borde ni relleno — ej. '✕' eliminar fila, acciones menores."""
    return dict(
        fg_color="transparent", hover_color=SURFACE_ALT, text_color=TEXT_SECONDARY,
        corner_radius=RADIUS_SM, border_width=0,
    )


def pill_button_style():
    """Botón compacto tipo pill — ej. selector de idioma, control de tema en el header."""
    return dict(
        fg_color=SURFACE_ALT, hover_color=BORDER, text_color=TEXT_SECONDARY,
        corner_radius=RADIUS_PILL, border_width=0,
    )


def input_style():
    """Campo de texto estándar (CTkEntry)."""
    return dict(
        fg_color=SURFACE_ALT, border_color=BORDER, border_width=BORDER_WIDTH,
        corner_radius=RADIUS_SM, text_color=TEXT_PRIMARY,
    )


def checkbox_style():
    """CTkCheckBox con el verde de marca, compacto para listas densas."""
    return dict(
        fg_color=GREEN, hover_color=GREEN_HOVER, border_color=BORDER_STRONG,
        corner_radius=5, checkmark_color=WHITE, checkbox_width=20, checkbox_height=20,
        border_width=2,
    )


def badge_style(active=True):
    """Badge/pill informativo (tipo de oferta, % de match)."""
    if active:
        return dict(fg_color=GREEN_SOFT, text_color=GREEN_SOFT_TEXT, corner_radius=RADIUS_SM, font=FONT_BADGE)
    return dict(fg_color=SURFACE_ALT, text_color=TEXT_SECONDARY, corner_radius=RADIUS_SM, font=FONT_BADGE)
