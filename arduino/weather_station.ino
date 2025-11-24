#include "DHT.h"
#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
  // Добавь индикацию, что все работает
  Serial.println("Arduino started with DHT11");
}

void loop() {
  delay(2000);
  
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("{\"error\": \"Sensor reading failed\"}");
    return;
  }

  // Убедись, что отправляется ВАЛИДНЫЙ JSON
  Serial.print("{\"temperature\": ");
  Serial.print(temperature);
  Serial.print(", \"humidity\": ");
  Serial.print(humidity);
  Serial.println("}");
  
  // Добавь индикацию работы
  Serial.println("Data sent");
}