import json
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

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
        self.role_vars = {}
        self.role_widgets = {}
        self.location_vars = {}
        self.source_vars = {}
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

        self.quick_filter_entry = ctk.CTkEntry(header, placeholder_text="Filtro rápido... (se conecta en el Paso 5)")
        self.quick_filter_entry.grid(row=0, column=1, padx=16, pady=8, sticky="ew")

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
            command=self.export_all,
        )
        self.export_button.pack(fill="x", pady=(0, 6))
        self.save_button = ctk.CTkButton(
            actions, text="Guardar configuración", fg_color="transparent", border_width=1,
            border_color=theme.GRAY, text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT,
            command=self.save_config,
        )
        self.save_button.pack(fill="x")

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=theme.FONT_SECTION, anchor="w").pack(fill="x", pady=(12, 4))

    def _small_action_button(self, parent, text, command):
        ctk.CTkButton(
            parent, text=text, height=26, font=theme.FONT_SMALL, fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT, command=command,
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
        self._small_action_button(parent, "Eliminar categorías desmarcadas", self.delete_unchecked_roles)

    def _build_location_section(self, parent):
        self._section_label(parent, "Ubicación")
        for loc in DEFAULT_LOCATIONS:
            v = tk.BooleanVar(value=True)
            self.location_vars[loc] = v
            ctk.CTkCheckBox(
                parent, text=loc, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
                fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
            ).pack(anchor="w", pady=1)
        self.custom_location_entry = ctk.CTkEntry(parent, placeholder_text="Otra ubicación...")
        self.custom_location_entry.pack(fill="x", pady=(4, 0))

    def _build_sources_section(self, parent):
        self._section_label(parent, "Fuentes")
        for src, enabled in DEFAULT_SOURCES.items():
            v = tk.BooleanVar(value=enabled)
            self.source_vars[src] = v
            ctk.CTkCheckBox(
                parent, text=src, variable=v, onvalue=True, offvalue=False, font=theme.FONT_BODY,
                fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
            ).pack(anchor="w", pady=1)

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
        self._small_action_button(parent, "Eliminar fuentes personalizadas desmarcadas", self.delete_unchecked_custom_sources)

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
        self._small_action_button(parent, "Eliminar keywords desmarcadas", self.delete_unchecked_keywords)

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

    def delete_role(self, role):
        widget = self.role_widgets.pop(role, None)
        if widget is not None:
            widget.destroy()
        self.role_vars.pop(role, None)
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

    def delete_keyword(self, keyword):
        widget = self.keyword_widgets.pop(keyword, None)
        if widget is not None:
            widget.destroy()
        self.keyword_vars.pop(keyword, None)
        self.keyword_weight_vars.pop(keyword, None)
        self.save_config(silent=True)

    def delete_unchecked_keywords(self):
        to_delete = [k for k, v in self.keyword_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, "No hay keywords desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} keyword(s) desmarcada(s)?"):
            for keyword in to_delete:
                self.delete_keyword(keyword)

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

    def delete_custom_source(self, name):
        widget = self.custom_source_widgets.pop(name, None)
        if widget is not None:
            widget.destroy()
        self.custom_source_vars.pop(name, None)
        self.custom_source_domains.pop(name, None)
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
        if custom:
            locs.append(custom)
        return locs or ["Remote"]

    def selected_sources(self):
        sources = [s for s, v in self.source_vars.items() if v.get()]
        sources += [s for s, v in self.custom_source_vars.items() if v.get()]
        return sources

    def selected_keywords(self):
        return {k: self._keyword_points(k) for k, v in self.keyword_vars.items() if v.get()}

    # ---------- Main area (temporary placeholder until Paso 5) ----------

    def _build_main_area(self):
        main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_area.grid(row=1, column=1, sticky="nsew", padx=16, pady=12)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkFrame(main_area, corner_radius=10)
        self.table_frame.grid(row=0, column=0, sticky="nsew")
        self.table_placeholder_label = ctk.CTkLabel(
            self.table_frame, text="Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas.",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED, justify="center",
        )
        self.table_placeholder_label.place(relx=0.5, rely=0.5, anchor="center")

        self.detail_frame = ctk.CTkFrame(main_area, corner_radius=10, height=90)
        self.detail_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.detail_frame.grid_propagate(False)
        ctk.CTkLabel(
            self.detail_frame, text="Selecciona un resultado para ver el detalle. (Paso 6)",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def populate_tree(self, jobs):
        self.displayed_jobs = list(jobs)
        api_count = sum(1 for j in jobs if j.get("type") == "api_result")
        link_count = len(jobs) - api_count
        if jobs:
            text = (
                f"{len(jobs)} resultados encontrados\n"
                f"({api_count} ofertas reales, {link_count} enlaces de búsqueda)\n\n"
                f"La tabla y el panel de detalle se conectan en los Pasos 5 y 6."
            )
        else:
            text = "Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas."
        self.table_placeholder_label.configure(text=text)
        self.result_count_label.configure(text=f"{len(jobs)} resultados")

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
        self.table_placeholder_label.configure(text="Buscando...")
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
            "locations": {k: v.get() for k, v in self.location_vars.items()},
            "custom_location": self.custom_location_entry.get(),
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
                    self.delete_role(role)
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
                    self.delete_keyword(kw)
                for item in keywords_list:
                    name = normalize_text(item.get("name", "")).lower()
                    if name:
                        self.create_keyword_row(name, item.get("points", 10), enabled=bool(item.get("enabled", True)))
            for k, val in cfg.get("locations", {}).items():
                if k in self.location_vars:
                    self.location_vars[k].set(bool(val))
            self.custom_location_entry.delete(0, "end")
            self.custom_location_entry.insert(0, cfg.get("custom_location", ""))
            for k, val in cfg.get("sources", {}).items():
                if k in self.source_vars:
                    self.source_vars[k].set(bool(val))
            custom_sources_list = cfg.get("custom_sources_list")
            if custom_sources_list is not None:
                for name in list(self.custom_source_vars.keys()):
                    self.delete_custom_source(name)
                for item in custom_sources_list:
                    name = normalize_text(item.get("name", ""))
                    domain = normalize_text(item.get("domain", "")).lower()
                    if name and domain:
                        self.create_custom_source_row(name, domain, enabled=bool(item.get("enabled", True)))
            if config_path != CONFIG_FILE:
                self.save_config(silent=True)
        except Exception as error:
            logger.exception("Unable to load configuration")
            messagebox.showwarning(APP_NAME, f"No se pudo cargar la configuración guardada:\n{error}")
