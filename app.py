import customtkinter as ctk
import database
from tkcalendar import Calendar
from tkinter import messagebox, filedialog
import os
import shutil
import csv
from datetime import datetime, date, timedelta
import webbrowser
import platform

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ESTADOS = ["Recibida", "En Análisis", "En Proceso", "Pendiente Cliente", "Finalizada"]

PRIORIDAD_COLORES = {
    "Baja": "#7f8c8d",
    "Media": "#3498db",
    "Alta": "#e67e22",
    "Urgente": "#e74c3c",
}

WIP_LIMITS = {
    "Recibida": 20,
    "En Análisis": 3,
    "En Proceso": 5,
    "Pendiente Cliente": 8,
    "Finalizada": 30,
}

# Semáforo SLA helpers
def get_semaforo(fecha_limite, estado):
    if not fecha_limite or estado == "Finalizada":
        return None, ""
    try:
        limite = datetime.strptime(fecha_limite, "%Y-%m-%d").date()
        hoy = date.today()
        dias = (limite - hoy).days
        if dias < 0:
            return "🔴", f"Vencido hace {-dias}d"
        elif dias == 0:
            return "🟡", "Vence hoy"
        elif dias == 1:
            return "🟠", "Vence mañana"
        elif dias <= 3:
            return "🟡", f"{dias}d restantes"
        else:
            return "🟢", f"{dias}d"
    except Exception:
        return None, ""


# ===============================================================
# VENTANA NOTAS + HISTORIAL + ADJUNTOS
# ===============================================================

class VentanaNotas(ctk.CTkToplevel):
    """Ventana emergente para ver y añadir notas/respuestas de un ticket, historial y adjuntos."""

    def __init__(self, master, ticket_id, titulo_ticket, on_close=None):
        super().__init__(master)
        self.ticket_id = ticket_id
        self.on_close = on_close

        self.title(f"Ticket #{ticket_id} - {titulo_ticket}")
        self.geometry("620x650")
        self.transient(master)

        lbl_titulo = ctk.CTkLabel(
            self, text=titulo_ticket, font=ctk.CTkFont(size=16, weight="bold"), wraplength=550
        )
        lbl_titulo.pack(padx=15, pady=(15, 5), anchor="w")

        # Info ticket
        self.lbl_info = ctk.CTkLabel(self, text="", text_color="gray", wraplength=580, justify="left")
        self.lbl_info.pack(padx=15, pady=2, anchor="w")
        self._cargar_info_ticket()

        # Tabs
        self.tabview = ctk.CTkTabview(self, height=460)
        self.tabview.pack(padx=15, pady=5, fill="both", expand=True)
        self.tabview.add("Notas")
        self.tabview.add("Historial")
        self.tabview.add("Adjuntos")

        # --- TAB NOTAS ---
        self.frame_notas = ctk.CTkScrollableFrame(self.tabview.tab("Notas"), label_text="Historial de notas")
        self.frame_notas.pack(padx=5, pady=5, fill="both", expand=True)
        frame_nueva = ctk.CTkFrame(self.tabview.tab("Notas"), fg_color="transparent")
        frame_nueva.pack(padx=5, pady=(5, 5), fill="x")
        self.txt_nueva_nota = ctk.CTkTextbox(frame_nueva, height=60)
        self.txt_nueva_nota.pack(fill="x", pady=(0, 8))
        btn_agregar = ctk.CTkButton(frame_nueva, text="Añadir nota", command=self.agregar_nota)
        btn_agregar.pack(fill="x")

        # --- TAB HISTORIAL ---
        self.frame_historial = ctk.CTkScrollableFrame(self.tabview.tab("Historial"), label_text="Auditoría")
        self.frame_historial.pack(padx=5, pady=5, fill="both", expand=True)

        # --- TAB ADJUNTOS ---
        self.frame_adjuntos = ctk.CTkScrollableFrame(self.tabview.tab("Adjuntos"), label_text="Archivos adjuntos")
        self.frame_adjuntos.pack(padx=5, pady=5, fill="both", expand=True)
        btn_adj = ctk.CTkButton(self.tabview.tab("Adjuntos"), text="📎 Adjuntar archivo", command=self.adjuntar_archivo)
        btn_adj.pack(padx=5, pady=5, fill="x")

        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.cargar_notas()
        self.cargar_historial()
        self.cargar_adjuntos()
        self.bind("<Visibility>", self._al_visibilizar)

    def _cargar_info_ticket(self):
        try:
            t = database.obtener_ticket(self.ticket_id)
            if t:
                _, cliente, _, _, titulo, _, prioridad, estado, fecha, responsable, fecha_limite, _, tiempo = t
                sem, txt = get_semaforo(fecha_limite, estado)
                sem_txt = f" {sem} {txt}" if sem else ""
                info = f"Cliente: {cliente}  |  Prioridad: {prioridad}  |  Estado: {estado}  |  Resp: {responsable or '—'}{sem_txt}"
                if fecha_limite:
                    info += f"  |  Límite: {fecha_limite}"
                self.lbl_info.configure(text=info)
        except Exception:
            pass

    def _al_visibilizar(self, event=None):
        self.unbind("<Visibility>")
        self.lift()
        self.attributes("-topmost", True)
        self.attributes("-topmost", False)
        self.txt_nueva_nota.focus_set()

    def cargar_notas(self):
        for child in self.frame_notas.winfo_children():
            child.destroy()
        notas = database.obtener_notas(self.ticket_id)
        if not notas:
            ctk.CTkLabel(self.frame_notas, text="Sin notas todavía.", text_color="gray").pack(padx=5, pady=10)
            return
        for nota_id, texto, fecha in notas:
            item = ctk.CTkFrame(self.frame_notas, corner_radius=8, border_width=1, border_color="#3a3a3a")
            item.pack(padx=5, pady=5, fill="x")
            top = ctk.CTkFrame(item, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(6, 0))
            ctk.CTkLabel(top, text=fecha, font=ctk.CTkFont(size=10), text_color="gray").pack(side="left")
            ctk.CTkButton(top, text="🗑", width=30, height=18, fg_color="transparent", text_color="red", hover_color="#3a1111",
                          command=lambda nid=nota_id: self._eliminar_nota(nid)).pack(side="right")
            ctk.CTkLabel(item, text=texto, wraplength=480, justify="left", anchor="w").pack(anchor="w", padx=8, pady=(2, 6), fill="x")

    def _eliminar_nota(self, nota_id):
        if not messagebox.askyesno("Eliminar", "¿Eliminar esta nota?"):
            return
        database.eliminar_nota(nota_id)
        self.cargar_notas()
        if self.on_close:
            self.on_close()

    def agregar_nota(self):
        texto = self.txt_nueva_nota.get("0.0", "end").strip()
        if not texto:
            messagebox.showwarning("Nota vacía", "Escribe una nota antes de pulsar «Añadir nota».")
            self.txt_nueva_nota.focus_set()
            return
        try:
            database.crear_nota(self.ticket_id, texto)
            self.txt_nueva_nota.delete("0.0", "end")
            self.cargar_notas()
            if self.on_close:
                self.on_close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la nota:\n\n{e}")

    def cargar_historial(self):
        for child in self.frame_historial.winfo_children():
            child.destroy()
        hist = database.obtener_historial(self.ticket_id)
        if not hist:
            ctk.CTkLabel(self.frame_historial, text="Sin movimientos aún.", text_color="gray").pack(padx=5, pady=10)
            return
        for hid, ant, nuevo, fecha, usuario in hist:
            item = ctk.CTkFrame(self.frame_historial, corner_radius=8, border_width=1, border_color="#3a3a3a")
            item.pack(padx=5, pady=4, fill="x")
            ctk.CTkLabel(item, text=fecha, font=ctk.CTkFont(size=9), text_color="gray").pack(anchor="w", padx=8, pady=(6, 0))
            ant_txt = ant if ant else "—"
            ctk.CTkLabel(item, text=f"{ant_txt}  →  {nuevo}", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(anchor="w", padx=8)
            ctk.CTkLabel(item, text=f"por {usuario}", font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", padx=8, pady=(0, 6))

    def cargar_adjuntos(self):
        for child in self.frame_adjuntos.winfo_children():
            child.destroy()
        adj = database.obtener_adjuntos(self.ticket_id)
        if not adj:
            ctk.CTkLabel(self.frame_adjuntos, text="Sin adjuntos.", text_color="gray").pack(padx=5, pady=10)
            return
        for aid, nombre, ruta, fecha in adj:
            item = ctk.CTkFrame(self.frame_adjuntos, corner_radius=8, border_width=1, border_color="#3a3a3a")
            item.pack(padx=5, pady=4, fill="x")
            ctk.CTkLabel(item, text=nombre, font=ctk.CTkFont(size=11, weight="bold"), anchor="w", wraplength=380).pack(side="left", padx=8, pady=8)
            ctk.CTkButton(item, text="Abrir", width=50, height=24, command=lambda r=ruta: self._abrir_adjunto(r)).pack(side="right", padx=2)
            ctk.CTkButton(item, text="X", width=30, height=24, fg_color="#4a1111", hover_color="#6a1111", command=lambda aid=aid: self._eliminar_adjunto(aid)).pack(side="right", padx=2)

    def _abrir_adjunto(self, ruta):
        try:
            if os.path.exists(ruta):
                webbrowser.open(f"file://{os.path.abspath(ruta)}")
                os.startfile(ruta)
            else:
                messagebox.showerror("Error", "Archivo no encontrado.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _eliminar_adjunto(self, adj_id):
        if not messagebox.askyesno("Eliminar", "¿Eliminar adjunto?"):
            return
        database.eliminar_adjunto(adj_id)
        self.cargar_adjuntos()

    def adjuntar_archivo(self):
        ruta = filedialog.askopenfilename(title="Seleccionar archivo")
        if not ruta:
            return
        try:
            os.makedirs("adjuntos", exist_ok=True)
            nombre = os.path.basename(ruta)
            dest = os.path.join("adjuntos", f"{self.ticket_id}_{nombre}")
            # evitar colisión
            base, ext = os.path.splitext(dest)
            i = 1
            while os.path.exists(dest):
                dest = f"{base}_{i}{ext}"
                i += 1
            shutil.copy2(ruta, dest)
            database.crear_adjunto(self.ticket_id, nombre, dest)
            self.cargar_adjuntos()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _cerrar(self):
        if self.on_close:
            self.on_close()
        self.destroy()


class VentanaEditarTicket(ctk.CTkToplevel):
    def __init__(self, master, ticket_id, on_save=None):
        super().__init__(master)
        self.ticket_id = ticket_id
        self.on_save = on_save
        t = database.obtener_ticket(ticket_id)
        if not t:
            messagebox.showerror("Error", "Ticket no encontrado")
            self.destroy()
            return
        _, cliente, canal, contacto, titulo, descripcion, prioridad, estado, fecha, responsable, fecha_limite, posicion, tiempo = t
        self.title(f"Editar Ticket #{ticket_id}")
        self.geometry("520x650")
        self.transient(master)
        lbl = ctk.CTkLabel(self, text=f"Editar Ticket #{ticket_id}", font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(padx=20, pady=15)
        self.entry_cliente = ctk.CTkEntry(self, placeholder_text="Cliente / Empresa")
        self.entry_cliente.pack(padx=20, pady=5, fill="x")
        self.entry_cliente.insert(0, cliente)
        self.combo_canal = ctk.CTkOptionMenu(self, values=["Llamada", "Correo electrónico", "Presencial", "Chat"])
        self.combo_canal.pack(padx=20, pady=5, fill="x")
        self.combo_canal.set(canal)
        self.entry_contacto = ctk.CTkEntry(self, placeholder_text="Teléfono / Email")
        self.entry_contacto.pack(padx=20, pady=5, fill="x")
        self.entry_contacto.insert(0, contacto or "")
        self.entry_titulo = ctk.CTkEntry(self, placeholder_text="Título / Asunto")
        self.entry_titulo.pack(padx=20, pady=5, fill="x")
        self.entry_titulo.insert(0, titulo)
        self.txt_desc = ctk.CTkTextbox(self, height=100)
        self.txt_desc.pack(padx=20, pady=5, fill="x")
        self.txt_desc.insert("0.0", descripcion or "")
        self.combo_prioridad = ctk.CTkOptionMenu(self, values=["Baja", "Media", "Alta", "Urgente"])
        self.combo_prioridad.pack(padx=20, pady=5, fill="x")
        self.combo_prioridad.set(prioridad)
        # Responsable
        usuarios = database.obtener_nombres_usuarios()
        self.combo_resp = ctk.CTkOptionMenu(self, values=usuarios)
        self.combo_resp.pack(padx=20, pady=5, fill="x")
        if responsable and responsable in usuarios:
            self.combo_resp.set(responsable)
        # Fecha límite
        ctk.CTkLabel(self, text="Fecha límite (YYYY-MM-DD) - opcional", text_color="gray").pack(padx=20, pady=(8, 0), anchor="w")
        self.entry_limite = ctk.CTkEntry(self, placeholder_text="2026-12-31")
        self.entry_limite.pack(padx=20, pady=5, fill="x")
        if fecha_limite:
            self.entry_limite.insert(0, fecha_limite)
        self.entry_tiempo = ctk.CTkEntry(self, placeholder_text="Tiempo estimado (ej: 2h, 1d)")
        self.entry_tiempo.pack(padx=20, pady=5, fill="x")
        if tiempo:
            self.entry_tiempo.insert(0, tiempo)
        self.combo_estado = ctk.CTkOptionMenu(self, values=ESTADOS)
        self.combo_estado.pack(padx=20, pady=5, fill="x")
        self.combo_estado.set(estado)
        btn = ctk.CTkButton(self, text="Guardar cambios", fg_color="green", hover_color="darkgreen", command=self.guardar)
        btn.pack(padx=20, pady=15, fill="x")
        ctk.CTkButton(self, text="Cancelar", fg_color="transparent", border_width=1, command=self.destroy).pack(padx=20, fill="x")

    def guardar(self):
        cliente = self.entry_cliente.get().strip()
        titulo = self.entry_titulo.get().strip()
        if not cliente or not titulo:
            messagebox.showwarning("Faltan datos", "Cliente y título son obligatorios")
            return
        fecha_limite = self.entry_limite.get().strip() or None
        if fecha_limite:
            try:
                datetime.strptime(fecha_limite, "%Y-%m-%d")
            except Exception:
                messagebox.showwarning("Fecha inválida", "Usa formato YYYY-MM-DD")
                return
        try:
            database.actualizar_ticket(
                self.ticket_id,
                cliente,
                self.combo_canal.get(),
                self.entry_contacto.get().strip(),
                titulo,
                self.txt_desc.get("0.0", "end").strip(),
                self.combo_prioridad.get(),
                responsable=self.combo_resp.get(),
                fecha_limite=fecha_limite,
                tiempo_estimado=self.entry_tiempo.get().strip() or None
            )
            # si cambió estado, registrar historial
            t = database.obtener_ticket(self.ticket_id)
            if t and t[7] != self.combo_estado.get():
                database.actualizar_estado(self.ticket_id, self.combo_estado.get())
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class VentanaUsuarios(ctk.CTkToplevel):
    def __init__(self, master, on_close=None):
        super().__init__(master)
        self.on_close = on_close
        self.title("Gestión de usuarios")
        self.geometry("450x500")
        self.transient(master)
        ctk.CTkLabel(self, text="Usuarios / Responsables", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=15, pady=15)
        self.frame_lista = ctk.CTkScrollableFrame(self, label_text="Listado")
        self.frame_lista.pack(padx=15, pady=5, fill="both", expand=True)
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(padx=15, pady=10, fill="x")
        self.entry_nombre = ctk.CTkEntry(frm, placeholder_text="Nombre")
        self.entry_nombre.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_email = ctk.CTkEntry(frm, placeholder_text="Email")
        self.entry_email.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(frm, text="+", width=40, command=self.crear).pack(side="right", padx=(5, 0))
        self.cargar()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def cargar(self):
        for c in self.frame_lista.winfo_children():
            c.destroy()
        for uid, nombre, email, color, activo in database.obtener_usuarios(solo_activos=False):
            row = ctk.CTkFrame(self.frame_lista, corner_radius=6, border_width=1, border_color="#3a3a3a")
            row.pack(fill="x", padx=5, pady=3)
            ctk.CTkLabel(row, text=nombre, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=email, text_color="gray", font=ctk.CTkFont(size=10)).pack(side="left")
            if nombre != "Sin asignar":
                ctk.CTkButton(row, text="X", width=30, height=22, fg_color="#4a1111", hover_color="#6a1111",
                              command=lambda uid=uid: self.eliminar(uid)).pack(side="right", padx=5)
        if self.on_close:
            self.on_close()

    def crear(self):
        nombre = self.entry_nombre.get().strip()
        email = self.entry_email.get().strip()
        if not nombre:
            messagebox.showwarning("Falta nombre", "Introduce un nombre")
            return
        try:
            database.crear_usuario(nombre, email)
            self.entry_nombre.delete(0, "end")
            self.entry_email.delete(0, "end")
            self.cargar()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar(self, uid):
        if not messagebox.askyesno("Eliminar", "¿Eliminar usuario?"):
            return
        database.eliminar_usuario(uid)
        self.cargar()

    def _cerrar(self):
        if self.on_close:
            self.on_close()
        self.destroy()


class VentanaPalette(ctk.CTkToplevel):
    """Paleta de comandos Ctrl+K"""
    def __init__(self, master, tickets):
        super().__init__(master)
        self.master_app = master
        self.tickets = tickets
        self.title("Búsqueda rápida - Ctrl+K")
        self.geometry("600x400")
        self.transient(master)
        ctk.CTkLabel(self, text="Escribe para filtrar (cliente, título, prioridad)", text_color="gray").pack(padx=15, pady=(15, 5), anchor="w")
        self.entry = ctk.CTkEntry(self, placeholder_text="Buscar ticket...")
        self.entry.pack(padx=15, pady=5, fill="x")
        self.entry.bind("<KeyRelease>", self.filtrar)
        self.entry.bind("<Return>", self.abrir_seleccionado)
        self.entry.bind("<Escape>", lambda e: self.destroy())
        self.lista = ctk.CTkScrollableFrame(self, label_text="Resultados")
        self.lista.pack(padx=15, pady=5, fill="both", expand=True)
        self.resultados = []
        self.filtrar()
        self.entry.focus_set()
        self.bind("<Visibility>", lambda e: self.lift())

    def filtrar(self, event=None):
        q = self.entry.get().lower().strip()
        for c in self.lista.winfo_children():
            c.destroy()
        self.resultados = []
        for t in self.tickets:
            tid, cliente, _, _, titulo, _, prioridad, estado, *_ = t
            texto = f"{cliente} {titulo} {prioridad} {estado}".lower()
            if not q or q in texto:
                self.resultados.append(t)
        for t in self.resultados[:30]:
            tid, cliente, _, _, titulo, _, prioridad, estado, *_ = t
            row = ctk.CTkFrame(self.lista, corner_radius=6, border_width=1, border_color="#3a3a3a")
            row.pack(fill="x", padx=5, pady=3)
            row.bind("<Button-1>", lambda e, tid=tid: self._ir(tid))
            ctk.CTkLabel(row, text=f"#{tid} [{prioridad}] {cliente}", font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=8, pady=(6, 0))
            lbl = ctk.CTkLabel(row, text=titulo, wraplength=500, anchor="w")
            lbl.pack(anchor="w", padx=8)
            ctk.CTkLabel(row, text=estado, text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(0, 6))
            for w in (row, lbl):
                w.bind("<Button-1>", lambda e, tid=tid: self._ir(tid))
        if not self.resultados:
            ctk.CTkLabel(self.lista, text="Sin resultados", text_color="gray").pack(pady=10)

    def _ir(self, tid):
        self.destroy()
        # resaltar tarjeta: buscar estado y hacer flash
        self.master_app.seleccionar_ticket(tid)

    def abrir_seleccionado(self, event=None):
        if self.resultados:
            self._ir(self.resultados[0][0])


class VentanaAgenda(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.title("Agenda")
        self.geometry("980x620")
        self.minsize(850, 540)

        self.transient(master)

        # -----------------------------------------------------------
        # CONFIGURACIÓN DE LA VENTANA
        # -----------------------------------------------------------

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------------------------------------
        # PANEL IZQUIERDO - CALENDARIO
        # -----------------------------------------------------------

        frame_calendario = ctk.CTkFrame(
            self,
            corner_radius=10
        )
        frame_calendario.grid(
            row=0,
            column=0,
            padx=(15, 7),
            pady=15,
            sticky="nsew"
        )

        lbl_calendario = ctk.CTkLabel(
            frame_calendario,
            text="Calendario",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        )
        lbl_calendario.pack(
            padx=15,
            pady=(15, 10)
        )

        self.calendario = Calendar(
            frame_calendario,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            background="#2b2b2b",
            foreground="white",
            headersbackground="#1f6aa5",
            headersforeground="white",
            selectbackground="#1f6aa5",
            selectforeground="white",
            normalbackground="#2b2b2b",
            normalforeground="white",
            weekendbackground="#252525",
            weekendforeground="#cccccc",
            othermonthbackground="#222222",
            othermonthforeground="#666666",
            bordercolor="#3a3a3a",
            font=("Arial", 11),
            headersfont=("Arial", 10, "bold")
        )

        self.calendario.pack(
            padx=15,
            pady=10
        )

        self.calendario.bind(
            "<<CalendarSelected>>",
            self.cambiar_dia
        )

        # Leyenda del calendario
        frame_leyenda = ctk.CTkFrame(frame_calendario, fg_color="transparent")
        frame_leyenda.pack(padx=15, pady=(4, 2), fill="x")
        ctk.CTkLabel(frame_leyenda, text="● Hoy", text_color="#1f6aa5", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(frame_leyenda, text="● Con eventos", text_color="#e67e22", font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
        ctk.CTkLabel(frame_leyenda, text="● Urgente", text_color="#e74c3c", font=ctk.CTkFont(size=11)).pack(side="left", padx=4)

        # Info contador + botón Ir a hoy
        self.lbl_cal_info = ctk.CTkLabel(frame_calendario, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_cal_info.pack(padx=15, pady=(6, 2))

        ctk.CTkButton(frame_calendario, text="⟳ Ir a hoy", height=28, fg_color="transparent", border_width=1,
                      command=self.ir_a_hoy).pack(padx=15, pady=(2, 6), fill="x")

        # Panel de próximo evento / alarma en la agenda
        self.frame_proximo = ctk.CTkFrame(frame_calendario, corner_radius=8, border_width=1, border_color="#3a3a3a")
        self.frame_proximo.pack(padx=15, pady=8, fill="x")
        ctk.CTkLabel(self.frame_proximo, text="⏰ Próximo aviso", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.lbl_proximo = ctk.CTkLabel(self.frame_proximo, text="Sin eventos próximos", text_color="gray", wraplength=300, justify="left")
        self.lbl_proximo.pack(anchor="w", padx=8, pady=(2, 6), fill="x")

        # Configurar marcas y resaltar hoy / días con eventos
        self._configurar_marcas_calendario()
        self._resaltar_fechas()

        # -----------------------------------------------------------
        # PANEL DERECHO - EVENTOS
        # -----------------------------------------------------------

        frame_eventos = ctk.CTkFrame(
            self,
            corner_radius=10
        )
        frame_eventos.grid(
            row=0,
            column=1,
            padx=(7, 15),
            pady=15,
            sticky="nsew"
        )

        frame_eventos.grid_columnconfigure(0, weight=1)
        frame_eventos.grid_rowconfigure(1, weight=1)

        self.lbl_fecha = ctk.CTkLabel(
            frame_eventos,
            text="Eventos del día",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        )
        self.lbl_fecha.grid(
            row=0,
            column=0,
            padx=15,
            pady=(15, 10),
            sticky="w"
        )

        self.frame_lista = ctk.CTkScrollableFrame(
            frame_eventos,
            label_text="Tareas y citas"
        )
        self.frame_lista.grid(
            row=1,
            column=0,
            padx=15,
            pady=5,
            sticky="nsew"
        )

        # -----------------------------------------------------------
        # BOTÓN NUEVO EVENTO
        # -----------------------------------------------------------

        btn_nuevo = ctk.CTkButton(
            frame_eventos,
            text="+ Nueva tarea / cita",
            height=40,
            command=self.nuevo_evento
        )
        btn_nuevo.grid(
            row=2,
            column=0,
            padx=15,
            pady=15,
            sticky="ew"
        )

        # Seleccionar hoy por defecto y cargar
        try:
            hoy = date.today()
            self.calendario.selection_set(hoy)
        except Exception:
            pass
        self.cambiar_dia()
        # Refrescar marcas periódicamente cada 60s (por si cambia el día)
        self._tick_proximo()
        # Refrescar marcas cuando cambia de mes (el Calendar recrea celdas)
        self.calendario.bind("<<CalendarMonthChanged>>", lambda e: self.after(100, self._resaltar_fechas))

    # ===============================================================
    # MARCAS DEL CALENDARIO: HOY + DÍAS CON EVENTOS
    # ===============================================================

    def _configurar_marcas_calendario(self):
        try:
            # Hoy en azul, evento pendiente en naranja, urgente en rojo, completado en gris
            self.calendario.tag_config('hoy', background='#1f6aa5', foreground='white')
            self.calendario.tag_config('evento', background='#e67e22', foreground='white')
            self.calendario.tag_config('urgente', background='#e74c3c', foreground='white')
            self.calendario.tag_config('hoy_evento', background='#1f6aa5', foreground='#ffcc00')
            self.calendario.tag_config('hoy_urgente', background='#e74c3c', foreground='white')
        except Exception:
            pass

    def _resaltar_fechas(self):
        """Marca el día de hoy y los días que tienen eventos programados."""
        try:
            # limpiar marcas previas
            for tag in ('hoy', 'evento', 'urgente', 'hoy_evento', 'hoy_urgente'):
                try:
                    self.calendario.calevent_remove(tag=tag)
                except Exception:
                    pass
        except Exception:
            pass

        hoy_str = date.today().isoformat()
        fechas = {}
        try:
            fechas = database.obtener_fechas_con_eventos()
        except Exception:
            fechas = {}

        # marcar hoy siempre
        try:
            hoy_date = date.today()
            # si hoy tiene eventos, usar tag combinado, si no 'hoy'
            info_hoy = fechas.get(hoy_str)
            if info_hoy and info_hoy.get('pendientes', 0) > 0:
                tag_hoy = 'hoy_urgente' if info_hoy.get('tiene_urgente') else 'hoy_evento'
                self.calendario.calevent_create(hoy_date, 'Hoy', tag_hoy)
            else:
                self.calendario.calevent_create(hoy_date, 'Hoy', 'hoy')
        except Exception:
            pass

        # marcar días con eventos (excluyendo hoy ya marcado)
        for fecha_str, info in fechas.items():
            if fecha_str == hoy_str:
                continue
            try:
                d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                pendientes = info.get('pendientes', 0)
                if pendientes == 0:
                    continue  # solo pendientes se resaltan
                tag = 'urgente' if info.get('tiene_urgente') else 'evento'
                tooltip = f"{pendientes} pendiente(s)"
                self.calendario.calevent_create(d, tooltip, tag)
            except Exception:
                continue

        # actualizar contador
        pendientes_total = sum(v.get('pendientes', 0) for v in fechas.values())
        hoy_pend = fechas.get(hoy_str, {}).get('pendientes', 0) if fechas else 0
        try:
            self.lbl_cal_info.configure(text=f"Hoy: {hoy_pend} pendiente(s)  •  Total: {pendientes_total} pendiente(s)")
        except Exception:
            pass

    def ir_a_hoy(self):
        try:
            hoy = date.today()
            self.calendario.selection_set(hoy)
            # asegurar que se vea el mes actual
            try:
                self.calendario._show_month(hoy.year, hoy.month)
            except Exception:
                pass
        except Exception:
            pass
        self._resaltar_fechas()
        self.cambiar_dia()

    def _tick_proximo(self):
        """Actualiza el panel 'Próximo aviso' cada 30s dentro de la Agenda."""
        try:
            proximos = database.obtener_eventos_proximos(minutos=120, incluir_vencidos_min=30)
            if not proximos:
                # buscar el siguiente pendiente aunque esté más lejos
                pendientes = database.obtener_eventos_pendientes()
                if pendientes:
                    # tomar el más cercano futuro con hora
                    ahora = datetime.now()
                    candidato = None
                    min_delta = None
                    for row in pendientes:
                        _, titulo, fecha, hora, *_ = row
                        if not hora:
                            continue
                        try:
                            for fmt in ("%H:%M", "%H:%M:%S"):
                                try:
                                    t = datetime.strptime(hora, fmt).time()
                                    break
                                except ValueError:
                                    continue
                            else:
                                continue
                            f = datetime.strptime(fecha, "%Y-%m-%d").date()
                            evento_dt = datetime.combine(f, t)
                            delta = (evento_dt - ahora).total_seconds() / 60
                            if delta >= 0 and (min_delta is None or delta < min_delta):
                                min_delta = delta
                                candidato = (row, delta, evento_dt)
                        except Exception:
                            continue
                    if candidato:
                        row, delta, edt = candidato
                        titulo = row[1]
                        hora = row[3]
                        if delta < 1440:
                            horas = int(delta // 60)
                            mins = int(delta % 60)
                            if horas > 0:
                                txt = f"{titulo}\n{row[2]} {hora}  •  en {horas}h {mins}min"
                            else:
                                txt = f"{titulo}\n{row[2]} {hora}  •  en {mins} min"
                        else:
                            dias = int(delta // 1440)
                            txt = f"{titulo}\n{row[2]} {hora}  •  en {dias} día(s)"
                        self.lbl_proximo.configure(text=txt, text_color="white")
                        self.frame_proximo.configure(border_color="#1f6aa5")
                    else:
                        self.lbl_proximo.configure(text="Sin eventos con hora próximos", text_color="gray")
                        self.frame_proximo.configure(border_color="#3a3a3a")
                else:
                    self.lbl_proximo.configure(text="Sin eventos pendientes", text_color="gray")
                    self.frame_proximo.configure(border_color="#3a3a3a")
            else:
                # hay al menos uno en ventana próxima (0-120min o vencido reciente)
                row, delta, edt = proximos[0]
                titulo, fecha, hora = row[1], row[2], row[3]
                prioridad = row[6]
                if delta < 0:
                    txt = f"⚠ ¡AHORA! {titulo}\n{fecha} {hora}  •  hace {int(-delta)} min"
                    self.lbl_proximo.configure(text=txt, text_color="#e74c3c")
                    self.frame_proximo.configure(border_color="#e74c3c")
                elif delta <= 5:
                    txt = f"🔔 En {int(delta)} min: {titulo}\n{fecha} {hora} [{prioridad}]"
                    self.lbl_proximo.configure(text=txt, text_color="#e74c3c")
                    self.frame_proximo.configure(border_color="#e74c3c")
                elif delta <= 15:
                    txt = f"⏰ En {int(delta)} min: {titulo}\n{fecha} {hora} [{prioridad}]"
                    self.lbl_proximo.configure(text=txt, text_color="#e67e22")
                    self.frame_proximo.configure(border_color="#e67e22")
                else:
                    txt = f"{titulo}\n{fecha} {hora}  •  en {int(delta)} min"
                    self.lbl_proximo.configure(text=txt, text_color="white")
                    self.frame_proximo.configure(border_color="#e67e22")
        except Exception:
            pass
        try:
            self.after(30000, self._tick_proximo)
        except Exception:
            pass

    # ===============================================================
    # CAMBIAR DE DÍA
    # ===============================================================

    def cambiar_dia(self, event=None):

        fecha = self.calendario.get_date()

        self.lbl_fecha.configure(
            text=f"Agenda - {fecha}"
        )

        self.cargar_eventos(fecha)

    # ===============================================================
    # CARGAR EVENTOS DEL DÍA
    # ===============================================================

    def cargar_eventos(self, fecha):

        # Limpiar la lista
        for child in self.frame_lista.winfo_children():
            child.destroy()

        eventos = database.obtener_eventos_fecha(fecha)

        if not eventos:
            lbl_vacio = ctk.CTkLabel(
                self.frame_lista,
                text="No hay tareas ni citas para este día.",
                text_color="gray"
            )
            lbl_vacio.pack(
                padx=10,
                pady=20
            )
            return

        for evento in eventos:

            (
                evento_id,
                titulo,
                fecha,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id,
                fecha_creacion
            ) = evento

            self.crear_tarjeta_evento(
                evento_id,
                titulo,
                hora,
                descripcion,
                tipo,
                prioridad,
                completada,
                ticket_id
            )

    # ===============================================================
    # TARJETA DE EVENTO
    # ===============================================================

    def crear_tarjeta_evento(
        self,
        evento_id,
        titulo,
        hora,
        descripcion,
        tipo,
        prioridad,
        completada,
        ticket_id
    ):

        # Detectar si el evento es inminente / vencido para resaltar
        border_color = "#3a3a3a"
        border_width = 1
        estado_hora = ""
        if not completada and hora:
            try:
                hoy_str = date.today().isoformat()
                if fecha == hoy_str:
                    for fmt in ("%H:%M", "%H:%M:%S"):
                        try:
                            t = datetime.strptime(hora, fmt).time()
                            break
                        except ValueError:
                            continue
                    else:
                        t = None
                    if t is not None:
                        evento_dt = datetime.combine(date.today(), t)
                        delta_min = (evento_dt - datetime.now()).total_seconds() / 60
                        if delta_min < 0 and delta_min >= -60:
                            border_color = "#e74c3c"
                            border_width = 2
                            estado_hora = f"  ⚠ VENCIDO hace {int(-delta_min)} min"
                        elif 0 <= delta_min <= 5:
                            border_color = "#e74c3c"
                            border_width = 2
                            estado_hora = f"  🔔 ¡AHORA! en {int(delta_min)} min"
                        elif 0 <= delta_min <= 15:
                            border_color = "#e67e22"
                            border_width = 2
                            estado_hora = f"  ⏰ en {int(delta_min)} min"
                        elif 0 <= delta_min <= 60:
                            border_color = "#e67e22"
                            estado_hora = f"  • en {int(delta_min)} min"
            except Exception:
                pass

        item = ctk.CTkFrame(
            self.frame_lista,
            corner_radius=8,
            border_width=border_width,
            border_color=border_color
        )
        item.pack(
            padx=5,
            pady=5,
            fill="x"
        )

        # -----------------------------------------------------------
        # HORA + TIPO
        # -----------------------------------------------------------

        hora_texto = hora if hora else "Sin hora"

        lbl_info = ctk.CTkLabel(
            item,
            text=f"{hora_texto}  •  {tipo}{estado_hora}",
            text_color="#e74c3c" if "VENCIDO" in estado_hora or "AHORA" in estado_hora else ("#e67e22" if "en" in estado_hora else "gray"),
            font=ctk.CTkFont(size=11, weight="bold" if estado_hora else "normal")
        )
        lbl_info.pack(
            anchor="w",
            padx=10,
            pady=(8, 0)
        )

        # -----------------------------------------------------------
        # TÍTULO
        # -----------------------------------------------------------

        texto_titulo = titulo

        if completada:
            texto_titulo = f"✓ {titulo}"

        lbl_titulo = ctk.CTkLabel(
            item,
            text=texto_titulo,
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            anchor="w",
            justify="left",
            wraplength=450
        )
        lbl_titulo.pack(
            anchor="w",
            padx=10,
            pady=3
        )

        # -----------------------------------------------------------
        # PRIORIDAD
        # -----------------------------------------------------------

        lbl_prioridad = ctk.CTkLabel(
            item,
            text=f"Prioridad: {prioridad}",
            text_color="gray"
        )
        lbl_prioridad.pack(
            anchor="w",
            padx=10
        )

        # -----------------------------------------------------------
        # DESCRIPCIÓN
        # -----------------------------------------------------------

        if descripcion:

            lbl_descripcion = ctk.CTkLabel(
                item,
                text=descripcion,
                text_color="gray",
                justify="left",
                anchor="w",
                wraplength=450
            )
            lbl_descripcion.pack(
                anchor="w",
                padx=10,
                pady=(3, 5)
            )

        # -----------------------------------------------------------
        # BOTONES
        # -----------------------------------------------------------

        frame_botones = ctk.CTkFrame(
            item,
            fg_color="transparent"
        )
        frame_botones.pack(
            padx=10,
            pady=(3, 8),
            fill="x"
        )

        if completada:

            btn_completar = ctk.CTkButton(
                frame_botones,
                text="Marcar pendiente",
                height=25,
                fg_color="#555555",
                command=lambda eid=evento_id:
                    self.marcar_completado(eid, False)
            )

        else:

            btn_completar = ctk.CTkButton(
                frame_botones,
                text="✓ Completar",
                height=25,
                command=lambda eid=evento_id:
                    self.marcar_completado(eid, True)
            )

        btn_completar.pack(
            side="left",
            padx=(0, 5)
        )

        btn_eliminar = ctk.CTkButton(
            frame_botones,
            text="Eliminar",
            height=25,
            fg_color="transparent",
            text_color="red",
            hover_color="#3a1111",
            command=lambda eid=evento_id:
                self.eliminar_evento(eid)
        )
        btn_eliminar.pack(
            side="right"
        )

    # ===============================================================
    # NUEVO EVENTO
    # ===============================================================

    def _on_evento_cambiado(self, fecha=None):
        try:
            f = fecha or self.calendario.get_date()
            self.cargar_eventos(f)
        except Exception:
            try:
                self.cargar_eventos(self.calendario.get_date())
            except Exception:
                pass
        self._resaltar_fechas()
        self._tick_proximo()

    def nuevo_evento(self):

        VentanaNuevoEvento(
            self,
            self.calendario.get_date(),
            self._on_evento_cambiado
        )

    # ===============================================================
    # COMPLETAR EVENTO
    # ===============================================================

    def marcar_completado(self, evento_id, completada):

        database.marcar_evento_completado(
            evento_id,
            completada
        )

        self._on_evento_cambiado()

    # ===============================================================
    # ELIMINAR EVENTO
    # ===============================================================

    def eliminar_evento(self, evento_id):

        confirmar = messagebox.askyesno(
            "Eliminar evento",
            "¿Seguro que quieres eliminar este evento?"
        )

        if not confirmar:
            return

        database.eliminar_evento(evento_id)

        self._on_evento_cambiado()

class VentanaNuevoEvento(ctk.CTkToplevel):

    def __init__(self, master, fecha, callback):
        super().__init__(master)

        self.fecha = fecha
        self.callback = callback

        self.title("Nueva tarea / cita")
        self.geometry("450x520")
        self.resizable(False, False)

        self.transient(master)

        # -----------------------------------------------------------
        # TÍTULO
        # -----------------------------------------------------------

        lbl_titulo = ctk.CTkLabel(
            self,
            text="Nueva tarea / cita",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        )
        lbl_titulo.pack(
            padx=20,
            pady=(20, 15)
        )

        # -----------------------------------------------------------
        # TÍTULO DEL EVENTO
        # -----------------------------------------------------------

        self.entry_titulo = ctk.CTkEntry(
            self,
            placeholder_text="Título"
        )
        self.entry_titulo.pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # -----------------------------------------------------------
        # FECHA
        # -----------------------------------------------------------

        self.entry_fecha = ctk.CTkEntry(
            self
        )
        self.entry_fecha.pack(
            padx=20,
            pady=5,
            fill="x"
        )

        self.entry_fecha.insert(
            0,
            fecha
        )

        # -----------------------------------------------------------
        # HORA
        # -----------------------------------------------------------

        self.entry_hora = ctk.CTkEntry(
            self,
            placeholder_text="Hora (HH:MM), opcional"
        )
        self.entry_hora.pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # -----------------------------------------------------------
        # TIPO
        # -----------------------------------------------------------

        self.combo_tipo = ctk.CTkOptionMenu(
            self,
            values=[
                "Tarea",
                "Cita",
                "Llamada",
                "Reunión",
                "Seguimiento",
                "Otro"
            ]
        )
        self.combo_tipo.pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # -----------------------------------------------------------
        # PRIORIDAD
        # -----------------------------------------------------------

        self.combo_prioridad = ctk.CTkOptionMenu(
            self,
            values=[
                "Baja",
                "Media",
                "Alta",
                "Urgente"
            ]
        )
        self.combo_prioridad.pack(
            padx=20,
            pady=5,
            fill="x"
        )

        # -----------------------------------------------------------
        # DESCRIPCIÓN
        # -----------------------------------------------------------

        self.txt_descripcion = ctk.CTkTextbox(
            self,
            height=120
        )
        self.txt_descripcion.pack(
            padx=20,
            pady=5,
            fill="both"
        )

        # -----------------------------------------------------------
        # GUARDAR
        # -----------------------------------------------------------

        btn_guardar = ctk.CTkButton(
            self,
            text="Guardar",
            height=40,
            command=self.guardar
        )
        btn_guardar.pack(
            padx=20,
            pady=15,
            fill="x"
        )

        self.entry_titulo.focus_set()

    # ===============================================================
    # GUARDAR EVENTO
    # ===============================================================

    def guardar(self):

        titulo = self.entry_titulo.get().strip()
        fecha = self.entry_fecha.get().strip()
        hora = self.entry_hora.get().strip()
        tipo = self.combo_tipo.get()
        prioridad = self.combo_prioridad.get()
        descripcion = self.txt_descripcion.get(
            "0.0",
            "end"
        ).strip()

        if not titulo:
            messagebox.showwarning(
                "Datos incompletos",
                "Introduce un título para la tarea o cita."
            )
            self.entry_titulo.focus_set()
            return

        if not fecha:
            messagebox.showwarning(
                "Datos incompletos",
                "Introduce una fecha."
            )
            return

        try:

            database.crear_evento(
                titulo=titulo,
                fecha=fecha,
                hora=hora,
                descripcion=descripcion,
                tipo=tipo,
                prioridad=prioridad
            )

            self.callback(fecha)

            self.destroy()

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo guardar el evento:\n\n{e}"
            )


class VentanaAlarma(ctk.CTkToplevel):
    """Popup de alarma para evento inminente. Topmost, sonido y acciones."""
    def __init__(self, master, evento_row, delta_min, evento_dt):
        super().__init__(master)
        self.evento_row = evento_row
        evento_id, titulo, fecha, hora, descripcion, tipo, prioridad, completada, ticket_id, _ = evento_row
        self.title("⏰ Alarma - Evento próximo")
        self.geometry("480x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(master)

        # Sonido
        self._sonar()

        if delta_min < 0:
            estado_txt = f"¡VENCIDO hace {int(-delta_min)} min!"
            color = "#e74c3c"
        elif delta_min <= 1:
            estado_txt = "¡AHORA MISMO!"
            color = "#e74c3c"
        elif delta_min <= 5:
            estado_txt = f"En {int(delta_min)} minutos"
            color = "#e74c3c"
        elif delta_min <= 15:
            estado_txt = f"En {int(delta_min)} minutos"
            color = "#e67e22"
        else:
            estado_txt = f"En {int(delta_min)} minutos"
            color = "#1f6aa5"

        ctk.CTkLabel(self, text="⏰  ALARMA", font=ctk.CTkFont(size=22, weight="bold"), text_color=color).pack(pady=(18, 4))
        ctk.CTkLabel(self, text=estado_txt, font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack()

        frame_info = ctk.CTkFrame(self, corner_radius=8, border_width=1, border_color=color)
        frame_info.pack(padx=18, pady=12, fill="both", expand=True)
        ctk.CTkLabel(frame_info, text=titulo, font=ctk.CTkFont(size=15, weight="bold"), wraplength=430, justify="center").pack(padx=10, pady=(12, 4))
        ctk.CTkLabel(frame_info, text=f"{fecha}  {hora}  •  {tipo}  •  Prioridad: {prioridad}", text_color="gray").pack()
        if descripcion:
            ctk.CTkLabel(frame_info, text=descripcion, text_color="gray", wraplength=430, justify="center").pack(padx=10, pady=6)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(padx=18, pady=(6, 14), fill="x")
        ctk.CTkButton(frame_btn, text="✓ Completar", fg_color="green", hover_color="darkgreen",
                      command=self._completar).pack(side="left", expand=True, padx=4, fill="x")
        ctk.CTkButton(frame_btn, text="Posponer 10 min", fg_color="#e67e22",
                      command=self._posponer).pack(side="left", expand=True, padx=4, fill="x")
        ctk.CTkButton(frame_btn, text="Cerrar", fg_color="transparent", border_width=1,
                      command=self.destroy).pack(side="left", expand=True, padx=4, fill="x")

        # Auto-cerrar en 2 min si no se interactúa, pero sigue topmost
        self.after(120000, self._auto_cerrar)
        self.bind("<Visibility>", lambda e: self.lift())

    def _sonar(self):
        try:
            if HAS_WINSOUND:
                # beep pattern: 3 beeps ascendentes
                for freq in (800, 1000, 1200):
                    try:
                        winsound.Beep(freq, 300)
                    except Exception:
                        pass
            else:
                # fallback bell + system beep
                try:
                    self.bell()
                except Exception:
                    pass
                # en mac/linux intentar con print \a
                print("\a", end="", flush=True)
        except Exception:
            pass

    def _completar(self):
        try:
            database.marcar_evento_completado(self.evento_row[0], True)
        except Exception:
            pass
        self.destroy()

    def _posponer(self):
        # pospone 10 min añadiendo a la hora actual +10min y actualizando evento
        try:
            evento_id = self.evento_row[0]
            nueva_dt = datetime.now() + timedelta(minutes=10)
            nueva_fecha = nueva_dt.date().isoformat()
            nueva_hora = nueva_dt.strftime("%H:%M")
            database.actualizar_evento(
                evento_id,
                self.evento_row[1],
                nueva_fecha,
                nueva_hora,
                self.evento_row[4],
                self.evento_row[5],
                self.evento_row[6],
            )
        except Exception:
            pass
        self.destroy()

    def _auto_cerrar(self):
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass


class AplicacionIncidencias(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gestor de Incidencias - Tablero Kanban")
        self.geometry("1400x800")

        database.init_db()

        # Estado interno para drag & drop
        self._drag_data = {
            "ticket_id": None,
            "estado_origen": None,
            "titulo": "",
            "cliente": "",
            "prioridad": "",
            "ghost": None,
            "start_x": 0,
            "start_y": 0,
            "offset_x": 0,
            "offset_y": 0,
            "card": None,
            "activo": False,
        }
        self._columna_resaltada = None
        self._filtros = {"texto": "", "prioridad": "Todas", "responsable": "Todos"}
        self._ticket_seleccionado = None
        # Alarma: dict evento_id -> ultimo timestamp notificado (para no spamear)
        self._alarmas_notificadas = {}
        self._ventanas_alarma = {}  # evento_id -> ventana abierta

        # Layout principal: Dashboard + filtros arriba, lateral + kanban abajo
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._crear_dashboard()
        self._crear_barra_filtros()
        self._crear_panel_formulario()
        self._crear_tablero_kanban()
        self._crear_barra_estado()
        self.cargar_tarjetas()
        self._configurar_atajos()
        self.after(1500, self._chequear_notificaciones)
        self.after(5000, self._chequear_alarmas)

    # ===============================================================
    # DASHBOARD
    # ===============================================================
    def _crear_dashboard(self):
        self.frame_dash = ctk.CTkFrame(self, corner_radius=10, height=70)
        self.frame_dash.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        self.frame_dash.grid_propagate(False)
        for i in range(6):
            self.frame_dash.grid_columnconfigure(i, weight=1)
        self.lbl_dash_total = ctk.CTkLabel(self.frame_dash, text="Total: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_dash_total.grid(row=0, column=0, padx=10, pady=10)
        self.lbl_dash_urg = ctk.CTkLabel(self.frame_dash, text="Urgentes: 0", text_color="#e74c3c")
        self.lbl_dash_urg.grid(row=0, column=1, padx=10)
        self.lbl_dash_venc = ctk.CTkLabel(self.frame_dash, text="Vencidos: 0", text_color="#e74c3c")
        self.lbl_dash_venc.grid(row=0, column=2, padx=10)
        self.lbl_dash_analisis = ctk.CTkLabel(self.frame_dash, text="En Análisis: 0", text_color="#e67e22")
        self.lbl_dash_analisis.grid(row=0, column=3, padx=10)
        self.lbl_dash_proceso = ctk.CTkLabel(self.frame_dash, text="En Proceso: 0")
        self.lbl_dash_proceso.grid(row=0, column=4, padx=10)
        self.lbl_dash_final = ctk.CTkLabel(self.frame_dash, text="Finalizadas: 0", text_color="#2ecc71")
        self.lbl_dash_final.grid(row=0, column=5, padx=10)

    def _actualizar_dashboard(self):
        try:
            stats = database.obtener_estadisticas()
            self.lbl_dash_total.configure(text=f"Total: {stats['total']}")
            self.lbl_dash_urg.configure(text=f"Urgentes: {stats['urgentes_pendientes']}")
            self.lbl_dash_venc.configure(text=f"Vencidos: {stats['vencidos']}")
            self.lbl_dash_analisis.configure(text=f"En Análisis: {stats['por_estado'].get('En Análisis',0)}")
            self.lbl_dash_proceso.configure(text=f"En Proceso: {stats['por_estado'].get('En Proceso',0)}")
            self.lbl_dash_final.configure(text=f"Finalizadas: {stats['por_estado'].get('Finalizada',0)}")
        except Exception:
            pass

    # ===============================================================
    # BARRA FILTROS
    # ===============================================================
    def _crear_barra_filtros(self):
        # filtros debajo del dashboard pero encima del kanban, ocupa todo el ancho
        #Fila 0 ya es dashboard, fila 1 es contenido; creamos frame filtros en row=0 column 0 span? Mejor dentro de frame_kanban top
        # Para no complicar grid, creamos barra como frame separado en row=0 col 1 arriba del kanban? Simplificamos: barra en frame superior junto a dashboard
        # En su lugar, añadimos filtros dentro del panel lateral superior
        pass

    def _crear_panel_formulario(self):
        frame_form = ctk.CTkFrame(self, width=310, corner_radius=10)
        frame_form.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        frame_form.grid_propagate(False)

        lbl_titulo = ctk.CTkLabel(frame_form, text="Nueva Incidencia", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_titulo.pack(padx=10, pady=(12, 8))

        # --- Filtros Kanban (integrados en lateral) ---
        box_filtros = ctk.CTkFrame(frame_form, corner_radius=8, border_width=1, border_color="#3a3a3a")
        box_filtros.pack(padx=10, pady=8, fill="x")
        ctk.CTkLabel(box_filtros, text="Filtros / Búsqueda  (Ctrl+K)", font=ctk.CTkFont(size=11, weight="bold")).pack(padx=8, pady=(6, 4), anchor="w")
        self.entry_busqueda = ctk.CTkEntry(box_filtros, placeholder_text="Buscar cliente, título...")
        self.entry_busqueda.pack(padx=8, pady=3, fill="x")
        self.entry_busqueda.bind("<KeyRelease>", lambda e: self.cargar_tarjetas())
        row_f = ctk.CTkFrame(box_filtros, fg_color="transparent")
        row_f.pack(padx=8, pady=3, fill="x")
        self.combo_filtro_prioridad = ctk.CTkOptionMenu(row_f, values=["Todas", "Baja", "Media", "Alta", "Urgente"], width=130, command=lambda v: self.cargar_tarjetas())
        self.combo_filtro_prioridad.pack(side="left", padx=(0, 5))
        self.combo_filtro_prioridad.set("Todas")
        usuarios = ["Todos"] + database.obtener_nombres_usuarios()
        self.combo_filtro_resp = ctk.CTkOptionMenu(row_f, values=usuarios, width=130, command=lambda v: self.cargar_tarjetas())
        self.combo_filtro_resp.pack(side="left")
        self.combo_filtro_resp.set("Todos")
        ctk.CTkButton(box_filtros, text="Limpiar filtros", height=24, fg_color="transparent", border_width=1, command=self._limpiar_filtros).pack(padx=8, pady=(3, 6), fill="x")

        # --- Formulario alta ---
        self.entry_cliente = ctk.CTkEntry(frame_form, placeholder_text="Cliente / Empresa *")
        self.entry_cliente.pack(padx=10, pady=4, fill="x")

        self.combo_canal = ctk.CTkOptionMenu(frame_form, values=["Llamada", "Correo electrónico", "Presencial", "Chat"])
        self.combo_canal.pack(padx=10, pady=4, fill="x")

        self.entry_contacto = ctk.CTkEntry(frame_form, placeholder_text="Teléfono / Email contacto")
        self.entry_contacto.pack(padx=10, pady=4, fill="x")

        self.entry_asunto = ctk.CTkEntry(frame_form, placeholder_text="Título / Asunto breve *")
        self.entry_asunto.pack(padx=10, pady=4, fill="x")

        self.txt_descripcion = ctk.CTkTextbox(frame_form, height=70)
        self.txt_descripcion.pack(padx=10, pady=4, fill="x")
        self.txt_descripcion.insert("0.0", "")

        self.combo_prioridad = ctk.CTkOptionMenu(frame_form, values=["Baja", "Media", "Alta", "Urgente"])
        self.combo_prioridad.pack(padx=10, pady=4, fill="x")
        self.combo_prioridad.set("Media")

        # Responsable y fecha límite
        row2 = ctk.CTkFrame(frame_form, fg_color="transparent")
        row2.pack(padx=10, pady=4, fill="x")
        usuarios2 = database.obtener_nombres_usuarios()
        self.combo_responsable = ctk.CTkOptionMenu(row2, values=usuarios2, width=150)
        self.combo_responsable.pack(side="left", padx=(0, 5))
        self.combo_responsable.set("Sin asignar")
        self.entry_limite = ctk.CTkEntry(row2, placeholder_text="Límite YYYY-MM-DD", width=130)
        self.entry_limite.pack(side="left")

        btn_guardar = ctk.CTkButton(frame_form, text="Registrar Ticket  (Ctrl+N)", command=self.guardar_incidencia, fg_color="green", hover_color="darkgreen")
        btn_guardar.pack(padx=10, pady=(8, 6), fill="x")

        # --- Acciones ---
        grid_acc = ctk.CTkFrame(frame_form, fg_color="transparent")
        grid_acc.pack(padx=10, pady=4, fill="x")
        grid_acc.grid_columnconfigure(0, weight=1)
        grid_acc.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(grid_acc, text="📅 Agenda", height=30, command=self.abrir_agenda).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(grid_acc, text="👥 Usuarios", height=30, fg_color="#34495e", command=self.abrir_usuarios).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(grid_acc, text="📊 Excel", height=30, fg_color="#1f6aa5", command=self.exportar_excel).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(grid_acc, text="📄 PDF", height=30, fg_color="#7f8c8d", command=self.exportar_pdf).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(grid_acc, text="💾 Backup", height=28, fg_color="transparent", border_width=1, command=self.hacer_backup).grid(row=2, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(grid_acc, text="📂 Restaurar", height=28, fg_color="transparent", border_width=1, command=self.restaurar_backup).grid(row=2, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkLabel(frame_form, text="Doble-click tarjeta = editar  |  Ctrl+K buscar", font=ctk.CTkFont(size=10), text_color="gray").pack(padx=10, pady=(6, 4))

    def _limpiar_filtros(self):
        self.entry_busqueda.delete(0, "end")
        self.combo_filtro_prioridad.set("Todas")
        self.combo_filtro_resp.set("Todos")
        self.cargar_tarjetas()

    def _crear_tablero_kanban(self):
        self.frame_kanban = ctk.CTkFrame(self, corner_radius=10)
        self.frame_kanban.grid(row=1, column=1, padx=(5, 10), pady=5, sticky="nsew")

        self.columnas_frames = {}
        self.columnas_contenedores = {}
        for i, estado in enumerate(ESTADOS):
            self.frame_kanban.grid_columnconfigure(i, weight=1)
            self.frame_kanban.grid_rowconfigure(0, weight=1)

            cont = ctk.CTkFrame(self.frame_kanban, fg_color="transparent")
            cont.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            cont.grid_rowconfigure(0, weight=1)
            cont.grid_columnconfigure(0, weight=1)
            self.columnas_contenedores[estado] = cont

            col_frame = ctk.CTkScrollableFrame(cont, label_text=estado)
            col_frame.grid(row=0, column=0, sticky="nsew")
            self.columnas_frames[estado] = col_frame

    def _crear_barra_estado(self):
        self.frame_estado = ctk.CTkFrame(self, height=22, corner_radius=0, fg_color="#1a1a1a")
        self.frame_estado.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.lbl_estado = ctk.CTkLabel(self.frame_estado, text="Listo  •  Ctrl+K buscar  •  Ctrl+N nuevo  •  Doble-click editar  •  Drag & drop activo", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_estado.pack(side="left", padx=10, pady=2)
        self.lbl_reloj = ctk.CTkLabel(self.frame_estado, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_reloj.pack(side="right", padx=10, pady=2)
        self._tick_reloj()

    def _tick_reloj(self):
        try:
            self.lbl_reloj.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        except Exception:
            pass
        self.after(60000, self._tick_reloj)

    # ===============================================================
    # ATAJOS
    # ===============================================================
    def _configurar_atajos(self):
        self.bind("<Control-n>", lambda e: self.entry_cliente.focus_set())
        self.bind("<Control-N>", lambda e: self.entry_cliente.focus_set())
        self.bind("<Control-k>", lambda e: self.abrir_palette())
        self.bind("<Control-K>", lambda e: self.abrir_palette())
        self.bind("<Control-e>", lambda e: self.exportar_excel())
        self.bind("<Control-E>", lambda e: self.exportar_excel())
        self.bind("<F5>", lambda e: self.cargar_tarjetas())
        self.bind("<Delete>", lambda e: self._borrar_seleccionado())

    def abrir_palette(self):
        tickets = database.obtener_tickets()
        VentanaPalette(self, tickets)

    def seleccionar_ticket(self, ticket_id):
        # resalta y abre notas
        t = database.obtener_ticket(ticket_id)
        if t:
            self._ticket_seleccionado = ticket_id
            self.abrir_notas(ticket_id, t[4])
            # flash dashboard
            self.lbl_estado.configure(text=f"Ticket #{ticket_id} seleccionado", text_color="white")
            self.after(2000, lambda: self.lbl_estado.configure(text_color="gray"))

    def _borrar_seleccionado(self):
        if self._ticket_seleccionado and messagebox.askyesno("Borrar", f"¿Borrar ticket #{self._ticket_seleccionado}?"):
            database.eliminar_ticket(self._ticket_seleccionado)
            self._ticket_seleccionado = None
            self.cargar_tarjetas()

    # ===============================================================
    # NOTIFICACIONES
    # ===============================================================
    def _chequear_notificaciones(self):
        try:
            stats = database.obtener_estadisticas()
            msgs = []
            if stats["vencidos"] > 0:
                msgs.append(f"{stats['vencidos']} ticket(s) vencido(s)")
            if stats["urgentes_pendientes"] > 0:
                msgs.append(f"{stats['urgentes_pendientes']} urgente(s) pendiente(s)")
            if msgs:
                self.lbl_estado.configure(text="⚠ " + "  •  ".join(msgs), text_color="#e74c3c")
            # también chequear agenda hoy
            hoy = date.today().isoformat()
            evs = database.obtener_eventos_fecha(hoy)
            pendientes = [e for e in evs if not e[7]]
            if pendientes:
                self.lbl_estado.configure(text=self.lbl_estado.cget("text") + f"  •  {len(pendientes)} tarea(s) hoy")
        except Exception:
            pass
        self.after(60000, self._chequear_notificaciones)

    # ===============================================================
    # DRAG & DROP - Helpers
    # ===============================================================

    def _get_estado_bajo_cursor(self, x_root, y_root):
        try:
            widget = self.winfo_containing(x_root, y_root)
            if widget is not None:
                cur = widget
                for _ in range(14):
                    for estado, col in self.columnas_frames.items():
                        if cur == col:
                            return estado
                        try:
                            parent = cur
                            while parent is not None and str(parent) != ".":
                                if parent == col:
                                    return estado
                                parent = parent.nametowidget(parent.winfo_parent()) if parent.winfo_parent() else None
                        except Exception:
                            pass
                    for estado, cont in getattr(self, "columnas_contenedores", {}).items():
                        if cur == cont:
                            return estado
                    try:
                        parent_name = cur.winfo_parent()
                        if not parent_name:
                            break
                        cur = cur.nametowidget(parent_name)
                    except Exception:
                        break
        except Exception:
            pass
        conts = getattr(self, "columnas_contenedores", self.columnas_frames)
        for estado, cont in conts.items():
            try:
                x0 = cont.winfo_rootx()
                y0 = cont.winfo_rooty()
                x1 = x0 + cont.winfo_width()
                y1 = y0 + cont.winfo_height()
                if x0 <= x_root <= x1 and y0 <= y_root <= y1:
                    return estado
            except Exception:
                continue
        try:
            kx = self.frame_kanban.winfo_rootx()
            ky = self.frame_kanban.winfo_rooty()
            kw = self.frame_kanban.winfo_width()
            kh = self.frame_kanban.winfo_height()
            if kw > 10 and kh > 10 and kx <= x_root <= kx + kw and ky <= y_root <= ky + kh:
                col_w = kw / len(ESTADOS)
                idx = int((x_root - kx) // col_w)
                idx = max(0, min(idx, len(ESTADOS) - 1))
                return ESTADOS[idx]
        except Exception:
            pass
        return None

    def _resaltar_columna(self, estado):
        if self._columna_resaltada == estado:
            return
        self._limpiar_resaltado()
        if estado and estado in self.columnas_frames:
            try:
                self.columnas_frames[estado].configure(border_width=2, border_color="#1f6aa5")
            except Exception:
                pass
            try:
                if hasattr(self, "columnas_contenedores") and estado in self.columnas_contenedores:
                    self.columnas_contenedores[estado].configure(border_width=2, border_color="#1f6aa5")
            except Exception:
                pass
            self._columna_resaltada = estado

    def _limpiar_resaltado(self):
        if self._columna_resaltada and self._columna_resaltada in self.columnas_frames:
            try:
                self.columnas_frames[self._columna_resaltada].configure(border_width=0)
            except Exception:
                pass
            try:
                if hasattr(self, "columnas_contenedores") and self._columna_resaltada in self.columnas_contenedores:
                    self.columnas_contenedores[self._columna_resaltada].configure(border_width=0)
            except Exception:
                pass
        self._columna_resaltada = None

    def _iniciar_drag(self, event, ticket_id, estado_origen, titulo, cliente, prioridad, card_widget):
        if self._drag_data["activo"]:
            return
        # WIP check no bloquea inicio, se valida al soltar
        self._drag_data.update({
            "ticket_id": ticket_id,
            "estado_origen": estado_origen,
            "titulo": titulo,
            "cliente": cliente,
            "prioridad": prioridad,
            "card": card_widget,
            "ghost": None,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "offset_x": event.x_root - card_widget.winfo_rootx() if card_widget else 0,
            "offset_y": event.y_root - card_widget.winfo_rooty() if card_widget else 0,
            "activo": True,
        })
        self.bind_all("<B1-Motion>", self._mover_drag, add="+")
        self.bind_all("<ButtonRelease-1>", self._soltar_drag, add="+")

    def _mover_drag(self, event):
        if not self._drag_data["activo"]:
            return
        try:
            if self._drag_data["ghost"] is None:
                dx = abs(event.x_root - self._drag_data.get("start_x", event.x_root))
                dy = abs(event.y_root - self._drag_data.get("start_y", event.y_root))
                if dx < 8 and dy < 8:
                    return
                ghost = ctk.CTkToplevel(self)
                ghost.overrideredirect(True)
                ghost.attributes("-topmost", True)
                try:
                    ghost.attributes("-alpha", 0.90)
                except Exception:
                    pass
                ghost.geometry(f"220x90+{event.x_root + 12}+{event.y_root + 12}")
                frame = ctk.CTkFrame(ghost, corner_radius=8, border_width=2, border_color="#1f6aa5")
                frame.pack(fill="both", expand=True, padx=2, pady=2)
                ctk.CTkLabel(frame, text=f"[{self._drag_data['prioridad']}] {self._drag_data['cliente']}", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
                ctk.CTkLabel(frame, text=self._drag_data["titulo"], font=ctk.CTkFont(size=12, weight="bold"), wraplength=190, justify="left").pack(anchor="w", padx=8, pady=2)
                ctk.CTkLabel(frame, text="→ arrastra a otra columna", font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", padx=8, pady=(2, 6))
                self._drag_data["ghost"] = ghost
                try:
                    self._drag_data["card"].configure(border_color="#1f6aa5", border_width=2)
                except Exception:
                    pass
                self.configure(cursor="fleur")
            ghost = self._drag_data["ghost"]
            ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
            estado = self._get_estado_bajo_cursor(event.x_root, event.y_root)
            if estado:
                self._resaltar_columna(estado)
            else:
                self._limpiar_resaltado()
        except Exception as e:
            print(f"[drag] _mover_drag error: {e}")

    def _soltar_drag(self, event):
        if not self._drag_data["activo"]:
            return
        try:
            self.unbind_all("<B1-Motion>")
            self.unbind_all("<ButtonRelease-1>")
        except Exception:
            pass
        self.configure(cursor="")
        ghost = self._drag_data.get("ghost")
        ticket_id = self._drag_data.get("ticket_id")
        estado_origen = self._drag_data.get("estado_origen")
        estado_destino = self._get_estado_bajo_cursor(event.x_root, event.y_root) if event else None
        if ghost is not None:
            try:
                ghost.destroy()
            except Exception:
                pass
        self._limpiar_resaltado()
        card = self._drag_data.get("card")
        if card is not None:
            try:
                card.configure(border_color="#3a3a3a", border_width=1)
            except Exception:
                pass
        self._drag_data.update({"ghost": None, "card": None, "activo": False, "ticket_id": None, "estado_origen": None})
        if estado_destino and ticket_id is not None and estado_destino != estado_origen:
            # WIP limit check
            try:
                tickets_dest = [t for t in database.obtener_tickets() if t[7] == estado_destino]
                if len(tickets_dest) >= WIP_LIMITS.get(estado_destino, 100):
                    messagebox.showwarning("WIP Límite", f"La columna '{estado_destino}' ha alcanzado su límite WIP ({WIP_LIMITS[estado_destino]}). Libera un ticket antes de mover.")
                    return
            except Exception:
                pass
            try:
                database.actualizar_estado(ticket_id, estado_destino)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo mover el ticket:\n\n{e}")
                return
            self.cargar_tarjetas()

    def _bind_single(self, w, ticket_id, estado, titulo, cliente, prioridad, card_widget):
        try:
            w.configure(cursor="fleur")
        except Exception:
            pass
        try:
            w.bind("<Button-1>", lambda e, tid=ticket_id, est=estado, tit=titulo, cli=cliente, pri=prioridad, cw=card_widget: self._iniciar_drag(e, tid, est, tit, cli, pri, cw), add="+")
            w.bind("<ButtonPress-1>", lambda e, tid=ticket_id, est=estado, tit=titulo, cli=cliente, pri=prioridad, cw=card_widget: self._iniciar_drag(e, tid, est, tit, cli, pri, cw), add="+")
        except Exception:
            pass
        try:
            canvas = getattr(w, "_canvas", None)
            if canvas is not None:
                canvas.bind("<Button-1>", lambda e, tid=ticket_id, est=estado, tit=titulo, cli=cliente, pri=prioridad, cw=card_widget: self._iniciar_drag(e, tid, est, tit, cli, pri, cw), add="+")
                canvas.bind("<ButtonPress-1>", lambda e, tid=ticket_id, est=estado, tit=titulo, cli=cliente, pri=prioridad, cw=card_widget: self._iniciar_drag(e, tid, est, tit, cli, pri, cw), add="+")
                try:
                    canvas.configure(cursor="fleur")
                except Exception:
                    pass
        except Exception:
            pass

    def _hacer_arrastrable(self, widget, ticket_id, estado, titulo, cliente, prioridad, card_widget):
        self._bind_single(widget, ticket_id, estado, titulo, cliente, prioridad, card_widget)
        try:
            for child in widget.winfo_children():
                self._bind_single(child, ticket_id, estado, titulo, cliente, prioridad, card_widget)
        except Exception:
            pass

    # ===============================================================
    # ACCIONES
    # ===============================================================
    def abrir_agenda(self):
        VentanaAgenda(self)

    def abrir_usuarios(self):
        VentanaUsuarios(self, on_close=self.cargar_tarjetas)

    def guardar_incidencia(self):
        cliente = self.entry_cliente.get().strip()
        canal = self.combo_canal.get()
        contacto = self.entry_contacto.get().strip()
        titulo = self.entry_asunto.get().strip()
        descripcion = self.txt_descripcion.get("0.0", "end").strip()
        prioridad = self.combo_prioridad.get()
        responsable = self.combo_responsable.get()
        fecha_limite = self.entry_limite.get().strip() or None
        if fecha_limite:
            try:
                datetime.strptime(fecha_limite, "%Y-%m-%d")
            except Exception:
                messagebox.showwarning("Fecha inválida", "Usa formato YYYY-MM-DD para fecha límite")
                return
        if not cliente or not titulo:
            messagebox.showwarning("Faltan datos", "Cliente y título son obligatorios")
            return
        database.crear_ticket(cliente, canal, contacto, titulo, descripcion, prioridad, responsable=responsable, fecha_limite=fecha_limite)
        self.entry_cliente.delete(0, 'end')
        self.entry_contacto.delete(0, 'end')
        self.entry_asunto.delete(0, 'end')
        self.txt_descripcion.delete("0.0", 'end')
        self.entry_limite.delete(0, 'end')
        self.cargar_tarjetas()

    def exportar_excel(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")], initialfile="incidencias.xlsx")
        if not ruta:
            return
        tickets = database.obtener_tickets()
        try:
            if ruta.endswith(".csv"):
                with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["ID", "Cliente", "Canal", "Contacto", "Título", "Prioridad", "Estado", "Responsable", "Fecha límite", "Fecha creación"])
                    for t in tickets:
                        w.writerow([t[0], t[1], t[2], t[3], t[4], t[6], t[7], t[9] if len(t) > 9 else "", t[10] if len(t) > 10 else "", t[8]])
            else:
                try:
                    import openpyxl
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Incidencias"
                    ws.append(["ID", "Cliente", "Canal", "Contacto", "Título", "Descripción", "Prioridad", "Estado", "Responsable", "Fecha límite", "Fecha creación"])
                    for t in tickets:
                        ws.append([t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[9] if len(t) > 9 else "", t[10] if len(t) > 10 else "", t[8]])
                    # autosize
                    for col in ws.columns:
                        max_len = max(len(str(c.value or "")) for c in col)
                        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
                    wb.save(ruta)
                except ImportError:
                    # fallback a csv con extensión xlsx renombrada
                    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                        w = csv.writer(f)
                        w.writerow(["ID", "Cliente", "Título", "Prioridad", "Estado", "Responsable"])
                        for t in tickets:
                            w.writerow([t[0], t[1], t[4], t[6], t[7], t[9] if len(t) > 9 else ""])
                    messagebox.showinfo("Exportado", f"openpyxl no instalado, exportado como CSV en {ruta}\nInstala: pip install openpyxl")
                    return
            messagebox.showinfo("Exportado", f"Exportado a {ruta}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exportar_pdf(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="incidencias.pdf")
        if not ruta:
            return
        tickets = database.obtener_tickets()
        try:
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                doc = SimpleDocTemplate(ruta, pagesize=A4, leftMargin=20, rightMargin=20)
                styles = getSampleStyleSheet()
                story = [Paragraph("Gestor de Incidencias - Reporte", styles["Title"]), Spacer(1, 12),
                         Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  -  Total: {len(tickets)} tickets", styles["Normal"]), Spacer(1, 12)]
                data = [["ID", "Cliente", "Título", "Prior.", "Estado", "Resp."]]
                for t in tickets:
                    data.append([str(t[0]), t[1][:15], t[4][:30], t[6], t[7][:12], (t[9][:10] if len(t) > 9 and t[9] else "-")])
                table = Table(data, repeatRows=1, colWidths=[30, 80, 180, 50, 80, 70])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6aa5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ]))
                story.append(table)
                doc.build(story)
                messagebox.showinfo("Exportado", f"PDF guardado en {ruta}")
            except ImportError:
                # fallback: crear txt
                txt_path = ruta.replace(".pdf", ".txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"Gestor Incidencias - {datetime.now()}\n")
                    for t in tickets:
                        f.write(f"#{t[0]} {t[1]} - {t[4]} [{t[6]}] {t[7]}\n")
                messagebox.showwarning("PDF no disponible", f"Instala reportlab (pip install reportlab). Se generó TXT en {txt_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def hacer_backup(self):
        dest = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("DB", "*.db"), ("Backup", "*.bak")], initialfile=f"incidencias_backup_{date.today().isoformat()}.db")
        if not dest:
            return
        try:
            shutil.copy2(database.DB_NAME, dest)
            messagebox.showinfo("Backup", f"Backup creado en {dest}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def restaurar_backup(self):
        src = filedialog.askopenfilename(filetypes=[("DB", "*.db"), ("Todos", "*.*")])
        if not src:
            return
        if not messagebox.askyesno("Restaurar", "¿Restaurar backup? Se reiniciará la app y se perderán cambios no guardados."):
            return
        try:
            shutil.copy2(src, database.DB_NAME)
            messagebox.showinfo("Restaurado", "Backup restaurado. Reinicia la app.")
            self.cargar_tarjetas()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def cargar_tarjetas(self):
        # Filtros
        texto = self.entry_busqueda.get().strip() if hasattr(self, "entry_busqueda") else ""
        prio = self.combo_filtro_prioridad.get() if hasattr(self, "combo_filtro_prioridad") else "Todas"
        resp = self.combo_filtro_resp.get() if hasattr(self, "combo_filtro_resp") else "Todos"
        # Limpiar columnas
        for frame in self.columnas_frames.values():
            for child in frame.winfo_children():
                child.destroy()

        tickets = database.obtener_tickets(filtro_texto=texto or None, filtro_prioridad=prio, filtro_responsable=resp)

        # Agrupar por estado para WIP y orden
        por_estado = {e: [] for e in ESTADOS}
        for t in tickets:
            est = t[7]
            if est in por_estado:
                por_estado[est].append(t)

        # Actualizar label_text con contador WIP
        for estado, col in self.columnas_frames.items():
            cnt = len(por_estado[estado])
            lim = WIP_LIMITS.get(estado, 99)
            suffix = f" ({cnt}/{lim})" if lim < 99 else f" ({cnt})"
            alerta = " ⚠" if cnt >= lim else ""
            try:
                col.configure(label_text=estado + suffix + alerta)
            except Exception:
                pass

        for t in tickets:
            # t: id, cliente, canal, contacto, titulo, descripcion, prioridad, estado, fecha_creacion, responsable, fecha_limite, posicion, tiempo_estimado
            # compatibilidad con DB antigua sin nuevas columnas
            t_id = t[0]
            cliente = t[1]
            titulo = t[4]
            descripcion = t[5] if len(t) > 5 else ""
            prioridad = t[6] if len(t) > 6 else "Media"
            estado = t[7] if len(t) > 7 else "Recibida"
            responsable = t[9] if len(t) > 9 and t[9] else "Sin asignar"
            fecha_limite = t[10] if len(t) > 10 else None

            if estado not in self.columnas_frames:
                continue
            parent = self.columnas_frames[estado]

            color_prio = PRIORIDAD_COLORES.get(prioridad, "#7f8c8d")
            sem_icon, sem_txt = get_semaforo(fecha_limite, estado)

            card = ctk.CTkFrame(parent, corner_radius=8, border_width=1, border_color="#3a3a3a")
            card.pack(padx=5, pady=5, fill="x")

            # Barra de prioridad (izquierda)
            barra = ctk.CTkFrame(card, width=6, corner_radius=4, fg_color=color_prio)
            barra.pack(side="left", fill="y", padx=(0, 0), pady=0)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True)

            # Handle + botones mover
            frame_drag = ctk.CTkFrame(inner, fg_color="#2a2a2a", corner_radius=6, height=20)
            frame_drag.pack(fill="x", padx=4, pady=(4, 0))
            ctk.CTkLabel(frame_drag, text="⋮⋮  arrastra", font=ctk.CTkFont(size=10), text_color="#888888").pack(side="left", padx=6, pady=2)
            # botones reordenar vertical
            ctk.CTkButton(frame_drag, text="▲", width=22, height=18, fg_color="transparent", hover_color="#333",
                          command=lambda tid=t_id, est=estado: self._mover_orden(tid, est, -1)).pack(side="right", padx=1)
            ctk.CTkButton(frame_drag, text="▼", width=22, height=18, fg_color="transparent", hover_color="#333",
                          command=lambda tid=t_id, est=estado: self._mover_orden(tid, est, 1)).pack(side="right", padx=1)

            # Header cliente + prioridad badge
            row_h = ctk.CTkFrame(inner, fg_color="transparent")
            row_h.pack(fill="x", padx=6, pady=(4, 0))
            ctk.CTkLabel(row_h, text=cliente, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")
            badge = ctk.CTkLabel(row_h, text=prioridad, font=ctk.CTkFont(size=9, weight="bold"), fg_color=color_prio, corner_radius=6, text_color="white", padx=6, pady=1)
            badge.pack(side="right")

            ctk.CTkLabel(inner, text=titulo, font=ctk.CTkFont(size=12, weight="bold"), wraplength=170, justify="left", anchor="w").pack(anchor="w", padx=6, pady=2)
            if descripcion:
                ctk.CTkLabel(inner, text=descripcion[:70] + ("..." if len(descripcion) > 70 else ""), text_color="gray", wraplength=170, justify="left", anchor="w", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=6)
            # responsable + sla
            row2 = ctk.CTkFrame(inner, fg_color="transparent")
            row2.pack(fill="x", padx=6, pady=2)
            ctk.CTkLabel(row2, text=f"👤 {responsable}", font=ctk.CTkFont(size=10), text_color="gray").pack(side="left")
            if sem_icon:
                ctk.CTkLabel(row2, text=f"{sem_icon} {sem_txt}", font=ctk.CTkFont(size=10), text_color="#e74c3c" if sem_icon == "🔴" else "#e67e22").pack(side="right")

            # Doble-click para editar
            for w in (inner, card, barra):
                w.bind("<Double-Button-1>", lambda e, tid=t_id: self.abrir_editar(tid))
            # Arrastrables
            for w in (frame_drag, inner, card):
                self._hacer_arrastrable(w, t_id, estado, titulo, cliente, prioridad, card)
            # y labels internos
            # labels ya están dentro de inner, hacerlos arrastrables via inner children
            for child in inner.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for cc in child.winfo_children():
                        self._bind_single(cc, t_id, estado, titulo, cliente, prioridad, card)

            # Combo estado fallback
            combo_estado = ctk.CTkOptionMenu(inner, values=ESTADOS, height=22, font=ctk.CTkFont(size=11),
                                              command=lambda nuevo_est, tid=t_id: self.cambiar_estado(tid, nuevo_est))
            combo_estado.set(estado)
            combo_estado.pack(padx=6, pady=4, fill="x")

            # Botones inferior
            frame_botones = ctk.CTkFrame(inner, fg_color="transparent")
            frame_botones.pack(padx=4, pady=(0, 4), fill="x")
            num_notas = database.contar_notas(t_id)
            num_adj = database.contar_adjuntos(t_id) if hasattr(database, "contar_adjuntos") else 0
            txt_notas = f"Notas ({num_notas})" if num_notas else "Notas"
            if num_adj:
                txt_notas += f" +{num_adj}📎"
            ctk.CTkButton(frame_botones, text=txt_notas, height=20, width=90, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                          command=lambda tid=t_id, tit=titulo: self.abrir_notas(tid, tit)).pack(side="left", padx=2)
            ctk.CTkButton(frame_botones, text="✎", width=28, height=20, fg_color="transparent", border_width=1,
                          command=lambda tid=t_id: self.abrir_editar(tid)).pack(side="left", padx=2)
            ctk.CTkButton(frame_botones, text="Borrar", height=20, width=55, fg_color="transparent", text_color="red", hover_color="#3a1111",
                          command=lambda tid=t_id: self.borrar_ticket(tid)).pack(side="right", padx=2)
            # click seleccion
            card.bind("<Button-1>", lambda e, tid=t_id: self._seleccionar(tid), add="+")

        self._actualizar_dashboard()
        # refrescar combos de filtro responsable por si hubo nuevo usuario
        try:
            usuarios = ["Todos"] + database.obtener_nombres_usuarios()
            self.combo_filtro_resp.configure(values=usuarios)
            self.combo_responsable.configure(values=database.obtener_nombres_usuarios())
        except Exception:
            pass

    def _mover_orden(self, ticket_id, estado, delta):
        # reordenar dentro del estado
        tickets_estado = [t for t in database.obtener_tickets() if t[7] == estado]
        tickets_estado.sort(key=lambda x: x[11] if len(x) > 11 and x[11] is not None else x[0])
        ids = [t[0] for t in tickets_estado]
        if ticket_id not in ids:
            return
        idx = ids.index(ticket_id)
        new_idx = idx + delta
        if 0 <= new_idx < len(ids):
            ids.insert(new_idx, ids.pop(idx))
            database.reordenar_tickets(estado, ids)
            self.cargar_tarjetas()

    def _seleccionar(self, tid):
        self._ticket_seleccionado = tid

    def abrir_notas(self, ticket_id, titulo):
        VentanaNotas(self, ticket_id, titulo, on_close=self.cargar_tarjetas)

    def abrir_editar(self, ticket_id):
        VentanaEditarTicket(self, ticket_id, on_save=self.cargar_tarjetas)

    def cambiar_estado(self, ticket_id, nuevo_estado):
        # WIP check
        tickets_dest = [t for t in database.obtener_tickets() if t[7] == nuevo_estado]
        if len(tickets_dest) >= WIP_LIMITS.get(nuevo_estado, 100):
            messagebox.showwarning("WIP Límite", f"Columna '{nuevo_estado}' llena ({WIP_LIMITS[nuevo_estado]}).")
            self.cargar_tarjetas()
            return
        database.actualizar_estado(ticket_id, nuevo_estado)
        self.cargar_tarjetas()

    def borrar_ticket(self, ticket_id):
        if not messagebox.askyesno("Borrar", f"¿Borrar ticket #{ticket_id}? Se eliminarán notas y adjuntos."):
            return
        database.eliminar_ticket(ticket_id)
        self.cargar_tarjetas()


if __name__ == "__main__":
    app = AplicacionIncidencias()
    app.mainloop()
