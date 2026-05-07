#include <SPI.h>
#include <RH_RF95.h>

#define RFM95_CS 8
#define RFM95_RST 4
#define RFM95_INT 7

#define RF95_FREQ 868.0

RH_RF95 rf95(RFM95_CS, RFM95_INT);

void setup() {
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  Serial.begin(115200);
  delay(1000);

  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  if (!rf95.init()) {
    Serial.println("ERREUR_INIT_LORA");
    while (1);
  }

  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("ERREUR_FREQ");
    while (1);
  }

  rf95.setTxPower(13, false);

  Serial.println("FEATHER_LORA_READY");
}

void loop() {
  // Raspberry -> USB -> LoRa
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg.length() > 0) {
      rf95.send((uint8_t *)msg.c_str(), msg.length());
      rf95.waitPacketSent();

      Serial.println("SENT:" + msg);
    }
  }

  // LoRa -> USB -> Raspberry
  if (rf95.available()) {
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      Serial.print("RECV:");
      for (uint8_t i = 0; i < len; i++) {
        Serial.print((char)buf[i]);
      }
      Serial.print("|RSSI:");
      Serial.println(rf95.lastRssi());
    }
  }
}
