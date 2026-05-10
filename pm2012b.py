# pm2012b.py – Driver MicroPython para Raspberry Pi Pico
# Adaptado desde el driver ESP-IDF original de Bettair Cities S.L.
# UART1: TX=GP4, RX=GP5 (ajusta los pines según tu cableado)

from machine import UART, Pin
import time
import struct

# ── Configuración ────────────────────────────────────────────────────────────

UART_ID   = 1   # LAS CAMBIO POR CODIGO DESDE MI PROPIO SCRIPT (Nota de Julen)
UART_TX   = 4   # GP4
UART_RX   = 5   # GP5
BAUDRATE  = 9600

# ── Utilidades ───────────────────────────────────────────────────────────────

def crc_calc(buffer: bytes) -> int:
    """CRC idéntico al original: suma los N-1 primeros bytes, devuelve 256-suma (mod 256)."""
    return (256 - sum(buffer)) & 0xFF

def make_u32(buf: bytes, offset: int) -> int:
    """Big-endian uint32 desde 4 bytes (igual que make_u32 en C)."""
    return struct.unpack_from(">I", buf, offset)[0]

# ── Clase principal ──────────────────────────────────────────────────────────

class PM2012B:

    def __init__(self, uart_id=UART_ID, tx=UART_TX, rx=UART_RX):
        self.uart = UART(
            uart_id,
            baudrate  = BAUDRATE,
            bits      = 8,
            parity    = None,
            stop      = 1,
            tx        = Pin(tx),
            rx        = Pin(rx),
            rxbuf     = 256,
        )
        self._samples = 0
        # Acumuladores de media (espejo de las variables *_final del original)
        self._avg = {k: 0.0 for k in
                     ("pc2_5", "pc0_3", "pc1", "pc10",
                      "PM1",   "PM2_5", "PM10")}

    # ── CRC helpers ──────────────────────────────────────────────────────────

    def _build_cmd(self, payload: list) -> bytes:
        """Construye comando con CRC al final."""
        buf = bytes(payload)
        return buf + bytes([crc_calc(buf)])

    # ── Comandos al sensor (misma secuencia que pm2012b_task) ────────────────

    def init_sensor(self):
        """Reproduce la secuencia de inicialización del task original."""

        time.sleep(2)
        #print("[PM2012B] Leyendo versión de firmware…")
        cmd = self._build_cmd([0x11, 0x01, 0x1E])
        self.uart.write(cmd)
        time.sleep(2)

        #print("[PM2012B] Configurando intervalo de medida (5 s)…")
        cmd = self._build_cmd([0x11, 0x03, 0x0D, 0x00, 0x05])
        self.uart.write(cmd)
        time.sleep(2)

        #print("[PM2012B] Activando modo continuo…")
        self._set_continuous_mode()
        #print("[PM2012B] Listo.")

    def _set_continuous_mode(self):
        cmd = self._build_cmd([0x11, 0x03, 0x0D, 0xFF, 0xFF])
        self.uart.write(cmd)

    def _request_measurement(self):
        cmd = self._build_cmd([0x11, 0x02, 0x0B, 0x07])
        self.uart.write(cmd)

    # ── Recepción y parseo ────────────────────────────────────────────────────

    def _read_frame(self, timeout_ms=2000) -> bytes | None:
        """
        Espera una trama válida:  0x16  <len=53>  0x0B  ...
        Devuelve los bytes crudos o None si hay timeout/error.
        """
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)

        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.uart.any():
                header = self.uart.read(1)
                if not header or header[0] != 0x16:
                    continue

                size_b = self.uart.read(1)
                if not size_b:
                    continue
                size = size_b[0]

                if size != 53:
                    # Vacía el resto y descarta
                    time.sleep_ms(50)
                    self.uart.read(self.uart.any())
                    continue

                # Leer el resto de la trama (size bytes)
                rest = self.uart.read(size)
                if not rest or len(rest) < size:
                    continue

                if rest[0] != 0x0B:   # tercer byte de la trama original
                    continue

                # Reconstruir el buffer completo (igual que uart_rx en el original)
                frame = bytes([0x16, size]) + rest   # total = 55 bytes
                return frame

            time.sleep_ms(10)

        return None   # timeout

    # ── Media acumulada (espejo exacto de pmb2012b_average_rt) ──────────────

    @staticmethod
    def _running_avg(n: int, value: float, mu: float) -> float:
        return (n * mu + value) / (n + 1)

    # ── Lectura pública ──────────────────────────────────────────────────────

    def get_data(self) -> dict | None:
        """
        Solicita una medida, parsea la respuesta y devuelve un diccionario
        con los mismos campos que el snprintf() del original.
        Devuelve None si no llega respuesta válida.
        """
        self._request_measurement()
        frame = self._read_frame()

        if frame is None:
            print("[PM2012B] Timeout – sin respuesta")
            return None

        # i=2 igual que en el original (offset base sobre uart_rx)
        i = 2
        pc0_3  = make_u32(frame, 25 + i)
        pc1    = make_u32(frame, 33 + i)
        pc2_5  = make_u32(frame, 37 + i)
        pc5    = make_u32(frame, 41 + i)
        pc10   = make_u32(frame, 45 + i)
        pm1_g  = make_u32(frame,  1 + i)
        pm2_5g = make_u32(frame,  5 + i)
        pm10_g = make_u32(frame,  9 + i)

        n = self._samples
        avg = self._avg

        avg["pc2_5"]  = self._running_avg(n, pc2_5,  avg["pc2_5"])
        avg["pc0_3"]  = self._running_avg(n, pc0_3,  avg["pc0_3"])
        avg["pc1"]    = self._running_avg(n, pc1,    avg["pc1"])
        avg["pc10"]   = self._running_avg(n, pc10,   avg["pc10"])
        avg["PM1"]    = self._running_avg(n, pm1_g,  avg["PM1"])
        avg["PM2_5"]  = self._running_avg(n, pm2_5g, avg["PM2_5"])
        avg["PM10"]   = self._running_avg(n, pm10_g, avg["PM10"])

        self._samples += 1

        return {
            "pm2_5"     : round(avg["pc2_5"], 2),   # PC2.5 (partículas/L)
            "pm0_3"     : round(avg["pc0_3"], 2),   # PC0.3
            "pm1"       : round(avg["pc1"],   2),   # PC1
            "pm10"      : round(avg["pc10"],  2),   # PC10
            "PM2_5"     : round(avg["PM2_5"], 2),   # PM2.5 µg/m³
            "PM1"       : round(avg["PM1"],   2),   # PM1   µg/m³
            "PM10"      : round(avg["PM10"],  2),   # PM10  µg/m³
            "pm_samples": self._samples,
            "pc5"       : pc5,                      # sin average en el original
        }

    def reset_averages(self):
        """Reinicia contadores (el original hace esto al final de pm2012b_get_data)."""
        self._samples = 0
        for k in self._avg:
            self._avg[k] = 0.0


# ── Programa principal ────────────────────────────────────────────────────────

if __name__ == "__main__":
    sensor = PM2012B(uart_id=1, tx=4, rx=5)
    sensor.init_sensor()

    cycle   = 0
    RESET_EVERY = 6   # igual que counter==6 en el original → cada ~30 s

    while True:
        data = sensor.get_data()

        if data:
            print(
                f'pm2_5={data["pm2_5"]:.2f}  pm0_3={data["pm0_3"]:.2f}  '
                f'pm1={data["pm1"]:.2f}  pm10={data["pm10"]:.2f}  '
                f'PM2_5={data["PM2_5"]:.2f} µg/m³  '
                f'PM1={data["PM1"]:.2f} µg/m³  '
                f'PM10={data["PM10"]:.2f} µg/m³  '
                f'samples={data["pm_samples"]}'
            )
        else:
            print("Sin datos.")

        cycle += 1
        if cycle >= RESET_EVERY:
            cycle = 0
            print("[PM2012B] Renovando modo continuo…")
            sensor._set_continuous_mode()
            sensor.reset_averages()

        time.sleep(5)   # intervalo igual al del original (5 s)