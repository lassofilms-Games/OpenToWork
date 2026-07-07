import customtkinter as ctk
from PIL import Image

from constants import APP_NAME, APP_VERSION, APP_AUTHOR
from ui import theme


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1360x800")
        self.minsize(1180, 680)
        self._set_icon()
        self._build_layout()

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

        self.quick_filter_entry = ctk.CTkEntry(header, placeholder_text="Filtro rápido...")
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

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=theme.SIDEBAR_WIDTH, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkButton(
            sidebar, text="🔍  Buscar ofertas", height=42, font=theme.FONT_SECTION,
            fg_color=theme.GREEN, hover_color=theme.GREEN_HOVER,
        ).pack(fill="x", padx=16, pady=(16, 12))

        scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16)

        for section in ("Roles", "Ubicación", "Fuentes", "Keywords / Match"):
            ctk.CTkLabel(scroll, text=section, font=theme.FONT_SECTION, anchor="w").pack(fill="x", pady=(12, 4))
            ctk.CTkLabel(
                scroll, text="(placeholder — se completa en el Paso 4)",
                font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED, anchor="w",
                wraplength=theme.SIDEBAR_WIDTH - 32, justify="left",
            ).pack(fill="x")

        ctk.CTkButton(
            sidebar, text="⚙ Configuración avanzada", fg_color="transparent",
            text_color=theme.TEXT_MUTED, hover_color=theme.GRAY_LIGHT, anchor="w",
        ).pack(fill="x", padx=16, pady=(8, 16))

    def _build_main_area(self):
        main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_area.grid(row=1, column=1, sticky="nsew", padx=16, pady=12)
        main_area.grid_rowconfigure(0, weight=1)
        main_area.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkFrame(main_area, corner_radius=10)
        self.table_frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            self.table_frame, text="Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas.",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED, justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")

        self.detail_frame = ctk.CTkFrame(main_area, corner_radius=10, height=90)
        self.detail_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.detail_frame.grid_propagate(False)
        ctk.CTkLabel(
            self.detail_frame, text="Selecciona un resultado para ver el detalle.",
            font=theme.FONT_BODY, text_color=theme.TEXT_MUTED,
        ).place(relx=0.5, rely=0.5, anchor="center")

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
