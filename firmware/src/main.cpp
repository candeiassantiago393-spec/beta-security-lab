#include <Arduino.h>
#include <Wire.h>
#include <esp_camera.h>
#include <U8g2lib.h>

#define XPOWERS_CHIP_AXP2101
#include <XPowersLib.h>
#include "utilities.h"

static const uint32_t PHOTO_COOLDOWN_MS = 8000;
static const uint32_t PIR_WARMUP_MS = 12000;
static const char MAGIC[4] = {'T', 'C', 'S', '3'};

XPowersPMU PMU;
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

uint32_t bootMs = 0;
uint32_t lastPhotoMs = 0;
bool cameraOk = false;
uint32_t photoCount = 0;

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

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera falhou: 0x%x\n", err);
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

void sendPhoto(camera_fb_t *fb)
{
    uint32_t n = fb->len;
    Serial.write((const uint8_t *)MAGIC, 4);
    Serial.write((uint8_t *)&n, 4);
    Serial.write(fb->buf, fb->len);
    Serial.flush();
}

bool captureAndSend()
{
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb || fb->len < 100) {
        if (fb) {
            esp_camera_fb_return(fb);
        }
        return false;
    }

    sendPhoto(fb);
    esp_camera_fb_return(fb);
    photoCount++;
    return true;
}

void setup()
{
    Serial.begin(115200);
    uint32_t waitUntil = millis() + 2500;
    while (!Serial && millis() < waitUntil) {
        delay(10);
    }

    pinMode(PIR_INPUT_PIN, INPUT);
    Wire.begin(I2C_SDA, I2C_SCL);

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
    if (!cameraOk) {
        delay(500);
        return;
    }

    uint32_t now = millis();
    if (now - bootMs < PIR_WARMUP_MS) {
        delay(50);
        return;
    }

    static bool idleShown = false;
    if (!idleShown) {
        showScreen("Entrada", "Aguardando", "Apontado a porta");
        idleShown = true;
    }

    bool motion = digitalRead(PIR_INPUT_PIN) == HIGH;
    if (!motion) {
        delay(30);
        return;
    }

    if (now - lastPhotoMs < PHOTO_COOLDOWN_MS) {
        delay(30);
        return;
    }

    showScreen("Entrada", "Movimento!", "A fotografar...");
    delay(120);

    bool ok = captureAndSend();
    lastPhotoMs = millis();

    if (ok) {
        char extra[24];
        snprintf(extra, sizeof(extra), "Fotos: %lu", (unsigned long)photoCount);
        showScreen("Entrada", "Foto enviada", extra);
        delay(1800);
        showScreen("Entrada", "Aguardando", extra);
    } else {
        showScreen("Entrada", "Falha foto", "Tenta outra vez");
        delay(1500);
        showScreen("Entrada", "Aguardando", "Apontado a porta");
    }
}
