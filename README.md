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
* **Dual STA profiles** – configure two STA WiFi profiles and choose which one is tried first.
* **STA fallback order** – try selected primary STA profile, then the other profile, then AP mode.
* Separate roll URLs for AP and STA modes.
* Web UI served from LittleFS to configure SSIDs, passwords and URLs at runtime.
* HTTP Basic Authentication protects the web UI, configuration API and browser roll endpoint.
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

The browser will prompt for the web username and password. The default credentials are:

* Username: `admin`
* Password: `catandice`

Change the web password from the **Web Server Authentication** section. The password field is
blank and locked until its **Change** button is clicked. A web password must contain at least
8 characters, and an empty web username is rejected.

HTTP Basic Authentication protects all web routes. Credentials are not encrypted because the
ESP serves HTTP rather than HTTPS, so use this on a trusted local network. Change the default
password before using the device on a network where other users may connect.

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/config` | Returns non-secret configuration as JSON |
| `POST` | `/config` | Update configuration (JSON body) |
| `POST` | `/roll`   | Trigger a dice roll from browser |

All API requests require valid HTTP Basic Authentication. `GET /config` never returns the AP,
STA, or web-server passwords. The web UI only includes a password in `POST /config` after that
password's **Change** button has been clicked; otherwise the stored password is left unchanged.
The username is returned by `GET /config` because it is not secret.

Example request:

```bash
curl --user admin:catandice http://192.168.4.1/config
```

## Default Configuration

| Setting | Default |
|---------|---------|
| AP SSID | `CatanDice` |
| AP Password | `catandice` |
| Local Catan WiFi SSID | `LocalCatanWiFi` |
| Local Catan WiFi password | `LocalCatanPass` |
| Local Catan WiFi roll URL | `http://192.168.4.1/rollDice` |
| Home WiFi SSID | *(empty)* |
| Home WiFi password | *(empty)* |
| Home WiFi roll URL | `http://catan.mydomain.eu/rollDice` |
| Primary STA profile | Local Catan WiFi |
| Web username | `admin` |
| Web password | `catandice` |

Passwords are stored in `/config.json` on LittleFS so they survive reboots, but they are not
sent back through `GET /config`. Existing configuration files without web credentials use the
defaults above.
