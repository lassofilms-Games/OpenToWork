STRINGS = {
    "es": {
        # Header
        "quick_filter_placeholder": "Filtro rápido... (Enter para filtrar)",
        "result_count": "{n} resultados",

        # Sidebar sections
        "section_roles": "Roles",
        "section_location": "Ubicación",
        "section_sources": "Fuentes",
        "section_custom_sources": "Fuentes personalizadas",
        "section_custom_sources_hint": "Añade otros portales de empleo por dominio",
        "section_keywords": "Keywords / Match",

        # Buttons
        "search_button": "🔍  Buscar ofertas",
        "delete_unchecked": "Eliminar desmarcadas",
        "export_button": "Exportar TXT/CSV/HTML",
        "save_button": "Guardar configuración",
        "add_source_button": "+ Añadir fuente",
        "add_keyword_button": "+ Añadir keyword",
        "open_link_button": "🔗 Abrir enlace",
        "open_fallback_button": "Abrir fallback Google",
        "export_all_button": "📤 Exportar todo",

        # Placeholders
        "new_role_placeholder": "Nueva categoría...",
        "new_location_placeholder": "Añadir ubicación...",
        "new_source_name_placeholder": "Nombre de la fuente",
        "new_source_domain_placeholder": "Dominio (ej: indeed.com)",
        "new_keyword_placeholder": "Nueva keyword...",

        # Table
        "col_match": "Match",
        "col_title": "Título",
        "col_company": "Empresa",
        "col_location": "Ubicación",
        "col_source": "Fuente",
        "col_published": "Publicado",
        "col_type": "Tipo",
        "type_api": "Oferta real",
        "type_search": "Enlace de búsqueda",

        # Empty states
        "empty_results": "Todavía no hay resultados.\nElige tus filtros y pulsa Buscar ofertas.",
        "searching": "Buscando...",
        "empty_detail": "Selecciona un resultado para ver el detalle.",

        # Detail panel
        "detail_skills": "Skills: {skills}",
        "detail_skills_empty": "Skills: -",
        "detail_subtitle": "{company}  ·  {location}  ·  {source}\nPublicado: {published}   ·   Detectado: {detected}",
        "not_available": "No disponible",
        "future_favorite": "⭐ Favorito",
        "future_applied": "✔ Aplicado",
        "future_discarded": "✕ Descartado",
        "future_notes": "📝 Notas",
        "future_suffix": "(próximamente)",

        # Status bar
        "status_ready": "Listo",
        "status_filter_clean": "Filtro limpio",
        "status_filtered": "{n} filtrados",
        "status_generating_links": "Generando enlaces de búsqueda...",
        "status_querying_remoteok": "Consultando RemoteOK...",
        "status_querying_remotive": "Consultando Remotive...",
        "status_search_error": "Error en la búsqueda",
        "status_search_done": "Búsqueda completada: {n} resultados",
        "credit": "Creado por",

        # Confirm dialogs
        "confirm_delete_roles": "¿Eliminar {n} categoría(s) desmarcada(s)?",
        "confirm_delete_keywords": "¿Eliminar {n} keyword(s) desmarcada(s)?",
        "confirm_delete_locations": "¿Eliminar {n} ubicación(es) desmarcada(s)?",
        "confirm_delete_sources": "¿Eliminar {n} fuente(s) desmarcada(s)?",
        "confirm_delete_custom_sources": "¿Eliminar {n} fuente(s) personalizada(s) desmarcada(s)?",

        # Info dialogs
        "no_unchecked_roles": "No hay categorías desmarcadas para eliminar.",
        "no_unchecked_keywords": "No hay keywords desmarcadas para eliminar.",
        "no_unchecked_locations": "No hay ubicaciones desmarcadas para eliminar.",
        "no_unchecked_sources": "No hay fuentes desmarcadas para eliminar.",
        "no_unchecked_custom_sources": "No hay fuentes personalizadas desmarcadas para eliminar.",

        # Warning dialogs
        "need_name_domain": "Indica un nombre y un dominio para la fuente personalizada.",
        "select_result_open_link": "Selecciona un resultado antes de abrir el enlace.",
        "no_link_available": "El resultado seleccionado no tiene enlace para abrir.",
        "select_result_fallback": "Selecciona un resultado antes de abrir el fallback.",
        "no_fallback_available": "El resultado seleccionado no tiene fallback disponible.",
        "select_one_role": "Selecciona al menos una categoría.",
        "no_results_to_export": "No hay resultados para exportar.",

        # Error / result dialogs
        "no_results_found": "No se encontraron resultados para los criterios seleccionados.",
        "no_results_some_failed": "No se encontraron resultados porque algunas fuentes fallaron o no devolvieron coincidencias.",
        "results_some_failed": "Se encontraron resultados, pero algunas fuentes fallaron.",
        "error_timeout": "Tiempo de espera agotado",
        "error_connection": "Error de conexión",
        "error_invalid_response": "Respuesta invalida",
        "error_dependency": "Dependencia faltante",
        "error_api": "Error de API",
        "error_unexpected": "Error inesperado",
        "unexpected_search_error": "Se produjo un error inesperado durante la búsqueda: {error}",
        "unexpected_error": "Se produjo un error inesperado.",
        "source_fallback_label": "Fuente",

        "export_success": "Exportado en:\n{dir}\n\nArchivos creados:\n- {txt}\n- {csv}\n- {html}",
        "export_write_error": "No se pudo exportar por un problema de escritura:\n{error}",
        "export_unexpected_error": "Error inesperado al exportar:\n{error}",
        "config_saved": "Configuración guardada en:\n{path}",
        "config_save_error": "No se pudo guardar la configuración:\n{error}",
        "config_load_error": "No se pudo cargar la configuración guardada:\n{error}",

        # core/sources.py generated content
        "search_link_title": "Buscar: {role}",
        "search_link_description": "Búsqueda directa en {src} para {role} en {loc}. Si el link directo falla, usa el fallback de Google.",

        # core/export.py
        "export_created_by": "Creado por {author}",
        "export_exported_on": "Exportado: {date}",
        "export_description_label": "Descripción:",
        "export_field_title": "Título",
        "export_field_company": "Empresa",
        "export_field_location": "Ubicación",
        "export_field_mode": "Modalidad",
        "export_field_source": "Fuente",
        "export_field_published": "Publicado",
        "export_field_detected": "Detectado",
        "export_field_url": "URL aplicar/buscar",
        "export_field_fallback": "Fallback Google",
        "export_field_skills": "Skills encontradas",
        "export_html_link": "Abrir",
        "export_html_google": "Google",
    },
    "en": {
        # Header
        "quick_filter_placeholder": "Quick filter... (Enter to filter)",
        "result_count": "{n} results",

        # Sidebar sections
        "section_roles": "Roles",
        "section_location": "Location",
        "section_sources": "Sources",
        "section_custom_sources": "Custom sources",
        "section_custom_sources_hint": "Add other job portals by domain",
        "section_keywords": "Keywords / Match",

        # Buttons
        "search_button": "🔍  Search jobs",
        "delete_unchecked": "Delete unchecked",
        "export_button": "Export TXT/CSV/HTML",
        "save_button": "Save configuration",
        "add_source_button": "+ Add source",
        "add_keyword_button": "+ Add keyword",
        "open_link_button": "🔗 Open link",
        "open_fallback_button": "Open Google fallback",
        "export_all_button": "📤 Export all",

        # Placeholders
        "new_role_placeholder": "New category...",
        "new_location_placeholder": "Add location...",
        "new_source_name_placeholder": "Source name",
        "new_source_domain_placeholder": "Domain (e.g. indeed.com)",
        "new_keyword_placeholder": "New keyword...",

        # Table
        "col_match": "Match",
        "col_title": "Title",
        "col_company": "Company",
        "col_location": "Location",
        "col_source": "Source",
        "col_published": "Published",
        "col_type": "Type",
        "type_api": "Real offer",
        "type_search": "Search link",

        # Empty states
        "empty_results": "No results yet.\nChoose your filters and click Search jobs.",
        "searching": "Searching...",
        "empty_detail": "Select a result to see its detail.",

        # Detail panel
        "detail_skills": "Skills: {skills}",
        "detail_skills_empty": "Skills: -",
        "detail_subtitle": "{company}  ·  {location}  ·  {source}\nPublished: {published}   ·   Detected: {detected}",
        "not_available": "Not available",
        "future_favorite": "⭐ Favorite",
        "future_applied": "✔ Applied",
        "future_discarded": "✕ Discarded",
        "future_notes": "📝 Notes",
        "future_suffix": "(coming soon)",

        # Status bar
        "status_ready": "Ready",
        "status_filter_clean": "Filter cleared",
        "status_filtered": "{n} filtered",
        "status_generating_links": "Generating search links...",
        "status_querying_remoteok": "Querying RemoteOK...",
        "status_querying_remotive": "Querying Remotive...",
        "status_search_error": "Search error",
        "status_search_done": "Search completed: {n} results",
        "credit": "Created by",

        # Confirm dialogs
        "confirm_delete_roles": "Delete {n} unchecked role(s)?",
        "confirm_delete_keywords": "Delete {n} unchecked keyword(s)?",
        "confirm_delete_locations": "Delete {n} unchecked location(s)?",
        "confirm_delete_sources": "Delete {n} unchecked source(s)?",
        "confirm_delete_custom_sources": "Delete {n} unchecked custom source(s)?",

        # Info dialogs
        "no_unchecked_roles": "There are no unchecked categories to delete.",
        "no_unchecked_keywords": "There are no unchecked keywords to delete.",
        "no_unchecked_locations": "There are no unchecked locations to delete.",
        "no_unchecked_sources": "There are no unchecked sources to delete.",
        "no_unchecked_custom_sources": "There are no unchecked custom sources to delete.",

        # Warning dialogs
        "need_name_domain": "Enter a name and a domain for the custom source.",
        "select_result_open_link": "Select a result before opening the link.",
        "no_link_available": "The selected result has no link to open.",
        "select_result_fallback": "Select a result before opening the fallback.",
        "no_fallback_available": "The selected result has no fallback available.",
        "select_one_role": "Select at least one category.",
        "no_results_to_export": "There are no results to export.",

        # Error / result dialogs
        "no_results_found": "No results were found for the selected criteria.",
        "no_results_some_failed": "No results were found because some sources failed or returned no matches.",
        "results_some_failed": "Results were found, but some sources failed.",
        "error_timeout": "Timed out",
        "error_connection": "Connection error",
        "error_invalid_response": "Invalid response",
        "error_dependency": "Missing dependency",
        "error_api": "API error",
        "error_unexpected": "Unexpected error",
        "unexpected_search_error": "An unexpected error occurred during the search: {error}",
        "unexpected_error": "An unexpected error occurred.",
        "source_fallback_label": "Source",

        "export_success": "Exported to:\n{dir}\n\nFiles created:\n- {txt}\n- {csv}\n- {html}",
        "export_write_error": "Export failed due to a write error:\n{error}",
        "export_unexpected_error": "Unexpected error while exporting:\n{error}",
        "config_saved": "Configuration saved to:\n{path}",
        "config_save_error": "Could not save the configuration:\n{error}",
        "config_load_error": "Could not load the saved configuration:\n{error}",

        # core/sources.py generated content
        "search_link_title": "Search: {role}",
        "search_link_description": "Direct search on {src} for {role} in {loc}. If the direct link fails, use the Google fallback.",

        # core/export.py
        "export_created_by": "Created by {author}",
        "export_exported_on": "Exported: {date}",
        "export_description_label": "Description:",
        "export_field_title": "Title",
        "export_field_company": "Company",
        "export_field_location": "Location",
        "export_field_mode": "Mode",
        "export_field_source": "Source",
        "export_field_published": "Published",
        "export_field_detected": "Detected",
        "export_field_url": "Apply/search URL",
        "export_field_fallback": "Google fallback",
        "export_field_skills": "Skills found",
        "export_html_link": "Open",
        "export_html_google": "Google",
    },
}


def t(lang, key, **kwargs):
    lang_strings = STRINGS.get(lang, STRINGS["es"])
    text = lang_strings.get(key, STRINGS["es"].get(key, key))
    return text.format(**kwargs) if kwargs else text
