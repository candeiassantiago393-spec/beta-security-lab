# Firmware

Código: `firmware/src/main.cpp`  
Plataforma: PlatformIO, Arduino-ESP32 2.0.x, U8g2, XPowersLib, WiFi, HTTPClient, Preferences.

## Ciclo de vida

1. Inicia PMU, OLED, câmara (VGA JPEG, vflip/hmirror).
2. Aquecimento PIR 12 s.
3. Lê série USB: `PING`, `WIFI`, `HOST`.
4. Se o último `PING` tem mais de 8 s, OLED **PC offline**.
5. Se o PIR está armado e há movimento, dispara série de 3 fotos.
6. Envia por USB se o PC estiver online; senão POST HTTP `http://HOST:PORT/api/upload`.

SSID/password/host ficam em **Preferences** (NVS) na placa, para o Wi-Fi sobreviver a um reset.

## Mensagens OLED

| Texto | Significado |
| --- | --- |
| A iniciar... | Arranque |
| PIR a aquecer... | Espera inicial |
| Aguardando | PIR armado, à espera |
| Pausa | PIR não dispara |
| Movimento n/3 | Série PIR |
| Foto manual | BOOT |
| Foto enviada | Envio concluído |
| PC offline | Sem heartbeat do servidor |
| Erro camera / Erro PMU | Falha de hardware |

## Protocolo série (placa → PC)

Linha ASCII e a seguir o JPEG:

```
PHOTO,pir,1
TCS3 + uint32 LE (tamanho) + bytes JPEG
```

`source`: `pir` ou `manual`. `burst`: 1–3 no PIR, 0 no manual.

Heartbeat: a placa responde `ALIVE` aos `PING` (no máximo de 1,5 em 1,5 s).

## Protocolo série (PC → placa)

| Linha | Função |
| --- | --- |
| `PING 15` | Heartbeat + hora local (0–23) |
| `HOST\t192.168.1.10\t8080` | IP e porta do servidor |
| `WIFI\tSSID\tpassword` | Credenciais STA |

Separador das linhas HOST/WIFI: tabulação (`\t`).

Velocidade configurada: 115200. No USB nativo do S3 o débito efetivo é o do CDC.

## Gravar de novo

```powershell
py -3 -m platformio run -d firmware -t upload
```

Parar o `start.ps1` antes: a porta COM não pode estar aberta em dois programas.
