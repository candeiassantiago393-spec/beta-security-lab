# Hardware

## Kit (encomenda de referência)

| Item | Modelo |
| --- | --- |
| Placa | LILYGO T-Camera S3 OV5640 — ESP32-S3, câmara 5 MP, OLED 0,96", microfone, PIR AS312 |
| Caixa | LILYGO T-Camera Shell |
| Cabo extra | LILYGO P353 (PH2.0, 5 condutores) — não é obrigatório para USB-C |

Documentação do fabricante: [LilyGo-Cam-ESP32S3](https://github.com/Xinyuan-LilyGO/LilyGo-Cam-ESP32S3).

## Identificação USB (Windows)

- Espressif nativo: `VID_303A` / `PID_1001`
- Porta série típica: **COM8** (pode mudar)
- Também aparece *USB JTAG/serial debug unit*

A ligação deve ser **USB-C na torre**. Portas USB do monitor só funcionam se o monitor for hub USB ligado ao PC.

## Pinos usados no firmware

Definidos em `firmware/include/utilities.h`.

| Função | GPIO |
| --- | --- |
| Câmara I2C SDA / SCL | 5 / 4 |
| Câmara XCLK, PCLK, VSYNC, HREF | 38, 12, 8, 18 |
| Câmara D2–D9 | 14, 47, 48, 21, 13, 11, 10, 9 |
| Câmara RESET | 39 |
| OLED + PMU I2C SDA / SCL | 7 / 6 |
| PIR AS312 | 17 |
| IRQ do PMU | 2 |
| BOOT | 0 |

## Alimentação (PMU AXP2101)

A placa **não alimenta** câmara e PIR sem inicializar o PMU. O firmware liga:

- ALDO1 / ALDO2 / ALDO4 — câmara
- ALDO3 — PIR
- Desliga a medição do pino TS (carregamento)

O OLED partilha o canal do núcleo; não se desliga a alimentação do ecrã.

## Aquecimento

É **normal** a placa aquecer ao toque (ESP32-S3 a 240 MHz, câmara e PIR ligados, USB permanente). 40–55 °C é típico. Desligar se estiver demasiado quente para segurar, cheirar a queimado, ou o ecrã falhar. A caixa no teto piora a dissipação. Pausar o PIR **não** desliga a câmara.

## Posicionamento

Teto, apontado à entrada. O PIR AS312 precisa de uns **12 segundos** a aquecer após ligar. Evitar fontes de calor diretas junto ao sensor.
