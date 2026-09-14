# beta-security-lab

**Estado: beta (0.2.0)**

Sistema local de captura na entrada do escritório: [LILYGO T-Camera S3 OV5640](https://github.com/Xinyuan-LilyGO/LilyGo-Cam-ESP32S3) com sensor PIR, ecrã OLED e envio das fotos por USB para um PC. Wi-Fi é só recurso se o cabo falhar.

Repositório: https://github.com/candeiassantiago393-spec/beta-security-lab

Página do projeto (GitHub Pages): https://candeiassantiago393-spec.github.io/beta-security-lab/

A galeria **com fotos** corre no PC (`http://IP-DO-PC:8080`). O GitHub Pages não guarda imagens nem fala com o USB.

## Especificações (beta 0.2.0)

- PIR: **3 fotos**, 1 segundo entre cada uma; depois 8 s de pausa
- **Noite (20:00–08:00):** arma sozinho. PWR curto pausa mesmo à noite
- **Dia:** PIR só depois de PWR curto (armar)
- **BOOT curto:** foto manual, a qualquer hora
- Watchdog: OLED `PC offline` se o servidor parar; site `ESP32 desligado` se a placa falhar
- Aviso no Windows quando entra movimento
- Filtros por dia e origem (PIR / manual / Wi-Fi)
- Exportar ZIP; à meia-noite copia o dia para `Ambiente de trabalho/entrada-AAAA-MM-DD` e tira da interface
- Wi-Fi de recurso: preenche `wifi_ssid` e `wifi_password` em `config.json` (não commits a password)

## Correr no PC

```powershell
py -3 -m pip install -r requirements.txt
.\start.ps1
```

Abre `http://127.0.0.1:8080` neste PC, ou `http://IP-DA-TORRE:8080` noutro dispositivo na mesma rede.

## Gravar firmware

```powershell
py -3 -m platformio run -d firmware -t upload
```

## Privacidade

Repositório público: sem faturas, sem fotos da entrada, sem passwords Wi-Fi.
