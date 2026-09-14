# Problemas frequentes

## A galeria não abre / ESP32 desligado

- `start.ps1` a correr?
- Cabo na **torre**, não numa porta de carregamento do monitor.
- Gestor de dispositivos: COM Espressif (`303A`).
- Só um programa na COM (fechar monitor série / Arduino IDE).
- Depois de gravar firmware, esperar o reboot e o PING (~2 s).

## OLED em branco ou Erro PMU / camera

- USB a alimentar bem a placa.
- Gravou o firmware deste repositório (o PMU tem de ligar a câmara).
- Módulo da câmara bem assente.

## PIR não tira fotos de dia

Normal: de dia o PIR começa **pausado**. Toque curto em **PWR** até *Aguardando*. Esperar 12 s após ligar.

Falsos alarmes: sol, aquecimento, animais. Aumentar distância ou ângulo.

## Upload PlatformIO falha

BOOT + RST (largar RST, depois BOOT), `upload` outra vez. `upload_port` correto.

## Wi-Fi de recurso não envia

- `wifi_ssid` / `wifi_password` preenchidos, servidor reiniciado.
- Placa e PC na **mesma** rede 2,4 GHz.
- Firewall a permitir TCP 8080.
- O Wi-Fi só dispara quando o USB **não** tem PING (PC offline). Com o cabo e o servidor ok, o envio é USB.

## GitHub Pages sem fotografias

Esperado. Usar `http://IP-DO-PC:8080`.

## Pasta diária não aparece no ambiente de trabalho

O servidor tem de estar **a correr à meia-noite**, ou usar o botão *Pasta no ambiente de trabalho*. OneDrive pode mover o Ambiente de Trabalho — a app procura também `OneDrive\Desktop`.

## A placa aquece

Ver [hardware](hardware.md#aquecimento).
