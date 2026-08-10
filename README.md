# Catan Dice – ESP8266 D1 Mini

A physical dice-roller for Catan.  
Press the button → the ESP performs an HTTP GET to a configured URL (your game server / smart home integration).

## Hardware

| Component | D1 Mini pin | Notes |
|-----------|-------------|-------|
| Mode switch | **D5** (GPIO 14) | LOW = AP mode · HIGH = home WiFi (STA) mode |
| Roll button | **D6** (GPIO 12) | Active LOW, internal pull-up enabled |

Wire each component between the pin and GND.  
No external pull-up resistors needed (internal pull-ups are used).

## Features

* **AP mode** – the ESP creates its own WiFi network so you can connect without a router.
* **STA mode** – the ESP connects to your home WiFi.
* Separate roll URLs for AP and STA modes.
* Web UI served from LittleFS to configure SSIDs, passwords and URLs at runtime.
* Config persisted in `/config.json` on the filesystem (survives reboots).
* Roll button is debounced (50 ms).

## Building & Flashing

Install [PlatformIO](https://platformio.org/).

```bash
# Build firmware
pio run

# Upload firmware
pio run -t upload

# Upload web UI (data/ folder) to LittleFS
pio run -t uploadfs

# Monitor serial output
pio device monitor
```

## Web UI

After flashing, connect to the ESP's IP address in a browser:

* **AP mode** – connect to the `CatanDice` WiFi, then open `http://192.168.4.1/`
* **STA mode** – find the IP from serial monitor or your router, then open `http://<ip>/`

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/config` | Returns current config as JSON |
| `POST` | `/config` | Update config (JSON body) |
| `POST` | `/roll`   | Trigger a dice roll from browser |

## Default Configuration

| Setting | Default |
|---------|---------|
| AP SSID | `CatanDice` |
| AP Password | `catandice` |
| AP Roll URL | `http://192.168.4.1/roll` |
| STA SSID | *(empty – set via web UI)* |
| STA Password | *(empty)* |
| STA Roll URL | `http://192.168.1.100/roll` |
