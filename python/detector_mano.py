"""
Detector de mano abierta con la cámara.

Cuenta los dedos levantados con la cámara y, cuando ve los 5 dedos,
le avisa al Arduino por USB para que suene Rosa Pastel y prenda el LED.

  - Manda '1' cuando ve la mano abierta (5 dedos) y '0' cuando no.
  - Para salir: presiona Q o ESC en la ventana de la cámara.
"""

import math
import sys
import time

import cv2
import mediapipe as mp
import serial
import serial.tools.list_ports

# ---------------- Configuración ----------------

# Puerto del Arduino. None = lo busca solo (chip CH340 u otro Arduino).
# Si no lo encuentra, escríbelo a mano, por ejemplo: PUERTO = "COM3"
PUERTO = None
VELOCIDAD = 9600  # debe ser igual a Serial.begin(9600) del Arduino

CAMARA = 0  # 0 = cámara de la laptop. Si tienes otra cámara USB, prueba con 1

DEDOS_PARA_ACTIVAR = 5

# Cuántos cuadros seguidos debe ver la mano abierta antes de activar
# (evita que suene por un parpadeo de la detección)
CUADROS_PARA_ACTIVAR = 4
CUADROS_PARA_DESACTIVAR = 4

# Cada cuánto se le recuerda el estado al Arduino (segundos).
# El Arduino se apaga solo si deja de recibir órdenes por 1 segundo.
INTERVALO_ENVIO = 0.15

# -----------------------------------------------

# Puntos de MediaPipe: 0 = muñeca, luego 4 por dedo (base → punta)
MUNECA = 0
PULGAR_IP, PULGAR_PUNTA = 3, 4
MENIQUE_BASE = 17
# (articulación media, punta) de índice, medio, anular y meñique
DEDOS = [(6, 8), (10, 12), (14, 16), (18, 20)]


def distancia(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def contar_dedos(puntos):
    """Cuenta los dedos levantados. Funciona aunque la mano esté inclinada."""
    levantados = 0

    # Un dedo está levantado si su punta está más lejos de la muñeca que su articulación media
    for articulacion, punta in DEDOS:
        if distancia(puntos[punta], puntos[MUNECA]) > distancia(puntos[articulacion], puntos[MUNECA]):
            levantados += 1

    # El pulgar se dobla hacia el meñique: está abierto si su punta queda lejos de la base del meñique
    if distancia(puntos[PULGAR_PUNTA], puntos[MENIQUE_BASE]) > distancia(puntos[PULGAR_IP], puntos[MENIQUE_BASE]):
        levantados += 1

    return levantados


def buscar_puerto():
    if PUERTO:
        return PUERTO
    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        descripcion = f"{p.description} {p.manufacturer or ''}".lower()
        if p.vid == 0x1A86 or "arduino" in descripcion or "ch340" in descripcion:
            return p.device
    if len(puertos) == 1:
        return puertos[0].device
    return None


def conectar_arduino():
    puerto = buscar_puerto()
    if puerto is None:
        print("No encontré el Arduino. Revisa que esté conectado por USB,")
        print("o escribe el puerto en PUERTO = \"COM3\" al inicio de este archivo.")
        sys.exit(1)

    try:
        arduino = serial.Serial(puerto, VELOCIDAD, timeout=0)
    except serial.SerialException as error:
        print(f"No pude abrir {puerto}: {error}")
        print("Cierra el Serial Monitor de VS Code (o cualquier programa que use el puerto) e intenta de nuevo.")
        sys.exit(1)

    print(f"Arduino conectado en {puerto}. Esperando a que reinicie...")
    time.sleep(2)  # el Arduino se reinicia al abrir el puerto
    arduino.reset_input_buffer()
    return arduino


def abrir_camara():
    camara = cv2.VideoCapture(CAMARA, cv2.CAP_DSHOW)
    if not camara.isOpened():
        camara = cv2.VideoCapture(CAMARA)
    if not camara.isOpened():
        print(f"No pude abrir la cámara {CAMARA}. Revisa que no la esté usando otro programa.")
        sys.exit(1)
    return camara


def main():
    arduino = conectar_arduino()
    camara = abrir_camara()

    detector = mp.solutions.hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )
    dibujo = mp.solutions.drawing_utils
    conexiones = mp.solutions.hands.HAND_CONNECTIONS

    activo = False
    cuadros_abierta = 0
    cuadros_cerrada = 0
    ultimo_envio = 0.0

    print("Listo. Muestra tu mano abierta a la cámara. Presiona Q o ESC para salir.")

    try:
        while True:
            ok, cuadro = camara.read()
            if not ok:
                print("La cámara dejó de mandar imagen.")
                break

            cuadro = cv2.flip(cuadro, 1)  # efecto espejo, más natural
            resultado = detector.process(cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB))

            dedos = 0
            if resultado.multi_hand_landmarks:
                mano = resultado.multi_hand_landmarks[0]
                dibujo.draw_landmarks(cuadro, mano, conexiones)
                dedos = contar_dedos(mano.landmark)

            if dedos == DEDOS_PARA_ACTIVAR:
                cuadros_abierta += 1
                cuadros_cerrada = 0
            else:
                cuadros_cerrada += 1
                cuadros_abierta = 0

            if not activo and cuadros_abierta >= CUADROS_PARA_ACTIVAR:
                activo = True
                print("Mano abierta: SONANDO")
            elif activo and cuadros_cerrada >= CUADROS_PARA_DESACTIVAR:
                activo = False
                print("Mano cerrada: en silencio")

            ahora = time.time()
            if ahora - ultimo_envio >= INTERVALO_ENVIO:
                arduino.write(b"1" if activo else b"0")
                ultimo_envio = ahora
            arduino.reset_input_buffer()  # descarta los mensajes de distancia del Arduino

            # Texto en pantalla (OpenCV no muestra acentos)
            color = (0, 200, 0) if activo else (0, 0, 255)
            cv2.putText(cuadro, f"Dedos: {dedos}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            estado = "SONANDO" if activo else "Silencio (muestra 5 dedos)"
            cv2.putText(cuadro, estado, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            cv2.putText(cuadro, "Q o ESC para salir", (20, cuadro.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("Detector de mano - Arduino", cuadro)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                break
            if cv2.getWindowProperty("Detector de mano - Arduino", cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        arduino.write(b"0")  # deja el Arduino en silencio al salir
        arduino.close()
        camara.release()
        detector.close()
        cv2.destroyAllWindows()
        print("Programa cerrado.")


if __name__ == "__main__":
    main()
