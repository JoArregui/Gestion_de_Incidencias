import sqlite3

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

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ===================================================================
# TICKETS
# ===================================================================

def crear_ticket(cliente, canal, contacto, titulo, descripcion, prioridad):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tickets (
                cliente,
                canal,
                contacto,
                titulo,
                descripcion,
                prioridad,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Recibida')
        ''', (
            cliente,
            canal,
            contacto,
            titulo,
            descripcion,
            prioridad
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def obtener_tickets():
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                id,
                cliente,
                canal,
                contacto,
                titulo,
                descripcion,
                prioridad,
                estado,
                fecha_creacion
            FROM tickets
            ORDER BY id DESC
        ''')

        return cursor.fetchall()

    finally:
        conn.close()


def actualizar_estado(ticket_id, nuevo_estado):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tickets
            SET estado = ?
            WHERE id = ?
        ''', (nuevo_estado, ticket_id))

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