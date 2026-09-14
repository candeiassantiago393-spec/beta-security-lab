#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_camera.h>
#include <U8g2lib.h>
#include <Preferences.h>

#define XPOWERS_CHIP_AXP2101
#include <XPowersLib.h>
#include "utilities.h"

static const uint32_t PHOTO_COOLDOWN_MS = 8000;
static const uint32_t PIR_WARMUP_MS = 12000;
static const uint32_t PC_TIMEOUT_MS = 8000;
static const char MAGIC[4] = {'T', 'C', 'S', '3'};

XPowersPMU PMU;
Preferences prefs;
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

uint32_t bootMs = 0;
uint32_t lastPhotoMs = 0;
uint32_t lastPingMs = 0;
uint32_t lastAliveMs = 0;
uint32_t lastOledMs = 0;
bool cameraOk = false;
bool dayArmed = false;
bool nightPaused = false;
bool bootWasPressed = false;
bool showedOffline = false;
int localHour = -1;
int nightStart = 20;
int nightEnd = 8;
uint32_t photoCount = 0;
String wifiSsid;
String wifiPass;
String httpHost;
uint16_t httpPort = 8080;
String rxLine;

void showScreen(const char *title, const char *line1, const char *line2 = "")
{
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x12_tf);
    u8g2.drawStr(0, 12, title);
    u8g2.drawHLine(0, 16, 128);
    u8g2.setFont(u8g2_font_7x13B_tf);
    u8g2.drawStr(0, 36, line1);
    u8g2.setFont(u8g2_font_6x12_tf);
    u8g2.drawStr(0, 54, line2);
    u8g2.sendBuffer();
    lastOledMs = millis();
}

bool setupPower()
{
    if (!PMU.begin(Wire, AXP2101_SLAVE_ADDRESS, I2C_SDA, I2C_SCL)) {
        Serial.println("PMU falhou");
        return false;
    }
    PMU.setSysPowerDownVoltage(2600);
    PMU.disableTSPinMeasure();
    PMU.setALDO1Voltage(1800);
    PMU.enableALDO1();
    PMU.setALDO2Voltage(2800);
    PMU.enableALDO2();
    PMU.setALDO4Voltage(3000);
    PMU.enableALDO4();
    PMU.setALDO3Voltage(3300);
    PMU.enableALDO3();
    PMU.setPowerKeyPressOffTime(XPOWERS_POWEROFF_4S);
    PMU.disableIRQ(XPOWERS_AXP2101_ALL_IRQ);
    PMU.clearIrqStatus();
    PMU.enableIRQ(XPOWERS_AXP2101_PKEY_SHORT_IRQ);
    return true;
}

bool setupCamera()
{
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = psramFound() ? 2 : 1;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

    if (esp_camera_init(&config) != ESP_OK) {
        return false;
    }
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s, FRAMESIZE_VGA);
        s->set_vflip(s, 1);
        s->set_hmirror(s, 1);
    }
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) {
        esp_camera_fb_return(fb);
    }
    return true;
}

bool pcOnline()
{
    return lastPingMs != 0 && (millis() - lastPingMs) < PC_TIMEOUT_MS;
}

bool hourIsNight(int h)
{
    if (h < 0) {
        return false;
    }
    if (nightStart > nightEnd) {
        return h >= nightStart || h < nightEnd;
    }
    return h >= nightStart && h < nightEnd;
}

bool pirArmed()
{
    if (hourIsNight(localHour)) {
        return !nightPaused;
    }
    return dayArmed;
}

void applyHour(int h)
{
    if (h < 0 || h > 23) {
        return;
    }
    if (localHour >= 0 && localHour != h) {
        bool wasNight = hourIsNight(localHour);
        bool nowNight = hourIsNight(h);
        if (!wasNight && nowNight) {
            nightPaused = false;
        }
        if (wasNight && !nowNight) {
            dayArmed = false;
        }
    }
    localHour = h;
}

void showIdle()
{
    char extra[28];
    snprintf(extra, sizeof(extra), "Fotos:%lu %s", (unsigned long)photoCount,
             hourIsNight(localHour) ? "Noite" : "Dia");
    if (!pcOnline()) {
        showScreen("Entrada", "PC offline", extra);
        showedOffline = true;
        return;
    }
    showedOffline = false;
    if (pirArmed()) {
        showScreen("Entrada", "Aguardando", extra);
    } else {
        showScreen("Entrada", "Pausa", extra);
    }
}

void sendPhotoUsb(camera_fb_t *fb, const char *source, int burst)
{
    Serial.printf("PHOTO,%s,%d\n", source, burst);
    uint32_t n = fb->len;
    Serial.write((const uint8_t *)MAGIC, 4);
    Serial.write((uint8_t *)&n, 4);
    Serial.write(fb->buf, fb->len);
    Serial.flush();
}

void sendPhotoWifi(camera_fb_t *fb, const char *source, int burst)
{
    if (httpHost.isEmpty() || WiFi.status() != WL_CONNECTED) {
        return;
    }
    HTTPClient http;
    String url = "http://" + httpHost + ":" + String(httpPort) + "/api/upload";
    if (!http.begin(url)) {
        return;
    }
    http.setTimeout(8000);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Source", source);
    http.addHeader("X-Burst", String(burst));
    http.POST(fb->buf, fb->len);
    http.end();
}

bool captureAndSend(const char *source, int burst)
{
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb || fb->len < 100) {
        if (fb) {
            esp_camera_fb_return(fb);
        }
        return false;
    }
    if (pcOnline()) {
        sendPhotoUsb(fb, source, burst);
    } else {
        sendPhotoWifi(fb, source, burst);
    }
    esp_camera_fb_return(fb);
    photoCount++;
    lastPhotoMs = millis();
    return true;
}

void takeBurstPir()
{
    for (int i = 1; i <= 3; i++) {
        char line[20];
        snprintf(line, sizeof(line), "Movimento %d/3", i);
        showScreen("Entrada", line, "A fotografar...");
        delay(80);
        captureAndSend("pir", i);
        if (i < 3) {
            delay(1000);
        }
    }
    showScreen("Entrada", "Foto enviada", "Serie PIR x3");
    delay(900);
    showIdle();
}

void takeManual()
{
    showScreen("Entrada", "Foto manual", "A fotografar...");
    delay(80);
    bool ok = captureAndSend("manual", 0);
    showScreen("Entrada", ok ? "Foto enviada" : "Falha foto", "");
    delay(900);
    showIdle();
}

bool pwrShortPressed()
{
    PMU.getIrqStatus();
    bool pressed = PMU.isPekeyShortPressIrq();
    PMU.clearIrqStatus();
    return pressed;
}

bool bootShortPressed()
{
    bool pressed = digitalRead(BOOT_BUTTON_PIN) == LOW;
    bool edge = pressed && !bootWasPressed;
    bootWasPressed = pressed;
    if (!edge) {
        return false;
    }
    delay(40);
    return digitalRead(BOOT_BUTTON_PIN) == LOW;
}

void tryWifi()
{
    if (wifiSsid.isEmpty() || WiFi.status() == WL_CONNECTED) {
        return;
    }
    WiFi.mode(WIFI_STA);
    WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
}

void handleLine(const String &line)
{
    if (line.startsWith("PING")) {
        lastPingMs = millis();
        int sp = line.indexOf(' ');
        if (sp > 0) {
            applyHour(line.substring(sp + 1).toInt());
        }
        if (millis() - lastAliveMs > 1500) {
            Serial.println("ALIVE");
            lastAliveMs = millis();
        }
        return;
    }
    if (line.startsWith("WIFI\t")) {
        int t1 = line.indexOf('\t');
        int t2 = line.indexOf('\t', t1 + 1);
        if (t2 > t1) {
            wifiSsid = line.substring(t1 + 1, t2);
            wifiPass = line.substring(t2 + 1);
            prefs.putString("ssid", wifiSsid);
            prefs.putString("pass", wifiPass);
            WiFi.disconnect(true);
            tryWifi();
        }
        return;
    }
    if (line.startsWith("HOST\t")) {
        int t1 = line.indexOf('\t');
        int t2 = line.indexOf('\t', t1 + 1);
        if (t2 > t1) {
            httpHost = line.substring(t1 + 1, t2);
            httpPort = line.substring(t2 + 1).toInt();
            if (httpPort == 0) {
                httpPort = 8080;
            }
            prefs.putString("host", httpHost);
            prefs.putUShort("port", httpPort);
        }
        return;
    }
}

void pollIncoming()
{
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\r') {
            continue;
        }
        if (c == '\n') {
            handleLine(rxLine);
            rxLine = "";
        } else if (rxLine.length() < 180) {
            rxLine += c;
        } else {
            rxLine = "";
        }
    }
}

void setup()
{
    Serial.begin(115200);
    uint32_t waitUntil = millis() + 2500;
    while (!Serial && millis() < waitUntil) {
        delay(10);
    }

    pinMode(PIR_INPUT_PIN, INPUT);
    pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
    pinMode(PMU_INPUT_PIN, INPUT);
    Wire.begin(I2C_SDA, I2C_SCL);
    prefs.begin("entrada", false);
    wifiSsid = prefs.getString("ssid", "");
    wifiPass = prefs.getString("pass", "");
    httpHost = prefs.getString("host", "");
    httpPort = prefs.getUShort("port", 8080);

    if (!setupPower()) {
        u8g2.begin();
        showScreen("Entrada", "Erro PMU", "Reinicia a placa");
        while (true) {
            delay(1000);
        }
    }

    delay(200);
    u8g2.setBusClock(100000);
    u8g2.begin();
    u8g2.setContrast(180);
    showScreen("Entrada", "A iniciar...", "T-Camera S3");
    tryWifi();

    cameraOk = setupCamera();
    bootMs = millis();
    if (!cameraOk) {
        showScreen("Entrada", "Erro camera", "Verifica o modulo");
    } else {
        showScreen("Entrada", "Aguardando", "PIR a aquecer...");
    }
    Serial.println("READY T-Camera-S3");
}

void loop()
{
    pollIncoming();

    if (!cameraOk) {
        delay(200);
        return;
    }

    if (!pcOnline() && !showedOffline && millis() - lastOledMs > 400) {
        showIdle();
    } else if (pcOnline() && showedOffline) {
        showIdle();
    }

    if (pwrShortPressed()) {
        if (hourIsNight(localHour)) {
            nightPaused = !nightPaused;
        } else {
            dayArmed = !dayArmed;
        }
        showIdle();
    }

    if (bootShortPressed()) {
        takeManual();
        return;
    }

    uint32_t now = millis();
    if (now - bootMs < PIR_WARMUP_MS) {
        delay(20);
        return;
    }

    static bool idleShown = false;
    if (!idleShown) {
        showIdle();
        idleShown = true;
    }

    if (!pirArmed()) {
        delay(20);
        return;
    }

    bool motion = digitalRead(PIR_INPUT_PIN) == HIGH;
    if (!motion || now - lastPhotoMs < PHOTO_COOLDOWN_MS) {
        delay(20);
        return;
    }

    takeBurstPir();
}
