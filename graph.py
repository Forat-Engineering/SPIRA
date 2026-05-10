#GRACIAS CLAUDE
import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque

class LoRaMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("LoRa Monitor con Gráfico en Tiempo Real")
        self.root.geometry("1400x650")
        
        self.ser = None
        self.ejecutando = False
        
        # Datos para gráficos (últimos 50 puntos)
        self.max_puntos = 50
        self.tiempos = deque(maxlen=self.max_puntos)
        self.alturas = deque(maxlen=self.max_puntos)
        self.presiones = deque(maxlen=self.max_puntos)
        self.humedades = deque(maxlen=self.max_puntos)
        self.temperaturas = deque(maxlen=self.max_puntos)
        
        self.tiempo_inicial = datetime.now()
        
        # Configurar la GUI
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Frame superior - Configuración
        frame_config = tk.Frame(self.root, padx=10, pady=5)
        frame_config.pack(fill=tk.X)
        
        tk.Label(frame_config, text="Puerto:").pack(side=tk.LEFT)
        
        self.combo_puertos = ttk.Combobox(frame_config, width=20, state='readonly')
        self.actualizar_puertos()
        self.combo_puertos.pack(side=tk.LEFT, padx=5)
        
        # Botón de actualizar puertos (siempre activo)
        self.btn_actualizar = tk.Button(frame_config, text="🔄", 
                 command=self.actualizar_puertos, width=3)
        self.btn_actualizar.pack(side=tk.LEFT, padx=2)
        
        tk.Label(frame_config, text="Baudrate:").pack(side=tk.LEFT, padx=(10,5))
        self.entry_baudrate = tk.Entry(frame_config, width=8)
        self.entry_baudrate.insert(0, "9600")
        self.entry_baudrate.pack(side=tk.LEFT)
        
        self.btn_conectar = tk.Button(frame_config, text="🔌 Conectar", 
                                      command=self.toggle_conexion, 
                                      bg="lightgreen", width=10)
        self.btn_conectar.pack(side=tk.LEFT, padx=10)
        
        # Botón de limpiar (siempre activo)
        self.btn_limpiar = tk.Button(frame_config, text="🗑️ Limpiar", 
                 command=self.limpiar_graficos, width=8)
        self.btn_limpiar.pack(side=tk.LEFT, padx=2)
        
        # Barra de estado
        self.label_estado = tk.Label(frame_config, text="⚫ Desconectado", 
                                     relief=tk.SUNKEN, anchor=tk.W, width=40)
        self.label_estado.pack(side=tk.LEFT, padx=10)
        
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, pady=2)
        
        # Frame principal con dos paneles
        frame_principal = tk.Frame(self.root, padx=10, pady=5)
        frame_principal.pack(fill=tk.BOTH, expand=True)
        
        # PANEL IZQUIERDO - Monitor de mensajes
        frame_izquierdo = tk.Frame(frame_principal)
        frame_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        
        tk.Label(frame_izquierdo, text=" Monitor", 
                font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        self.text_monitor = scrolledtext.ScrolledText(
            frame_izquierdo, 
            wrap=tk.WORD, 
            width=45, 
            height=25,
            font=("Courier", 8),
            bg="#ffffff",
            fg="#000000"
        )
        self.text_monitor.pack(fill=tk.BOTH, expand=True, pady=2)
        self.text_monitor.config(state=tk.DISABLED)
        
        # PANEL DERECHO - Gráfico
        frame_derecho = tk.Frame(frame_principal)
        frame_derecho.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,0))
        
        tk.Label(frame_derecho, text="📊 Datos en Tiempo Real", 
                font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        # Valores actuales
        frame_valores = tk.Frame(frame_derecho, bg="#f0f0f0", relief=tk.RIDGE, bd=2)
        frame_valores.pack(fill=tk.X, pady=2)
        
        self.label_altura = tk.Label(frame_valores, text="Alt: -- m", 
                                     font=("Arial", 9, "bold"), bg="#f0f0f0", fg="blue")
        self.label_altura.grid(row=0, column=0, padx=8, pady=3)
        
        self.label_presion = tk.Label(frame_valores, text="Pres: -- hPa", 
                                      font=("Arial", 9, "bold"), bg="#f0f0f0", fg="red")
        self.label_presion.grid(row=0, column=1, padx=8, pady=3)
        
        self.label_humedad = tk.Label(frame_valores, text="Hum: -- %", 
                                      font=("Arial", 9, "bold"), bg="#f0f0f0", fg="green")
        self.label_humedad.grid(row=0, column=2, padx=8, pady=3)
        
        self.label_temperatura = tk.Label(frame_valores, text="Temp: -- °C", 
                                         font=("Arial", 9, "bold"), bg="#f0f0f0", fg="purple")
        self.label_temperatura.grid(row=0, column=3, padx=8, pady=3)
        
        # Crear figura de matplotlib con UN SOLO GRÁFICO
        self.fig = Figure(figsize=(8, 5.5), dpi=100, facecolor='#f0f0f0')
        self.fig.subplots_adjust(left=0.08, right=0.88, top=0.95, bottom=0.1)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Tiempo (s)', fontweight='bold')
        self.ax.set_ylabel('Valores', fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor('#ffffff')
        
        # Crear 4 líneas con diferentes colores
        self.line_altura, = self.ax.plot([], [], 'b-', linewidth=2, label='Altura (m)')
        self.line_presion, = self.ax.plot([], [], 'r-', linewidth=2, label='Presión (hPa)')
        self.line_humedad, = self.ax.plot([], [], 'g-', linewidth=2, label='Humedad (%)')
        self.line_temperatura, = self.ax.plot([], [], 'm-', linewidth=2, label='Temp (°C)')
        
        # Crear leyenda
        self.ax.legend(loc='upper left', fontsize=8)
        
        # Integrar matplotlib en tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_derecho)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame inferior - Envío de comandos
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, pady=2)
        
        frame_envio = tk.Frame(self.root, padx=10, pady=5)
        frame_envio.pack(fill=tk.X)
        
        tk.Label(frame_envio, text="💬 Comando:", 
                font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        
        self.entry_comando = tk.Entry(frame_envio, font=("Arial", 10))
        self.entry_comando.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_comando.bind('<Return>', lambda e: self.enviar_comando())
        
        self.btn_enviar = tk.Button(frame_envio, text="📤 Enviar", 
                                    command=self.enviar_comando,
                                    state=tk.DISABLED, bg="lightblue", width=8)
        self.btn_enviar.pack(side=tk.LEFT, padx=2)
        
        # Botones de comandos rápidos (guardamos referencias)
        self.botones_rapidos = []
        comandos_rapidos = []
        for cmd in comandos_rapidos:
            btn = tk.Button(frame_envio, text=cmd, 
                           command=lambda c=cmd: self.enviar_comando_rapido(c),
                           state=tk.DISABLED, width=7)
            btn.pack(side=tk.LEFT, padx=1)
            self.botones_rapidos.append(btn)
    
    def actualizar_puertos(self):
        """Actualiza la lista de puertos disponibles"""
        puerto_actual = self.combo_puertos.get()
        
        puertos = serial.tools.list_ports.comports()
        lista_puertos = [f"{p.device} - {p.description}" for p in puertos]
        
        if not lista_puertos:
            lista_puertos = ["No hay puertos disponibles"]
        
        self.combo_puertos['values'] = lista_puertos
        
        # Verificar si el puerto actualmente seleccionado sigue existiendo
        if puerto_actual:
            puerto_existe = False
            for puerto in lista_puertos:
                if puerto_actual in puerto or (puerto_actual and puerto_actual.split(" - ")[0] in puerto):
                    puerto_existe = True
                    break
            
            if puerto_existe and "No hay" not in lista_puertos[0]:
                # El puerto sigue existiendo, mantener la selección
                for i, puerto in enumerate(lista_puertos):
                    if puerto_actual in puerto or (puerto_actual and puerto_actual.split(" - ")[0] in puerto):
                        self.combo_puertos.current(i)
                        break
            else:
                # El puerto ya no existe, seleccionar el primero disponible
                if lista_puertos and "No hay" not in lista_puertos[0]:
                    self.combo_puertos.current(0)
                    self.agregar_mensaje(f"⚠️ Puerto {puerto_actual.split(' - ')[0]} desconectado", "error")
                else:
                    self.combo_puertos.set("")
        else:
            # No hay selección previa, seleccionar el primero
            if lista_puertos and "No hay" not in lista_puertos[0]:
                self.combo_puertos.current(0)
    
    def toggle_conexion(self):
        """Conectar o desconectar del puerto serial"""
        if not self.ejecutando:
            self.conectar()
        else:
            self.desconectar()
    
    def conectar(self):
        """Conectar al puerto serial"""
        try:
            puerto_seleccionado = self.combo_puertos.get()
            if "No hay" in puerto_seleccionado:
                self.agregar_mensaje("✗ No hay puertos disponibles", "error")
                return
            
            puerto = puerto_seleccionado.split(" - ")[0]
            baudrate = int(self.entry_baudrate.get())
            
            self.ser = serial.Serial(puerto, baudrate, timeout=1)
            self.ejecutando = True
            
            # Reiniciar tiempo inicial
            self.tiempo_inicial = datetime.now()
            
            # Actualizar interfaz
            self.btn_conectar.config(text="🔌 Desconectar", bg="lightcoral")
            self.btn_enviar.config(state=tk.NORMAL)
            self.combo_puertos.config(state=tk.DISABLED)
            self.entry_baudrate.config(state=tk.DISABLED)
            self.label_estado.config(text=f"🟢 Conectado: {puerto} @ {baudrate} baudios")
            
            # Habilitar solo los botones de comandos rápidos
            for btn in self.botones_rapidos:
                btn.config(state=tk.NORMAL)
            
            self.agregar_mensaje(f"✓ Conectado a {puerto} @ {baudrate} baudios", "exito")
            
            # Iniciar hilo de recepción
            self.hilo_rx = threading.Thread(target=self.recibir_datos, daemon=True)
            self.hilo_rx.start()
            
        except Exception as e:
            self.agregar_mensaje(f"✗ Error al conectar: {e}", "error")
    
    def desconectar(self):
        """Desconectar del puerto serial"""
        self.ejecutando = False
        
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        # Actualizar interfaz
        self.btn_conectar.config(text="🔌 Conectar", bg="lightgreen")
        self.btn_enviar.config(state=tk.DISABLED)
        self.combo_puertos.config(state='readonly')
        self.entry_baudrate.config(state=tk.NORMAL)
        self.label_estado.config(text="⚫ Desconectado")
        
        # Deshabilitar solo los botones de comandos rápidos
        for btn in self.botones_rapidos:
            btn.config(state=tk.DISABLED)
        
        self.agregar_mensaje("✓ Desconectado", "info")
    
    def recibir_datos(self):
        """Hilo que recibe datos continuamente"""
        while self.ejecutando:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    datos = self.ser.readline()
                    if datos:
                        mensaje = datos.decode('utf-8', 'ignore').strip()
                        if mensaje:
                            # Intentar parsear formato: altura;temperatura;presión;humedad
                            if ';' in mensaje and ">" in mensaje:
                                self.procesar_datos_sensor(mensaje)
                            else:
                                # Mensaje normal (como "hola mundo")
                                self.agregar_mensaje(f" {mensaje}", "error")
            except Exception as e:
                self.agregar_mensaje(f"✗ Error en recepción: {e}", "error")
                self.ejecutando = False
    
    def procesar_datos_sensor(self, mensaje):
        """Procesar datos con formato altura;temperatura;presión;humedad"""
        try:
            mensaje = mensaje.strip(">")
            partes = mensaje.split(';')
            if len(partes) == 4:
                altura = float(partes[0])
                temperatura = float(partes[1])
                presion = float(partes[2])
                humedad = float(partes[3])
                
                # Calcular tiempo transcurrido
                tiempo_actual = (datetime.now() - self.tiempo_inicial).total_seconds()
                
                # Agregar datos a las colas
                self.tiempos.append(tiempo_actual)
                self.alturas.append(altura)
                self.presiones.append(presion)
                self.humedades.append(humedad)
                self.temperaturas.append(temperatura)
                
                # Actualizar gráfico
                self.actualizar_grafico()
                
                # Actualizar labels con valores actuales
                self.label_altura.config(text=f"Alt: {altura:.2f} m")
                self.label_presion.config(text=f"Pres: {presion:.2f} hPa")
                self.label_humedad.config(text=f"Hum: {humedad:.2f} %")
                self.label_temperatura.config(text=f"Temp: {temperatura:.2f} °C")
                
                # Agregar al monitor
                self.agregar_mensaje(
                    f"{altura:.1f}m|{presion:.1f}hPa|{humedad:.1f}%|{temperatura:.1f}°C", 
                    "recibido"
                )
            else:
                self.agregar_mensaje(f" {mensaje}", "recibido")
        except ValueError:
            self.agregar_mensaje(f"⚠️ Formato inválido: {mensaje}", "error")
    
    def actualizar_grafico(self):
        """Actualizar el gráfico con los nuevos datos"""
        try:
            # Convertir deques a listas
            tiempos = list(self.tiempos)
            alturas = list(self.alturas)
            presiones = list(self.presiones)
            humedades = list(self.humedades)
            temperaturas = list(self.temperaturas)
            
            # Actualizar datos de las líneas
            self.line_altura.set_data(tiempos, alturas)
            self.line_presion.set_data(tiempos, presiones)
            self.line_humedad.set_data(tiempos, humedades)
            self.line_temperatura.set_data(tiempos, temperaturas)
            
            # Reescalar ejes si hay datos
            if tiempos:
                self.ax.relim()
                self.ax.autoscale_view()
            
            # Redibujar canvas
            self.canvas.draw()
        except Exception as e:
            print(f"Error actualizando gráfico: {e}")
    
    def limpiar_graficos(self):
        """Limpiar todos los datos del gráfico"""
        self.tiempos.clear()
        self.alturas.clear()
        self.presiones.clear()
        self.humedades.clear()
        self.temperaturas.clear()
        
        self.tiempo_inicial = datetime.now()
        
        # Limpiar líneas
        self.line_altura.set_data([], [])
        self.line_presion.set_data([], [])
        self.line_humedad.set_data([], [])
        self.line_temperatura.set_data([], [])
        
        # Resetear labels
        self.label_altura.config(text="Alt: -- m")
        self.label_presion.config(text="Pres: -- hPa")
        self.label_humedad.config(text="Hum: -- %")
        self.label_temperatura.config(text="Temp: -- °C")
        
        self.canvas.draw()
        self.agregar_mensaje("✓ Gráfico limpiado", "info")
    
    def enviar_comando(self):
        """Enviar comando desde el entry"""
        comando = self.entry_comando.get().strip()
        if comando:
            self.enviar_comando_rapido(comando)
            self.entry_comando.delete(0, tk.END)
    
    def enviar_comando_rapido(self, comando):
        """Enviar comando predefinido"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((comando + '\n').encode('utf-8'))
                self.agregar_mensaje(f"📤 {comando}", "enviado")
            except Exception as e:
                self.agregar_mensaje(f"✗ Error al enviar: {e}", "error")
    
    def agregar_mensaje(self, mensaje, tipo="info"):
        """Agregar mensaje al monitor con timestamp y color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        colores = {
            "recibido": "#00ff00",
            "enviado": "#00bfff",
            "error": "#ff4444",
            "exito": "#00ff00",
            "info": "#ffaa00"
        }
        
        color = colores.get(tipo, "#ffffff")
        
        self.text_monitor.config(state=tk.NORMAL)
        self.text_monitor.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        
        linea_actual = self.text_monitor.index("end-1c linestart")
        self.text_monitor.tag_add(tipo, linea_actual, "end-1c")
        self.text_monitor.tag_config(tipo, foreground=color)
        
        self.text_monitor.see(tk.END)
        self.text_monitor.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Manejar cierre de ventana"""
        if self.ejecutando:
            self.desconectar()
        self.root.destroy()

# Crear y ejecutar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = LoRaMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()