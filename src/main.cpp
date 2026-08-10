/*
 * Catan Dice - ESP8266 D1 Mini
 *
 * Hardware:
 *   - Switch on D5 (GPIO14): LOW = AP mode, HIGH = STA (home WiFi) mode
 *   - Push button on D6 (GPIO12): active LOW (pull-up), rolls the dice (HTTP GET)
 *
 * Configuration is stored in LittleFS as /config.json
 * Web UI is served from LittleFS (/index.html)
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

// ── Pin definitions ──────────────────────────────────────────────────────────
static const uint8_t PIN_MODE_SWITCH = D5; // LOW = AP, HIGH = STA
static const uint8_t PIN_BUTTON      = D6; // active LOW

// ── Configuration defaults ───────────────────────────────────────────────────
struct Config {
    // AP mode
    char apSsid[32]     = "CatanDice";
    char apPassword[64] = "catandice";
    char urlAp[256]     = "http://192.168.4.1/roll"; // called when in AP mode

    // STA (home WiFi) mode
    char staSsid[32]     = "";
    char staPassword[64] = "";
    char urlSta[256]     = "http://192.168.1.100/roll"; // called when in STA mode
};

static Config cfg;
static ESP8266WebServer server(80);
static bool apMode = false;

// ── Config persistence ───────────────────────────────────────────────────────
static const char* CONFIG_FILE = "/config.json";

void loadConfig() {
    if (!LittleFS.exists(CONFIG_FILE)) return;
    File f = LittleFS.open(CONFIG_FILE, "r");
    if (!f) return;

    StaticJsonDocument<512> doc;
    if (deserializeJson(doc, f) != DeserializationError::Ok) { f.close(); return; }
    f.close();

    strlcpy(cfg.apSsid,      doc["apSsid"]      | cfg.apSsid,      sizeof(cfg.apSsid));
    strlcpy(cfg.apPassword,  doc["apPassword"]  | cfg.apPassword,  sizeof(cfg.apPassword));
    strlcpy(cfg.urlAp,       doc["urlAp"]       | cfg.urlAp,       sizeof(cfg.urlAp));
    strlcpy(cfg.staSsid,     doc["staSsid"]     | cfg.staSsid,     sizeof(cfg.staSsid));
    strlcpy(cfg.staPassword, doc["staPassword"] | cfg.staPassword,  sizeof(cfg.staPassword));
    strlcpy(cfg.urlSta,      doc["urlSta"]      | cfg.urlSta,       sizeof(cfg.urlSta));
}

void saveConfig() {
    File f = LittleFS.open(CONFIG_FILE, "w");
    if (!f) return;

    StaticJsonDocument<512> doc;
    doc["apSsid"]      = cfg.apSsid;
    doc["apPassword"]  = cfg.apPassword;
    doc["urlAp"]       = cfg.urlAp;
    doc["staSsid"]     = cfg.staSsid;
    doc["staPassword"] = cfg.staPassword;
    doc["urlSta"]      = cfg.urlSta;

    serializeJson(doc, f);
    f.close();
}

// ── HTTP GET to roll URL ─────────────────────────────────────────────────────
void rollDice() {
    const char* url = apMode ? cfg.urlAp : cfg.urlSta;
    if (strlen(url) == 0) {
        Serial.println("[roll] URL not configured");
        return;
    }
    Serial.printf("[roll] GET %s\n", url);

    WiFiClient client;
    HTTPClient http;
    if (http.begin(client, url)) {
        int code = http.GET();
        Serial.printf("[roll] response: %d\n", code);
        http.end();
    } else {
        Serial.println("[roll] http.begin() failed");
    }
}

// ── Web UI handlers ──────────────────────────────────────────────────────────
void handleRoot() {
    if (LittleFS.exists("/index.html")) {
        File f = LittleFS.open("/index.html", "r");
        server.streamFile(f, "text/html");
        f.close();
    } else {
        server.send(200, "text/plain", "UI not found. Flash filesystem.");
    }
}

void handleGetConfig() {
    StaticJsonDocument<512> doc;
    doc["apSsid"]      = cfg.apSsid;
    doc["apPassword"]  = cfg.apPassword;
    doc["urlAp"]       = cfg.urlAp;
    doc["staSsid"]     = cfg.staSsid;
    doc["staPassword"] = cfg.staPassword;
    doc["urlSta"]      = cfg.urlSta;
    doc["mode"]        = apMode ? "ap" : "sta";

    String out;
    serializeJson(doc, out);
    server.send(200, "application/json", out);
}

void handleSaveConfig() {
    if (!server.hasArg("plain")) { server.send(400, "text/plain", "No body"); return; }

    StaticJsonDocument<512> doc;
    if (deserializeJson(doc, server.arg("plain")) != DeserializationError::Ok) {
        server.send(400, "text/plain", "Invalid JSON");
        return;
    }

    if (doc.containsKey("apSsid"))      strlcpy(cfg.apSsid,      doc["apSsid"],      sizeof(cfg.apSsid));
    if (doc.containsKey("apPassword"))  strlcpy(cfg.apPassword,  doc["apPassword"],  sizeof(cfg.apPassword));
    if (doc.containsKey("urlAp"))       strlcpy(cfg.urlAp,       doc["urlAp"],       sizeof(cfg.urlAp));
    if (doc.containsKey("staSsid"))     strlcpy(cfg.staSsid,     doc["staSsid"],     sizeof(cfg.staSsid));
    if (doc.containsKey("staPassword")) strlcpy(cfg.staPassword, doc["staPassword"], sizeof(cfg.staPassword));
    if (doc.containsKey("urlSta"))      strlcpy(cfg.urlSta,      doc["urlSta"],      sizeof(cfg.urlSta));

    saveConfig();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
}

void handleRoll() {
    rollDice();
    server.send(200, "application/json", "{\"status\":\"rolling\"}");
}

// ── WiFi setup ───────────────────────────────────────────────────────────────
void startAP() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(cfg.apSsid, cfg.apPassword);
    Serial.printf("[wifi] AP started: SSID=%s  IP=%s\n",
                  cfg.apSsid, WiFi.softAPIP().toString().c_str());
}

void startSTA() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(cfg.staSsid, cfg.staPassword);
    Serial.printf("[wifi] Connecting to %s", cfg.staSsid);
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
        delay(500);
        Serial.print('.');
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[wifi] Connected  IP=%s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[wifi] STA failed, falling back to AP");
        startAP();
        apMode = true;
    }
}

// ── Arduino entry points ─────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(200);

    pinMode(PIN_MODE_SWITCH, INPUT_PULLUP);
    pinMode(PIN_BUTTON,      INPUT_PULLUP);

    if (!LittleFS.begin()) {
        Serial.println("[fs] LittleFS mount failed");
    }
    loadConfig();

    // Read switch: LOW = AP mode
    apMode = (digitalRead(PIN_MODE_SWITCH) == LOW);
    Serial.printf("[mode] %s\n", apMode ? "AP" : "STA");

    if (apMode) {
        startAP();
    } else {
        startSTA();
    }

    server.on("/",           HTTP_GET,  handleRoot);
    server.on("/config",     HTTP_GET,  handleGetConfig);
    server.on("/config",     HTTP_POST, handleSaveConfig);
    server.on("/roll",       HTTP_POST, handleRoll);

    // Serve static files from LittleFS
    server.onNotFound([]() {
        String path = server.uri();
        if (LittleFS.exists(path)) {
            File f = LittleFS.open(path, "r");
            String mime = "text/plain";
            if (path.endsWith(".html")) mime = "text/html";
            else if (path.endsWith(".css"))  mime = "text/css";
            else if (path.endsWith(".js"))   mime = "application/javascript";
            else if (path.endsWith(".json")) mime = "application/json";
            server.streamFile(f, mime);
            f.close();
        } else {
            server.send(404, "text/plain", "Not found");
        }
    });

    server.begin();
    Serial.println("[http] Server started on port 80");
}

// Button debounce state
static bool     lastButtonState  = HIGH;
static unsigned long lastDebounce = 0;
static const unsigned long DEBOUNCE_MS = 50;

void loop() {
    server.handleClient();

    // Debounced button read
    bool reading = digitalRead(PIN_BUTTON);
    if (reading != lastButtonState) {
        lastDebounce = millis();
    }
    if (millis() - lastDebounce > DEBOUNCE_MS) {
        static bool buttonPressed = false;
        if (reading == LOW && !buttonPressed) {
            buttonPressed = true;
            rollDice();
        } else if (reading == HIGH) {
            buttonPressed = false;
        }
    }
    lastButtonState = reading;
}
