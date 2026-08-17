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

// Constants for button debounce state
static bool     lastButtonState  = HIGH;
static unsigned long lastDebounce = 0;
static const unsigned long DEBOUNCE_MS = 50;

// Pin definitions 
static const uint8_t PIN_BUTTON      = D5; // active LOW (Push button to roll dice)

// Config defaults
struct Config {
    // Ad-hoc AP mode
    char apSsid[32]     = "CatanDice";
    char apPassword[64] = "catandice";

    // STA profile 1 (home WiFi)
    char staLocalCatanSsid[32]     = "";
    char staLocalCatanPassword[64] = "";

    // STA profile 2 (secondary WiFi)
    char staHomeSsid[32]     = "";
    char staHomePassword[64] = "";

    // Preferred first profile when connecting in STA mode (1 or 2)
    uint8_t staPrimary    = 1;

    char urlLocalCatanSta[256] = "http://192.168.4.1/rollDice"; // called when in STA mode
    char urlHomeSta[256]       = "http://catan.mydomain.eu/rollDice"; // called when in STA mode
};

static Config cfg;
static ESP8266WebServer server(80);
static bool apMode = false;

// Config persistence
static const char* CONFIG_FILE = "/config.json";

void loadConfig() {
    if (!LittleFS.exists(CONFIG_FILE)) return;
    File f = LittleFS.open(CONFIG_FILE, "r");
    if (!f) return;

    StaticJsonDocument<768> doc;
    if (deserializeJson(doc, f) != DeserializationError::Ok) { f.close(); return; }
    f.close();

    strlcpy(cfg.apSsid,      doc["apSsid"]      | cfg.apSsid,      sizeof(cfg.apSsid));
    strlcpy(cfg.apPassword,  doc["apPassword"]  | cfg.apPassword,  sizeof(cfg.apPassword));
    strlcpy(cfg.staLocalCatanSsid,     doc["staLocalCatanSsid"]     | cfg.staLocalCatanSsid,     sizeof(cfg.staLocalCatanSsid));
    strlcpy(cfg.staLocalCatanPassword, doc["staLocalCatanPassword"] | cfg.staLocalCatanPassword,  sizeof(cfg.staLocalCatanPassword));
    strlcpy(cfg.staHomeSsid,    doc["staHomeSsid"]    | cfg.staHomeSsid,    sizeof(cfg.staHomeSsid));
    strlcpy(cfg.staHomePassword,doc["staHomePassword"]| cfg.staHomePassword,sizeof(cfg.staHomePassword));
    
    cfg.staPrimary = doc["staPrimary"] | cfg.staPrimary;
    if (cfg.staPrimary != 1 && cfg.staPrimary != 2) cfg.staPrimary = 1;
    strlcpy(cfg.urlLocalCatanSta, doc["urlLocalCatanSta"] | cfg.urlLocalCatanSta, sizeof(cfg.urlLocalCatanSta));
    strlcpy(cfg.urlHomeSta,       doc["urlHomeSta"]       | cfg.urlHomeSta,       sizeof(cfg.urlHomeSta)); 
}

void saveConfig() {
    File f = LittleFS.open(CONFIG_FILE, "w");
    if (!f) return;

    StaticJsonDocument<768> doc;
    doc["apSsid"]      = cfg.apSsid;
    doc["apPassword"]  = cfg.apPassword;
    doc["staLocalCatanSsid"]     = cfg.staLocalCatanSsid;
    doc["staLocalCatanPassword"] = cfg.staLocalCatanPassword;
    doc["staHomeSsid"]    = cfg.staHomeSsid;
    doc["staHomePassword"] = cfg.staHomePassword;
    doc["staPrimary"]  = cfg.staPrimary;
    doc["urlLocalCatanSta"] = cfg.urlLocalCatanSta;
    doc["urlHomeSta"]       = cfg.urlHomeSta;

    serializeJson(doc, f);
    f.close();
}

// HTTP GET to roll URL 
void rollDice() {

    const char* url = (apMode || cfg.staPrimary == 1) ? cfg.urlLocalCatanSta : cfg.urlHomeSta;
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

//  Web UI handlers 
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
    StaticJsonDocument<768> doc;
    doc["apSsid"]      = cfg.apSsid;
    doc["apPassword"]  = cfg.apPassword;
    doc["staLocalCatanSsid"]     = cfg.staLocalCatanSsid;
    doc["staLocalCatanPassword"] = cfg.staLocalCatanPassword;
    doc["staHomeSsid"]    = cfg.staHomeSsid;
    doc["staHomePassword"] = cfg.staHomePassword;
    doc["staPrimary"]  = cfg.staPrimary;
    doc["urlLocalCatanSta"] = cfg.urlLocalCatanSta;
    doc["urlHomeSta"]       = cfg.urlHomeSta;
    doc["mode"]        = apMode ? "ap" : "sta";

    String out;
    serializeJson(doc, out);
    server.send(200, "application/json", out);
}

void handleSaveConfig() {
    if (!server.hasArg("plain")) { server.send(400, "text/plain", "No body"); return; }

    StaticJsonDocument<768> doc;
    if (deserializeJson(doc, server.arg("plain")) != DeserializationError::Ok) {
        server.send(400, "text/plain", "Invalid JSON");
        return;
    }

    if (doc.containsKey("apSsid"))                  strlcpy(cfg.apSsid,                 doc["apSsid"],      sizeof(cfg.apSsid));
    if (doc.containsKey("apPassword"))              strlcpy(cfg.apPassword,             doc["apPassword"],  sizeof(cfg.apPassword));
    if (doc.containsKey("staLocalCatanSsid"))       strlcpy(cfg.staLocalCatanSsid,      doc["staLocalCatanSsid"],     sizeof(cfg.staLocalCatanSsid));
    if (doc.containsKey("staLocalCatanPassword"))   strlcpy(cfg.staLocalCatanPassword,  doc["staLocalCatanPassword"], sizeof(cfg.staLocalCatanPassword));
    if (doc.containsKey("staHomeSsid"))             strlcpy(cfg.staHomeSsid,            doc["staHomeSsid"],    sizeof(cfg.staHomeSsid));
    if (doc.containsKey("staHomePassword"))         strlcpy(cfg.staHomePassword,        doc["staHomePassword"],sizeof(cfg.staHomePassword));
    if (doc.containsKey("staPrimary")) {
        int primary = doc["staPrimary"];
        if (primary == 1 || primary == 2) cfg.staPrimary = primary;
    }
    if (doc.containsKey("urlLocalCatanSta")) strlcpy(cfg.urlLocalCatanSta, doc["urlLocalCatanSta"], sizeof(cfg.urlLocalCatanSta));
    if (doc.containsKey("urlHomeSta"))       strlcpy(cfg.urlHomeSta,       doc["urlHomeSta"],       sizeof(cfg.urlHomeSta));

    saveConfig();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
}

void handleRoll() {
    rollDice();
    server.send(200, "application/json", "{\"status\":\"rolling\"}");
}

// WiFi setup
void startAP() {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(cfg.apSsid, cfg.apPassword);
    Serial.printf("[wifi] AP started: SSID=%s  IP=%s\n",
                  cfg.apSsid, WiFi.softAPIP().toString().c_str());
}


// Connect to STA profile, returns true if connected
bool connectSTAProfile(const char* label, const char* ssid, const char* password) {
    if (strlen(ssid) == 0) {
        Serial.printf("[wifi] %s skipped (empty SSID)\n", label);
        return false;
    }

    WiFi.begin(ssid, password);
    Serial.printf("[wifi] Connecting (%s) to %s", label, ssid);
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
        delay(500);
        Serial.print('.');
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[wifi] Connected (%s) IP=%s\n", label, WiFi.localIP().toString().c_str());
        return true;
    }

    Serial.printf("\n[wifi] %s failed\n", label);
    WiFi.disconnect();
    delay(100);
    return false;
}

// Start STA mode, try both profiles, fallback to AP if both fail
void startSTA() {
    WiFi.mode(WIFI_STA);

    bool connected = false;
    if (cfg.staPrimary == 2) {
        connected = connectSTAProfile("STA Home Profile", cfg.staHomeSsid, cfg.staHomePassword);
        if (!connected) {
            connected = connectSTAProfile("STA Local Catan Profile", cfg.staLocalCatanSsid, cfg.staLocalCatanPassword);
        }
    } else {
        connected = connectSTAProfile("STA Local Catan Profile", cfg.staLocalCatanSsid, cfg.staLocalCatanPassword);
        if (!connected) {
            connected = connectSTAProfile("STA Home Profile", cfg.staHomeSsid, cfg.staHomePassword);
        }
    }

    if (!connected) {
        Serial.println("\n[wifi] STA failed, falling back to AP");
        startAP();
        apMode = true;
    } else {
        apMode = false;
    }
}

// Arduino entry points
void setup() {
    Serial.begin(115200);
    delay(200);

    // Configure button pin
    pinMode(PIN_BUTTON,      INPUT_PULLUP);

    // Mount LittleFS and load config
    if (!LittleFS.begin()) {
        Serial.println("[fs] LittleFS mount failed");
    }
    loadConfig();

    // Start WiFi in STA, if fails, fallback to AP mode
    startSTA();

    // Setup HTTP server routes
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

// Main loop
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
