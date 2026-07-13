# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

OpenToWork: aplicación de escritorio Windows en Python (CustomTkinter) para buscar ofertas de empleo. Combina 8 APIs públicas sin key (ofertas reales en la tabla) con ~35 portales por dominio (enlaces de búsqueda directos + fallback Google), con scoring de match por keywords, seguimiento por oferta y exportación. Idiomas ES/EN en caliente, modo claro/oscuro.

## Comandos

```bash
python -m pip install -r requirements.txt   # deps: requests, pyinstaller, customtkinter, pillow
python opentowork_app.py                    # ejecutar la app
python -m PyInstaller OpenToWork.spec --noconfirm   # generar dist/OpenToWork.exe
```

No hay suite de tests ni linter. Verificación de sintaxis rápida: `python -c "import py_compile; py_compile.compile('ui/main_window.py', doraise=True)"`.

**Git en la unidad F:** falla con "dubious ownership". Nunca uses `git config --global`; antepon a cada comando git:
`GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="F:/Jobfinder/Opentowork_v1_3"`.
El remote es `https://github.com/lassofilms-Games/OpenToWork.git` (el nombre antiguo OPentowork_app redirige). `dist/`, `build/` y `user_data/` están gitignorados.

**Tras cada cambio shippable**: reconstruir el `.exe` (cierra antes cualquier `OpenToWork.exe` en ejecución: bloquea la escritura) y, si el cambio es visual, regenerar `docs/screenshot.png`.

## Cómo probar la UI

Sin simulación de clics. Se escriben scripts temporales que importan `ui.main_window.MainWindow`, inyectan datos falsos (`app.jobs = [...]; app.populate_tree(app._visible_jobs())`) o llaman métodos directamente (`app._toggle_theme()`, `app._toggle_source_group(...)`), se lanzan en background y se capturan con PowerShell (`SetWindowPos` topmost + `Graphics.CopyFromScreen`). La ventana pierde el color DWM de la barra de título al estar desenfocada en las capturas — es normal, activa está bien.

## Arquitectura

- `opentowork_app.py` — entrada (3 líneas). Toda la UI vive en `ui/main_window.py`, una sola clase `MainWindow(ctk.CTk)` (~1500 líneas) organizada por secciones comentadas (Header, Sidebar, Tabla, Detalle, Search, Config).
- `ui/theme.py` — sistema de diseño completo: paleta como tuplas `(claro, oscuro)`, tipografía, espaciados, radios y helpers de estilo (`primary_button_style()`, `card_style()`, etc.). **Nunca** colores hardcodeados en componentes; todo sale de aquí.
- `ui/icons.py` — iconos monocromos dibujados con PIL a 4x y reescalados (lupa, documento, marca de agua del logo). **Prohibidos los emojis en la UI**: no siguen el tema; se usan glifos de texto (★ ✓ ✕ ✎ ✦) o iconos PIL.
- `i18n.py` — dict `STRINGS` con ES y EN + `t(lang, key, **kwargs)`. Cada texto visible nuevo necesita clave en AMBOS idiomas, y `_apply_language()` en main_window debe actualizar el widget.
- `constants.py` — `DEFAULT_SOURCE_GROUPS` (fuentes agrupadas en 6 categorías con estado por defecto) del que se derivan `DEFAULT_SOURCES` (plano, compatibilidad con config) y `SOURCE_GROUP_OF` (colocación en la UI).
- `core/sources.py` — fetchers de las 8 APIs + generador de enlaces de búsqueda. Patrón común por fetcher: caché en memoria 15 min (`_cache_get/_cache_set`), filtro local por rol (`_matches_role_terms`), constructor `_job_entry()` (aplica `score_job` + `freshness_bonus`). Errores → `SourceFetchError(source, kind, message)`; el `kind` mapea a mensajes i18n. Peculiaridad: Jobicy responde 404 cuando un tag no tiene ofertas — se trata como resultado vacío, no como error.
- `core/scoring.py` — `score_job()` (rol en título +50, keywords del usuario suman sus puntos, exclusiones -35) y `freshness_bonus()` (+10 ≤7 días, -10 >30). Los enlaces de búsqueda NO se puntúan (match=0, la tabla muestra "—"): su descripción contiene el rol y salían al 100%.
- `core/config_store.py` — datos de usuario en `%APPDATA%\OpenToWork\` con migración automática desde carpetas legacy (`OPentowork_app`, `JobFinderPro`). `core/job_states.py` — estados por oferta (favorito/aplicado/descartado/notas, clave = apply_url) y `seen_jobs.json` (histórico para marcar ofertas nuevas ✦, poda 90 días).

### Flujo de búsqueda (incremental)

`search_jobs()` lanza `_search_jobs_worker` en un hilo; se comunica con la UI solo vía `self.search_queue` con mensajes `{"kind": "status"|"partial"|"done"|"fatal"}` que `_poll_search_queue` consume con `after()`. Cada fuente publica un "partial" al responder → `_absorb_partial` marca nuevas, hace dedupe y repuebla la tabla en caliente. La vista de la tabla siempre pasa por `_visible_jobs()` (switch "Solo ofertas reales" + filtro rápido). Orden en `dedupe_jobs`: ofertas API primero, luego match, luego fecha.

### Compatibilidad de configuración

`config.json` guarda listas (`sources_list`, `roles_list`...) que en `load_config` REEMPLAZAN las por defecto; las fuentes nuevas añadidas en versiones posteriores se mergean tras cargar (bloque `DEFAULT_SOURCES.items()` en load_config). No renombres claves de config ni nombres de fuentes existentes: romperías configs guardadas.

## Trampas de CustomTkinter/Tk aprendidas a base de bugs

- **Widgets CTk dentro de `tk.PanedWindow`**: CTk no puede deducir el color del padre no-CTk y congela el detectado al crearse → pasa siempre `bg_color=theme.X` explícito (tupla) a frames hijos de un paned, y fija el `bg` del paned en su constructor, no después.
- **PanedWindow con `opaqueresize=False`** (ambos): con True, cada píxel de arrastre relanza el layout completo y CTk deja artefactos (textos cortados, tearing).
- **ttk.Treeview (tema clam)** dibuja bordes propios: iguala `bordercolor/lightcolor/darkcolor` al fondo en `_setup_treeview_style`, que se re-ejecuta al cambiar de tema. El Treeview es un rectángulo opaco: va inseteado en su tarjeta para no tapar las esquinas redondeadas.
- **Cambio de tema**: `_toggle_theme` debe refrescar todo lo no-CTk (estilo ttk, colores de paned, DWM de la barra de título, icono, marca de agua, detalle).
- **Barra de título Windows**: sin texto (`title("")`) y sin icono visible — el icono 16px se pinta del color de la barra (Tk pierde el alfa al convertir a HICON) y se regenera al cambiar tema; DWM (`DwmSetWindowAttribute` 35/36) la pinta del color del fondo.
- Los divisores del layout son `tk.PanedWindow` (h: sidebar/main, v: tabla/detalle); el header alinea el filtro rápido con la tarjeta de resultados vía `header_brand` cuyo ancho sigue al sidebar en `_on_sidebar_resize`.

## Estilo

Comentarios del código en español, explicando el porqué (constraints no evidentes), no el qué. La estética es flat moderna con metáfora de carpeta (pestaña sobre el sidebar); sin sombras reales (Tk no las soporta), profundidad por color y bordes sutiles de `theme.BORDER`.
