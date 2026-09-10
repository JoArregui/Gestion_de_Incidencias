import customtkinter as ctk
import database
from tkcalendar import Calendar
from tkinter import messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ESTADOS = ["Recibida", "En Análisis", "En Proceso", "Pendiente Cliente", "Finalizada"]


class VentanaNotas(ctk.CTkToplevel):
    """Ventana emergente para ver y añadir notas/respuestas de un ticket."""

    def __init__(self, master, ticket_id, titulo_ticket, on_close=None):
        super().__init__(master)
        self.ticket_id = ticket_id
        self.on_close = on_close

        self.title(f"Notas - {titulo_ticket}")
        self.geometry("450x500")
        self.transient(master)

        lbl_titulo = ctk.CTkLabel(
            self, text=titulo_ticket, font=ctk.CTkFont(size=16, weight="bold"), wraplength=400
        )
        lbl_titulo.pack(padx=15, pady=(15, 5), anchor="w")

        self.frame_notas = ctk.CTkScrollableFrame(self, label_text="Historial de notas")
        self.frame_notas.pack(padx=15, pady=5, fill="both", expand=True)

        frame_nueva = ctk.CTkFrame(self, fg_color="transparent")
        frame_nueva.pack(padx=15, pady=(5, 15), fill="x")

        self.txt_nueva_nota = ctk.CTkTextbox(frame_nueva, height=70)
        self.txt_nueva_nota.pack(fill="x", pady=(0, 8))

        btn_agregar = ctk.CTkButton(
            frame_nueva, text="Añadir nota", command=self.agregar_nota
        )
        btn_agregar.pack(fill="x")

        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self.cargar_notas()

        # En lugar de usar grab_set() que bloquea la ventana, enfocamos el campo
        # una vez la ventana sea completamente visible en la pantalla
        self.bind("<Visibility>", self._al_visibilizar)

    def _al_visibilizar(self, event=None):
        """Asegura el foco sobre el campo de texto cuando la ventana está renderizada."""
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
            lbl_vacio = ctk.CTkLabel(
                self.frame_notas, text="Sin notas todavía.", text_color="gray"
            )
            lbl_vacio.pack(padx=5, pady=10)
            return

        for nota_id, texto, fecha in notas:
            item = ctk.CTkFrame(self.frame_notas, corner_radius=8, border_width=1, border_color="#3a3a3a")
            item.pack(padx=5, pady=5, fill="x")

            lbl_fecha = ctk.CTkLabel(
                item, text=fecha, font=ctk.CTkFont(size=10), text_color="gray"
            )
            lbl_fecha.pack(anchor="w", padx=8, pady=(6, 0))

            lbl_texto = ctk.CTkLabel(
                item, text=texto, wraplength=370, justify="left", anchor="w"
            )
            lbl_texto.pack(anchor="w", padx=8, pady=(2, 6), fill="x")

    def agregar_nota(self):
        texto = self.txt_nueva_nota.get("0.0", "end").strip()

        if not texto:
            from tkinter import messagebox
            messagebox.showwarning(
                "Nota vacía",
                "Escribe una nota antes de pulsar «Añadir nota»."
            )
            self.txt_nueva_nota.focus_set()
            return

        try:
            database.crear_nota(self.ticket_id, texto)

            self.txt_nueva_nota.delete("0.0", "end")
            self.cargar_notas()

            self.txt_nueva_nota.focus_set()

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"No se pudo guardar la nota:\n\n{e}"
            )

    def _cerrar(self):
        if self.on_close:
            self.on_close()
        self.destroy()

class VentanaAgenda(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.title("Agenda")
        self.geometry("900x600")
        self.minsize(800, 500)

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

        # Cargar el día seleccionado inicialmente
        self.cambiar_dia()

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

        item = ctk.CTkFrame(
            self.frame_lista,
            corner_radius=8,
            border_width=1,
            border_color="#3a3a3a"
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
            text=f"{hora_texto}  •  {tipo}",
            text_color="gray",
            font=ctk.CTkFont(size=11)
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

    def nuevo_evento(self):

        VentanaNuevoEvento(
            self,
            self.calendario.get_date(),
            self.cargar_eventos
        )

    # ===============================================================
    # COMPLETAR EVENTO
    # ===============================================================

    def marcar_completado(self, evento_id, completada):

        database.marcar_evento_completado(
            evento_id,
            completada
        )

        self.cargar_eventos(
            self.calendario.get_date()
        )

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

        self.cargar_eventos(
            self.calendario.get_date()
        )

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


class AplicacionIncidencias(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gestor de Incidencias - Tablero Kanban")
        self.geometry("1300x750")

        database.init_db()

        # Layout principal: Panel lateral (formulario) + Panel central (Kanban)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._crear_panel_formulario()
        self._crear_tablero_kanban()
        self.cargar_tarjetas()

    def _crear_panel_formulario(self):
        frame_form = ctk.CTkFrame(self, width=300, corner_radius=10)
        frame_form.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        lbl_titulo = ctk.CTkLabel(frame_form, text="Nueva Incidencia", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_titulo.pack(padx=10, pady=(15, 10))

        self.entry_cliente = ctk.CTkEntry(frame_form, placeholder_text="Cliente / Empresa")
        self.entry_cliente.pack(padx=10, pady=5, fill="x")

        self.combo_canal = ctk.CTkOptionMenu(frame_form, values=["Llamada", "Correo electrónico"])
        self.combo_canal.pack(padx=10, pady=5, fill="x")

        self.entry_contacto = ctk.CTkEntry(frame_form, placeholder_text="Teléfono / Email contacto")
        self.entry_contacto.pack(padx=10, pady=5, fill="x")

        self.entry_asunto = ctk.CTkEntry(frame_form, placeholder_text="Título / Asunto breve")
        self.entry_asunto.pack(padx=10, pady=5, fill="x")

        self.txt_descripcion = ctk.CTkTextbox(frame_form, height=100)
        self.txt_descripcion.pack(padx=10, pady=5, fill="x")
        self.txt_descripcion.insert("0.0", "Descripción de la incidencia...")

        self.combo_prioridad = ctk.CTkOptionMenu(frame_form, values=["Baja", "Media", "Alta", "Urgente"])
        self.combo_prioridad.pack(padx=10, pady=5, fill="x")

        btn_guardar = ctk.CTkButton(frame_form, text="Registrar Ticket", command=self.guardar_incidencia, fg_color="green", hover_color="darkgreen")
        btn_guardar.pack(padx=10, pady=15, fill="x")

        # Botón para desplegar la ventana de la Agenda
        btn_agenda = ctk.CTkButton(
            frame_form,
            text="📅 Abrir Agenda",
            height=35,
            command=self.abrir_agenda
        )
        btn_agenda.pack(padx=10, pady=(5, 15), fill="x")

    def _crear_tablero_kanban(self):
        self.frame_kanban = ctk.CTkFrame(self, corner_radius=10)
        self.frame_kanban.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.columnas_frames = {}

        for i, estado in enumerate(ESTADOS):
            self.frame_kanban.grid_columnconfigure(i, weight=1)
            self.frame_kanban.grid_rowconfigure(0, weight=1)

            col_frame = ctk.CTkScrollableFrame(self.frame_kanban, label_text=estado)
            col_frame.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            self.columnas_frames[estado] = col_frame

    def abrir_agenda(self):
        VentanaAgenda(self)

    def guardar_incidencia(self):
        cliente = self.entry_cliente.get()
        canal = self.combo_canal.get()
        contacto = self.entry_contacto.get()
        titulo = self.entry_asunto.get()
        descripcion = self.txt_descripcion.get("0.0", "end").strip()
        prioridad = self.combo_prioridad.get()

        if cliente and titulo:
            database.crear_ticket(cliente, canal, contacto, titulo, descripcion, prioridad)

            # Limpiar campos
            self.entry_cliente.delete(0, 'end')
            self.entry_contacto.delete(0, 'end')
            self.entry_asunto.delete(0, 'end')
            self.txt_descripcion.delete("0.0", 'end')

            self.cargar_tarjetas()

    def cargar_tarjetas(self):
        # Limpiar columnas
        for frame in self.columnas_frames.values():
            for child in frame.winfo_children():
                child.destroy()

        tickets = database.obtener_tickets()

        for t in tickets:
            t_id, cliente, canal, contacto, titulo, descripcion, prioridad, estado, fecha = t

            if estado in self.columnas_frames:
                parent = self.columnas_frames[estado]

                card = ctk.CTkFrame(parent, corner_radius=8, border_width=1, border_color="#3a3a3a")
                card.pack(padx=5, pady=5, fill="x")

                lbl_header = ctk.CTkLabel(card, text=f"[{prioridad}] {cliente}", font=ctk.CTkFont(size=12, weight="bold"))
                lbl_header.pack(anchor="w", padx=8, pady=(5, 0))

                lbl_title = ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=14, weight="bold"), wraplength=180, justify="left")
                lbl_title.pack(anchor="w", padx=8, pady=2)

                lbl_desc = ctk.CTkLabel(card, text=descripcion[:60] + "..." if len(descripcion) > 60 else descripcion, text_color="gray", wraplength=180, justify="left")
                lbl_desc.pack(anchor="w", padx=8, pady=2)

                # Control para mover la tarjeta de estado
                combo_estado = ctk.CTkOptionMenu(
                    card,
                    values=ESTADOS,
                    height=24,
                    font=ctk.CTkFont(size=11),
                    command=lambda nuevo_est, tid=t_id: self.cambiar_estado(tid, nuevo_est)
                )
                combo_estado.set(estado)
                combo_estado.pack(padx=8, pady=5, fill="x")

                # Fila de botones inferior: Notas + Borrar
                frame_botones = ctk.CTkFrame(card, fg_color="transparent")
                frame_botones.pack(padx=5, pady=(0, 5), fill="x")

                num_notas = database.contar_notas(t_id)
                texto_notas = f"Notas ({num_notas})" if num_notas else "Notas"

                btn_notas = ctk.CTkButton(
                    frame_botones,
                    text=texto_notas,
                    height=20,
                    fg_color="transparent",
                    border_width=1,
                    text_color=("gray10", "gray90"),
                    command=lambda tid=t_id, tit=titulo: self.abrir_notas(tid, tit)
                )
                btn_notas.pack(side="left", padx=(0, 5))

                btn_eliminar = ctk.CTkButton(
                    frame_botones, text="Borrar", height=20, fg_color="transparent",
                    text_color="red", hover_color="#3a1111",
                    command=lambda tid=t_id: self.borrar_ticket(tid)
                )
                btn_eliminar.pack(side="right")

    def abrir_notas(self, ticket_id, titulo):
        VentanaNotas(self, ticket_id, titulo, on_close=self.cargar_tarjetas)

    def cambiar_estado(self, ticket_id, nuevo_estado):
        database.actualizar_estado(ticket_id, nuevo_estado)
        self.cargar_tarjetas()

    def borrar_ticket(self, ticket_id):
        database.eliminar_ticket(ticket_id)
        self.cargar_tarjetas()


if __name__ == "__main__":
    app = AplicacionIncidencias()
    app.mainloop()