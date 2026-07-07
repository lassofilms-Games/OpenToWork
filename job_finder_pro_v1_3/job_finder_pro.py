import json
import queue
import threading
import webbrowser
from datetime import datetime
from tkinter import ttk, messagebox
import tkinter as tk

from constants import APP_NAME, APP_VERSION, APP_AUTHOR, DEFAULT_ROLES, DEFAULT_LOCATIONS, DEFAULT_SOURCES
from core.scoring import DEFAULT_PROFILE_KEYWORDS, normalize_text
from core.sources import SourceFetchError, SOURCE_DOMAINS, make_search_links, fetch_remoteok, fetch_remotive, dedupe_jobs
from core.export import now_stamp, export_txt, export_csv, export_html
from core.config_store import RESULTS_DIR, CONFIG_FILE, LEGACY_CONFIG_FILE, find_legacy_appdata_config
from core.logging_setup import setup_logging

logger = setup_logging()
logger.info("Application started")


class JobFinderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1100, 650)
        self.jobs = []
        self.role_vars = {}
        self.role_widgets = {}
        self.location_vars = {}
        self.location_widgets = {}
        self.source_vars = {}
        self.source_widgets = {}
        self.keyword_vars = {}
        self.keyword_weight_vars = {}
        self.keyword_widgets = {}
        self.custom_source_vars = {}
        self.custom_source_domains = {}
        self.custom_source_widgets = {}
        self.displayed_jobs = []
        self.search_queue = queue.Queue()
        self.search_in_progress = False
        self.search_button = None
        self.export_button = None
        self.open_button = None
        self.fallback_button = None
        self.save_button = None
        self.result_count = None
        self._build_ui()
        self.load_config()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Panel izquierdo con scroll para que se vean todas las opciones
        left_container = ttk.Frame(self)
        left_container.grid(row=0, column=0, sticky="ns")
        left_container.rowconfigure(0, weight=1)
        left_container.columnconfigure(0, weight=1)

        self.left_canvas = tk.Canvas(left_container, width=270, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        self.left_canvas.grid(row=0, column=0, sticky="ns")
        self.left_scrollbar.grid(row=0, column=1, sticky="ns")

        left = ttk.Frame(self.left_canvas, padding=10)
        self.left_window = self.left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _update_scroll_region(event=None):
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

        def _resize_inner_frame(event):
            self.left_canvas.itemconfigure(self.left_window, width=event.width)

        def _on_mousewheel(event):
            self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left.bind("<Configure>", _update_scroll_region)
        self.left_canvas.bind("<Configure>", _resize_inner_frame)
        self.left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        right = ttk.Frame(self, padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(left, text="Categorías", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.roles_frame = ttk.Frame(left)
        self.roles_frame.pack(fill="x", pady=(4, 8))
        for r in DEFAULT_ROLES:
            self.create_role_row(r, enabled=True)

        ttk.Label(left, text="Añadir categoría").pack(anchor="w", pady=(8,0))
        self.new_role = ttk.Entry(left, width=34)
        self.new_role.pack(fill="x")
        self.new_role.bind("<Return>", lambda e: self.add_role())
        ttk.Button(left, text="+ Añadir", command=self.add_role).pack(fill="x", pady=4)
        ttk.Button(left, text="Eliminar desmarcadas", command=self.delete_unchecked_roles).pack(fill="x", pady=(0,4))

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="Keywords / Match", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(left, text="Activa, elimina o añade palabras clave").pack(anchor="w")
        self.keywords_frame = ttk.Frame(left)
        self.keywords_frame.pack(fill="x", pady=(4, 4))
        for k, pts in DEFAULT_PROFILE_KEYWORDS.items():
            self.create_keyword_row(k, pts, enabled=True)

        kw_add = ttk.Frame(left)
        kw_add.pack(fill="x", pady=(4, 0))
        self.new_keyword = ttk.Entry(kw_add, width=22)
        self.new_keyword.pack(side="left", fill="x", expand=True)
        self.new_keyword_points = ttk.Spinbox(kw_add, from_=1, to=50, width=4)
        self.new_keyword_points.set(10)
        self.new_keyword_points.pack(side="left", padx=(4, 0))
        self.new_keyword.bind("<Return>", lambda e: self.add_keyword())
        ttk.Button(left, text="+ Añadir keyword", command=self.add_keyword).pack(fill="x", pady=4)
        ttk.Button(left, text="Eliminar desmarcadas", command=self.delete_unchecked_keywords).pack(fill="x", pady=(0,4))

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="Ubicación", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.locations_frame = ttk.Frame(left)
        self.locations_frame.pack(fill="x", pady=(4, 4))
        for loc in DEFAULT_LOCATIONS:
            self.create_location_row(loc, enabled=True)

        ttk.Label(left, text="Añadir ubicación").pack(anchor="w", pady=(8,0))
        self.custom_location = ttk.Entry(left, width=34)
        self.custom_location.pack(fill="x")
        self.custom_location.bind("<Return>", lambda e: self.add_location())
        ttk.Button(left, text="+ Añadir", command=self.add_location).pack(fill="x", pady=4)
        ttk.Button(left, text="Eliminar desmarcadas", command=self.delete_unchecked_locations).pack(fill="x", pady=(0,4))

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="Fuentes", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.sources_frame = ttk.Frame(left)
        self.sources_frame.pack(fill="x", pady=(4, 4))
        for src, enabled in DEFAULT_SOURCES.items():
            self.create_source_row(src, enabled=enabled)
        ttk.Button(left, text="Eliminar desmarcadas", command=self.delete_unchecked_sources).pack(fill="x", pady=(0,4))

        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="Fuentes personalizadas", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(left, text="Añade otros portales de empleo por dominio").pack(anchor="w")
        self.custom_sources_frame = ttk.Frame(left)
        self.custom_sources_frame.pack(fill="x", pady=(4, 4))

        ttk.Label(left, text="Nombre de la fuente").pack(anchor="w", pady=(8, 0))
        self.new_custom_source_name = ttk.Entry(left, width=34)
        self.new_custom_source_name.pack(fill="x")
        ttk.Label(left, text="Dominio (ej: indeed.com)").pack(anchor="w", pady=(4, 0))
        self.new_custom_source_domain = ttk.Entry(left, width=34)
        self.new_custom_source_domain.pack(fill="x")
        self.new_custom_source_domain.bind("<Return>", lambda e: self.add_custom_source())
        ttk.Button(left, text="+ Añadir fuente", command=self.add_custom_source).pack(fill="x", pady=4)
        ttk.Button(left, text="Eliminar desmarcadas", command=self.delete_unchecked_custom_sources).pack(fill="x", pady=(0,4))

        ttk.Separator(left).pack(fill="x", pady=8)
        self.search_button = ttk.Button(left, text="Buscar ofertas", command=self.search_jobs)
        self.search_button.pack(fill="x", pady=3)
        self.export_button = ttk.Button(left, text="Exportar TXT/CSV/HTML", command=self.export_all)
        self.export_button.pack(fill="x", pady=3)
        self.open_button = ttk.Button(left, text="Abrir link seleccionado", command=self.open_selected)
        self.open_button.pack(fill="x", pady=3)
        self.fallback_button = ttk.Button(left, text="Abrir fallback Google", command=self.open_fallback)
        self.fallback_button.pack(fill="x", pady=3)
        self.save_button = ttk.Button(left, text="Guardar configuración", command=self.save_config)
        self.save_button.pack(fill="x", pady=3)

        top = ttk.Frame(right)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Filtro rápido:").grid(row=0, column=0, padx=(0,6))
        self.quick_filter = ttk.Entry(top)
        self.quick_filter.grid(row=0, column=1, sticky="ew")
        ttk.Button(top, text="Filtrar", command=self.apply_quick_filter).grid(row=0, column=2, padx=6)
        self.status = ttk.Label(top, text="Listo")
        self.status.grid(row=0, column=3, padx=(4, 12))
        self.result_count = ttk.Label(top, text="0 resultados")
        self.result_count.grid(row=0, column=4)

        columns = ("match","published","title","company","location","source","type")
        self.tree = ttk.Treeview(right, columns=columns, show="headings")
        headings = {"match":"Match","published":"Publicado","title":"Título","company":"Empresa","location":"Ubicación","source":"Fuente","type":"Tipo"}
        widths = {"match":70,"published":110,"title":300,"company":180,"location":180,"source":150,"type":100}
        for c in columns:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.tag_configure("api", background="#eef7ef")
        self.tree.tag_configure("search", background="#f4f6f8")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())

        details_frame = ttk.LabelFrame(right, text="Detalles")
        details_frame.grid(row=2, column=0, sticky="ew")
        self.details = tk.Text(details_frame, height=10, wrap="word")
        self.details.pack(fill="both", expand=True)

        footer = ttk.Frame(right)
        footer.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(footer, text=f"{APP_NAME} v{APP_VERSION} · Creado por {APP_AUTHOR}", foreground="#888888").pack(side="right")

    def _set_search_state(self, busy, message=None):
        self.search_in_progress = busy
        state = "disabled" if busy else "normal"
        for button in (self.search_button, self.export_button, self.open_button, self.fallback_button, self.save_button):
            if button is not None:
                button.config(state=state)
        if message is not None:
            self.status.config(text=message)

    def _queue_status(self, message):
        self.search_queue.put({"kind": "status", "message": message})

    def _poll_search_queue(self):
        try:
            while True:
                item = self.search_queue.get_nowait()
                kind = item.get("kind")
                if kind == "status":
                    self.status.config(text=item.get("message", ""))
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

    def create_role_row(self, role, enabled=True):
        role = normalize_text(role)
        if not role or role in self.role_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.role_vars[role] = v

        row = ttk.Frame(self.roles_frame)
        row.pack(fill="x", anchor="w")
        cb = ttk.Checkbutton(row, text=role, variable=v)
        cb.pack(side="left", fill="x", expand=True, anchor="w")
        btn = ttk.Button(row, text="✕", width=3, command=lambda r=role: self.delete_role(r))
        btn.pack(side="right")
        self.role_widgets[role] = row

    def add_role(self):
        role = normalize_text(self.new_role.get())
        if not role:
            return
        if role in self.role_vars:
            self.role_vars[role].set(True)
            self.new_role.delete(0, "end")
            return
        self.create_role_row(role, enabled=True)
        self.new_role.delete(0, "end")
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

    def create_keyword_row(self, keyword, points=10, enabled=True):
        keyword = normalize_text(keyword).lower()
        if not keyword or keyword in self.keyword_vars:
            return
        v = tk.BooleanVar(value=enabled)
        pts = tk.IntVar(value=int(points) if str(points).isdigit() else 10)
        self.keyword_vars[keyword] = v
        self.keyword_weight_vars[keyword] = pts

        row = ttk.Frame(self.keywords_frame)
        row.pack(fill="x", anchor="w")
        cb = ttk.Checkbutton(row, text=keyword, variable=v)
        cb.pack(side="left", fill="x", expand=True, anchor="w")
        sp = ttk.Spinbox(row, from_=1, to=50, width=4, textvariable=pts)
        sp.pack(side="left", padx=(4, 2))
        btn = ttk.Button(row, text="✕", width=3, command=lambda k=keyword: self.delete_keyword(k))
        btn.pack(side="right")
        self.keyword_widgets[keyword] = row

    def add_keyword(self):
        keyword = normalize_text(self.new_keyword.get()).lower()
        if not keyword:
            return
        try:
            points = int(self.new_keyword_points.get())
        except Exception:
            points = 10
        points = max(1, min(50, points))
        if keyword in self.keyword_vars:
            self.keyword_vars[keyword].set(True)
            self.keyword_weight_vars[keyword].set(points)
        else:
            self.create_keyword_row(keyword, points, enabled=True)
        self.new_keyword.delete(0, "end")
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

    def create_location_row(self, location, enabled=True):
        location = normalize_text(location)
        if not location or location in self.location_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.location_vars[location] = v

        row = ttk.Frame(self.locations_frame)
        row.pack(fill="x", anchor="w")
        cb = ttk.Checkbutton(row, text=location, variable=v)
        cb.pack(side="left", fill="x", expand=True, anchor="w")
        btn = ttk.Button(row, text="✕", width=3, command=lambda l=location: self.delete_location(l))
        btn.pack(side="right")
        self.location_widgets[location] = row

    def add_location(self):
        location = normalize_text(self.custom_location.get())
        if not location:
            return
        if location in self.location_vars:
            self.location_vars[location].set(True)
            self.custom_location.delete(0, "end")
            return
        self.create_location_row(location, enabled=True)
        self.custom_location.delete(0, "end")
        self.save_config(silent=True)

    def delete_location(self, location):
        widget = self.location_widgets.pop(location, None)
        if widget is not None:
            widget.destroy()
        self.location_vars.pop(location, None)
        self.save_config(silent=True)

    def delete_unchecked_locations(self):
        to_delete = [l for l, v in self.location_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, "No hay ubicaciones desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} ubicación(es) desmarcada(s)?"):
            for location in to_delete:
                self.delete_location(location)

    def create_source_row(self, source, enabled=True):
        source = normalize_text(source)
        if not source or source in self.source_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.source_vars[source] = v

        row = ttk.Frame(self.sources_frame)
        row.pack(fill="x", anchor="w")
        cb = ttk.Checkbutton(row, text=source, variable=v)
        cb.pack(side="left", fill="x", expand=True, anchor="w")
        btn = ttk.Button(row, text="✕", width=3, command=lambda s=source: self.delete_source(s))
        btn.pack(side="right")
        self.source_widgets[source] = row

    def delete_source(self, source):
        widget = self.source_widgets.pop(source, None)
        if widget is not None:
            widget.destroy()
        self.source_vars.pop(source, None)
        self.save_config(silent=True)

    def delete_unchecked_sources(self):
        to_delete = [s for s, v in self.source_vars.items() if not v.get()]
        if not to_delete:
            messagebox.showinfo(APP_NAME, "No hay fuentes desmarcadas para eliminar.")
            return
        if messagebox.askyesno(APP_NAME, f"¿Eliminar {len(to_delete)} fuente(s) desmarcada(s)?"):
            for source in to_delete:
                self.delete_source(source)

    def create_custom_source_row(self, name, domain, enabled=True):
        name = normalize_text(name)
        domain = normalize_text(domain).lower()
        if not name or not domain or name in self.custom_source_vars:
            return
        v = tk.BooleanVar(value=enabled)
        self.custom_source_vars[name] = v
        self.custom_source_domains[name] = domain

        row = ttk.Frame(self.custom_sources_frame)
        row.pack(fill="x", anchor="w")
        cb = ttk.Checkbutton(row, text=f"{name} ({domain})", variable=v)
        cb.pack(side="left", fill="x", expand=True, anchor="w")
        btn = ttk.Button(row, text="✕", width=3, command=lambda n=name: self.delete_custom_source(n))
        btn.pack(side="right")
        self.custom_source_widgets[name] = row

    def add_custom_source(self):
        name = normalize_text(self.new_custom_source_name.get())
        domain = normalize_text(self.new_custom_source_domain.get()).lower()
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        if not name or not domain:
            messagebox.showwarning(APP_NAME, "Indica un nombre y un dominio para la fuente personalizada.")
            return
        if name in self.custom_source_vars:
            self.custom_source_vars[name].set(True)
            self.custom_source_domains[name] = domain
        else:
            self.create_custom_source_row(name, domain, enabled=True)
        self.new_custom_source_name.delete(0, "end")
        self.new_custom_source_domain.delete(0, "end")
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

    def selected_keywords(self):
        out = {}
        for k, enabled in self.keyword_vars.items():
            if enabled.get():
                try:
                    out[k] = int(self.keyword_weight_vars[k].get())
                except Exception:
                    out[k] = 10
        return out

    def selected_roles(self):
        roles = [r for r, v in self.role_vars.items() if v.get()]
        custom = normalize_text(self.new_role.get())
        if custom and custom not in roles:
            roles.append(custom)
        return roles

    def selected_locations(self):
        locs = [l for l, v in self.location_vars.items() if v.get()]
        custom = normalize_text(self.custom_location.get())
        if custom and custom not in locs:
            locs.append(custom)
        return locs or ["Remote"]

    def selected_sources(self):
        sources = [s for s, v in self.source_vars.items() if v.get()]
        sources += [s for s, v in self.custom_source_vars.items() if v.get()]
        return sources

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
        self.tree.delete(*self.tree.get_children())
        self.details.delete("1.0", "end")
        if self.result_count is not None:
            self.result_count.config(text="0 resultados")
        self.search_queue = queue.Queue()
        self._set_search_state(True, "Buscando...")
        worker = threading.Thread(
            target=self._search_jobs_worker,
            args=(roles, locs, sources, profile_keywords, self.all_source_domains()),
            daemon=True,
        )
        worker.start()
        self.after(120, self._poll_search_queue)

    def populate_tree(self, jobs):
        self.displayed_jobs = list(jobs)
        self.tree.delete(*self.tree.get_children())
        for idx, j in enumerate(jobs):
            job_type = "Oferta real" if j.get("type") == "api_result" else "Enlace de búsqueda"
            tag = "api" if j.get("type") == "api_result" else "search"
            self.tree.insert("", "end", iid=str(idx), values=(
                f"{j.get('match',0)}%", j.get("published_date",""), j.get("title",""),
                j.get("company",""), j.get("location",""), j.get("source",""), job_type
            ), tags=(tag,))
        if self.result_count is not None:
            self.result_count.config(text=f"{len(jobs)} resultados")

    def apply_quick_filter(self):
        q = self.quick_filter.get().lower().strip()
        if not q:
            self.populate_tree(self.jobs)
            self.status.config(text="Filtro limpio")
            return
        filtered = []
        for j in self.jobs:
            text = " ".join(str(v) for v in j.values()).lower()
            if q in text:
                filtered.append(j)
        self.populate_tree(filtered)
        self.status.config(text=f"{len(filtered)} filtrados")

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

    def show_details(self, event=None):
        j = self.get_selected_job()
        self.details.delete("1.0", "end")
        if not j:
            return
        type_label = "Oferta real" if j.get("type") == "api_result" else "Enlace de búsqueda"
        text = (
            f"Tipo: {type_label}\n"
            f"MATCH: {j.get('match')}%\n"
            f"Título: {j.get('title')}\n"
            f"Empresa: {j.get('company')}\n"
            f"Ubicación: {j.get('location')}\n"
            f"Fuente: {j.get('source')}\n"
            f"Publicado: {j.get('published_date')}\n"
            f"Detectado: {j.get('detected_date')}\n"
            f"URL: {j.get('apply_url')}\n"
            f"Fallback: {j.get('fallback_url')}\n"
            f"Skills: {j.get('skills_found')}\n\n"
            f"{j.get('description')}"
        )
        self.details.insert("1.0", text)

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

    def save_config(self, silent=False):
        cfg = {
            "roles_list": [{"name": k, "enabled": v.get()} for k, v in self.role_vars.items()],
            "roles": {k: v.get() for k, v in self.role_vars.items()},
            "locations_list": [{"name": k, "enabled": v.get()} for k, v in self.location_vars.items()],
            "locations": {k: v.get() for k, v in self.location_vars.items()},
            "custom_location": self.custom_location.get(),
            "sources_list": [{"name": k, "enabled": v.get()} for k, v in self.source_vars.items()],
            "sources": {k: v.get() for k, v in self.source_vars.items()},
            "custom_sources_list": [
                {"name": k, "domain": self.custom_source_domains[k], "enabled": v.get()}
                for k, v in self.custom_source_vars.items()
            ],
            "keywords_list": [
                {"name": k, "enabled": self.keyword_vars[k].get(), "points": int(self.keyword_weight_vars[k].get())}
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
            locations_list = cfg.get("locations_list")
            if locations_list is not None:
                for loc in list(self.location_vars.keys()):
                    self.delete_location(loc)
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
            self.custom_location.delete(0, "end")
            self.custom_location.insert(0, cfg.get("custom_location", ""))
            sources_list = cfg.get("sources_list")
            if sources_list is not None:
                for src in list(self.source_vars.keys()):
                    self.delete_source(src)
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


if __name__ == "__main__":
    app = JobFinderApp()
    app.mainloop()
