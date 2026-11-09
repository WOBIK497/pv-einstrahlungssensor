var NAME = "Einstr-Sued";     // für Südwest und West anpassen
var PIN_SHUNT = D31;           // über R3 an den Shunt R1
var PIN_KOND = D30;            // Mitte des Teilers R4/R5
var MESSUNG_MS = 3000;         // alle 3 s messen, so oft wie der Solakon die Strings meldet

function mittel(pin) {
  var s = 0;
  for (var i = 0; i < 16; i++) s += analogRead(pin);
  return s / 16;
}

function senden() {
  var vdd = E.getAnalogVRef();               // aktuelle Betriebsspannung
  var uShunt = mittel(PIN_SHUNT) * vdd;      // Volt am Shunt
  var uKond = mittel(PIN_KOND) * vdd * 2;    // Volt am Superkondensator
  var k = Math.round(uKond * 10);            // 0,1-V-Schritte für Objekt 0x4A
  NRF.setAdvertising(require("BTHome").getAdvertisement([
    { type: "voltage", v: uShunt },
    { type: "raw", v: [0x4A, k & 255, k >> 8] }
  ]), { name: NAME, interval: 1000, manufacturer: false });  // jede Sekunde funken
}

function onInit() {
  senden();
  setInterval(senden, MESSUNG_MS);
}
