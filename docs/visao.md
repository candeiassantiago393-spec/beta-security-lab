# Visão e funcionalidades

## Objetivo

Registar quem passa na entrada do escritório, com fotografias guardadas **apenas** no computador da torre, consultáveis numa página web local.

## O que o sistema faz

- Detecta movimento com o sensor PIR da T-Camera S3.
- Em cada deteção PIR tira **três fotografias**, com cerca de **1 segundo** entre disparos, e depois espera **8 segundos** antes de nova série.
- Mostra estado no OLED: a aguardar, pausa, movimento, foto enviada, PC offline.
- Envia as imagens por **USB** para o PC. Se o PC não responder, tenta **Wi-Fi** (se estiver configurado).
- Notifica o Windows quando entra uma captura relevante.
- Galeria com filtros (dia e origem: PIR, manual, Wi-Fi).
- Exportação ZIP da vista filtrada.
- **À meia-noite**, move as fotos desse dia para `Ambiente de trabalho/entrada-AAAA-MM-DD` e tira-as da interface.
- Watchdog: OLED `PC offline` se o servidor parar; site `ESP32 desligado` se a placa falhar.

## O que o sistema não faz

- Não transmite vídeo contínuo.
- Não envia fotos para a internet nem para o GitHub Pages.
- Não substitui um alarme certificado nem videovigilância profissional.
- O GitHub Pages **não é** a galeria com imagens.

## Horário (predefinição)

| Período | Horas | PIR |
| --- | --- | --- |
| Dia | 08:00–20:00 | Só depois de toque curto em **PWR** (armar) |
| Noite | 20:00–08:00 | Arma automaticamente. PWR curto pausa |

A hora chega do PC (comando `PING` com a hora local). Sem PC ligado, o firmware trata o período como dia (PIR desarmado até haver botão ou hora).

`night_start` e `night_end` em `config.json` descrevem a intenção no servidor; o firmware usa a hora enviada pelo PC. Alterar as horas na interface guarda o JSON; a lógica de noite/dia no ESP32 está fixa em 20/8 no firmware atual até se enviar um comando extra (não implementado). Para mudar o intervalo no hardware é preciso alterar `nightStart` / `nightEnd` em `firmware/src/main.cpp` e gravar outra vez.

## Botões físicos

| Botão | Toque curto | Toque longo |
| --- | --- | --- |
| **PWR** | Dia: arma / pausa o PIR. Noite: pausa / volta a armar | ~4 s desliga a placa (PMU) |
| **BOOT** | Foto manual (uma), mesmo em pausa | Com RST: modo de gravação de firmware |
| **RST** | Reinicia a placa | — |

Não usar BOOT e RST ao mesmo tempo em utilização normal.

## Origem das fotografias

Nomes no disco, exemplo: `20260914-152419-pir-1.jpg`

| Sufixo | Origem |
| --- | --- |
| `-pir` / `-pir-1` … `-pir-3` | Série PIR |
| `-manual` | Botão BOOT |
| `-wifi` | Envio HTTP de recurso |
