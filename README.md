# beta-security-lab

**Estado: beta (0.1.0)**

Sistema local de captura na entrada do escritório: [LILYGO T-Camera S3 OV5640](https://github.com/Xinyuan-LilyGO/LilyGo-Cam-ESP32S3) com sensor PIR, ecrã OLED e envio das fotos por USB para um PC. A galeria corre num site Python no computador fixo.

Repositório: https://github.com/candeiassantiago393-spec/beta-security-lab

## O que isto não é (ainda)

- Não é um serviço na cloud. As fotos ficam no disco do PC.
- [GitHub Pages](https://pages.github.com/) serve para a **página de documentação** (link fixo do projeto). Não substitui o servidor local: o Pages não fala com o cabo USB nem guarda as imagens.

Quando ativares Pages neste repo (`Settings → Pages → Deploy from a branch → /docs`), o link típico fica:

`https://candeiassantiago393-spec.github.io/beta-security-lab/`

Essa página explica o beta e tem um atalho para a interface local (`http://127.0.0.1:8080`) quando o servidor estiver a correr no PC.

## Hardware

| Item | Modelo |
| --- | --- |
| Placa | LILYGO T-Camera S3 OV5640 (ESP32-S3, câmara 5 MP, OLED 0.96", microfone, PIR AS312) |
| Caixa | LILYGO T-Camera Shell |
| Ligação | USB-C na torre do PC (CDC nativo Espressif `VID_303A`) |
| Porta usada no desenvolvimento | COM8 |

## Especificações atuais (beta 0.1.0)

### Firmware (`firmware/`)

- Detecção por **PIR** (GPIO 17), não por análise de vídeo.
- Aquecimento do PIR: **12 s** após boot.
- Pausa mínima entre fotos: **8 s**.
- Resolução JPEG: **VGA** (640×480), qualidade 12.
- Envio por série USB com cabeçalho `TCS3` + tamanho + JPEG.
- OLED SSD1306 (I2C SDA 7 / SCL 6): `Aguardando`, `Movimento!`, `A fotografar...`, `Foto enviada`.
- PMU AXP2101 ligado (alimentação da câmara e do PIR).
- Os dois botões físicos da placa **ainda não são usados pelo software** (ver sugestões no fim desta conversa / issues).

### Servidor e interface (`server/`)

- Python (FastAPI + Uvicorn) em `http://127.0.0.1:8080`
- Galeria HTML/JS, atualização automática
- Apagar uma foto ou **apagar tudo**
- Retenção configurável (predefinição: **168 horas / 7 dias**)
- Fotos em `photos/` (não vão para o GitHub)

### Stack

- Firmware: PlatformIO, Arduino-ESP32 2.0.17, U8g2, XPowersLib
- PC: Python 3, FastAPI, pyserial

## Correr no PC

1. Placa ligada por USB-C (o OLED deve mostrar *Aguardando* após o aquecimento do PIR).
2. Na pasta do projeto:

```powershell
py -3 -m pip install -r requirements.txt
.\start.ps1
```

3. Abrir [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Gravar o firmware outra vez

```powershell
py -3 -m platformio run -d firmware -t upload
```

Se o upload falhar: mantém **BOOT**, carrega **RST**, larga **BOOT**, tenta outra vez.

## Privacidade

Este repositório é público. Não commits faturas, moradas, nem fotografias da entrada.
