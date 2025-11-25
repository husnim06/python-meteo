#include "DHT.h"

// Конфигурация
#define DHTPIN 2
#define DHTTYPE DHT11
#define SERIAL_BAUD 9600
#define READING_INTERVAL 2000
#define SERIAL_STABILIZE_DELAY 2000

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(SERIAL_BAUD);
  // Ждем стабилизации serial соединения
  delay(SERIAL_STABILIZE_DELAY);
  dht.begin();
  Serial.println("{\"status\": \"Arduino DHT11 started\"}");
}

void loop() {
  delay(READING_INTERVAL);

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("{\"error\": \"Sensor reading failed\"}");
    return;
  }

  Serial.print("{\"temperature\": ");
  Serial.print(temperature);
  Serial.print(", \"humidity\": ");
  Serial.print(humidity);
  Serial.println("}");
}
