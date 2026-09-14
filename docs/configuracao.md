# Configuração

Ficheiro `config.json` na raiz (partir de `config.example.json`).

| Campo | Predefinição | Significado |
| --- | --- | --- |
| `retention_hours` | `168` | Apaga de `photos/` ficheiros mais velhos que X horas (o arquivo diário no ambiente de trabalho já os tira da pasta) |
| `port` | `COM8` | Porta série preferida |
| `baud` | `115200` | Baud da série |
| `night_start` | `20` | Início da noite (documentado / gravado pela UI; ver nota em [visão](visao.md)) |
| `night_end` | `8` | Fim da noite |
| `wifi_ssid` | `""` | Rede 2,4 GHz da casa/escritório |
| `wifi_password` | `""` | Não fazer commit |
| `listen_host` | `0.0.0.0` | Referência; o `start.ps1` usa `0.0.0.0` |
| `listen_port` | `8080` | Porta HTTP enviada à placa em `HOST` |

A interface pode alterar retenção e horas de noite (`POST /api/settings`). SSID e password só se editam no JSON, para não as expor no browser.

Reiniciar o `start.ps1` depois de mudar Wi-Fi ou porta COM.
