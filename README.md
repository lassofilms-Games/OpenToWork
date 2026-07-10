# OpenToWork 

Aplicación de escritorio en Python (CustomTkinter) para buscar ofertas de empleo combinando enlaces de búsqueda directos y APIs públicas, con un sistema de match por keywords y roles.

![OpenToWork screenshot](docs/screenshot.png)

## Características

- **Roles, ubicaciones, fuentes y keywords** totalmente configurables desde la barra lateral, con puntuación de match (0-100%) por oferta.
- **Fuentes personalizadas**: añade cualquier portal de empleo por nombre + dominio, sin tocar código.
- **Tabla de resultados** con color por tipo (oferta real vs. enlace de búsqueda) y por score de match.
- **Panel de detalle** con descripción (keywords resaltadas), y accesos directos para abrir el enlace o el fallback de Google.
- **Seguimiento por oferta**: marca ★ Favorito, ✓ Aplicado o ✕ Descartado y escribe notas propias — persiste entre sesiones y se ve de un vistazo en la columna Estado.
- **Exportación** a TXT, CSV y HTML.
- **Modo claro/oscuro** y **selector de idioma español/inglés**, ambos en caliente.
- **Paneles redimensionables**: arrastra los divisores entre buscador, tabla y detalle.
- Integraciones ya incluidas: LinkedIn, Wellfound, Work With Indies, Hitmarker, Creativepool, InfoJobs, Glassdoor, ArtStation, RemoteOK API y Remotive API.

## Instalación

```bash
python -m pip install -r requirements.txt
python opentowork_app.py
```

## Generar el ejecutable (.exe)

```bash
python -m PyInstaller OpenToWork.spec --noconfirm
```

o usando el script incluido:

```bash
build_exe_opentowork.bat
```

El `.exe` queda en `dist/OpenToWork.exe`.

## Dónde se guardan tus datos

- Configuración: `%APPDATA%\OpenToWork\config.json`
- Favoritos, aplicados, descartados y notas: `%APPDATA%\OpenToWork\job_states.json`
- Resultados exportados: `%APPDATA%\OpenToWork\results\`
- Logs: `%APPDATA%\OpenToWork\logs\opentowork.log`

Si vienes de una versión anterior (`OPentowork_app`), la configuración y tus
estados por oferta se migran automáticamente al primer arranque.

## Estructura del proyecto

```
opentowork_app.py       # Punto de entrada
constants.py             # Nombre, versión, valores por defecto
i18n.py                  # Textos en español/inglés
core/                    # Lógica: scoring, fuentes, export, config, logging
ui/                      # Interfaz CustomTkinter
assets/                  # Logo e icono
```

## Autor

Creado por **Diego Lasso**.
