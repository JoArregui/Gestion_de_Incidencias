import sqlite3
import os
from datetime import datetime, date

DB_NAME = "incidencias.db"


# -------------------------------------------------------------------
# CONEXIÓN
# -------------------------------------------------------------------

def conectar():
    """
    Crea y devuelve una conexión con la base de datos.

    Activa las claves foráneas de SQLite para que funcionen
    correctamente ON DELETE CASCADE y ON DELETE SET NULL.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    cols = [row[1] for row in cursor.fetchall()]
    return columna in cols


# -------------------------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS
# -------------------------------------------------------------------

def init_db():
    conn = conectar()

    try:
        cursor = conn.cursor()

        # -----------------------------------------------------------
        # TABLA DE TICKETS
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                canal TEXT NOT NULL,
                contacto TEXT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                prioridad TEXT NOT NULL,
                estado TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migraciones para tickets existentes
        for col, ddl in [
            ("responsable", "TEXT"),
            ("fecha_limite", "TEXT"),
            ("posicion", "INTEGER DEFAULT 0"),
            ("tiempo_estimado", "TEXT"),
        ]:
            if not _columna_existe(cursor, "tickets", col):
                cursor.execute(f"ALTER TABLE tickets ADD COLUMN {col} {ddl}")

        # -----------------------------------------------------------
        # TABLA DE USUARIOS
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                email TEXT,
                color TEXT DEFAULT '#1f6aa5',
                activo INTEGER DEFAULT 1
            )
        ''')

        # Usuarios por defecto
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            for nombre, email, color in [
                ("Sin asignar", "", "#555555"),
            ]:
                try:
                    cursor.execute("INSERT INTO usuarios (nombre, email, color) VALUES (?, ?, ?)", (nombre, email, color))
                except Exception:
                    pass

        # -----------------------------------------------------------
        # TABLA DE NOTAS
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id)
                    REFERENCES tickets (id)
                    ON DELETE CASCADE
            )
        ''')

        # -----------------------------------------------------------
        # TABLA DE HISTORIAL / AUDITORÍA
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                estado_anterior TEXT,
                estado_nuevo TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario TEXT DEFAULT 'Sistema',
                FOREIGN KEY (ticket_id)
                    REFERENCES tickets (id)
                    ON DELETE CASCADE
            )
        ''')

        # -----------------------------------------------------------
        # TABLA DE ADJUNTOS
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adjuntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                nombre_archivo TEXT NOT NULL,
                ruta TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id)
                    REFERENCES tickets (id)
                    ON DELETE CASCADE
            )
        ''')

        # -----------------------------------------------------------
        # TABLA DE AGENDA
        # -----------------------------------------------------------

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT,
                descripcion TEXT,
                tipo TEXT NOT NULL,
                prioridad TEXT NOT NULL,
                completada INTEGER DEFAULT 0,
                ticket_id INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id)
                    REFERENCES tickets (id)
                    ON DELETE SET NULL
            )
        ''')

        # Inicializar posicion para tickets sin posicion
        cursor.execute("UPDATE tickets SET posicion = id WHERE posicion IS NULL OR posicion = 0")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ===================================================================
# TICKETS
# ===================================================================

def crear_ticket(cliente, canal, contacto, titulo, descripcion, prioridad, responsable="Sin asignar", fecha_limite=None, tiempo_estimado=None):
    conn = conectar()

    try:
        cursor = conn.cursor()

        # posicion = max + 1
        cursor.execute("SELECT COALESCE(MAX(posicion), 0) + 1 FROM tickets")
        pos = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO tickets (
                cliente,
                canal,
                contacto,
                titulo,
                descripcion,
                prioridad,
                estado,
                responsable,
                fecha_limite,
                posicion,
                tiempo_estimado
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Recibida', ?, ?, ?, ?)
        ''', (
            cliente,
            canal,
            contacto,
            titulo,
            descripcion,
            prioridad,
            responsable,
            fecha_limite,
            pos,
            tiempo_estimado
        ))

        ticket_id = cursor.lastrowid

        # historial inicial
        cursor.execute("INSERT INTO historial (ticket_id, estado_anterior, estado_nuevo, usuario) VALUES (?, ?, ?, ?)",
                       (ticket_id, None, "Recibida", "Sistema"))

        conn.commit()
        return ticket_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_tickets(filtro_texto=None, filtro_prioridad=None, filtro_estado=None, filtro_responsable=None):
    conn = conectar()

    try:
        cursor = conn.cursor()

        query = '''
            SELECT
                id,
                cliente,
                canal,
                contacto,
                titulo,
                descripcion,
                prioridad,
                estado,
                fecha_creacion,
                responsable,
                fecha_limite,
                posicion,
                tiempo_estimado
            FROM tickets
            WHERE 1=1
        '''
        params = []
        if filtro_texto:
            query += " AND (cliente LIKE ? OR titulo LIKE ? OR descripcion LIKE ?)"
            like = f"%{filtro_texto}%"
            params.extend([like, like, like])
        if filtro_prioridad and filtro_prioridad != "Todas":
            query += " AND prioridad = ?"
            params.append(filtro_prioridad)
        if filtro_estado and filtro_estado != "Todos":
            query += " AND estado = ?"
            params.append(filtro_estado)
        if filtro_responsable and filtro_responsable != "Todos":
            query += " AND responsable = ?"
            params.append(filtro_responsable)

        query += " ORDER BY posicion ASC, id DESC"

        cursor.execute(query, params)
        return cursor.fetchall()

    finally:
        conn.close()


def obtener_ticket(ticket_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, cliente, canal, contacto, titulo, descripcion, prioridad, estado, fecha_creacion, responsable, fecha_limite, posicion, tiempo_estimado
            FROM tickets WHERE id = ?
        ''', (ticket_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def actualizar_ticket(ticket_id, cliente, canal, contacto, titulo, descripcion, prioridad, responsable=None, fecha_limite=None, tiempo_estimado=None):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tickets SET cliente=?, canal=?, contacto=?, titulo=?, descripcion=?, prioridad=?, responsable=COALESCE(?, responsable), fecha_limite=?, tiempo_estimado=?
            WHERE id=?
        ''', (cliente, canal, contacto, titulo, descripcion, prioridad, responsable, fecha_limite, tiempo_estimado, ticket_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def actualizar_estado(ticket_id, nuevo_estado, usuario="Sistema"):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT estado FROM tickets WHERE id=?", (ticket_id,))
        row = cursor.fetchone()
        estado_ant = row[0] if row else None

        cursor.execute('''
            UPDATE tickets
            SET estado = ?
            WHERE id = ?
        ''', (nuevo_estado, ticket_id))

        if estado_ant != nuevo_estado:
            cursor.execute("INSERT INTO historial (ticket_id, estado_anterior, estado_nuevo, usuario) VALUES (?, ?, ?, ?)",
                           (ticket_id, estado_ant, nuevo_estado, usuario))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def actualizar_posicion(ticket_id, nueva_posicion):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET posicion=? WHERE id=?", (nueva_posicion, ticket_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reordenar_tickets(estado, orden_ids):
    """Reordena tickets dentro de un estado según lista de ids."""
    conn = conectar()
    try:
        cursor = conn.cursor()
        for idx, tid in enumerate(orden_ids):
            cursor.execute("UPDATE tickets SET posicion=? WHERE id=? AND estado=?", (idx, tid, estado))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_ticket(ticket_id):
    conn = conectar()

    try:
        cursor = conn.cursor()

        # Las notas se eliminan automáticamente mediante
        # ON DELETE CASCADE.
        #
        # Las tareas de agenda relacionadas conservan su registro
        # pero ticket_id pasa a NULL mediante ON DELETE SET NULL.
        cursor.execute('''
            DELETE FROM tickets
            WHERE id = ?
        ''', (ticket_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_estadisticas():
    conn = conectar()
    try:
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM tickets")
        stats["total"] = cursor.fetchone()[0]
        cursor.execute("SELECT estado, COUNT(*) FROM tickets GROUP BY estado")
        stats["por_estado"] = dict(cursor.fetchall())
        cursor.execute("SELECT prioridad, COUNT(*) FROM tickets GROUP BY prioridad")
        stats["por_prioridad"] = dict(cursor.fetchall())
        cursor.execute("SELECT responsable, COUNT(*) FROM tickets GROUP BY responsable")
        stats["por_responsable"] = dict(cursor.fetchall())
        # urgentes pendientes (no finalizadas)
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE prioridad='Urgente' AND estado!='Finalizada'")
        stats["urgentes_pendientes"] = cursor.fetchone()[0]
        # vencidos
        hoy = date.today().isoformat()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE fecha_limite IS NOT NULL AND fecha_limite < ? AND estado!='Finalizada'", (hoy,))
        stats["vencidos"] = cursor.fetchone()[0]
        # promedio dias en En Análisis (aprox)
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE estado='En Análisis'")
        stats["en_analisis"] = cursor.fetchone()[0]
        return stats
    finally:
        conn.close()


# ===================================================================
# USUARIOS
# ===================================================================

def obtener_usuarios(solo_activos=True):
    conn = conectar()
    try:
        cursor = conn.cursor()
        if solo_activos:
            cursor.execute("SELECT id, nombre, email, color, activo FROM usuarios WHERE activo=1 ORDER BY nombre")
        else:
            cursor.execute("SELECT id, nombre, email, color, activo FROM usuarios ORDER BY nombre")
        return cursor.fetchall()
    finally:
        conn.close()


def crear_usuario(nombre, email="", color="#1f6aa5"):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nombre, email, color) VALUES (?, ?, ?)", (nombre, email, color))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_usuario(usuario_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_nombres_usuarios():
    rows = obtener_usuarios()
    return [r[1] for r in rows]


# ===================================================================
# HISTORIAL
# ===================================================================

def obtener_historial(ticket_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, estado_anterior, estado_nuevo, fecha, usuario FROM historial WHERE ticket_id=? ORDER BY fecha ASC", (ticket_id,))
        return cursor.fetchall()
    finally:
        conn.close()


def contar_historial(ticket_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM historial WHERE ticket_id=?", (ticket_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()


# ===================================================================
# ADJUNTOS
# ===================================================================

def crear_adjunto(ticket_id, nombre_archivo, ruta):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO adjuntos (ticket_id, nombre_archivo, ruta) VALUES (?, ?, ?)", (ticket_id, nombre_archivo, ruta))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_adjuntos(ticket_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_archivo, ruta, fecha FROM adjuntos WHERE ticket_id=? ORDER BY fecha ASC", (ticket_id,))
        return cursor.fetchall()
    finally:
        conn.close()


def contar_adjuntos(ticket_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM adjuntos WHERE ticket_id=?", (ticket_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()


def eliminar_adjunto(adjunto_id):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ruta FROM adjuntos WHERE id=?", (adjunto_id,))
        row = cursor.fetchone()
        if row and row[0] and os.path.exists(row[0]):
            try:
                os.remove(row[0])
            except Exception:
                pass
        cursor.execute("DELETE FROM adjuntos WHERE id=?", (adjunto_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ===================================================================
# NOTAS / ANOTACIONES
# ===================================================================

def crear_nota(ticket_id, texto):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO notas (
                ticket_id,
                texto
            )
            VALUES (?, ?)
        ''', (ticket_id, texto))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_notas(ticket_id):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                id,
                texto,
                fecha
            FROM notas
            WHERE ticket_id = ?
            ORDER BY fecha ASC
        ''', (ticket_id,))

        return cursor.fetchall()

    finally:
        conn.close()


def contar_notas(ticket_id):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*)
            FROM notas
            WHERE ticket_id = ?
        ''', (ticket_id,))

        return cursor.fetchone()[0]

    finally:
        conn.close()


def eliminar_nota(nota_id):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM notas
            WHERE id = ?
        ''', (nota_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ===================================================================
# AGENDA / CALENDARIO
# ===================================================================

def crear_evento(titulo, fecha, hora, descripcion, tipo, prioridad, ticket_id=None):
    """
    Crea una nueva tarea, cita o evento en la agenda.

    fecha: formato YYYY-MM-DD
    hora: formato HH:MM o None
    tipo: Tarea, Cita, Llamada, Reunión, etc.
    prioridad: Baja, Media, Alta, Urgente
    ticket_id: opcional
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO agenda (
                titulo,
                fecha,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        ''', (
            titulo,
            fecha,
            hora,
            descripcion,
            tipo,
            prioridad,
            ticket_id
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_eventos_fecha(fecha):
    """
    Obtiene todos los eventos de una fecha concreta.

    fecha: formato YYYY-MM-DD
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                id,
                titulo,
                fecha,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id,
                fecha_creacion
            FROM agenda
            WHERE fecha = ?
            ORDER BY
                CASE
                    WHEN hora IS NULL OR hora = '' THEN 1
                    ELSE 0
                END,
                hora ASC,
                id ASC
        ''', (fecha,))

        return cursor.fetchall()

    finally:
        conn.close()


def obtener_eventos_mes(fecha_inicio, fecha_fin):
    """
    Obtiene los eventos comprendidos entre dos fechas.

    fecha_inicio y fecha_fin: formato YYYY-MM-DD
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                id,
                titulo,
                fecha,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id,
                fecha_creacion
            FROM agenda
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha ASC, hora ASC, id ASC
        ''', (fecha_inicio, fecha_fin))

        return cursor.fetchall()

    finally:
        conn.close()


def obtener_evento(evento_id):
    """
    Obtiene un evento concreto por su ID.
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                id,
                titulo,
                fecha,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id,
                fecha_creacion
            FROM agenda
            WHERE id = ?
        ''', (evento_id,))

        return cursor.fetchone()

    finally:
        conn.close()


def actualizar_evento(
    evento_id,
    titulo,
    fecha,
    hora,
    descripcion,
    tipo,
    prioridad,
    ticket_id=None
):
    """
    Modifica un evento existente.
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE agenda
            SET
                titulo = ?,
                fecha = ?,
                hora = ?,
                descripcion = ?,
                tipo = ?,
                prioridad = ?,
                ticket_id = ?
            WHERE id = ?
        ''', (
            titulo,
            fecha,
            hora,
            descripcion,
            tipo,
            prioridad,
            ticket_id,
            evento_id
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def marcar_evento_completado(evento_id, completada=True):
    """
    Marca una tarea/evento como completado o pendiente.

    completada:
        True  -> completada
        False -> pendiente
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE agenda
            SET completada = ?
            WHERE id = ?
        ''', (
            1 if completada else 0,
            evento_id
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def eliminar_evento(evento_id):
    """
    Elimina un evento de la agenda.
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM agenda
            WHERE id = ?
        ''', (evento_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def contar_eventos_fecha(fecha):
    """
    Devuelve el número de eventos de una fecha.
    """
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*)
            FROM agenda
            WHERE fecha = ?
        ''', (fecha,))

        return cursor.fetchone()[0]

    finally:
        conn.close()


def obtener_fechas_con_eventos(solo_pendientes=False):
    """
    Devuelve dict {fecha_str: {'total': int, 'pendientes': int, 'tiene_urgente': bool}}
    para todas las fechas que tienen al menos un evento.
    Útil para pintar el calendario.
    """
    conn = conectar()
    try:
        cursor = conn.cursor()
        if solo_pendientes:
            cursor.execute('''
                SELECT fecha, COUNT(*), SUM(CASE WHEN completada=0 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN prioridad='Urgente' AND completada=0 THEN 1 ELSE 0 END)
                FROM agenda GROUP BY fecha HAVING SUM(CASE WHEN completada=0 THEN 1 ELSE 0 END) > 0
            ''')
        else:
            cursor.execute('''
                SELECT fecha, COUNT(*), SUM(CASE WHEN completada=0 THEN 1 ELSE 0 END),
                       SUM(CASE WHEN prioridad='Urgente' AND completada=0 THEN 1 ELSE 0 END)
                FROM agenda GROUP BY fecha
            ''')
        result = {}
        for fecha, total, pendientes, urgentes in cursor.fetchall():
            result[fecha] = {
                'total': total,
                'pendientes': pendientes or 0,
                'tiene_urgente': bool(urgentes),
            }
        return result
    finally:
        conn.close()


def obtener_eventos_pendientes(desde_fecha=None):
    """
    Devuelve eventos no completados desde una fecha (por defecto hoy) ordenados.
    Cada fila: id, titulo, fecha, hora, descripcion, tipo, prioridad, completada, ticket_id, fecha_creacion
    """
    if desde_fecha is None:
        desde_fecha = date.today().isoformat()
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, titulo, fecha, hora, descripcion, tipo, prioridad, completada, ticket_id, fecha_creacion
            FROM agenda
            WHERE completada = 0 AND fecha >= ?
            ORDER BY fecha ASC, CASE WHEN hora IS NULL OR hora='' THEN 1 ELSE 0 END, hora ASC
        ''', (desde_fecha,))
        return cursor.fetchall()
    finally:
        conn.close()


def obtener_eventos_proximos(minutos=60, incluir_vencidos_min=30):
    """
    Devuelve eventos cuya hora está dentro de la ventana:
      - próximos en los siguientes `minutos`
      - o vencidos hace menos de `incluir_vencidos_min` minutos
    Solo considera eventos de hoy con hora definida y no completados.
    """
    hoy = date.today().isoformat()
    ahora = datetime.now()
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, titulo, fecha, hora, descripcion, tipo, prioridad, completada, ticket_id, fecha_creacion
            FROM agenda
            WHERE fecha = ? AND completada = 0 AND hora IS NOT NULL AND hora != ''
            ORDER BY hora ASC
        ''', (hoy,))
        filas = cursor.fetchall()
        proximos = []
        for row in filas:
            _, _, _, hora, *_ = row
            try:
                # soporta HH:MM y HH:MM:SS
                for fmt in ("%H:%M", "%H:%M:%S"):
                    try:
                        t = datetime.strptime(hora, fmt).time()
                        break
                    except ValueError:
                        continue
                else:
                    continue
                evento_dt = datetime.combine(ahora.date(), t)
                delta_min = (evento_dt - ahora).total_seconds() / 60
                # ventana: -incluir_vencidos_min .. minutos
                if -incluir_vencidos_min <= delta_min <= minutos:
                    proximos.append((row, delta_min, evento_dt))
            except Exception:
                continue
        # ordenar por cercanía (negativos primero = ya vencidos)
        proximos.sort(key=lambda x: x[1])
        return proximos
    finally:
        conn.close()
