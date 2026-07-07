import json
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk
from PIL import Image

from constants import APP_NAME, APP_VERSION, APP_AUTHOR, DEFAULT_ROLES, DEFAULT_LOCATIONS, DEFAULT_SOURCES
from core.scoring import DEFAULT_PROFILE_KEYWORDS, normalize_text
from core.sources import SourceFetchError, SOURCE_DOMAINS, make_search_links, fetch_remoteok, fetch_remotive, dedupe_jobs
from core.export import now_stamp, export_txt, export_csv, export_html
from core.config_store import RESULTS_DIR, CONFIG_FILE, LEGACY_CONFIG_FILE, find_legacy_appdata_config
from core.logging_setup import setup_logging
from ui import theme

logger = setup_logging()


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1360x800")
        self.minsize(1180, 680)
        self._set_icon()

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
        self.search_button = None
        self.export_button = None
        self.save_button = None

        self._build_layout()
        self.load_config()

    def _set_icon(self):
        try:
            self.iconbitmap(str(theme.ICON_PATH))
        except Exception:
            pass

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_main_area()
        self._build_status_bar()

    # ---------- Header ----------

    def _build_header(self):
        header = ctk.CTkFrame(self, height=theme.HEADER_HEIGHT, corner_radius=0, fg_color=(theme.WHITE, theme.GRAY_DARK))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, padx=16, pady=8, sticky="w")
        try:
            logo_image = ctk.CTkImage(light_image=Image.open(theme.LOGO_PATH), size=(34, 34))
            ctk.CTkLabel(brand, image=logo_image, text="").pack(side="left", padx=(0, 8))
        except Exception:
            pass
        ctk.CTkLabel(brand, text=APP_NAME, font=theme.FONT_TITLE).pack(side="left")

        self.quick_filter_entry = ctk.CTkEntry(header, placeholder_text="Filtro rápido... (Enter para filtrar)")
        self.quick_filter_entry.grid(row=0, column=1, padx=16, pady=8, sticky="ew")
        self.quick_filter_entry.bind("<Return>", self.apply_quick_filter)

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, padx=16, pady=8, sticky="e")
        self.result_count_label = ctk.CTkLabel(right, text="0 resultados", font=theme.FONT_BODY, text_color=theme.TEXT_MUTED)
        self.result_count_label.pack(side="left", padx=(0, 12))
        self.theme_button = ctk.CTkButton(
            right, text="🌙", width=32, height=28, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT, command=self._toggle_theme,
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
        self._render_detail(self.selected_job)

    # ---------- Sidebar ----------

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=theme.SIDEBAR_WIDTH, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        self.search_button = ctk.CTkButton(
            sidebar, text="🔍  Buscar ofertas", height=42, font=theme.FONT_SECTION,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER, command=self.search_jobs,
        )
        self.search_button.pack(fill="x", padx=16, pady=(16, 12))

        scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16)
        self.sidebar_scroll = scroll

        self._build_roles_section(scroll)
        self._build_location_section(scroll)
        self._build_sources_section(scroll)
        self._build_custom_sources_section(scroll)
        self._build_keywords_section(scroll)

        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(4, 16))
        self.export_button = ctk.CTkButton(
            actions, text="Exportar TXT/CSV/HTML", fg_color="transparent", border_width=1,
            border_color=theme.GRAY, text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=self.export_all, anchor="w",
        )
        self.export_button.pack(fill="x", pady=(0, 6))
        self.save_button = ctk.CTkButton(
            actions, text="Guardar configuración", fg_color="transparent", border_width=1,
            border_color=theme.GRAY, text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=self.save_config, anchor="w",
        )
        self.save_button.pack(fill="x")

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=theme.FONT_SECTION, anchor="w").pack(fill="x", pady=(12, 4))

    def _small_action_button(self, parent, text, command):
        ctk.CTkButton(
            parent, text=text, height=26, font=theme.FONT_SMALL, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT, command=command,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

    def _build_roles_section(self, parent):
        self._section_label(parent, "Roles")
        self.roles_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.roles_frame.pack(fill="x")
        for r in DEFAULT_ROLES:
            self.create_role_row(r, enabled=True)

        add_row = ctk.CTkFrame(parent, fg_color="transparent")
        add_row.pack(fill="x", pady=(4, 0))
        self.new_role_entry = ctk.CTkEntry(add_row, placeholder_text="Nueva categoría...")
        self.new_role_entry.pack(side="left", fill="x", expand=True)
        self.new_role_entry.bind("<Return>", lambda e: self.add_role())
        ctk.CTkButton(
            add_row, text="+", width=32, command=self.add_role,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", padx=(4, 0))
        self._small_action_button(parent, "Eliminar desmarcadas", self.delete_unchecked_roles)

    def _build_location_section(self, parent):
        self._section_label(parent, "Ubicación")
        self.locations_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.locations_frame.pack(fill="x")
        for loc in DEFAULT_LOCATIONS:
            self.create_location_row(loc, enabled=True)

        add_row = ctk.CTkFrame(parent, fg_color="transparent")
        add_row.pack(fill="x", pady=(4, 0))
        self.custom_location_entry = ctk.CTkEntry(add_row, placeholder_text="Añadir ubicación...")
        self.custom_location_entry.pack(side="left", fill="x", expand=True)
        self.custom_location_entry.bind("<Return>", lambda e: self.add_location())
        ctk.CTkButton(
            add_row, text="+", width=32, command=self.add_location,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", padx=(4, 0))
        self._small_action_button(parent, "Eliminar desmarcadas", self.delete_unchecked_locations)

    def _build_sources_section(self, parent):
        self._section_label(parent, "Fuentes")
        self.sources_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.sources_frame.pack(fill="x")
        for src, enabled in DEFAULT_SOURCES.items():
            self.create_source_row(src, enabled=enabled)
        self._small_action_button(parent, "Eliminar desmarcadas", self.delete_unchecked_sources)

    def _build_custom_sources_section(self, parent):
        self._section_label(parent, "Fuentes personalizadas")
        ctk.CTkLabel(
            parent, text="Añade otros portales de empleo por dominio",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED, anchor="w",
            wraplength=theme.SIDEBAR_WIDTH - 32, justify="left",
        ).pack(fill="x")
        self.custom_sources_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.custom_sources_frame.pack(fill="x", pady=(4, 0))

        self.new_custom_source_name_entry = ctk.CTkEntry(parent, placeholder_text="Nombre de la fuente")
        self.new_custom_source_name_entry.pack(fill="x", pady=(4, 2))
        self.new_custom_source_domain_entry = ctk.CTkEntry(parent, placeholder_text="Dominio (ej: indeed.com)")
        self.new_custom_source_domain_entry.pack(fill="x")
        self.new_custom_source_domain_entry.bind("<Return>", lambda e: self.add_custom_source())
        ctk.CTkButton(
            parent, text="+ Añadir fuente", command=self.add_custom_source,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(fill="x", pady=(4, 0))
        self._small_action_button(parent, "Eliminar desmarcadas", self.delete_unchecked_custom_sources)

    def _build_keywords_section(self, parent):
        self._section_label(parent, "Keywords / Match")
        self.keywords_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.keywords_frame.pack(fill="x")
        for k, pts in DEFAULT_PROFILE_KEYWORDS.items():
            self.create_keyword_row(k, pts, enabled=True)

        add_row = ctk.CTkFrame(parent, fg_color="transparent")
        add_row.pack(fill="x", pady=(4, 0))
        self.new_keyword_entry = ctk.CTkEntry(add_row, placeholder_text="Nueva keyword...")
        self.new_keyword_entry.pack(side="left", fill="x", expand=True)
        self.new_keyword_entry.bind("<Return>", lambda e: self.add_keyword())
        self.new_keyword_points_entry = ctk.CTkEntry(add_row, width=40)
        self.new_keyword_points_entry.insert(0, "10")
        self.new_keyword_points_entry.pack(side="left", padx=(4, 0))
        ctk.CTkButton(
            parent, text="+ Añadir keyword", command=self.add_keyword,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(fill="x", pady=(4, 0))
        self._small_action_button(parent, "Eliminar desmarcadas", self.delete_unchecked_keywords)

    # ---------- Roles ----------

    def create_role_row(self, role, enabled=True):
        role = normalize_text(role)
        if not role or role in self.role_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.role_vars[role] = v

        row = ctk.CTkFrame(self.roles_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=1)
        ctk.CTkCheckBox(
            row, text=role, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkButton(
            row, text="✕", width=24, height=24, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=lambda r=role: self.delete_role(r),
        ).pack(side="right")
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
            messagebox.showinfo(APP_NAME, "No hay categorías desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} categoría(s) desmarcada(s)?"):
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
        row.pack(fill="x", anchor="w", pady=1)
        ctk.CTkCheckBox(
            row, text=keyword, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkEntry(row, width=40, textvariable=pts).pack(side="left", padx=(4, 2))
        ctk.CTkButton(
            row, text="✕", width=24, height=24, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=lambda k=keyword: self.delete_keyword(k),
        ).pack(side="right")
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
            messagebox.showinfo(APP_NAME, "No hay keywords desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} keyword(s) desmarcada(s)?"):
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
        row.pack(fill="x", anchor="w", pady=1)
        ctk.CTkCheckBox(
            row, text=location, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkButton(
            row, text="✕", width=24, height=24, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=lambda l=location: self.delete_location(l),
        ).pack(side="right")
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
            messagebox.showinfo(APP_NAME, "No hay ubicaciones desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} ubicación(es) desmarcada(s)?"):
            for location in to_delete:
                self.delete_location(location)

    # ---------- Built-in sources ----------

    def create_source_row(self, source, enabled=True):
        source = normalize_text(source)
        if not source or source in self.source_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.source_vars[source] = v

        row = ctk.CTkFrame(self.sources_frame, fg_color="transparent")
        row.pack(fill="x", anchor="w", pady=1)
        ctk.CTkCheckBox(
            row, text=source, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkButton(
            row, text="✕", width=24, height=24, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=lambda s=source: self.delete_source(s),
        ).pack(side="right")
        self.source_widgets[source] = row

    def delete_source(self, source, save=True):
        widget = self.source_widgets.pop(source, None)
        if widget is not None:
            widget.destroy()
        self.source_vars.pop(source, None)
        if save:
            self.save_config(silent=True)

    def delete_unchecked_sources(self):
        to_delete = [s for s, v in self.source_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, "No hay fuentes desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} fuente(s) desmarcada(s)?"):
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
        row.pack(fill="x", anchor="w", pady=1)
        ctk.CTkCheckBox(
            row, text=f"{name} ({domain})", variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(side="left", fill="x", expand=True, anchor="w")
        ctk.CTkButton(
            row, text="✕", width=24, height=24, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=lambda n=name: self.delete_custom_source(n),
        ).pack(side="right")
        self.custom_source_widgets[name] = row

    def add_custom_source(self):
        name = normalize_text(self.new_custom_source_name_entry.get())
        domain = normalize_text(self.new_custom_source_domain_entry.get()).lower()
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        if not name or not domain:
            messagebox.showwarning(APP_NAME, "Indica un nombre y un dominio para la fuente personalizada.")
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
            messagebox.showinfo(APP_NAME, "No hay fuentes personalizadas desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} fuente(s) personalizada(s) desmarcada(s)?"):
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
            foreground=theme.TABLE_FG[idx], rowheight=26, borderwidth=0, font=theme.FONT_BODY,
        )
        style.configure(
            "OTW.Treeview.Heading", background=theme.TABLE_HEADING_BG[idx], foreground=theme.TABLE_FG[idx],
            font=theme.FONT_SECTION, relief="flat",
        )
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

    def _build_main_area(self):
        main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_area.grid(row=1, column=1, sticky="nsew", padx=16, pady=12)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkFrame(main_area, corner_radius=10)
        self.table_frame.grid(row=0, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        columns = ("match", "title", "company", "location", "source", "published", "type")
        headings = {
            "match": "Match", "title": "Título", "company": "Empresa", "location": "Ubicación",
            "source": "Fuente", "published": "Publicado", "type": "Tipo",
        }
        widths = {"match": 70, "title": 260, "company": 150, "location": 140, "source": 130, "published": 100, "type": 150}
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", style="OTW.Treeview")
        for c in columns:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self._setup_treeview_style()
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())

        tree_scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=1)

        self.empty_state_label = ctk.CTkLabel(
            self.table_frame, text="Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas.",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED, justify="center", fg_color=theme.TABLE_BG,
        )
        self.empty_state_label.place(relx=0.5, rely=0.5, anchor="center")

        self._build_detail_panel(main_area)

    def _build_detail_panel(self, main_area):
        self.detail_frame = ctk.CTkFrame(main_area, corner_radius=10, height=220)
        self.detail_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.detail_frame.grid_propagate(False)
        self.detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_frame.grid_columnconfigure(0, weight=1)

        self.detail_empty_label = ctk.CTkLabel(
            self.detail_frame, text="Selecciona un resultado para ver el detalle.",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED,
        )
        self.detail_empty_label.place(relx=0.5, rely=0.5, anchor="center")

        self.detail_content = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        self.detail_content.grid_columnconfigure(0, weight=1)
        self.detail_content.grid_columnconfigure(1, weight=0)
        self.detail_content.grid_rowconfigure(3, weight=1)

        header_row = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        self.detail_type_badge = ctk.CTkLabel(
            header_row, text="", font=theme.FONT_SMALL, corner_radius=6, width=110,
        )
        self.detail_type_badge.pack(side="left")
        self.detail_match_badge = ctk.CTkLabel(
            header_row, text="", font=("Segoe UI", 13, "bold"), corner_radius=6, width=54,
        )
        self.detail_match_badge.pack(side="left", padx=(8, 0))
        self.detail_title_label = ctk.CTkLabel(header_row, text="", font=theme.FONT_TITLE, anchor="w")
        self.detail_title_label.pack(side="left", padx=(12, 0), fill="x", expand=True)

        self.detail_subtitle_label = ctk.CTkLabel(
            self.detail_content, text="", font=theme.FONT_BODY, text_color=theme.TEXT_MUTED,
            anchor="w", justify="left",
        )
        self.detail_subtitle_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 0))

        self.detail_skills_label = ctk.CTkLabel(
            self.detail_content, text="", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            anchor="w", justify="left",
        )
        self.detail_skills_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 0))

        self.detail_description_box = ctk.CTkTextbox(
            self.detail_content, height=70, font=theme.FONT_SMALL, wrap="word",
            fg_color=theme.DESCRIPTION_BG, text_color=theme.TABLE_FG,
        )
        self.detail_description_box.grid(row=3, column=0, sticky="nsew", padx=16, pady=(8, 12))

        buttons_col = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        buttons_col.grid(row=0, column=1, rowspan=4, sticky="n", padx=16, pady=12)
        self.detail_open_button = ctk.CTkButton(
            buttons_col, text="🔗 Abrir enlace", fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
            command=self.open_selected,
        )
        self.detail_open_button.pack(fill="x", pady=(0, 6))
        self.detail_fallback_button = ctk.CTkButton(
            buttons_col, text="Abrir fallback Google", fg_color="transparent", border_width=1,
            border_color=theme.GRAY, text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=self.open_fallback,
        )
        self.detail_fallback_button.pack(fill="x", pady=(0, 6))
        self.detail_export_button = ctk.CTkButton(
            buttons_col, text="📤 Exportar todo", fg_color="transparent", border_width=1,
            border_color=theme.GRAY, text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=self.export_all,
        )
        self.detail_export_button.pack(fill="x")

        future_row = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        future_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        for future_text in ("⭐ Favorito", "✔ Aplicado", "✕ Descartado", "📝 Notas"):
            ctk.CTkLabel(
                future_row, text=f"{future_text} (próximamente)", font=theme.FONT_SMALL,
                text_color=theme.TEXT_MUTED,
            ).pack(side="left", padx=(0, 16))

    def _render_detail(self, job):
        if not job:
            self.detail_content.grid_forget()
            self.detail_empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return
        self.detail_empty_label.place_forget()
        self.detail_content.grid(row=0, column=0, sticky="nsew")

        is_api = job.get("type") == "api_result"
        self.detail_type_badge.configure(
            text="Oferta real" if is_api else "Enlace de búsqueda",
            fg_color=theme.GREEN if is_api else theme.GRAY,
            text_color=theme.WHITE if is_api else "#333333",
        )
        match = job.get("match", 0) or 0
        idx = self._dark_mode_index()
        match_color = theme.MATCH_HIGH[idx] if match >= 70 else theme.MATCH_MID[idx] if match >= 40 else theme.MATCH_LOW[idx]
        self.detail_match_badge.configure(text=f"{match}%", text_color=match_color, fg_color=theme.DESCRIPTION_BG)
        self.detail_title_label.configure(text=job.get("title") or "-")
        self.detail_subtitle_label.configure(
            text=(
                f"{job.get('company', '-')}  ·  {job.get('location', '-')}  ·  {job.get('source', '-')}\n"
                f"Publicado: {job.get('published_date', 'No disponible')}   ·   "
                f"Detectado: {job.get('detected_date', '-')}"
            )
        )
        skills = job.get("skills_found", "")
        self.detail_skills_label.configure(text=f"Skills: {skills}" if skills else "Skills: -")
        self.detail_description_box.configure(state="normal")
        self.detail_description_box.delete("1.0", "end")
        self.detail_description_box.insert("1.0", job.get("description") or "-")
        self.detail_description_box.configure(state="disabled")

    def populate_tree(self, jobs):
        self.displayed_jobs = list(jobs)
        self.tree.delete(*self.tree.get_children())
        for idx, j in enumerate(jobs):
            job_type = "Oferta real" if j.get("type") == "api_result" else "Enlace de búsqueda"
            bg_tag = "api" if j.get("type") == "api_result" else "search"
            match = j.get("match", 0) or 0
            match_tag = "match_high" if match >= 70 else "match_mid" if match >= 40 else "match_low"
            self.tree.insert("", "end", iid=str(idx), values=(
                f"{match}%", j.get("title", ""), j.get("company", ""), j.get("location", ""),
                j.get("source", ""), j.get("published_date", ""), job_type,
            ), tags=(bg_tag, match_tag))
        self.result_count_label.configure(text=f"{len(jobs)} resultados")
        if jobs:
            self.empty_state_label.place_forget()
        else:
            self.empty_state_label.configure(text="Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas.")
            self.empty_state_label.place(relx=0.5, rely=0.5, anchor="center")
        self.selected_job = None
        self._render_detail(None)

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
        self.selected_job = self.get_selected_job()
        self._render_detail(self.selected_job)

    def open_selected(self):
        j = self.get_selected_job()
        if not j:
            messagebox.showwarning(APP_NAME, "Selecciona un resultado antes de abrir el enlace.")
            return
        if j.get("apply_url"):
            webbrowser.open(j["apply_url"])
            return
        messagebox.showwarning(APP_NAME, "El resultado seleccionado no tiene enlace para abrir.")

    def open_fallback(self):
        j = self.get_selected_job()
        if not j:
            messagebox.showwarning(APP_NAME, "Selecciona un resultado antes de abrir el fallback.")
            return
        if j.get("fallback_url"):
            webbrowser.open(j["fallback_url"])
            return
        messagebox.showwarning(APP_NAME, "El resultado seleccionado no tiene fallback disponible.")

    def apply_quick_filter(self, event=None):
        q = self.quick_filter_entry.get().lower().strip()
        if not q:
            self.populate_tree(self.jobs)
            self.status_label.configure(text="Filtro limpio")
            return
        filtered = [j for j in self.jobs if q in " ".join(str(v) for v in j.values()).lower()]
        self.populate_tree(filtered)
        self.status_label.configure(text=f"{len(filtered)} filtrados")

    # ---------- Status bar ----------

    def _build_status_bar(self):
        status_bar = ctk.CTkFrame(self, height=theme.STATUSBAR_HEIGHT, corner_radius=0, fg_color=(theme.GRAY_LIGHT, theme.GRAY_DARK))
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        status_bar.grid_propagate(False)
        self.status_label = ctk.CTkLabel(status_bar, text="Listo", font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED)
        self.status_label.pack(side="left", padx=12)

        credit_label = ctk.CTkLabel(
            status_bar, text=f"{APP_NAME} v{APP_VERSION} · Creado por {APP_AUTHOR}",
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
        )
        credit_label.pack(side="right", padx=12)

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
                elif kind == "done":
                    self._finish_search(item.get("jobs", []), item.get("errors", []))
                elif kind == "fatal":
                    self._fail_search(item.get("message", "Se produjo un error inesperado."))
        except queue.Empty:
            pass
        if self.search_in_progress:
            self.after(120, self._poll_search_queue)

    def _fail_search(self, message):
        logger.error(message)
        self._set_search_state(False, "Error en la búsqueda")
        messagebox.showerror(APP_NAME, message)

    def _build_error_message(self, errors, no_results=False):
        lines = []
        if no_results:
            lines.append("No se encontraron resultados porque algunas fuentes fallaron o no devolvieron coincidencias.")
        else:
            lines.append("Se encontraron resultados, pero algunas fuentes fallaron.")
        for error in errors:
            source = error.get("source", "Fuente")
            kind = error.get("kind", "api")
            message = error.get("message", "")
            if kind == "timeout":
                label = "Tiempo de espera agotado"
            elif kind == "connection":
                label = "Error de conexión"
            elif kind == "invalid_response":
                label = "Respuesta invalida"
            elif kind == "dependency":
                label = "Dependencia faltante"
            elif kind == "api":
                label = "Error de API"
            else:
                label = "Error inesperado"
            lines.append(f"- {source}: {label}. {message}")
        return "\n".join(lines)

    def _finish_search(self, jobs, errors):
        self.jobs = dedupe_jobs(jobs)
        self.populate_tree(self.jobs)
        self.save_config(silent=True)
        self._set_search_state(False, f"Búsqueda completada: {len(self.jobs)} resultados")
        if not self.jobs and errors:
            messagebox.showerror(APP_NAME, self._build_error_message(errors, no_results=True))
        elif not self.jobs:
            messagebox.showinfo(APP_NAME, "No se encontraron resultados para los criterios seleccionados.")
        elif errors:
            messagebox.showwarning(APP_NAME, self._build_error_message(errors, no_results=False))

    def _search_jobs_worker(self, roles, locs, sources, profile_keywords, source_domains):
        jobs = []
        errors = []
        try:
            self._queue_status("Generando enlaces de búsqueda...")
            jobs += make_search_links(roles, locs, sources, profile_keywords, source_domains)

            if "RemoteOK API" in sources:
                self._queue_status("Consultando RemoteOK...")
                try:
                    jobs += fetch_remoteok(roles, profile_keywords)
                except SourceFetchError as error:
                    logger.warning("%s", error.message)
                    errors.append({"source": error.source, "kind": error.kind, "message": error.message})

            if "Remotive API" in sources:
                self._queue_status("Consultando Remotive...")
                try:
                    jobs += fetch_remotive(roles, profile_keywords)
                except SourceFetchError as error:
                    logger.warning("%s", error.message)
                    errors.append({"source": error.source, "kind": error.kind, "message": error.message})

            self.search_queue.put({"kind": "done", "jobs": jobs, "errors": errors})
        except Exception as error:
            logger.exception("Unexpected error during job search")
            self.search_queue.put({"kind": "fatal", "message": f"Se produjo un error inesperado durante la búsqueda: {error}"})

    def search_jobs(self):
        if self.search_in_progress:
            return
        roles = self.selected_roles()
        locs = self.selected_locations()
        sources = self.selected_sources()
        if not roles:
            messagebox.showwarning(APP_NAME, "Selecciona al menos una categoría.")
            return
        profile_keywords = self.selected_keywords()
        self.save_config(silent=True)
        self.jobs = []
        self.displayed_jobs = []
        self.selected_job = None
        self._render_detail(None)
        self.tree.delete(*self.tree.get_children())
        self.empty_state_label.configure(text="Buscando...")
        self.empty_state_label.place(relx=0.5, rely=0.5, anchor="center")
        self.result_count_label.configure(text="0 resultados")
        self.search_queue = queue.Queue()
        self._set_search_state(True, "Buscando...")
        worker = threading.Thread(
            target=self._search_jobs_worker,
            args=(roles, locs, sources, profile_keywords, self.all_source_domains()),
            daemon=True,
        )
        worker.start()
        self.after(120, self._poll_search_queue)

    # ---------- Export ----------

    def export_all(self):
        if not self.jobs:
            messagebox.showwarning(APP_NAME, "No hay resultados para exportar.")
            return
        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = now_stamp()
            txt = RESULTS_DIR / f"job_results_{stamp}.txt"
            csvp = RESULTS_DIR / f"job_results_{stamp}.csv"
            html = RESULTS_DIR / f"job_results_{stamp}.html"
            export_txt(self.jobs, txt)
            export_csv(self.jobs, csvp)
            export_html(self.jobs, html)
            messagebox.showinfo(
                APP_NAME,
                f"Exportado en:\n{RESULTS_DIR}\n\nArchivos creados:\n- {txt.name}\n- {csvp.name}\n- {html.name}",
            )
            webbrowser.open(str(html))
        except (OSError, PermissionError) as error:
            logger.exception("Export failed")
            messagebox.showerror(APP_NAME, f"No se pudo exportar por un problema de escritura:\n{error}")
        except Exception as error:
            logger.exception("Unexpected export error")
            messagebox.showerror(APP_NAME, f"Error inesperado al exportar:\n{error}")

    # ---------- Config persistence ----------

    def save_config(self, silent=False):
        cfg = {
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
                messagebox.showinfo(APP_NAME, f"Configuración guardada en:\n{CONFIG_FILE}")
        except OSError as error:
            logger.exception("Unable to save configuration")
            if not silent:
                messagebox.showerror(APP_NAME, f"No se pudo guardar la configuración:\n{error}")

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
            messagebox.showwarning(APP_NAME, f"No se pudo cargar la configuración guardada:\n{error}")
