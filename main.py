#Código por Julen Moras Moreno, programador del CanSat SPIRA
#Forat Engineering, 2026.
import os
import uasyncio                                                                           
from machine import Pin, UART, I2C                                              
import time
from bme280 import BME280                        
import sdcard                                    
from pm2012b import PM2012B                


#BOMBAS 
b1 =Pin(28,Pin.OUT)
b1.value(0)
b2 =Pin(27,Pin.OUT)
b2.value(0)

time.sleep(3)

# ==========DECLARACIONES Y PRUEBAS================    
# Antes de cada declaracion, he añadido un pitido de buzzer:
# 1 pitido: LoRa
# 2 pitidos: SD
# 3 pitidos: BME280
# 4 pitidos: PM2012B
# Así, cuando haya un error y suene el pitido de error, podré saber rápidamente qué falla

#Buzzer y LED                                            
buzzer = Pin(22,Pin.OUT)                          
buzzer.value(0)
def Buzz(times):
    for i in range(times):
        buzzer.value(1)
        time.sleep(0.1)
        buzzer.value(0)
        time.sleep(0.1)   
    time.sleep(0.4)
def BuzzErr():
    for i in range(20):
        buzzer.value(1) 
        led.value(0)
        time.sleep(0.05)
        led.value(1)
        buzzer.value(0)
        time.sleep(0.05)
    time.sleep(0.5)               
                                                    
led = Pin(20,Pin.OUT)
led.value(1) 

#LoRa                                             
Buzz(1)
try:
    lora = UART(0,9600,tx = Pin(0),rx = Pin(1))
    lora.write(">>>>Estableciendo conexión...\n")
    time.sleep(0.1)
    print(">>> LoRa configurado correctamente.")
    t = time.localtime()
    
    time.sleep(0.1)
    lora.write(">>>>LoRa configurado correctamente\n")
except Exception as err:
    print(f">>> ERROR al configurar el LoRa. Código de error: {err}")

    BuzzErr()

#SD
Buzz(2)
filepath_log = "/sd/data/" + f"LOG.txt"
filepath_data = "/sd/data/" + f"DATA.csv" 
try:
    spi = machine.SPI(0, baudrate=400000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    cs = Pin(17, Pin.OUT)
    sd = sdcard.SDCard(spi, cs)
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
    t = time.localtime()
    

    with open(filepath_log , "w") as file:
        t = time.localtime()
        file.write("Log de datos SPIRA. Iniciado en t: " + f"[{t[3]}:{t[4]}:{t[5]}].\n")
    with open(filepath_data , "w") as file:
        t = time.localtime()
        file.write("Tiempo;Altitud;Temperatura;Presión;Humedad;PM1;PM2_5;PM10;pm0_3;pm2_5;pm10;pm_samples\n")

        
    print(">>> Log de datos creado con éxito")
    lora.write(">>>>Log de datos creado con éxito\n")
    with open(filepath_log,"a") as file:
        file.write(">>>> Log de datos creado con éxito.\n")
except Exception as err:
    print(f">>> ERROR en la creación del Log de datos. Código de error: {err}")
    lora.write(f">>>>ERROR en la creación del Log de datos. Código de error: {err}\n")
    BuzzErr()


#BME280

Buzz(3)

altitud_minima = 0

try:
    i2c = I2C(1,sda= Pin(2),scl= Pin(3),freq= 400000)
    bme = BME280(i2c=i2c)
    bme.sealevel = 101325 
    time.sleep(0.5)
    altitudes_minimas = []
    
    for i in range(20):
        bme.read_compensated_data()
        altitudes_minimas.append(bme.altitude)
    altitud_minima = round(sum(altitudes_minimas) / 20 ,1)
    
    print(f">>> BME280 configurado correctamente. Altitud mínima: {altitud_minima}. Sealevel = {bme.sealevel}")
    lora.write(f">>>>BME280 configurado correctamente. Altitud mínima: {altitud_minima}\n")
    try:
        with open(filepath_log,"a") as file:
            file.write(f">>>> BME280 configurado correctamente. Altitud mínima: {altitud_minima}.\n")
    except:
        pass
except Exception as err:
    print(f">>> ERROR al configurar el BME280. Código de error: {err}")
    lora.write(f">>>>ERROR al configurar el BME280. Código de error: {err}\n")
    try:
        with open(filepath_log,"a") as file:
            file.write(f">>>> ERROR al configurar el BME280. Código de error: {err}.\n")
    except:
        pass
    BuzzErr()

#PM2012B
Buzz(4)

UART_ID = 1
UART_TX = 8
UART_RX = 9
print(f">>> Iniciando PM2012B...")
lora.write(f">>>>Iniciando PM2012B...\n")
try:
    with open(filepath_log,"a") as file:
        file.write(f">>>> Iniciando PM2012B...\n")
except:
    pass

sensor = PM2012B(uart_id=UART_ID, tx=UART_TX, rx=UART_RX)
sensor.init_sensor()

# Check inicial PM2012B
intentos = 0
while intentos < 5:
    data = sensor.get_data()
    if data is not None:
        print(f">>> PM2012B configurado correctamente.")
        lora.write(f">>>>SM configurado correctamente.\n")
        try:
            with open(filepath_log,"a") as file:
                file.write(f">>>> PM2012B configurado correctamente.\n")
        except:
            pass
        break
    
    intentos += 1
    print(">>> Sin respuesta, intento {}/5...".format(intentos))
    lora.write(">>>>Sin respuesta, intento {}/5...\n".format(intentos))
    try:
        with open(filepath_log,"a") as file:
            file.write(">>>> Sin respuesta, intento {}/5...\n".format(intentos))
    except:
        pass
    time.sleep(3)
else:
    print(">>> ERROR: PM2012B no funciona.")
    lora.write(">>>>ERROR: PM2012B no funciona.\n")
    try:
        with open(filepath_log,"a") as file:
            file.write(">>>> ERROR: PM2012B no funciona.\n")
    except:
        pass
    BuzzErr()
    
sensor_data = {
    "PM1": 0.0, "PM2_5": 0.0, "PM10": 0.0,
    "pm0_3": 0, "pm2_5": 0, "pm10": 0,
    "pm_samples": 0, "ok": False
}





print("Módulo SPIRA inicializado.")
try:
    with open(filepath_log,"a") as file:
        file.write(">>>> Módulo SPIRA inicializado.\n")
except:
    pass
lora.write(">>>>Módulo OK.\n")
print(144*"_")

#=========================INICIO========================
#Aviso
led.value(0)
buzzer.value(1)
time.sleep(0.1)
buzzer.value(0)


alpha = 0.2
altitud_filtrada = None
def get_values(): #Te devuelve todos los valores parseados
    global altitud_filtrada
    
    t, p, h = bme.read_compensated_data()
    altitud_raw = 44330 * (1.0 - (p / bme.sealevel) ** 0.1903)
    
    if altitud_filtrada is None:
        altitud_filtrada = altitud_raw 
    else:
        altitud_filtrada = alpha * altitud_raw + (1 - alpha) * altitud_filtrada
    
    altitud = int(altitud_filtrada * 10) / 10
    temperatura = t
    presion = (p / 100)
    humedad = h
    
    return altitud, temperatura, presion, humedad

def get_time(): #Para poder devolver el tiempo actual de la siguiente forma: HH:MM:SS,ms
    t = time.localtime()
    ms = time.ticks_ms() % 1000  
    return f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d},{ms:03d}"

async def asyncError(val): #Mostrar el ERROR por hardware (ASÍNCRONO)
    for i in range(3):
        led.value(1)
        buzzer.value(0)
        await uasyncio.sleep(0.05)
        buzzer.value(1) 
        led.value(0)
        await uasyncio.sleep(0.05)
    buzzer.value(val)

async def sensor_task(sensor): #Obtener datos del PM2012B (ASÍNCRONO)
    global sensor_data
    while True:
        data = sensor.get_data()
        if data is not None:
            sensor_data.update(data)
            sensor_data["ok"] = True
        else:
            sensor_data["ok"] = False
        await uasyncio.sleep(5)

altitud_maxima = 0

async def main(): # MAIN LOOP (ASÍNCRONO)
    
    global altitud_minima      
    global altitud_maxima      
    global filepath_log
    global filepath_data
    global paquete
    global sensor_data
    max_tamaño_paquete = 10 # Para saber cada cuantos logs abrir la SD
    paquete = [] #Aqui se almacenan hasta "max_tamaño_paquete" lineas en la flash

    descendiendo = False
    umbral = False                       #Para saber si hemos cruzado el umbral y solo mandar 1 LOG
    b1_open = False
    b2_open = False
    #Parámetros de control de las bombas de aire
    trigger_ascenso = 100                  # Altitud minima en la cual se sabe que hemos despegado! 
    margen_error_descenso = 10             # Un margen para asegurarse de que estamos descendiendo
    metros_encendido = 200                 # Los metros que cada bomba permanecera encendida
    
    cycle = 0
    RENEW_MODE_AT = 6
    uasyncio.create_task(sensor_task(sensor))

    while True:
        try:
            a,t,p,h = get_values()
            timestamp = get_time()
            altitud_relativa = a-altitud_minima
            if altitud_relativa < 0: altitud_relativa = 0.00 #ASI NO HAY NEGATIVOS
            
            print(altitud_relativa, t, p, h, sensor_data["PM1"], sensor_data["PM2_5"], sensor_data["PM10"], sensor_data["pm0_3"], sensor_data["pm2_5"], sensor_data["pm10"], sensor_data["pm_samples"])          
            lora.write(f">>>>{round(altitud_relativa,2)};{round(t,2)};{round(p,2)};{round(h,2)}\n")
            
            if not descendiendo:
                if altitud_relativa > trigger_ascenso:  #UMBRAL PARA SABER SI HA DESPEGADO
                    if not umbral:
                        buzzer.value(1) # Enciende el buzzer de localización
                        lora.write(">>>>Comienza el juego\n")
                        print(">>> Comienza el juego")
                        try:
                            with open(filepath_log,"a") as file:
                                file.write(f">>>> [{timestamp}] SUPERAMOS LOS {trigger_ascenso} METROS. ¡Comienza el juego!\n")
                        except:
                            pass
                        umbral = True
                    if altitud_relativa > altitud_maxima:
                        altitud_maxima = altitud_relativa # Se va reescribiendo altitud_maxima
                        
                    elif altitud_maxima - altitud_relativa >= margen_error_descenso: #Aqui ya ha comenzado a caer
                        descendiendo = True
                        b1.value(1)
                        b1_open = True
                        print(f"[{timestamp}] Bomba 1 abierta en altitud {altitud_relativa} metros.")
                        lora.write(f">>>>B1 ON en {a}m\n")
                        try:
                            with open(filepath_log,"a") as file:
                                file.write(f">>>> [{timestamp}] Bomba 1 abierta en altitud {altitud_relativa} metros.\n")
                        except:
                            pass
                        
            else:
                if altitud_relativa <= altitud_maxima - metros_encendido: #Si estamos a menor altura que altura_maxima - "metros_encendido" de actividad
                    if altitud_relativa > altitud_maxima / 2: # si estamos por encima de la mitad               
                        if b1_open:
                            b1.value(0)
                            b1_open = False
                            print(f"[{timestamp}] Bomba 1 cerrada en altitud {altitud_relativa} metros.")
                            lora.write(f">>>>B1 OFF en {a}m\n")
                            try:
                                with open(filepath_log,"a") as file:
                                    file.write(f">>>> [{timestamp}] Bomba 1 cerrada en altitud {altitud_relativa} metros.\n")
                            except:
                                pass
                    elif altitud_relativa <= altitud_maxima / 2: # Si estamos debajo de la mitad
                        if altitud_relativa > (altitud_maxima / 2) - metros_encendido: #Si estamos por encima de la mitad - "metros_encendido"
                            if not b2_open:
                                b2.value(1)
                                b2_open = True
                                print(f"[{timestamp}] Bomba 2 abierta en altitud {altitud_relativa} metros.")
                                lora.write(f">>>>B2 ON en {a}m\n")
                                try:
                                    with open(filepath_log,"a") as file:
                                        file.write(f">>>> [{timestamp}] Bomba 2 abierta en altitud {altitud_relativa} metros.\n")
                                except:
                                    pass
                        elif altitud_relativa <= (altitud_maxima / 2) - metros_encendido: # Si bajamos de la mitad - "metros_encendido"
                            if b2_open:
                                b2.value(0)
                                b2_open = False
                                print(f"[{timestamp}] Bomba 2 cerrada en altitud {altitud_relativa} metros.")
                                lora.write(f">>>>B2 OFF en {a}m\n")
                                try:
                                    with open(filepath_log,"a") as file:
                                        file.write(f">>>> [{timestamp}] Bomba 2 cerrada en altitud {altitud_relativa} metros.\n")
                                except:
                                    pass
                        
            if len(paquete) < max_tamaño_paquete:
                #paquete.append(f"{timestamp};{altitud_relativa};{t};{p};{h}")
                paquete.append(f"{timestamp};{altitud_relativa};{t};{p};{h};{sensor_data['PM1']};{sensor_data['PM2_5']};{sensor_data['PM10']};{sensor_data['pm0_3']};{sensor_data['pm2_5']};{sensor_data['pm10']};{sensor_data['pm_samples']}")
            else:
                with open(filepath_data, "a")as file:
                    for i in paquete:
                        file.write(i+"\n")
                paquete = []
        
            
        except Exception as e:
            print("ERROR en Main() :",e)
            try:
                with open(filepath_log,"a") as file:
                    file.write(">>>> ERROR en Main() : "+str(e)+"\n")
            except Exception as e2:
                print(e2)
                
            lora.write(">>>>"+str(e)+"\n")
            uasyncio.create_task(asyncError(buzzer.value()))
        await uasyncio.sleep(0.1)
            
        
    


uasyncio.run(main())
