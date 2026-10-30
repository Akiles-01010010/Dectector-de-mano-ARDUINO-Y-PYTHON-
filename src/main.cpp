#include <Arduino.h>

// Buzzer PASIVO en el pin 9 (el activo solo hace "bip", no puede tocar melodías).
// LED en el pin 13: se queda prendido mientras algo esté cerca o la cámara vea la mano abierta.
// Sensor ultrasónico HC-SR04: Trig en el pin 7, Echo en el pin 6.
// Cámara: el programa de la carpeta python manda por USB '1' (mano abierta) o '0' (no).
const int PIN_BUZZER = 9;
const int PIN_LED = 13;
const int PIN_TRIG = 7;
const int PIN_ECHO = 6;

// Distancia (cm) a la que se activa la alarma
const float DISTANCIA_ACTIVACION = 50.0;

// Si la cámara deja de mandar órdenes por este tiempo (ms), se apaga sola
// (por ejemplo, si cierras el programa de Python).
const unsigned long TIEMPO_SIN_CAMARA = 1000;

// Frecuencias de las notas (Hz)
const int MI = 659;
const int FA_S = 740;   // fa#
const int SOL = 784;
const int LA = 880;
const int SI = 988;
// Notas agudas (las que llevan ' en el video: una octava más alto)
const int DO_A = 1047;   // do'
const int RE_A = 1175;   // re'
const int MI_A = 1319;   // mi'
const int FA_S_A = 1480; // fa#'
const int SOL_A = 1568;  // sol'

// Duración de un tiempo en milisegundos.
// Más chico = más rápido, más grande = más lento.
const int TIEMPO = 300;

// Rosa Pastel (Belanova), notas del tutorial de flauta.
// Cada nota: {frecuencia, duración en tiempos} (1 = normal, 2 = larga)
const int melodia[][2] = {
  // si do' si sol' fa#' fa#' si do' re'
  {SI, 1}, {DO_A, 1}, {SI, 1}, {SOL_A, 1}, {FA_S_A, 1}, {FA_S_A, 1}, {SI, 1}, {DO_A, 1}, {RE_A, 2},
  // mi mi fa# sol la si do' si sol'
  {MI, 1}, {MI, 1}, {FA_S, 1}, {SOL, 1}, {LA, 1}, {SI, 1}, {DO_A, 1}, {SI, 1}, {SOL_A, 2},
  // fa#' fa#' si mi' re' mi mi fa# sol
  {FA_S_A, 1}, {FA_S_A, 1}, {SI, 1}, {MI_A, 1}, {RE_A, 1}, {MI, 1}, {MI, 1}, {FA_S, 1}, {SOL, 2},
  // la si do' si re' si mi' re' re' si mi'
  {LA, 1}, {SI, 1}, {DO_A, 1}, {SI, 1}, {RE_A, 1}, {SI, 1}, {MI_A, 1}, {RE_A, 1}, {RE_A, 1}, {SI, 1}, {MI_A, 2},
  // re' re' si si do' re' do' si sol re' si
  {RE_A, 1}, {RE_A, 1}, {SI, 1}, {SI, 1}, {DO_A, 1}, {RE_A, 1}, {DO_A, 1}, {SI, 1}, {SOL, 1}, {RE_A, 1}, {SI, 2},
  // mi' re' re' si mi' re' re' mi mi fa#
  {MI_A, 1}, {RE_A, 1}, {RE_A, 1}, {SI, 1}, {MI_A, 1}, {RE_A, 1}, {RE_A, 1}, {MI, 1}, {MI, 1}, {FA_S, 2},
  // sol la si do' si si sol do' si si
  {SOL, 1}, {LA, 1}, {SI, 1}, {DO_A, 1}, {SI, 1}, {SI, 1}, {SOL, 1}, {DO_A, 1}, {SI, 1}, {SI, 2},
};
const int TOTAL_NOTAS = sizeof(melodia) / sizeof(melodia[0]);

// Nota que toca a continuación (para seguir la canción donde se quedó)
int notaActual = 0;

// Última orden recibida de la cámara y cuándo llegó
bool manoAbierta = false;
unsigned long ultimaOrdenCamara = 0;

// Lee las órdenes que manda el programa de Python ('1' = mano abierta, '0' = no).
// Devuelve true si la cámara está viendo la mano abierta ahora mismo.
bool leerCamara() {
  while (Serial.available() > 0) {
    char orden = Serial.read();
    if (orden == '1' || orden == '0') {
      manoAbierta = (orden == '1');
      ultimaOrdenCamara = millis();
    }
  }
  bool camaraConectada = millis() - ultimaOrdenCamara < TIEMPO_SIN_CAMARA;
  return manoAbierta && camaraConectada;
}

// Mide la distancia en cm. Devuelve -1 si no detecta nada (fuera de alcance).
float medirDistancia() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  unsigned long tiempoEco = pulseIn(PIN_ECHO, HIGH, 30000);  // espera máx. 30 ms
  if (tiempoEco == 0) {
    return -1;
  }
  return tiempoEco * 0.0343 / 2;  // velocidad del sonido, ida y vuelta
}

void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  Serial.begin(9600);  // para ver la distancia en el Serial Monitor
}

void loop() {
  float distancia = medirDistancia();
  Serial.print("Distancia: ");
  Serial.print(distancia);
  Serial.println(" cm");

  bool cerca = distancia > 0 && distancia <= DISTANCIA_ACTIVACION;
  bool manoEnCamara = leerCamara();

  if (cerca || manoEnCamara) {
    digitalWrite(PIN_LED, HIGH);  // LED fijo mientras esté activado

    int duracion = melodia[notaActual][1] * TIEMPO;
    tone(PIN_BUZZER, melodia[notaActual][0], duracion * 0.9);  // 90% sonando, 10% silencio
    delay(duracion);

    notaActual++;
    if (notaActual >= TOTAL_NOTAS) {
      notaActual = 0;  // vuelve a empezar la canción
    }
  } else {
    digitalWrite(PIN_LED, LOW);
    noTone(PIN_BUZZER);
    notaActual = 0;  // la próxima vez empieza desde el principio
    delay(60);       // pausa corta entre mediciones
  }
}
