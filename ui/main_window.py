import json
import queue
import re
import threading
import webbrowser
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk
from PIL import Image

from constants import (
    APP_NAME, APP_VERSION, APP_AUTHOR, DEFAULT_ROLES, DEFAULT_LOCATIONS,
    DEFAULT_SOURCES, DEFAULT_SOURCE_GROUPS, SOURCE_GROUP_OF, SOURCE_GROUP_OTHER,
)
from core.scoring import DEFAULT_PROFILE_KEYWORDS, normalize_text
from core.sources import (
    SourceFetchError, SOURCE_DOMAINS, make_search_links, dedupe_jobs,
    fetch_remoteok, fetch_remotive, fetch_arbeitnow, fetch_jobicy,
)
from core.export import now_stamp, export_txt, export_csv, export_html
from core.config_store import RESULTS_DIR, CONFIG_FILE, LEGACY_CONFIG_FILE, find_legacy_appdata_config
from core.job_states import job_key, load_states, save_states, load_seen, save_seen
from core.logging_setup import setup_logging
from i18n import t
from ui import icons, theme

logger = setup_logging()


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        # Barra de título minimalista: sin texto (el logo del header ya identifica
        # la app); el icono pequeño se oculta en _hide_titlebar_icon.
        self.title("")
        self.geometry("1360x800")
        self.minsize(1180, 680)
        self.configure(fg_color=theme.BG_MAIN)
        self._set_icon()

        self.language = "es"
        self.jobs = []
        self.displayed_jobs = []
        self.selected_job = None
        self.role_vars = {}
        self.role_widgets = {}
        self.location_vars = {}
        self.location_widgets = {}
        self.source_vars = {}
        self.source_widgets = {}
        self.custom_source_vars = {}
        self.custom_source_domains = {}
        self.custom_source_widgets = {}
        self.keyword_vars = {}
        self.keyword_weight_vars = {}
        self.keyword_widgets = {}
        self.search_queue = queue.Queue()
        self.search_in_progress = False
        self.only_offers_var = tk.BooleanVar(value=False)
        self.search_button = None
        self.export_button = None
        self.save_button = None
        self.delete_unchecked_buttons = []
        self.job_states = load_states()
        self.seen_jobs = load_seen()

        self._build_layout()
        self.load_config()
        self.after(60, self._set_titlebar_color)

    def _set_icon(self):
        try:
            self.iconbitmap(str(theme.ICON_PATH))
        except Exception:
            pass
        try:
            from PIL import ImageTk

            # Windows elige el icono por tamaño: 16px para la barra de título,
            # 32px+ para la barra de tareas y alt-tab. El 16px se pinta del
            # mismo color que la barra de título (Tk no conserva el alfa al
            # convertir a HICON), así queda visualmente vacía sin perder el
            # logo real en la barra de tareas. Se refresca al cambiar de tema.
            logo = Image.open(theme.LOGO_PATH)
            caption = theme.BG_MAIN[self._dark_mode_index()]
            blank = Image.new("RGB", (16, 16), caption)
            self._icon_images = [ImageTk.PhotoImage(blank)] + [
                ImageTk.PhotoImage(logo.resize((s, s), Image.LANCZOS)) for s in (32, 48, 256)
            ]
            self.iconphoto(False, *self._icon_images)
        except Exception:
            pass

    def _set_titlebar_color(self):
        # La barra de título nativa de Windows se pinta azulada por defecto y
        # desentona con el header blanco; DWM permite igualarla al tema actual.
        # (Solo Windows 11; en otros sistemas falla en silencio y no pasa nada.)
        try:
            import ctypes

            def colorref(hex_color):
                value = hex_color.lstrip("#")
                r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
                return (b << 16) | (g << 8) | r

            idx = self._dark_mode_index()
            # Mismo gris que el header: barra de título y header forman una sola banda.
            caption = colorref(theme.BG_MAIN[idx])
            text = colorref(("#1A1A1A", "#E8E8EA")[idx])
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR = 35, 36
            for attr, value in ((DWMWA_CAPTION_COLOR, caption), (DWMWA_TEXT_COLOR, text)):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(ctypes.c_int(value)), 4
                )
        except Exception:
            pass

    def t(self, key, **kwargs):
        return t(self.language, key, **kwargs)

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        # Divisores arrastrables: el usuario puede achicar/agrandar el panel de
        # búsqueda y el de detalle; los minsize evitan textos ilegibles.
        # El bg se fija ya en la creación: las tarjetas CTk capturan el color
        # del padre al construirse para dibujar sus esquinas redondeadas, y si
        # el paned aún tuviera el gris de sistema aparecerían picos claros.
        # opaqueresize=False: durante el arrastre solo se mueve una línea guía
        # y el contenido se reorganiza una única vez al soltar. Con el valor por
        # defecto (True) cada pixel de arrastre relanza el layout de todo el
        # árbol CTk y aparecen artefactos (textos cortados, tearing).
        self.h_paned = tk.PanedWindow(
            self, orient="horizontal", sashwidth=6, bd=0, relief="flat",
            bg=theme.WINDOW_BG[self._dark_mode_index()], opaqueresize=False,
        )
        self._style_paned_proxy(self.h_paned)
        self.h_paned.grid(row=1, column=0, sticky="nsew")
        self._build_sidebar()
        self._build_main_area()
        self._build_status_bar()
        self._update_paned_colors()

    def _style_paned_proxy(self, paned):
        # Línea guía verde durante el arrastre del divisor (Tk >= 8.6.6);
        # si la opción no existe se usa la guía por defecto del sistema.
        try:
            paned.configure(proxybackground=theme.GREEN, proxyborderwidth=0, proxyrelief="flat")
        except tk.TclError:
            pass

    def _update_paned_colors(self):
        idx = self._dark_mode_index()
        for paned in (self.h_paned, self.v_paned):
            paned.configure(bg=theme.WINDOW_BG[idx])

    # ---------- Header ----------

    def _build_header(self):
        # El header comparte fondo con la ventana: así la pestaña de carpeta
        # (blanca) destaca sobre él y se funde con el panel del sidebar de abajo,
        # dibujando la silueta de carpeta de Windows arriba a la izquierda.
        header = ctk.CTkFrame(self, height=theme.HEADER_HEIGHT, corner_radius=0, fg_color=theme.BG_MAIN)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # Espaciador de marca: ocupa exactamente el ancho del sidebar (+ divisor)
        # para que el filtro rápido arranque alineado con el borde izquierdo de la
        # tarjeta de resultados. El logo ya no vive aquí (ensuciaba el header):
        # ahora es marca de agua dentro del área de resultados.
        brand = ctk.CTkFrame(
            header, fg_color="transparent",
            width=theme.SIDEBAR_WIDTH + 6, height=theme.HEADER_HEIGHT - 2 * theme.SPACE_XS,
        )
        brand.grid(row=0, column=0, pady=theme.SPACE_XS, sticky="w")
        brand.grid_propagate(False)
        self.header_brand = brand

        # Pestaña de carpeta: esquinas superiores redondeadas visibles; las
        # inferiores quedan recortadas por el borde del header, y justo debajo
        # empieza la tarjeta del sidebar (mismo color) → conexión sin costura.
        tab_visible = 30
        self.folder_tab = ctk.CTkFrame(
            header, width=150, height=tab_visible + theme.RADIUS_MD + 6,
            corner_radius=theme.RADIUS_MD, fg_color=theme.SURFACE,
        )
        self.folder_tab.place(x=theme.SPACE_MD, y=theme.HEADER_HEIGHT - tab_visible)

        search_wrap = ctk.CTkFrame(
            header, fg_color=theme.SURFACE_ALT, corner_radius=theme.RADIUS_PILL,
            border_width=theme.BORDER_WIDTH, border_color=theme.BORDER,
        )
        # padx izquierdo = padx de la tarjeta de la tabla (12), para que ambas
        # cajas compartan la misma vertical.
        search_wrap.grid(row=0, column=1, padx=(theme.SPACE_MD, theme.SPACE_LG), pady=theme.SPACE_SM, sticky="ew")
        search_wrap.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            search_wrap, text="", image=icons.search_icon(15, theme.TEXT_SECONDARY), width=16,
        ).grid(row=0, column=0, padx=(theme.SPACE_MD, theme.SPACE_XS), pady=theme.SPACE_XS)
        self.quick_filter_entry = ctk.CTkEntry(
            search_wrap, placeholder_text=self.t("quick_filter_placeholder"),
            fg_color="transparent", border_width=0, text_color=theme.TEXT_PRIMARY,
        )
        self.quick_filter_entry.grid(row=0, column=1, sticky="ew", padx=(0, theme.SPACE_MD), pady=theme.SPACE_XS)
        self.quick_filter_entry.bind("<Return>", self.apply_quick_filter)

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, padx=theme.SPACE_LG, pady=theme.SPACE_SM, sticky="e")
        # Filtro rápido de señal/ruido: oculta los enlaces de búsqueda y deja
        # solo las ofertas reales de las APIs.
        self.only_offers_switch = ctk.CTkSwitch(
            right, text=self.t("only_real_offers"), variable=self.only_offers_var,
            onvalue=True, offvalue=False, command=self._on_offers_filter_toggle,
            font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY,
            progress_color=theme.GREEN, switch_width=36, switch_height=18,
        )
        self.only_offers_switch.pack(side="left", padx=(0, theme.SPACE_MD))
        self.result_count_label = ctk.CTkLabel(
            right, text=self.t("result_count", n=0), font=theme.FONT_BODY, text_color=theme.TEXT_SECONDARY,
        )
        self.result_count_label.pack(side="left", padx=(0, theme.SPACE_MD))
        self.language_button = ctk.CTkButton(
            right, text="EN", width=36, height=30, command=self._toggle_language,
            **theme.pill_button_style(),
        )
        self.language_button.pack(side="left", padx=(0, theme.SPACE_XS))
        self.theme_button = ctk.CTkButton(
            right, text="🌙", width=36, height=30, command=self._toggle_theme,
            **theme.pill_button_style(),
        )
        self.theme_button.pack(side="left")

    def _toggle_theme(self):
        if ctk.get_appearance_mode() == "Light":
            ctk.set_appearance_mode("dark")
            self.theme_button.configure(text="☀")
        else:
            ctk.set_appearance_mode("light")
            self.theme_button.configure(text="🌙")
        self._setup_treeview_style()
        self._update_paned_colors()
        self._set_titlebar_color()
        self._set_icon()
        self._refresh_watermark()
        self._render_detail(self.selected_job)

    def _toggle_language(self):
        self.language = "en" if self.language == "es" else "es"
        self.save_config(silent=True)
        self._apply_language()

    def _apply_language(self):
        self.language_button.configure(text="ES" if self.language == "en" else "EN")
        self.only_offers_switch.configure(text=self.t("only_real_offers"))
        self.quick_filter_entry.configure(placeholder_text=self.t("quick_filter_placeholder"))
        self.result_count_label.configure(text=self.t("result_count", n=len(self.displayed_jobs)))
        self.search_button.configure(text=self.t("search_button"))
        self.export_button.configure(text=self.t("export_button"))
        self.save_button.configure(text=self.t("save_button"))
        self.roles_section_label.configure(text=self.t("section_roles"))
        self.location_section_label.configure(text=self.t("section_location"))
        self.sources_section_label.configure(text=self.t("section_sources"))
        for group_key, ui in self.source_group_uis.items():
            ui["label"].configure(text=self.t(group_key))
        self.custom_sources_section_label.configure(text=self.t("section_custom_sources"))
        self.custom_sources_hint_label.configure(text=self.t("section_custom_sources_hint"))
        self.keywords_section_label.configure(text=self.t("section_keywords"))
        for btn in self.delete_unchecked_buttons:
            btn.configure(text=self.t("delete_unchecked"))
        self.new_role_entry.configure(placeholder_text=self.t("new_role_placeholder"))
        self.custom_location_entry.configure(placeholder_text=self.t("new_location_placeholder"))
        self.new_custom_source_name_entry.configure(placeholder_text=self.t("new_source_name_placeholder"))
        self.new_custom_source_domain_entry.configure(placeholder_text=self.t("new_source_domain_placeholder"))
        self.add_custom_source_button.configure(text=self.t("add_source_button"))
        self.new_keyword_entry.configure(placeholder_text=self.t("new_keyword_placeholder"))
        self.add_keyword_button.configure(text=self.t("add_keyword_button"))

        headings = {
            "state": self.t("col_state"),
            "match": self.t("col_match"), "title": self.t("col_title"), "company": self.t("col_company"),
            "location": self.t("col_location"), "source": self.t("col_source"),
            "published": self.t("col_published"), "type": self.t("col_type"),
        }
        for col, text in headings.items():
            self.tree.heading(col, text=text)

        self.detail_open_button.configure(text=self.t("open_link_button"))
        self.detail_fallback_button.configure(text=self.t("open_fallback_button"))
        self.detail_export_button.configure(text=self.t("export_all_button"))
        self.favorite_button.configure(text=self.t("mark_favorite"))
        self.applied_button.configure(text=self.t("mark_applied"))
        self.discarded_button.configure(text=self.t("mark_discarded"))
        self.notes_entry.configure(placeholder_text=self.t("notes_placeholder"))

        self.status_label.configure(text=self.t("status_ready"))
        self.credit_label.configure(text=f"{APP_NAME} v{APP_VERSION} · {self.t('credit')} {APP_AUTHOR}")

        if self.jobs:
            self._refresh_tree_type_labels()
        else:
            self._set_empty_state(self.t("empty_results"))
        if self.selected_job:
            self._render_detail(self.selected_job)
        else:
            self.detail_empty_label.configure(text=self.t("empty_detail"))

    # ---------- Sidebar ----------

    def _build_sidebar(self):
        # bg_color explícito por la misma razón que table_frame: el padre es
        # tk.PanedWindow y CTk congelaría el color detectado en la creación.
        sidebar = ctk.CTkFrame(self.h_paned, corner_radius=0, fg_color=theme.BG_MAIN, bg_color=theme.BG_MAIN)
        self.sidebar_frame = sidebar
        self.h_paned.add(sidebar, width=theme.SIDEBAR_WIDTH, minsize=theme.SIDEBAR_MIN_WIDTH, stretch="never")
        sidebar.bind("<Configure>", self._on_sidebar_resize)

        # Cuerpo de la carpeta: tarjeta que arranca pegada al header, justo
        # debajo de la pestaña, para que ambas formen una sola silueta.
        card = ctk.CTkFrame(
            sidebar, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_LG, bg_color=theme.BG_MAIN,
        )
        card.pack(fill="both", expand=True, padx=(theme.SPACE_MD, 0), pady=(0, theme.SPACE_SM))
        # Parche que cuadra la esquina superior-izquierda bajo la pestaña: sin
        # él, el radio de la tarjeta dejaría una cuña gris entre pestaña y cuerpo.
        ctk.CTkFrame(card, width=48, height=24, corner_radius=0, fg_color=theme.SURFACE).place(x=0, y=0)

        self.search_button = ctk.CTkButton(
            card, text=self.t("search_button"), height=44, command=self.search_jobs,
            **theme.primary_button_style(),
        )
        self.search_button.pack(fill="x", padx=theme.SPACE_LG, pady=(theme.SPACE_LG, theme.SPACE_MD))

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=theme.SPACE_SM)
        self.sidebar_scroll = scroll

        # Orden por función: qué buscas (rol + keywords que afinan el match),
        # dónde (ubicación) y desde qué portales (fuentes).
        self._build_roles_section(scroll)
        self._build_keywords_section(scroll)
        self._build_location_section(scroll)
        self._build_sources_section(scroll)
        self._build_custom_sources_section(scroll)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=theme.SPACE_LG, pady=(theme.SPACE_XS, theme.SPACE_LG))
        self.export_button = ctk.CTkButton(
            actions, text=self.t("export_button"), command=self.export_all,
            **theme.secondary_button_style(),
        )
        self.export_button.pack(fill="x", pady=(0, theme.SPACE_SM))
        self.save_button = ctk.CTkButton(
            actions, text=self.t("save_button"), command=self.save_config,
            **theme.secondary_button_style(),
        )
        self.save_button.pack(fill="x")

    def _on_sidebar_resize(self, event=None):
        # Mantiene la zona de marca del header con el mismo ancho que el
        # sidebar, para que el filtro rápido siga alineado con la tarjeta de
        # resultados aunque se arrastre el divisor.
        if hasattr(self, "header_brand"):
            self.header_brand.configure(width=self.sidebar_frame.winfo_width() + 6)
        # Reajusta el ancho de línea de los textos que envuelven, para que
        # sigan leyéndose completos al achicar/agrandar el panel.
        if not hasattr(self, "custom_sources_hint_label"):
            return
        wrap = max(130, self.sidebar_frame.winfo_width() - 80)
        self.custom_sources_hint_label.configure(wraplength=wrap)

    def _section_card(self, parent):
        """Tarjeta contenedora de una sección del sidebar (Roles, Keywords, etc.)."""
        card = ctk.CTkFrame(parent, **theme.bordered_card_style())
        card.pack(fill="x", pady=(0, theme.SPACE_MD))
        return card

    def _section_label(self, parent, text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_MD, theme.SPACE_XS))
        # Acento de marca en lugar de emoji: los emojis traen colores propios
        # que no siguen el tema; una barra verde marca la sección sin ruido.
        accent = ctk.CTkFrame(row, width=3, height=14, corner_radius=2, fg_color=theme.GREEN)
        accent.pack(side="left")
        accent.pack_propagate(False)
        label = ctk.CTkLabel(row, text=text, font=theme.FONT_SECTION, text_color=theme.TEXT_PRIMARY, anchor="w")
        label.pack(side="left", fill="x", expand=True, padx=(theme.SPACE_SM, 0))
        return label

    def _small_action_button(self, parent, text, command):
        button = ctk.CTkButton(
            parent, text=text, height=26, font=theme.FONT_SMALL, command=command,
            **theme.ghost_button_style(),
        )
        button.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_XS, theme.SPACE_MD))
        self.delete_unchecked_buttons.append(button)
        return button

    def _add_row_entry(self, parent, placeholder):
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, **theme.input_style())
        return entry

    def _add_row_button(self, parent, command):
        return ctk.CTkButton(parent, text="+", width=32, command=command, **theme.primary_button_style())

    def _row_checkbox(self, parent, text, variable):
        return ctk.CTkCheckBox(
            parent, text=text, variable=variable, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            text_color=theme.TEXT_PRIMARY, **theme.checkbox_style(),
        )

    def _row_delete_button(self, parent, command):
        return ctk.CTkButton(
            parent, text="✕", width=24, height=24, command=command, **theme.ghost_button_style(),
        )

    def _build_roles_section(self, parent):
        card = self._section_card(parent)
        self.roles_section_label = self._section_label(card, self.t("section_roles"))
        self.roles_frame = ctk.CTkFrame(card, fg_color="transparent", height=0)
        self.roles_frame.pack(fill="x", padx=theme.SPACE_MD)
        for r in DEFAULT_ROLES:
            self.create_role_row(r, enabled=True)

        add_row = ctk.CTkFrame(card, fg_color="transparent", height=0)
        add_row.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))
        self.new_role_entry = self._add_row_entry(add_row, self.t("new_role_placeholder"))
        self.new_role_entry.pack(side="left", fill="x", expand=True)
        self.new_role_entry.bind("<Return>", lambda e: self.add_role())
        self._add_row_button(add_row, self.add_role).pack(side="left", padx=(theme.SPACE_XS, 0))
        self._small_action_button(card, self.t("delete_unchecked"), self.delete_unchecked_roles)

    def _build_location_section(self, parent):
        card = self._section_card(parent)
        self.location_section_label = self._section_label(card, self.t("section_location"))
        self.locations_frame = ctk.CTkFrame(card, fg_color="transparent", height=0)
        self.locations_frame.pack(fill="x", padx=theme.SPACE_MD)
        for loc in DEFAULT_LOCATIONS:
            self.create_location_row(loc, enabled=True)

        add_row = ctk.CTkFrame(card, fg_color="transparent", height=0)
        add_row.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))
        self.custom_location_entry = self._add_row_entry(add_row, self.t("new_location_placeholder"))
        self.custom_location_entry.pack(side="left", fill="x", expand=True)
        self.custom_location_entry.bind("<Return>", lambda e: self.add_location())
        self._add_row_button(add_row, self.add_location).pack(side="left", padx=(theme.SPACE_XS, 0))
        self._small_action_button(card, self.t("delete_unchecked"), self.delete_unchecked_locations)

    def _build_sources_section(self, parent):
        # Con 30+ fuentes, una lista plana sería un muro de checkboxes: cada
        # categoría se muestra como un grupo plegable con contador activas/total,
        # plegado por defecto para que el sidebar siga siendo compacto.
        card = self._section_card(parent)
        self.sources_section_label = self._section_label(card, self.t("section_sources"))
        self.sources_frame = ctk.CTkFrame(card, fg_color="transparent", height=0)
        self.sources_frame.pack(fill="x", padx=theme.SPACE_MD)

        self.source_group_uis = {}
        self._source_group_order = [key for key, _ in DEFAULT_SOURCE_GROUPS] + [SOURCE_GROUP_OTHER]
        for group_key in self._source_group_order:
            self._build_source_group(group_key)
        for src, enabled in DEFAULT_SOURCES.items():
            self.create_source_row(src, enabled=enabled)
        self._update_source_group_counts()
        self._small_action_button(card, self.t("delete_unchecked"), self.delete_unchecked_sources)

    def _build_source_group(self, group_key):
        # Sin pack inicial: _update_source_group_counts empaqueta los grupos
        # con fuentes siguiendo siempre el orden canónico de las categorías.
        container = ctk.CTkFrame(self.sources_frame, fg_color="transparent")

        header = ctk.CTkFrame(container, fg_color="transparent", cursor="hand2")
        header.pack(fill="x", pady=1)
        chevron = ctk.CTkLabel(header, text="▸", width=16, font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY, anchor="w")
        chevron.pack(side="left")
        label = ctk.CTkLabel(header, text=self.t(group_key), font=theme.FONT_BODY, text_color=theme.TEXT_PRIMARY, anchor="w")
        label.pack(side="left", fill="x", expand=True)
        count = ctk.CTkLabel(header, text="", font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY, anchor="e")
        count.pack(side="right")
        for widget in (header, chevron, label, count):
            widget.bind("<Button-1>", lambda e, k=group_key: self._toggle_source_group(k))

        # El cuerpo se crea sin pack: el grupo nace plegado.
        body = ctk.CTkFrame(container, fg_color="transparent")
        self.source_group_uis[group_key] = {
            "container": container, "header": header, "chevron": chevron,
            "label": label, "count": count, "body": body,
        }

    def _toggle_source_group(self, group_key):
        ui = self.source_group_uis[group_key]
        if ui["body"].winfo_manager():
            ui["body"].pack_forget()
            ui["chevron"].configure(text="▸")
        else:
            ui["body"].pack(fill="x", padx=(theme.SPACE_MD, 0))
            ui["chevron"].configure(text="▾")

    def _source_group_for(self, source):
        return SOURCE_GROUP_OF.get(source, SOURCE_GROUP_OTHER)

    def _update_source_group_counts(self):
        if not hasattr(self, "source_group_uis"):
            return
        # Re-empaquetado completo en orden canónico: si solo se re-empaquetara
        # el grupo que cambia, quedaría al final y las categorías se
        # desordenarían. Los grupos vacíos (p. ej. "Otras") no ocupan sitio.
        for group_key in self._source_group_order:
            ui = self.source_group_uis[group_key]
            names = [s for s in self.source_vars if self._source_group_for(s) == group_key]
            active = sum(1 for s in names if self.source_vars[s].get())
            ui["count"].configure(text=f"{active}/{len(names)}")
            ui["container"].pack_forget()
            if names:
                ui["container"].pack(fill="x")

    def _build_custom_sources_section(self, parent):
        card = self._section_card(parent)
        self.custom_sources_section_label = self._section_label(card, self.t("section_custom_sources"))
        self.custom_sources_hint_label = ctk.CTkLabel(
            card, text=self.t("section_custom_sources_hint"),
            font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY, anchor="w",
            wraplength=theme.SIDEBAR_WIDTH - 80, justify="left",
        )
        self.custom_sources_hint_label.pack(fill="x", padx=theme.SPACE_MD)
        self.custom_sources_frame = ctk.CTkFrame(card, fg_color="transparent", height=0)
        self.custom_sources_frame.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))

        self.new_custom_source_name_entry = self._add_row_entry(card, self.t("new_source_name_placeholder"))
        self.new_custom_source_name_entry.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, theme.SPACE_XXS))
        self.new_custom_source_domain_entry = self._add_row_entry(card, self.t("new_source_domain_placeholder"))
        self.new_custom_source_domain_entry.pack(fill="x", padx=theme.SPACE_MD)
        self.new_custom_source_domain_entry.bind("<Return>", lambda e: self.add_custom_source())
        self.add_custom_source_button = ctk.CTkButton(
            card, text=self.t("add_source_button"), command=self.add_custom_source,
            **theme.primary_button_style(),
        )
        self.add_custom_source_button.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))
        self._small_action_button(card, self.t("delete_unchecked"), self.delete_unchecked_custom_sources)

    def _build_keywords_section(self, parent):
        card = self._section_card(parent)
        self.keywords_section_label = self._section_label(card, self.t("section_keywords"))
        self.keywords_frame = ctk.CTkFrame(card, fg_color="transparent", height=0)
        self.keywords_frame.pack(fill="x", padx=theme.SPACE_MD)
        for k, pts in DEFAULT_PROFILE_KEYWORDS.items():
            self.create_keyword_row(k, pts, enabled=True)

        add_row = ctk.CTkFrame(card, fg_color="transparent", height=0)
        add_row.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))
        self.new_keyword_entry = self._add_row_entry(add_row, self.t("new_keyword_placeholder"))
        self.new_keyword_entry.pack(side="left", fill="x", expand=True)
        self.new_keyword_entry.bind("<Return>", lambda e: self.add_keyword())
        self.new_keyword_points_entry = ctk.CTkEntry(add_row, width=40, **theme.input_style())
        self.new_keyword_points_entry.insert(0, "10")
        self.new_keyword_points_entry.pack(side="left", padx=(theme.SPACE_XS, 0))
        self.add_keyword_button = ctk.CTkButton(
            card, text=self.t("add_keyword_button"), command=self.add_keyword,
            **theme.primary_button_style(),
        )
        self.add_keyword_button.pack(fill="x", padx=theme.SPACE_MD, pady=(theme.SPACE_SM, 0))
        self._small_action_button(card, self.t("delete_unchecked"), self.delete_unchecked_keywords)

    # ---------- Roles ----------

    def create_role_row(self, role, enabled=True):
        role = normalize_text(role)
        if not role or role in self.role_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.role_vars[role] = v

        row = ctk.CTkFrame(self.roles_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=2)
        self._row_checkbox(row, role, v).pack(side="left", fill="x", expand=True, anchor="w")
        self._row_delete_button(row, lambda r=role: self.delete_role(r)).pack(side="right")
        self.role_widgets[role] = row

    def add_role(self):
        role = normalize_text(self.new_role_entry.get())
        if not role:
            return
        if role in self.role_vars:
            self.role_vars[role].set(True)
            self.new_role_entry.delete(0, "end")
            return
        self.create_role_row(role, enabled=True)
        self.new_role_entry.delete(0, "end")
        self.save_config(silent=True)

    def delete_role(self, role, save=True):
        widget = self.role_widgets.pop(role, None)
        if widget is not None:
            widget.destroy()
        self.role_vars.pop(role, None)
        if save:
            self.save_config(silent=True)

    def delete_unchecked_roles(self):
        to_delete = [r for r, v in self.role_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, self.t("no_unchecked_roles"))
            return
        if messagebox.askyesno(APP_NAME, self.t("confirm_delete_roles", n=len(to_delete))):
            for role in to_delete:
                self.delete_role(role)

    # ---------- Keywords ----------

    def create_keyword_row(self, keyword, points=10, enabled=True):
        keyword = normalize_text(keyword).lower()
        if not keyword or keyword in self.keyword_vars:
            return
        v = tk.BooleanVar(value=enabled)
        pts_str = str(int(points)) if str(points).isdigit() else "10"
        pts = tk.StringVar(value=pts_str)
        self.keyword_vars[keyword] = v
        self.keyword_weight_vars[keyword] = pts

        row = ctk.CTkFrame(self.keywords_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=2)
        self._row_checkbox(row, keyword, v).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkEntry(row, width=40, textvariable=pts, **theme.input_style()).pack(side="left", padx=(theme.SPACE_XS, theme.SPACE_XXS))
        self._row_delete_button(row, lambda k=keyword: self.delete_keyword(k)).pack(side="right")
        self.keyword_widgets[keyword] = row

    def _keyword_points(self, keyword):
        try:
            return int(self.keyword_weight_vars[keyword].get())
        except Exception:
            return 10

    def add_keyword(self):
        keyword = normalize_text(self.new_keyword_entry.get()).lower()
        if not keyword:
            return
        try:
            points = int(self.new_keyword_points_entry.get())
        except Exception:
            points = 10
        points = max(1, min(50, points))
        if keyword in self.keyword_vars:
            self.keyword_vars[keyword].set(True)
            self.keyword_weight_vars[keyword].set(str(points))
        else:
            self.create_keyword_row(keyword, points, enabled=True)
        self.new_keyword_entry.delete(0, "end")
        self.save_config(silent=True)

    def delete_keyword(self, keyword, save=True):
        widget = self.keyword_widgets.pop(keyword, None)
        if widget is not None:
            widget.destroy()
        self.keyword_vars.pop(keyword, None)
        self.keyword_weight_vars.pop(keyword, None)
        if save:
            self.save_config(silent=True)

    def delete_unchecked_keywords(self):
        to_delete = [k for k, v in self.keyword_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, self.t("no_unchecked_keywords"))
            return
        if messagebox.askyesno(APP_NAME, self.t("confirm_delete_keywords", n=len(to_delete))):
            for keyword in to_delete:
                self.delete_keyword(keyword)

    # ---------- Locations ----------

    def create_location_row(self, location, enabled=True):
        location = normalize_text(location)
        if not location or location in self.location_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.location_vars[location] = v

        row = ctk.CTkFrame(self.locations_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=2)
        self._row_checkbox(row, location, v).pack(side="left", fill="x", expand=True, anchor="w")
        self._row_delete_button(row, lambda l=location: self.delete_location(l)).pack(side="right")
        self.location_widgets[location] = row

    def add_location(self):
        location = normalize_text(self.custom_location_entry.get())
        if not location:
            return
        if location in self.location_vars:
            self.location_vars[location].set(True)
            self.custom_location_entry.delete(0, "end")
            return
        self.create_location_row(location, enabled=True)
        self.custom_location_entry.delete(0, "end")
        self.save_config(silent=True)

    def delete_location(self, location, save=True):
        widget = self.location_widgets.pop(location, None)
        if widget is not None:
            widget.destroy()
        self.location_vars.pop(location, None)
        if save:
            self.save_config(silent=True)

    def delete_unchecked_locations(self):
        to_delete = [l for l, v in self.location_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, self.t("no_unchecked_locations"))
            return
        if messagebox.askyesno(APP_NAME, self.t("confirm_delete_locations", n=len(to_delete))):
            for location in to_delete:
                self.delete_location(location)

    # ---------- Built-in sources ----------

    def create_source_row(self, source, enabled=True):
        source = normalize_text(source)
        if not source or source in self.source_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.source_vars[source] = v

        body = self.source_group_uis[self._source_group_for(source)]["body"]
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=2)
        checkbox = self._row_checkbox(row, source, v)
        checkbox.configure(command=self._update_source_group_counts)
        checkbox.pack(side="left", fill="x", expand=True, anchor="w")
        self._row_delete_button(row, lambda s=source: self.delete_source(s)).pack(side="right")
        self.source_widgets[source] = row
        self._update_source_group_counts()

    def delete_source(self, source, save=True):
        widget = self.source_widgets.pop(source, None)
        if widget is not None:
            widget.destroy()
        self.source_vars.pop(source, None)
        self._update_source_group_counts()
        if save:
            self.save_config(silent=True)

    def delete_unchecked_sources(self):
        to_delete = [s for s, v in self.source_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, self.t("no_unchecked_sources"))
            return
        if messagebox.askyesno(APP_NAME, self.t("confirm_delete_sources", n=len(to_delete))):
            for source in to_delete:
                self.delete_source(source)

    # ---------- Custom sources ----------

    def create_custom_source_row(self, name, domain, enabled=True):
        name = normalize_text(name)
        domain = normalize_text(domain).lower()
        if not name or not domain or name in self.custom_source_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.custom_source_vars[name] = v
        self.custom_source_domains[name] = domain

        row = ctk.CTkFrame(self.custom_sources_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=2)
        self._row_checkbox(row, f"{name} ({domain})", v).pack(side="left", fill="x", expand=True, anchor="w")
        self._row_delete_button(row, lambda n=name: self.delete_custom_source(n)).pack(side="right")
        self.custom_source_widgets[name] = row

    def add_custom_source(self):
        name = normalize_text(self.new_custom_source_name_entry.get())
        domain = normalize_text(self.new_custom_source_domain_entry.get()).lower()
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        if not name or not domain:
            messagebox.showwarning(APP_NAME, self.t("need_name_domain"))
            return
        if name in self.custom_source_vars:
            self.custom_source_vars[name].set(True)
            self.custom_source_domains[name] = domain
        else:
            self.create_custom_source_row(name, domain, enabled=True)
        self.new_custom_source_name_entry.delete(0, "end")
        self.new_custom_source_domain_entry.delete(0, "end")
        self.save_config(silent=True)

    def delete_custom_source(self, name, save=True):
        widget = self.custom_source_widgets.pop(name, None)
        if widget is not None:
            widget.destroy()
        self.custom_source_vars.pop(name, None)
        self.custom_source_domains.pop(name, None)
        if save:
            self.save_config(silent=True)

    def delete_unchecked_custom_sources(self):
        to_delete = [n for n, v in self.custom_source_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, self.t("no_unchecked_custom_sources"))
            return
        if messagebox.askyesno(APP_NAME, self.t("confirm_delete_custom_sources", n=len(to_delete))):
            for name in to_delete:
                self.delete_custom_source(name)

    def all_source_domains(self):
        domains = dict(SOURCE_DOMAINS)
        domains.update(self.custom_source_domains)
        return domains

    # ---------- Selection helpers ----------

    def selected_roles(self):
        roles = [r for r, v in self.role_vars.items() if v.get()]
        custom = normalize_text(self.new_role_entry.get())
        if custom and custom not in roles:
            roles.append(custom)
        return roles

    def selected_locations(self):
        locs = [l for l, v in self.location_vars.items() if v.get()]
        custom = normalize_text(self.custom_location_entry.get())
        if custom and custom not in locs:
            locs.append(custom)
        return locs or ["Remote"]

    def selected_sources(self):
        sources = [s for s, v in self.source_vars.items() if v.get()]
        sources += [s for s, v in self.custom_source_vars.items() if v.get()]
        return sources

    def selected_keywords(self):
        return {k: self._keyword_points(k) for k, v in self.keyword_vars.items() if v.get()}

    # ---------- Main area: results table ----------

    def _dark_mode_index(self):
        return 1 if ctk.get_appearance_mode() == "Dark" else 0

    def _setup_treeview_style(self):
        idx = self._dark_mode_index()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "OTW.Treeview", background=theme.TABLE_BG[idx], fieldbackground=theme.TABLE_BG[idx],
            foreground=theme.TABLE_FG[idx], rowheight=30, borderwidth=0, font=theme.FONT_BODY,
            relief="flat",
            # clam dibuja un borde propio con estos tres colores; igualarlos al
            # fondo elimina el marco claro que se ve alrededor de la tabla en oscuro.
            bordercolor=theme.TABLE_BG[idx], lightcolor=theme.TABLE_BG[idx], darkcolor=theme.TABLE_BG[idx],
        )
        # Cabecera integrada en la tarjeta (mismo fondo, texto secundario en
        # menor peso): las bandas grises de cabecera rompen la superficie.
        style.configure(
            "OTW.Treeview.Heading", background=theme.TABLE_BG[idx], foreground=theme.TEXT_SECONDARY[idx],
            font=theme.FONT_SMALL, relief="flat", padding=(6, 9),
            bordercolor=theme.TABLE_BG[idx], lightcolor=theme.TABLE_BG[idx], darkcolor=theme.TABLE_BG[idx],
        )
        style.map("OTW.Treeview.Heading", background=[("active", theme.TABLE_BG[idx])])
        style.map(
            "OTW.Treeview", background=[("selected", theme.SELECTION_BG[idx])],
            foreground=[("selected", theme.SELECTION_FG[idx])],
        )
        if hasattr(self, "tree"):
            self.tree.tag_configure("api", background=theme.ROW_API_BG[idx])
            self.tree.tag_configure("search", background=theme.ROW_SEARCH_BG[idx])
            self.tree.tag_configure("match_high", foreground=theme.MATCH_HIGH[idx])
            self.tree.tag_configure("match_mid", foreground=theme.MATCH_MID[idx])
            self.tree.tag_configure("match_low", foreground=theme.MATCH_LOW[idx])
            self.tree.tag_configure("discarded", foreground=theme.ROW_DISCARDED_FG[idx])

    def _build_main_area(self):
        self.v_paned = tk.PanedWindow(
            self.h_paned, orient="vertical", sashwidth=6, bd=0, relief="flat",
            bg=theme.WINDOW_BG[self._dark_mode_index()], opaqueresize=False,
        )
        self._style_paned_proxy(self.v_paned)
        self.h_paned.add(self.v_paned, minsize=theme.MAIN_AREA_MIN_WIDTH, stretch="always")

        # bg_color explícito: el padre es tk.PanedWindow, así que CTk no puede
        # deducir el color de fondo del tema y las esquinas saldrían claras.
        self.table_frame = ctk.CTkFrame(self.v_paned, bg_color=theme.BG_MAIN, **theme.bordered_card_style())
        self.v_paned.add(self.table_frame, minsize=theme.TABLE_MIN_HEIGHT, stretch="always", padx=12, pady=8)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        columns = ("state", "match", "title", "company", "location", "source", "published", "type")
        headings = {
            "state": self.t("col_state"),
            "match": self.t("col_match"), "title": self.t("col_title"), "company": self.t("col_company"),
            "location": self.t("col_location"), "source": self.t("col_source"),
            "published": self.t("col_published"), "type": self.t("col_type"),
        }
        widths = {"state": 80, "match": 70, "title": 250, "company": 150, "location": 130, "source": 130, "published": 100, "type": 155}
        # Los datos numéricos/simbólicos centrados se escanean mejor; el texto, a la izquierda.
        anchors = {"state": "center", "match": "center"}
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", style="OTW.Treeview")
        for c in columns:
            self.tree.heading(c, text=headings[c], anchor=anchors.get(c, "w"))
            self.tree.column(c, width=widths[c], anchor=anchors.get(c, "w"))
        self._setup_treeview_style()
        # El Treeview es un rectángulo opaco: si toca los bordes de la tarjeta
        # tapa las esquinas redondeadas, así que se inseta lo justo para que
        # la curva del radio quede siempre visible.
        self.tree.grid(
            row=0, column=0, sticky="nsew",
            padx=(theme.SPACE_MD, 0), pady=(theme.SPACE_SM, theme.SPACE_MD),
        )
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())

        tree_scroll = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=0, column=1, sticky="ns", padx=(0, theme.SPACE_XS), pady=(theme.SPACE_SM, theme.SPACE_MD))

        self._build_empty_state()
        self._build_detail_panel()

    def _build_empty_state(self):
        # Estado vacío centrado sobre la tabla: icono, título, texto y CTA.
        # Reutiliza las traducciones existentes de "empty_results" / "searching"
        # (primera línea = título, segunda línea opcional = subtítulo).
        self.empty_state_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")

        # Marca de agua: el logo grande y muy tenue, fundido con la superficie de
        # la tarjeta (Tk no compone alfa parcial fiable, así que la opacidad se
        # hornea en la imagen). Va encima del texto en el flujo vertical para que
        # nada lo solape, y se regenera al cambiar de tema.
        self.watermark_label = ctk.CTkLabel(self.empty_state_frame, text="", fg_color="transparent")
        self.watermark_label.pack(pady=(0, theme.SPACE_MD))
        self._refresh_watermark()

        self.empty_state_title_label = ctk.CTkLabel(
            self.empty_state_frame, text="", font=theme.FONT_SUBTITLE, text_color=theme.TEXT_PRIMARY,
        )
        self.empty_state_title_label.pack()
        self.empty_state_label = ctk.CTkLabel(
            self.empty_state_frame, text="", font=theme.FONT_BODY, text_color=theme.TEXT_SECONDARY, justify="center",
        )
        self.empty_state_label.pack(pady=(theme.SPACE_XS, 0))

        self._set_empty_state(self.t("empty_results"))

    def _refresh_watermark(self):
        try:
            self._watermark_image = icons.watermark_logo(theme.LOGO_PATH, 300, theme.SURFACE)
            self.watermark_label.configure(image=self._watermark_image)
        except Exception:
            pass

    def _set_empty_state(self, message):
        lines = message.split("\n", 1)
        self.empty_state_title_label.configure(text=lines[0])
        self.empty_state_label.configure(text=lines[1] if len(lines) > 1 else "")
        # Ligeramente por debajo del centro para no rozar la fila de cabeceras.
        self.empty_state_frame.place(relx=0.5, rely=0.56, anchor="center")

    def _hide_empty_state(self):
        self.empty_state_frame.place_forget()

    def _build_detail_panel(self):
        self.detail_frame = ctk.CTkFrame(self.v_paned, bg_color=theme.BG_MAIN, **theme.bordered_card_style())
        self.v_paned.add(
            self.detail_frame, height=theme.DETAIL_HEIGHT, minsize=theme.DETAIL_MIN_HEIGHT,
            stretch="never", padx=12, pady=8,
        )
        self.detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_frame.grid_columnconfigure(0, weight=1)

        empty_wrap = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        self.detail_empty_wrap = empty_wrap
        ctk.CTkLabel(
            empty_wrap, text="", image=icons.document_icon(20, theme.TEXT_SECONDARY),
            fg_color=theme.SURFACE_ALT, corner_radius=theme.RADIUS_PILL, width=48, height=48,
        ).pack(pady=(0, theme.SPACE_SM))
        self.detail_empty_label = ctk.CTkLabel(
            empty_wrap, text=self.t("empty_detail"),
            font=theme.FONT_BODY, text_color=theme.TEXT_SECONDARY,
        )
        self.detail_empty_label.pack()
        empty_wrap.place(relx=0.5, rely=0.5, anchor="center")

        self.detail_content = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        self.detail_content.grid_columnconfigure(0, weight=1)
        self.detail_content.grid_columnconfigure(1, weight=0)
        self.detail_content.grid_rowconfigure(3, weight=1)

        header_row = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=theme.SPACE_LG, pady=(theme.SPACE_MD, 0))
        self.detail_type_badge = ctk.CTkLabel(
            header_row, text="", font=theme.FONT_BADGE, corner_radius=theme.RADIUS_SM, width=110, height=26,
        )
        self.detail_type_badge.pack(side="left")
        self.detail_match_badge = ctk.CTkLabel(
            header_row, text="", font=theme.FONT_BADGE, corner_radius=theme.RADIUS_SM, width=54, height=26,
        )
        self.detail_match_badge.pack(side="left", padx=(theme.SPACE_SM, 0))
        # Badge "Nueva": solo se muestra (pack) cuando la oferta no se había
        # visto en búsquedas anteriores.
        self.detail_new_badge = ctk.CTkLabel(
            header_row, text="", font=theme.FONT_BADGE, corner_radius=theme.RADIUS_SM, height=26,
            fg_color=theme.GREEN, text_color=theme.WHITE,
        )
        self.detail_title_label = ctk.CTkLabel(
            header_row, text="", font=theme.FONT_TITLE, text_color=theme.TEXT_PRIMARY, anchor="w",
        )
        self.detail_title_label.pack(side="left", padx=(theme.SPACE_MD, 0), fill="x", expand=True)

        self.detail_subtitle_label = ctk.CTkLabel(
            self.detail_content, text="", font=theme.FONT_BODY, text_color=theme.TEXT_SECONDARY,
            anchor="w", justify="left",
        )
        self.detail_subtitle_label.grid(row=1, column=0, sticky="ew", padx=theme.SPACE_LG, pady=(theme.SPACE_SM, 0))

        self.detail_skills_label = ctk.CTkLabel(
            self.detail_content, text="", font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY,
            anchor="w", justify="left",
        )
        self.detail_skills_label.grid(row=2, column=0, sticky="ew", padx=theme.SPACE_LG, pady=(theme.SPACE_XS, 0))

        self.detail_description_box = ctk.CTkTextbox(
            self.detail_content, height=70, font=theme.FONT_SMALL, wrap="word", corner_radius=theme.RADIUS_SM,
            fg_color=theme.DESCRIPTION_BG, text_color=theme.TEXT_PRIMARY, border_width=theme.BORDER_WIDTH,
            border_color=theme.BORDER,
        )
        self.detail_description_box.grid(row=3, column=0, sticky="nsew", padx=theme.SPACE_LG, pady=(theme.SPACE_SM, theme.SPACE_MD))

        buttons_col = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        buttons_col.grid(row=0, column=1, rowspan=4, sticky="n", padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        self.detail_open_button = ctk.CTkButton(
            buttons_col, text=self.t("open_link_button"), command=self.open_selected,
            **theme.primary_button_style(),
        )
        self.detail_open_button.pack(fill="x", pady=(0, theme.SPACE_SM))
        self.detail_fallback_button = ctk.CTkButton(
            buttons_col, text=self.t("open_fallback_button"), command=self.open_fallback,
            **theme.secondary_button_style(),
        )
        self.detail_fallback_button.pack(fill="x", pady=(0, theme.SPACE_SM))
        self.detail_export_button = ctk.CTkButton(
            buttons_col, text=self.t("export_all_button"), command=self.export_all,
            **theme.secondary_button_style(),
        )
        self.detail_export_button.pack(fill="x")

        state_row = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        state_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=theme.SPACE_LG, pady=(0, theme.SPACE_MD))
        self.favorite_button = ctk.CTkButton(
            state_row, text=self.t("mark_favorite"), width=104, height=28, font=theme.FONT_SMALL,
            corner_radius=theme.RADIUS_SM, command=lambda: self._toggle_state_flag("favorite"),
        )
        self.favorite_button.pack(side="left", padx=(0, theme.SPACE_SM))
        self.applied_button = ctk.CTkButton(
            state_row, text=self.t("mark_applied"), width=104, height=28, font=theme.FONT_SMALL,
            corner_radius=theme.RADIUS_SM, command=lambda: self._toggle_state_flag("applied"),
        )
        self.applied_button.pack(side="left", padx=(0, theme.SPACE_SM))
        self.discarded_button = ctk.CTkButton(
            state_row, text=self.t("mark_discarded"), width=104, height=28, font=theme.FONT_SMALL,
            corner_radius=theme.RADIUS_SM, command=lambda: self._toggle_state_flag("discarded"),
        )
        self.discarded_button.pack(side="left", padx=(0, theme.SPACE_MD))
        self.notes_entry = ctk.CTkEntry(
            state_row, height=28, font=theme.FONT_SMALL, placeholder_text=self.t("notes_placeholder"),
            **theme.input_style(),
        )
        self.notes_entry.pack(side="left", fill="x", expand=True)
        self.notes_entry.bind("<Return>", lambda e: self._save_notes())
        self.notes_entry.bind("<FocusOut>", lambda e: self._save_notes())
        for button in (self.favorite_button, self.applied_button, self.discarded_button):
            self._style_state_button(button, active=False, active_color=theme.GREEN)

    # ---------- Estado por oferta (Favorito / Aplicado / Descartado / Notas) ----------

    def _get_state(self, job):
        return self.job_states.get(job_key(job), {})

    def _update_state(self, job, **changes):
        key = job_key(job)
        if not key:
            return
        state = dict(self.job_states.get(key, {}))
        state.update(changes)
        if not any((state.get("favorite"), state.get("applied"), state.get("discarded"), (state.get("notes") or "").strip())):
            self.job_states.pop(key, None)
        else:
            state["title"] = job.get("title", "")
            self.job_states[key] = state
        save_states(self.job_states)
        self._refresh_row_state(job)

    def _state_icons(self, job):
        # Glifos de texto (no emoji): monocromos, heredan el color de la fila
        # y mantienen la tabla visualmente serena.
        state = self._get_state(job)
        glyphs = ""
        if job.get("is_new"):
            glyphs += "✦"
        if state.get("favorite"):
            glyphs += "★"
        if state.get("applied"):
            glyphs += "✓"
        if state.get("discarded"):
            glyphs += "✕"
        if (state.get("notes") or "").strip():
            glyphs += "✎"
        return " ".join(glyphs)

    def _row_tags(self, job):
        bg_tag = "api" if job.get("type") == "api_result" else "search"
        match = job.get("match", 0) or 0
        match_tag = "match_high" if match >= 70 else "match_mid" if match >= 40 else "match_low"
        if self._get_state(job).get("discarded"):
            # "discarded" primero: en Treeview el primer tag gana el color de texto.
            return ("discarded", bg_tag)
        return (bg_tag, match_tag)

    def _refresh_row_state(self, job):
        key = job_key(job)
        for idx, displayed in enumerate(self.displayed_jobs):
            if job_key(displayed) == key:
                self.tree.set(str(idx), "state", self._state_icons(displayed))
                self.tree.item(str(idx), tags=self._row_tags(displayed))

    def _toggle_state_flag(self, flag):
        job = self.selected_job
        if not job:
            return
        new_value = not bool(self._get_state(job).get(flag))
        self._update_state(job, **{flag: new_value})
        self._render_state_controls(job)

    def _style_state_button(self, button, active, active_color):
        if active:
            button.configure(fg_color=active_color, hover_color=active_color, text_color=theme.WHITE, border_width=0)
        else:
            button.configure(
                fg_color="transparent", hover_color=theme.SURFACE_ALT, text_color=theme.TEXT_SECONDARY,
                border_width=theme.BORDER_WIDTH, border_color=theme.BORDER_STRONG,
            )

    def _render_state_controls(self, job):
        state = self._get_state(job)
        self._style_state_button(self.favorite_button, bool(state.get("favorite")), theme.STATE_FAVORITE)
        self._style_state_button(self.applied_button, bool(state.get("applied")), theme.STATE_APPLIED)
        self._style_state_button(self.discarded_button, bool(state.get("discarded")), theme.STATE_DISCARDED)

    def _save_notes(self):
        job = self.selected_job
        if not job or not hasattr(self, "notes_entry"):
            return
        notes = self.notes_entry.get().strip()
        if notes != (self._get_state(job).get("notes") or "").strip():
            self._update_state(job, notes=notes)

    def _render_detail(self, job):
        if not job:
            self.detail_content.grid_forget()
            self.detail_empty_wrap.place(relx=0.5, rely=0.5, anchor="center")
            return
        self.detail_empty_wrap.place_forget()
        self.detail_content.grid(row=0, column=0, sticky="nsew")

        is_api = job.get("type") == "api_result"
        badge = theme.badge_style(active=is_api)
        badge_text = self.t("type_api") if is_api else self.t("type_search")
        self.detail_type_badge.configure(
            # Aire lateral dentro de la pill: CTkLabel no tiene padding interno.
            text=f"  {badge_text}  ",
            fg_color=badge["fg_color"], text_color=badge["text_color"],
        )
        match = job.get("match", 0) or 0
        idx = self._dark_mode_index()
        if is_api:
            match_color = theme.MATCH_HIGH[idx] if match >= 70 else theme.MATCH_MID[idx] if match >= 40 else theme.MATCH_LOW[idx]
            match_text = f"{match}%"
        else:
            # Los enlaces de búsqueda no se puntúan.
            match_color = theme.TEXT_SECONDARY[idx]
            match_text = "—"
        self.detail_match_badge.configure(text=match_text, text_color=match_color, fg_color=theme.SURFACE_SUNKEN)
        if job.get("is_new"):
            self.detail_new_badge.configure(text=f"  ✦ {self.t('badge_new')}  ")
            self.detail_new_badge.pack(side="left", padx=(theme.SPACE_SM, 0), after=self.detail_match_badge)
        else:
            self.detail_new_badge.pack_forget()
        self.detail_title_label.configure(text=job.get("title") or "-")
        self.detail_subtitle_label.configure(
            text=self.t(
                "detail_subtitle",
                company=job.get("company", "-"), location=job.get("location", "-"), source=job.get("source", "-"),
                published=job.get("published_date") or self.t("not_available"), detected=job.get("detected_date", "-"),
            )
        )
        # Solo las keywords del usuario, sin los marcadores internos del scoring
        # (role_title:..., penalty:..., exclude:...), y con sus puntos de match.
        internal_markers = ("role_title", "role_text", "penalty:", "exclude:")
        found_keywords = [
            s.strip() for s in (job.get("skills_found") or "").split(",")
            if s.strip() and not s.strip().startswith(internal_markers)
        ]
        if found_keywords:
            labeled = []
            for kw in found_keywords:
                pts = self._keyword_points(kw) if kw in self.keyword_vars else None
                labeled.append(f"{kw} (+{pts})" if pts else kw)
            self.detail_skills_label.configure(text=self.t("detail_skills", skills=", ".join(labeled)))
        else:
            self.detail_skills_label.configure(text=self.t("detail_skills_empty"))

        description = job.get("description") or "-"
        self.detail_description_box.configure(state="normal")
        self.detail_description_box.delete("1.0", "end")
        self.detail_description_box.insert("1.0", description)
        self._highlight_keywords_in_description(description, found_keywords)
        self.detail_description_box.configure(state="disabled")

        self._render_state_controls(job)
        self.notes_entry.delete(0, "end")
        notes = (self._get_state(job).get("notes") or "").strip()
        if notes:
            self.notes_entry.insert(0, notes)

    def _highlight_keywords_in_description(self, description, keywords):
        # Enlace visual keywords <-> oferta: resalta en verde las apariciones
        # de las keywords encontradas dentro de la descripción.
        box = self.detail_description_box
        idx = self._dark_mode_index()
        try:
            box.tag_config("kw_hit", foreground=theme.MATCH_HIGH[idx])
        except Exception:
            return
        low = description.lower()
        for kw in keywords:
            kw_l = kw.lower()
            spans = [(m.start(), m.end()) for m in re.finditer(r"\b" + re.escape(kw_l) + r"\b", low)]
            if not spans:
                # La keyword coincidió con sus palabras sueltas: resaltarlas una a una.
                for word in kw_l.split():
                    spans += [(m.start(), m.end()) for m in re.finditer(r"\b" + re.escape(word) + r"\b", low)]
            for start, end in spans:
                box.tag_add("kw_hit", f"1.0+{start}c", f"1.0+{end}c")

    def populate_tree(self, jobs):
        self._save_notes()
        self.displayed_jobs = list(jobs)
        self.tree.delete(*self.tree.get_children())
        for idx, j in enumerate(jobs):
            is_api = j.get("type") == "api_result"
            job_type = self.t("type_api") if is_api else self.t("type_search")
            match = j.get("match", 0) or 0
            # Los enlaces de búsqueda no tienen match real: mostrar "—" evita
            # el porcentaje engañoso que los ponía por delante de las ofertas.
            match_text = f"{match}%" if is_api else "—"
            self.tree.insert("", "end", iid=str(idx), values=(
                self._state_icons(j),
                match_text, j.get("title", ""), j.get("company", ""), j.get("location", ""),
                j.get("source", ""), j.get("published_date", ""), job_type,
            ), tags=self._row_tags(j))
        self.result_count_label.configure(text=self.t("result_count", n=len(jobs)))
        if jobs:
            self._hide_empty_state()
        else:
            self._set_empty_state(self.t("empty_results"))
        self.selected_job = None
        self._render_detail(None)

    def _refresh_tree_type_labels(self):
        for idx, j in enumerate(self.displayed_jobs):
            job_type = self.t("type_api") if j.get("type") == "api_result" else self.t("type_search")
            self.tree.set(str(idx), "type", job_type)

    def get_selected_job(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            idx = int(sel[0])
            if 0 <= idx < len(self.displayed_jobs):
                return self.displayed_jobs[idx]
            return None
        except Exception:
            return None

    def _on_tree_select(self, event=None):
        # Guarda las notas de la oferta anterior antes de cambiar de selección.
        self._save_notes()
        self.selected_job = self.get_selected_job()
        self._render_detail(self.selected_job)

    def open_selected(self):
        j = self.get_selected_job()
        if not j:
            messagebox.showwarning(APP_NAME, self.t("select_result_open_link"))
            return
        if j.get("apply_url"):
            webbrowser.open(j["apply_url"])
            return
        messagebox.showwarning(APP_NAME, self.t("no_link_available"))

    def open_fallback(self):
        j = self.get_selected_job()
        if not j:
            messagebox.showwarning(APP_NAME, self.t("select_result_fallback"))
            return
        if j.get("fallback_url"):
            webbrowser.open(j["fallback_url"])
            return
        messagebox.showwarning(APP_NAME, self.t("no_fallback_available"))

    def _visible_jobs(self):
        # Vista actual de la tabla: los resultados de la búsqueda pasados por
        # el switch "Solo ofertas reales" y por el texto del filtro rápido.
        jobs = self.jobs
        if self.only_offers_var.get():
            jobs = [j for j in jobs if j.get("type") == "api_result"]
        q = self.quick_filter_entry.get().lower().strip()
        if q:
            jobs = [j for j in jobs if q in " ".join(str(v) for v in j.values()).lower()]
        return jobs

    def apply_quick_filter(self, event=None):
        q = self.quick_filter_entry.get().lower().strip()
        visible = self._visible_jobs()
        self.populate_tree(visible)
        if q:
            self.status_label.configure(text=self.t("status_filtered", n=len(visible)))
        else:
            self.status_label.configure(text=self.t("status_filter_clean"))

    def _on_offers_filter_toggle(self):
        self.populate_tree(self._visible_jobs())
        self.save_config(silent=True)

    # ---------- Status bar ----------

    def _build_status_bar(self):
        status_bar = ctk.CTkFrame(self, height=theme.STATUSBAR_HEIGHT, corner_radius=0, fg_color=theme.SURFACE)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_propagate(False)
        # Separador superior sutil, en línea con el del header (sin sombra real disponible).
        ctk.CTkFrame(status_bar, height=1, corner_radius=0, fg_color=theme.BORDER).place(relx=0, rely=0, relwidth=1, anchor="nw")
        self.status_label = ctk.CTkLabel(
            status_bar, text=self.t("status_ready"), font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY,
        )
        self.status_label.pack(side="left", padx=theme.SPACE_MD)

        self.credit_label = ctk.CTkLabel(
            status_bar, text=f"{APP_NAME} v{APP_VERSION} · {self.t('credit')} {APP_AUTHOR}",
            font=theme.FONT_SMALL, text_color=theme.TEXT_SECONDARY,
        )
        self.credit_label.pack(side="right", padx=theme.SPACE_MD)

    # ---------- Search ----------

    def _set_search_state(self, busy, message=None):
        self.search_in_progress = busy
        state = "disabled" if busy else "normal"
        for button in (self.search_button, self.export_button, self.save_button):
            if button is not None:
                button.configure(state=state)
        if message is not None:
            self.status_label.configure(text=message)

    def _queue_status(self, message):
        self.search_queue.put({"kind": "status", "message": message})

    def _poll_search_queue(self):
        try:
            while True:
                item = self.search_queue.get_nowait()
                kind = item.get("kind")
                if kind == "status":
                    self.status_label.configure(text=item.get("message", ""))
                elif kind == "partial":
                    self._absorb_partial(item.get("jobs", []))
                elif kind == "done":
                    self._finish_search(item.get("errors", []))
                elif kind == "fatal":
                    self._fail_search(item.get("message", self.t("unexpected_error")))
        except queue.Empty:
            pass
        if self.search_in_progress:
            self.after(120, self._poll_search_queue)

    def _fail_search(self, message):
        logger.error(message)
        self._set_search_state(False, self.t("status_search_error"))
        messagebox.showerror(APP_NAME, message)

    def _build_error_message(self, errors, no_results=False):
        lines = []
        if no_results:
            lines.append(self.t("no_results_some_failed"))
        else:
            lines.append(self.t("results_some_failed"))
        for error in errors:
            source = error.get("source") or self.t("source_fallback_label")
            kind = error.get("kind", "api")
            if kind == "timeout":
                label = self.t("error_timeout")
            elif kind == "connection":
                label = self.t("error_connection")
            elif kind == "invalid_response":
                label = self.t("error_invalid_response")
            elif kind == "dependency":
                label = self.t("error_dependency")
            elif kind == "api":
                label = self.t("error_api")
            else:
                label = self.t("error_unexpected")
            lines.append(f"- {source}: {label}.")
        return "\n".join(lines)

    def _absorb_partial(self, jobs):
        # Búsqueda incremental: cada fuente entrega sus resultados en cuanto
        # termina y la tabla se repuebla en caliente, sin esperar al resto.
        if not jobs:
            return
        for job in jobs:
            # Nueva = oferta real cuya URL no habíamos visto en búsquedas
            # anteriores (el histórico se poda a 90 días).
            key = job_key(job)
            if job.get("type") == "api_result" and key and key not in self.seen_jobs:
                job["is_new"] = True
        self.jobs = dedupe_jobs(self.jobs + jobs)
        self.populate_tree(self._visible_jobs())

    def _finish_search(self, errors):
        today = datetime.now().strftime("%Y-%m-%d")
        for job in self.jobs:
            key = job_key(job)
            if job.get("type") == "api_result" and key and key not in self.seen_jobs:
                self.seen_jobs[key] = today
        save_seen(self.seen_jobs)
        self.save_config(silent=True)
        self._set_search_state(False, self.t("status_search_done", n=len(self.jobs)))
        if not self.jobs and errors:
            messagebox.showerror(APP_NAME, self._build_error_message(errors, no_results=True))
        elif not self.jobs:
            messagebox.showinfo(APP_NAME, self.t("no_results_found"))
        elif errors:
            messagebox.showwarning(APP_NAME, self._build_error_message(errors, no_results=False))

    def _search_jobs_worker(self, roles, locs, sources, profile_keywords, source_domains, lang):
        # Fuentes API y su fetcher: se recorren en orden y los resultados de
        # cada una se publican en cuanto responde.
        api_fetchers = (
            ("RemoteOK API", "status_querying_remoteok", fetch_remoteok),
            ("Remotive API", "status_querying_remotive", fetch_remotive),
            ("Arbeitnow API", "status_querying_arbeitnow", fetch_arbeitnow),
            ("Jobicy API", "status_querying_jobicy", fetch_jobicy),
        )
        errors = []
        try:
            self._queue_status(t(lang, "status_generating_links"))
            links = make_search_links(roles, locs, sources, profile_keywords, source_domains, lang=lang)
            self.search_queue.put({"kind": "partial", "jobs": links})

            for source_name, status_key, fetcher in api_fetchers:
                if source_name not in sources:
                    continue
                self._queue_status(t(lang, status_key))
                try:
                    jobs = fetcher(roles, profile_keywords, lang=lang)
                    self.search_queue.put({"kind": "partial", "jobs": jobs})
                except SourceFetchError as error:
                    logger.warning("%s", error.message)
                    errors.append({"source": error.source, "kind": error.kind, "message": error.message})

            self.search_queue.put({"kind": "done", "errors": errors})
        except Exception as error:
            logger.exception("Unexpected error during job search")
            self.search_queue.put({"kind": "fatal", "message": t(lang, "unexpected_search_error", error=error)})

    def search_jobs(self):
        if self.search_in_progress:
            return
        roles = self.selected_roles()
        locs = self.selected_locations()
        sources = self.selected_sources()
        if not roles:
            messagebox.showwarning(APP_NAME, self.t("select_one_role"))
            return
        profile_keywords = self.selected_keywords()
        self.save_config(silent=True)
        self._save_notes()
        self.jobs = []
        self.displayed_jobs = []
        self.selected_job = None
        self._render_detail(None)
        self.tree.delete(*self.tree.get_children())
        self._set_empty_state(self.t("searching"))
        self.result_count_label.configure(text=self.t("result_count", n=0))
        self.search_queue = queue.Queue()
        self._set_search_state(True, self.t("searching"))
        worker = threading.Thread(
            target=self._search_jobs_worker,
            args=(roles, locs, sources, profile_keywords, self.all_source_domains(), self.language),
            daemon=True,
        )
        worker.start()
        self.after(120, self._poll_search_queue)

    # ---------- Export ----------

    def export_all(self):
        if not self.jobs:
            messagebox.showwarning(APP_NAME, self.t("no_results_to_export"))
            return
        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = now_stamp()
            txt = RESULTS_DIR / f"job_results_{stamp}.txt"
            csvp = RESULTS_DIR / f"job_results_{stamp}.csv"
            html = RESULTS_DIR / f"job_results_{stamp}.html"
            export_txt(self.jobs, txt, lang=self.language)
            export_csv(self.jobs, csvp)
            export_html(self.jobs, html, lang=self.language)
            messagebox.showinfo(
                APP_NAME,
                self.t("export_success", dir=RESULTS_DIR, txt=txt.name, csv=csvp.name, html=html.name),
            )
            webbrowser.open(str(html))
        except (OSError, PermissionError) as error:
            logger.exception("Export failed")
            messagebox.showerror(APP_NAME, self.t("export_write_error", error=error))
        except Exception as error:
            logger.exception("Unexpected export error")
            messagebox.showerror(APP_NAME, self.t("export_unexpected_error", error=error))

    # ---------- Config persistence ----------

    def save_config(self, silent=False):
        cfg = {
            "language": self.language,
            "only_real_offers": self.only_offers_var.get(),
            "roles_list": [{"name": k, "enabled": v.get()} for k, v in self.role_vars.items()],
            "roles": {k: v.get() for k, v in self.role_vars.items()},
            "locations_list": [{"name": k, "enabled": v.get()} for k, v in self.location_vars.items()],
            "locations": {k: v.get() for k, v in self.location_vars.items()},
            "custom_location": self.custom_location_entry.get(),
            "sources_list": [{"name": k, "enabled": v.get()} for k, v in self.source_vars.items()],
            "sources": {k: v.get() for k, v in self.source_vars.items()},
            "custom_sources_list": [
                {"name": k, "domain": self.custom_source_domains[k], "enabled": v.get()}
                for k, v in self.custom_source_vars.items()
            ],
            "keywords_list": [
                {"name": k, "enabled": self.keyword_vars[k].get(), "points": self._keyword_points(k)}
                for k in self.keyword_vars.keys()
            ],
        }
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            if not silent:
                messagebox.showinfo(APP_NAME, self.t("config_saved", path=CONFIG_FILE))
        except OSError as error:
            logger.exception("Unable to save configuration")
            if not silent:
                messagebox.showerror(APP_NAME, self.t("config_save_error", error=error))

    def load_config(self):
        if CONFIG_FILE.exists():
            config_path = CONFIG_FILE
        elif LEGACY_CONFIG_FILE.exists():
            config_path = LEGACY_CONFIG_FILE
        else:
            config_path = find_legacy_appdata_config()
        if config_path is None:
            return
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            saved_language = cfg.get("language")
            if saved_language in ("es", "en") and saved_language != self.language:
                self.language = saved_language
                self._apply_language()
            self.only_offers_var.set(bool(cfg.get("only_real_offers", False)))
            roles_list = cfg.get("roles_list")
            if roles_list is not None:
                for role in list(self.role_vars.keys()):
                    self.delete_role(role, save=False)
                for item in roles_list:
                    name = normalize_text(item.get("name", ""))
                    if name:
                        self.create_role_row(name, enabled=bool(item.get("enabled", True)))
            else:
                for k, val in cfg.get("roles", {}).items():
                    if k in self.role_vars:
                        self.role_vars[k].set(bool(val))
                    else:
                        self.create_role_row(k, enabled=bool(val))
            keywords_list = cfg.get("keywords_list")
            if keywords_list is not None:
                for kw in list(self.keyword_vars.keys()):
                    self.delete_keyword(kw, save=False)
                for item in keywords_list:
                    name = normalize_text(item.get("name", "")).lower()
                    if name:
                        self.create_keyword_row(name, item.get("points", 10), enabled=bool(item.get("enabled", True)))
            locations_list = cfg.get("locations_list")
            if locations_list is not None:
                for loc in list(self.location_vars.keys()):
                    self.delete_location(loc, save=False)
                for item in locations_list:
                    name = normalize_text(item.get("name", ""))
                    if name:
                        self.create_location_row(name, enabled=bool(item.get("enabled", True)))
            else:
                for k, val in cfg.get("locations", {}).items():
                    if k in self.location_vars:
                        self.location_vars[k].set(bool(val))
                    else:
                        self.create_location_row(k, enabled=bool(val))
            self.custom_location_entry.delete(0, "end")
            self.custom_location_entry.insert(0, cfg.get("custom_location", ""))
            sources_list = cfg.get("sources_list")
            if sources_list is not None:
                for src in list(self.source_vars.keys()):
                    self.delete_source(src, save=False)
                for item in sources_list:
                    name = normalize_text(item.get("name", ""))
                    if name:
                        self.create_source_row(name, enabled=bool(item.get("enabled", True)))
                # Fuentes añadidas en versiones nuevas de la app: se incorporan
                # a las configuraciones guardadas antes de que existieran.
                for src, enabled in DEFAULT_SOURCES.items():
                    if src not in self.source_vars:
                        self.create_source_row(src, enabled=enabled)
            else:
                for k, val in cfg.get("sources", {}).items():
                    if k in self.source_vars:
                        self.source_vars[k].set(bool(val))
                    else:
                        self.create_source_row(k, enabled=bool(val))
            custom_sources_list = cfg.get("custom_sources_list")
            if custom_sources_list is not None:
                for name in list(self.custom_source_vars.keys()):
                    self.delete_custom_source(name, save=False)
                for item in custom_sources_list:
                    name = normalize_text(item.get("name", ""))
                    domain = normalize_text(item.get("domain", "")).lower()
                    if name and domain:
                        self.create_custom_source_row(name, domain, enabled=bool(item.get("enabled", True)))
            # Guardado final único: refleja el estado ya completamente migrado,
            # sin los guardados incidentales a medias de los bucles de arriba.
            self.save_config(silent=True)
        except Exception as error:
            logger.exception("Unable to load configuration")
            messagebox.showwarning(APP_NAME, self.t("config_load_error", error=error))
