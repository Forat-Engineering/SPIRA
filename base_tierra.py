from machine import UART, Pin
import time

lora = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
led = Pin(22,Pin.OUT)
led.value(0)

buffer = ""

while True:
    
    if lora.any():
        data = lora.readline().decode()

        buffer += data
        
        while "\n" in buffer:
            linea, buffer = buffer.split("\n", 1)
            if linea.count(">>>>") <=1:
                if linea.startswith(">"):
                    led.value(1)
                    print(linea)
                    time.sleep(0.05)
                    led.value(0)





