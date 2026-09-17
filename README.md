# GestorIncidencias — Tablero Kanban

> **Gestor de incidencias y tareas con tablero Kanban, agenda integrada y sistema de auditoría.**  
> CustomTkinter • SQLite • Drag & Drop • Dashboard en tiempo real

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1f6aa5)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## 📑 Índice

- [1. Descripción](#1-descripción)
- [2. Características](#2-características)
- [3. Captura / Flujo](#3-flujo-kanban)
- [4. Tecnologías](#4-tecnologías)
- [5. Estructura del proyecto](#5-estructura-del-proyecto)
- [6. Instalación](#6-instalación)
- [7. Uso — Manual rápido](#7-uso--manual-rápido)
- [8. Atajos de teclado](#8-atajos-de-teclado)
- [9. Arquitectura](#9-arquitectura)
- [10. Base de datos](#10-base-de-datos)
- [11. Drag & Drop — Detalle técnico](#11-drag--drop--detalle-técnico)
- [12. Configuración](#12-configuración)
- [13. Export / Backup](#13-export--backup)
- [14. API interna (database.py)](#14-api-interna-databasepy)
- [15. Solución de problemas](#15-solución-de-problemas)
- [16. Roadmap](#16-roadmap)
- [17. Licencia](#17-licencia)

---

## 1. Descripción

**GestorIncidencias** es una aplicación de escritorio para **Windows** que centraliza la gestión de incidencias de clientes. Combina:

* **Tablero Kanban** de 5 estados con drag & drop entre columnas y reordenado vertical.
* **Agenda/Calendario** para tareas, citas, llamadas y seguimientos.
* **Sistema de notas, historial de auditoría y adjuntos** por ticket.
* **Dashboard** con KPIs y semáforo SLA por fecha límite.
* **Filtros, búsqueda global, WIP limits, gestión de usuarios y export** a Excel/PDF.

Todo persiste en `incidencias.db` (SQLite) sin necesidad de servidor.

---

## 2. Características

### Tier 1 — Productividad inmediata
| # | Funcionalidad | Dónde | Estado |
|---|---|---|---|
| 1 | **Búsqueda + Filtros Kanban** — texto (cliente/título/descripción) + prioridad + responsable + limpiar | Panel lateral `app.py:1060` | ✅ |
| 2 | **Dashboard KPIs** — Total, Urgentes pendientes, Vencidos, En Análisis/En Proceso/Finalizadas | Barra superior `app.py:1015` | ✅ |
| 3 | **Prioridad con color** — barra 6px + badge `Baja gris / Media azul / Alta naranja / Urgente rojo` | `PRIORIDAD_COLORES` `app.py:8` | ✅ |
| 4 | **Editar Ticket** — doble-click o botón ✎ | `VentanaEditarTicket:145` | ✅ |
| 5 | **Exportar** — Excel (openpyxl → CSV fallback) y PDF (reportlab → TXT fallback) | `app.py:1202` | ✅ |

### Tier 2 — Flujo
| 6 | **WIP Limits** — `Recibida 20 / En Análisis 3 / En Proceso 5 / Pendiente 8 / Finalizada 30` + `label (3/5) ⚠` y bloqueo al mover | `WIP_LIMITS` `app.py:13` | ✅ |
| 7 | **Reordenar vertical** — `▲▼` en handle + columna `posicion` + `reordenar_tickets()` | `app.py:1437` `database.py:361` | ✅ |
| 8 | **Historial / Auditoría** — tabla `historial`, timeline en Tab Historial | `VentanaNotas:71` `database.py:116` | ✅ |
| 9 | **SLA / Vencimiento** — `fecha_limite YYYY-MM-DD` + semáforo `🔴 Vencido / 🟡 Hoy / 🟠 Mañana / 🟢 Xd` | `get_semaforo()` `app.py:17` | ✅ |
| 10 | **Adjuntos** — Tab Adjuntos, copia a `adjuntos/`, Abrir/X | `VentanaNotas:76` `database.py:134` | ✅ |

### Tier 3 — Avanzado
| 11 | **Notificaciones** — chequeo 60s de vencidos/urgentes/tareas hoy en barra estado | `app.py:1152` | ✅ |
| 12 | **Palette + Atajos** — `Ctrl+K` búsqueda global, `Ctrl+N`, `Ctrl+E`, `F5`, `Delete` | `VentanaPalette:238` `app.py:1115` | ✅ |
| 13 | **Usuarios** — tabla `usuarios`, alta/baja, combo responsable + filtro | `VentanaUsuarios:195` `database.py:72` | ✅ |
| 14 | **Backup/Restore** — copia `incidencias.db` con filedialog | `app.py:1284` | ✅ |
| — | **Drag & Drop** — ghost flotante, resaltado columna, validación WIP, contenedor exterior para columnas vacías | `app.py:1178` | ✅ |

### Tier 4 — Calendario y Alarmas (nuevo)
| 15 | **Calendario: Día de hoy marcado** — `calevent` azul `#1f6aa5` siempre visible, botón `⟳ Ir a hoy` | `VentanaAgenda._resaltar_fechas()` `app.py:646` | ✅ |
| 16 | **Calendario: Días con eventos señalados** — naranja `#e67e22` (pendientes), rojo `#e74c3c` (urgentes), leyenda + contador `Hoy: X / Total: Y` | `app.py:646` `database.py:928` | ✅ |
| 17 | **Alarma / Aviso de evento** — popup `VentanaAlarma` topmost + sonido (`winsound.Beep` o `bell`) + barra estado `🔔/⏰/⚠` cuando falta ≤15 min o vencido ≤5 min, con `✓ Completar` y `Posponer 10 min` | `VentanaAlarma` `app.py:1328` + `_chequear_alarmas()` cada 30s | ✅ |
| 18 | **Resaltado inminente en agenda** — tarjetas con borde rojo/naranja y texto `⚠ VENCIDO hace Xm` / `🔔 ¡AHORA! en Xm` / `⏰ en Xm` si es hoy | `VentanaAgenda.crear_tarjeta_evento()` `app.py:880` | ✅ |

---

## 3. Flujo Kanban

```
Recibida  →  En Análisis  →  En Proceso  →  Pendiente Cliente  →  Finalizada
   ↑              3 WIP          5 WIP            8 WIP               ∞
   └── filtros + búsqueda ────────────────────────────────────────────┘
```

* **Crear:** formulario lateral (cliente*, título*, canal, contacto, prioridad, responsable, fecha límite).
* **Mover:** arrastra desde `⋮⋮ arrastra` / título / barra; o `CTkOptionMenu` fallback.
* **Editar:** doble-click tarjeta.
* **Notas/Historial/Adjuntos:** botón `Notas (n) +📎`.

---

## 4. Tecnologías

| Capa | Librería | Versión | Uso |
|---|---|---|---|
| GUI | `customtkinter` | 6.0.0 | Widgets modernos Dark/Blue |
| Calendario | `tkcalendar` | — | `Calendar` en `VentanaAgenda` |
| DB | `sqlite3` (stdlib) | — | `incidencias.db` con FK `ON DELETE CASCADE` |
| Excel | `openpyxl` (opcional) | — | Export `.xlsx` |
| PDF | `reportlab` (opcional) | — | Export `.pdf` |
| Otros | `shutil`, `csv`, `webbrowser`, `filedialog`, `winsound`/`platform` | stdlib | Adjuntos, export, backup, **sonido alarma** |

> Sin `openpyxl`/`reportlab` el export hace fallback a CSV/TXT automáticamente.

---

## 5. Estructura del proyecto

```
GestorIncidencias/
├── app.py              # ~2150 líneas: GUI, Kanban, drag&drop, ventanas, dashboard, export, **calendario marcado + alarmas**
├── database.py         # ~1020 líneas: init_db, CRUD tickets/notas/agenda/usuarios/historial/adjuntos + **fechas_con_eventos/proximos**
├── incidencias.db      # SQLite (autogenerado)
├── adjuntos/           # Archivos adjuntos copiados (autogenerado)
├── .venv/              # Entorno virtual
├── README.md           # Este archivo
├── app.spec / build/ / dist/  # PyInstaller
└── __pycache__/
```

**Clases principales `app.py`:**

* `AplicacionIncidencias(ctk.CTk)` — ventana principal, Kanban, dashboard, filtros, drag, atajos, **alarmas 30s**
* `VentanaNotas(ctk.CTkToplevel)` — 3 tabs: Notas / Historial / Adjuntos
* `VentanaEditarTicket` — edición completa
* `VentanaUsuarios` — CRUD responsables
* `VentanaPalette` — `Ctrl+K`
* `VentanaAgenda` + `VentanaNuevoEvento` — calendario con **marcas hoy/eventos + panel próximo aviso**
* `VentanaAlarma(ctk.CTkToplevel)` — popup alarma evento inminente con sonido y Posponer 10 min

---

## 6. Instalación

### Requisitos

* Windows 10/11, Python 3.10+
* Git (opcional)

### Pasos

```powershell
# 1. Clonar / copiar
cd C:\Users\josearregui\Desktop
git clone <repo> GestorIncidencias
cd GestorIncidencias

# 2. Entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Dependencias
.\.venv\Scripts\python.exe -m pip install --upgrade pip
pip install customtkinter tkcalendar
pip install openpyxl reportlab  # opcional pero recomendado

# 4. Ejecutar
.\.venv\Scripts\python.exe app.py
```

### Ejecutable

```powershell
pip install pyinstaller
pyinstaller --windowed --onefile --name GestorIncidencias app.py
# genera dist/GestorIncidencias.exe
```

---

## 7. Uso — Manual rápido

### Alta de ticket

1. Rellena **Cliente*** y **Título*** en panel izquierdo.
2. Elige `Canal`, `Prioridad` (color), `Responsable`, `Límite YYYY-MM-DD`.
3. `Registrar Ticket (Ctrl+N)` → aparece en **Recibida** con barra de color.

### Kanban

* **Filtrar:** escribe en `Buscar cliente, título...` o elige `Prioridad/Responsable` → filtra al instante (`KeyRelease`).
* **Mover:** arrastra tarjeta a otra columna (ghost `90×220` semitransparente, borde `#1f6aa5`). Si WIP lleno → aviso.
* **Reordenar:** `▲▼` en handle cambia `posicion`.
* **Editar:** doble-click o `✎`.
* **Notas/Historial/Adjuntos:** `Notas (2) +1📎` → 3 tabs. En Notas puedes borrar con `🗑`.

### Agenda (actualizada — calendario marcado + alarmas)

`📅 Agenda` → calendario `yyyy-mm-dd` a la izquierda, lista `Tareas y citas` a la derecha, `+ Nueva tarea / cita` (tipo, prioridad, hora opcional), `✓ Completar / Marcar pendiente`.

**Novedades calendario:**
* **Hoy** siempre marcado en **azul** (`tag 'hoy'` `#1f6aa5`), aunque tenga eventos combina a `hoy_evento` (borde amarillo) o `hoy_urgente` (rojo). Botón `⟳ Ir a hoy` centra el mes y selecciona el día.
* **Días con eventos pendientes** se pintan vía `calendar.calevent_create()` — **naranja** si hay pendientes, **rojo** si alguno es `Urgente`. Los completados no se resaltan para no saturar. Leyenda `● Hoy ● Con eventos ● Urgente` + contador `Hoy: X pendiente(s) • Total: Y pendiente(s)` bajo el calendario.
* El resaltado se refresca automáticamente al crear/completar/eliminar evento (`_on_evento_cambiado()`), al cambiar de mes (`<<CalendarMonthChanged>>`) y cada 30s en `_tick_proximo()`.

**Alarmas / avisos:**
* Cada **30s** (`AplicacionIncidencias._chequear_alarmas()`) revisa eventos de **hoy con hora**. Ventana de disparo: **15 min antes → 5 min después** (vencido). Muestra `VentanaAlarma` topmost con sonido (`winsound.Beep` 800/1000/1200 Hz en Windows, `bell()` fallback) y barra estado `🔔`/`⏰`/`⚠` con parpadeo. Botones: `✓ Completar` (marca completada), `Posponer 10 min` ( actualiza `fecha/hora` a `now+10m` vía `actualizar_evento()` ), `Cerrar`. Cooldown 10 min por evento para no spamear; vencidos antiguos (>5 min, <60 min) solo avisan en barra cada 30 min.
* Dentro de la Agenda, el panel izquierdo `⏰ Próximo aviso` muestra cuenta atrás (`En Xm`, `¡AHORA!`, `VENCIDO hace Xm`) y cada tarjeta de hoy añade borde rojo/naranja + texto de estado si es inminente.
* En la ventana principal la barra inferior también alterna a `🔔 Próximo: Título a las HH:MM (en Xm)` o `⚠ Vencido: ...`.

### Usuarios / Export / Backup

* `👥 Usuarios` → añade `Nombre + Email` / elimina (excepto Sin asignar).
* `📊 Excel` / `📄 PDF` → `filedialog.asksaveasfilename` con timestamp.
* `💾 Backup` / `📂 Restaurar` → copia `incidencias.db` (restaurar pide confirmación y recarga `cargar_tarjetas()`).

---

## 8. Atajos de teclado

| Atajo | Acción | Código |
|---|---|---|
| `Ctrl+K` | Palette búsqueda global | `app.py:1115` |
| `Ctrl+N` | Foco Cliente (nuevo ticket) | `app.py:1115` |
| `Ctrl+E` | Exportar Excel | `app.py:1115` |
| `F5` | Recargar Kanban | `app.py:1115` |
| `Delete` | Borrar ticket seleccionado | `app.py:1115` |
| `Doble-click` | Editar ticket | `app.py:1330` |
| `Esc` | Cerrar palette / ventana | `VentanaPalette` |

Barra estado inferior muestra `Listo • Ctrl+K buscar • Ctrl+N nuevo • Doble-click editar • Drag & drop activo` + reloj `dd/mm/yyyy HH:MM` (`_tick_reloj` 60s).

---

## 9. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│  AplicacionIncidencias (CTk)                            │
│  ├── Dashboard (6 KPIs) ──────────── obtener_estadisticas() │
│  ├── Panel Formulario ────────────── crear_ticket()     │
│  │    ├── Filtros (texto/prioridad/responsable)         │
│  │    ├── Alta + Responsable/Límite                     │
│  │    └── Acciones (Agenda/Usuarios/Excel/PDF/Backup)   │
│  ├── frame_kanban (grid 5 cols)                         │
│  │    └── columnas_contenedores → columnas_frames (CTkScrollableFrame) │
│  │         └── card (barra color + inner + handle ▲▼)   │
│  └── frame_estado (notificaciones + reloj)              │
│       └── VentanaNotas / Editar / Usuarios / Palette    │
└──────────────────────┬──────────────────────────────────┘
                       │ sqlite3 + PRAGMA foreign_keys
┌──────────────────────▼──────────────────────────────────┐
│  database.py                                            │
│  tickets • usuarios • notas • historial • adjuntos • agenda │
└─────────────────────────────────────────────────────────┘
```

* **Sin ORM:** `sqlite3` directo, `conectar()` centralizado.
* **Migración:** `_columna_existe()` + `ALTER TABLE ADD COLUMN` para `tickets` existentes.
* **Posicionamiento:** `ORDER BY posicion ASC, id DESC` + `UPDATE posicion` tras drag/reorden.

---

## 10. Base de datos

### Diagrama ER (Mermaid)

```mermaid
erDiagram
    tickets ||--o{ notas : "ON DELETE CASCADE"
    tickets ||--o{ historial : "ON DELETE CASCADE"
    tickets ||--o{ adjuntos : "ON DELETE CASCADE"
    tickets ||--o{ agenda : "ON DELETE SET NULL"
    usuarios ||--o{ tickets : "responsable TEXT"

    tickets {
        INTEGER id PK
        TEXT cliente
        TEXT canal
        TEXT contacto
        TEXT titulo
        TEXT descripcion
        TEXT prioridad "Baja/Media/Alta/Urgente"
        TEXT estado "5 valores"
        TIMESTAMP fecha_creacion
        TEXT responsable FK->usuarios.nombre
        TEXT fecha_limite "YYYY-MM-DD"
        INTEGER posicion
        TEXT tiempo_estimado
    }
    usuarios {
        INTEGER id PK
        TEXT nombre UNIQUE
        TEXT email
        TEXT color
        INTEGER activo
    }
    notas {
        INTEGER id PK
        INTEGER ticket_id FK
        TEXT texto
        TIMESTAMP fecha
    }
    historial {
        INTEGER id PK
        INTEGER ticket_id FK
        TEXT estado_anterior
        TEXT estado_nuevo
        TIMESTAMP fecha
        TEXT usuario
    }
    adjuntos {
        INTEGER id PK
        INTEGER ticket_id FK
        TEXT nombre_archivo
        TEXT ruta
        TIMESTAMP fecha
    }
    agenda {
        INTEGER id PK
        TEXT titulo
        TEXT fecha "YYYY-MM-DD"
        TEXT hora "HH:MM"
        TEXT descripcion
        TEXT tipo
        TEXT prioridad
        INTEGER completada 0/1
        INTEGER ticket_id FK
        TIMESTAMP fecha_creacion
    }
```

### Init

```python
database.init_db()  # app.py:739 -> crea tablas si no existen + usuarios por defecto + posicion = id
```

Usuarios por defecto: `Sin asignar (#555555)`, `Ana García`, `Carlos Ruiz`, `Laura Méndez`.

### Integridad

* `PRAGMA foreign_keys = ON` en `conectar()`.
* `notas`/`historial`/`adjuntos` → `CASCADE` al borrar ticket.
* `agenda.ticket_id` → `SET NULL`.

---

## 11. Drag & Drop — Detalle técnico

**Problema original:** `CTkScrollableFrame` vacío colapsa a `1px` → `winfo_containing` fallaba; `CTkFrame._canvas` no recibía `bind`.

**Solución `app.py:1178`:**

1. **Contenedor exterior** `columnas_contenedores: dict[estado, CTkFrame]` (`app.py:823`) `grid(sticky="nsew")` → siempre `198×720`, se usa para hit-test.
2. **Detección 3 niveles** `_get_estado_bajo_cursor(x_root, y_root)`:
   * `winfo_containing` + walk-up 14 niveles (col + contenedor + parent chain)
   * bbox del contenedor
   * división equitativa `frame_kanban` (`col_w = kw/len(ESTADOS)`)
3. **Bind recursivo** `_bind_single()` (`app.py:932`): `widget.bind("<Button-1>" + "<ButtonPress-1>", add="+")` + `widget._canvas.bind` + hijos. Cursor `fleur`.
4. **Ghost** (`_mover_drag`): se crea solo tras `>8px` para no flashear en click; `CTkToplevel(overrideredirect, -topmost, -alpha 0.90)` offset `+12px` (no tapa cursor), sin `transient` (oculta en Windows). Borde `#1f6aa5`.
5. **Validación WIP** en `_soltar_drag` + `cambiar_estado` → `messagebox` si `len(dest) >= WIP_LIMITS`.
6. **Resaltado** `_resaltar_columna` → `border_width 2 #1f6aa5` en col + contenedor; `_limpiar_resaltado` → `0`.

**E2E verificado:**

```
drag Recibida (326,149) -> En Análisis (622,458) -> historial + posicion actualizados PASS
```

---

## 12. Configuración

Edita en `app.py`:

```python
ESTADOS = ["Recibida", "En Análisis", "En Proceso", "Pendiente Cliente", "Finalizada"]
PRIORIDAD_COLORES = {"Baja":"#7f8c8d","Media":"#3498db","Alta":"#e67e22","Urgente":"#e74c3c"}
WIP_LIMITS = {"Recibida":20,"En Análisis":3,"En Proceso":5,"Pendiente Cliente":8,"Finalizada":30}
ctk.set_appearance_mode("Dark")  # Light/Dark/System
```

Notificaciones cada `60000 ms` en `_chequear_notificaciones`, reloj en `_tick_reloj`.

---

## 13. Export / Backup

| Acción | Función | Detalle |
|---|---|---|
| Excel | `exportar_excel()` `app.py:1202` | `asksaveasfilename .xlsx/.csv`, `openpyxl` con autosize `max_len+2`, fallback CSV si no instalado |
| PDF | `exportar_pdf()` | `reportlab` `A4` `TableStyle` `ROWBACKGROUNDS` + fallback TXT |
| Backup | `hacer_backup()` `app.py:1284` | `shutil.copy2(incidencias.db, dest)` con `date.today().isoformat()` |
| Restore | `restaurar_backup()` | `askopenfilename` + confirm + `copy2` + `cargar_tarjetas()` |

Adjuntos se guardan en `adjuntos/{ticket_id}_{nombre}` con deduplicación `_1`, `_2`.

---

## 14. API interna (database.py)

### Tickets

```python
crear_ticket(cliente, canal, contacto, titulo, descripcion, prioridad,
             responsable="Sin asignar", fecha_limite=None, tiempo_estimado=None) -> id
obtener_tickets(filtro_texto=None, filtro_prioridad=None, filtro_estado=None, filtro_responsable=None) -> list[tuple[13]]
obtener_ticket(ticket_id) -> tuple | None
actualizar_ticket(ticket_id, cliente, canal, contacto, titulo, descripcion, prioridad, responsable, fecha_limite, tiempo_estimado)
actualizar_estado(ticket_id, nuevo_estado, usuario="Sistema")  # + historial
actualizar_posicion(ticket_id, nueva_posicion)
reordenar_tickets(estado, orden_ids: list[int])
eliminar_ticket(ticket_id)
obtener_estadisticas() -> {"total", "por_estado", "por_prioridad", "por_responsable", "urgentes_pendientes", "vencidos", "en_analisis"}
```

### Usuarios / Historial / Adjuntos / Notas / Agenda

```python
obtener_usuarios(solo_activos=True) -> list[(id,nombre,email,color,activo)]
crear_usuario(nombre, email, color) -> id
eliminar_usuario(id)
obtener_nombres_usuarios() -> list[str]

obtener_historial(ticket_id) -> list[(id, ant, nuevo, fecha, usuario)]
contar_historial(ticket_id) -> int

crear_adjunto(ticket_id, nombre_archivo, ruta) -> id
obtener_adjuntos(ticket_id) -> list[(id, nombre, ruta, fecha)]
contar_adjuntos(ticket_id) -> int
eliminar_adjunto(id)  # borra archivo físico si existe

crear_nota(ticket_id, texto)
obtener_notas(ticket_id) -> list[(id, texto, fecha)]
contar_notas(ticket_id) -> int
eliminar_nota(id)

crear_evento(titulo, fecha, hora, descripcion, tipo, prioridad, ticket_id=None)
obtener_eventos_fecha(fecha) -> list
obtener_eventos_mes(inicio, fin) -> list
obtener_fechas_con_eventos(solo_pendientes=False) -> dict[fecha_str, {total, pendientes, tiene_urgente}]  # para pintar calendario
obtener_eventos_pendientes(desde_fecha=None) -> list  # >= hoy, ordenados
obtener_eventos_proximos(minutos=60, incluir_vencidos_min=30) -> list[(row, delta_min, evento_dt)]  # ventana alarma
obtener_evento(id) -> tuple | None
actualizar_evento(id, titulo, fecha, hora, descripcion, tipo, prioridad, ticket_id)
marcar_evento_completado(id, completada)
eliminar_evento(id)
contar_eventos_fecha(fecha) -> int
```

**Clases nuevas / ampliadas `app.py`:**
```python
VentanaAgenda  # + _configurar_marcas_calendario(), _resaltar_fechas(), ir_a_hoy(), _tick_proximo(), _on_evento_cambiado()
VentanaAlarma(ctk.CTkToplevel)  # popup topmost con sonido, Completar / Posponer 10 min / Cerrar
AplicacionIncidencias  # + _chequear_alarmas() 30s, _texto_proximo_evento(), _parpadear_estado()
```

---

## 15. Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: customtkinter` | venv no activado | `.\.venv\Scripts\Activate.ps1` + `pip install customtkinter tkcalendar` |
| Drag no mueve a columna vacía | Versión antigua sin contenedor | Actualiza `app.py:823` con `columnas_contenedores` |
| Export Excel vacío / error | `openpyxl` no instalado | `pip install openpyxl` o elige `.csv` |
| PDF no se genera | `reportlab` no instalado | `pip install reportlab` (fallback TXT) |
| Adjunto `Archivo no encontrado` | Ruta movida | Re-adjuntar, o revisa `adjuntos/` vs `ruta` en DB |
| `sqlite3.OperationalError: no such column` | DB antigua sin migración | `database.init_db()` añade columnas vía `_columna_existe` — reinicia app |
| WIP bloquea movimiento | Límite alcanzado | Libera un ticket a `Finalizada` o sube `WIP_LIMITS` en `app.py:13` |
| Ventana no aparece / foco | `grab_set` bloqueante antiguo | Ya usa `<Visibility>` + `lift` + `-topmost` toggle (`VentanaNotas:48`) |
| Calendario no marca hoy/eventos | Versión antigua sin `calevent` | Actualiza `app.py:646` `_resaltar_fechas()` + `tag_config`; verifica `tkcalendar` instalado |
| Alarma no suena | `winsound` solo Windows / volumen bajo | En Windows usa `Beep`; en otros `bell()` + `print(\a)` — sube volumen y prueba con evento a +2 min |

Logs drag/alarma: `print(f"[drag] _mover_drag error: {e}")` y `print(f"[alarma] ...")` en consola.

---

## 16. Roadmap

- [x] **Calendario con hoy + días con eventos + alarmas** — `calevent` + `VentanaAlarma` + sonido (implementado 2026-09)
- [ ] Sincronización nube (SQLite → API REST / Supabase)
- [ ] SLA con horas laborables + notificaciones `plyer` (base ya con `winsound`/`bell`)
- [ ] Comentarios con `@menciones` y markdown
- [ ] Filtros avanzados por rango de fechas + `fecha_creacion`
- [ ] Gráfica burndown en dashboard (`matplotlib`)
- [ ] Tests `pytest` para `database.py` + `drag` headless
- [ ] CI + `pre-commit` (ruff/black)

---

## 17. Licencia

MIT — Libre para uso personal y comercial. Mantén atribución.

---

## Créditos

* Autor: `josearregui` · GestorIncidencias
* GUI: [TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
* Calendario: [j4321/tkcalendar](https://github.com/j4321/tkcalendar)

> **Atajo útil:** `Ctrl+K` para buscar cualquier ticket por cliente/título/prioridad en toda la app.

