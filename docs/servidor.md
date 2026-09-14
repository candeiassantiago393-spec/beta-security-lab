# Servidor e API

O processo `uvicorn server.app:app` corre em `server/app.py`.

## Papel

- Lê o USB (COM) e grava JPEG em `photos/`.
- Aceita POST HTTP `/api/upload` (Wi-Fi de recurso).
- Serve a galeria e a API.
- Envia `PING <hora>` à placa de 2 em 2 segundos.
- Envia `HOST` (IP da LAN) e, se existir, `WIFI` + password.
- À mudança de dia civil, move as fotos do dia anterior para o ambiente de trabalho.
- Aplica retenção em horas (`retention_hours`) sobre ficheiros que ainda estejam em `photos/`.

## Pasta de imagens

`photos/` na raiz do projeto. Ignorada pelo Git (`.gitignore`).

## Ambiente de trabalho

Procura, por esta ordem: `Desktop`, `Ambiente de Trabalho`, `OneDrive/Desktop`.  
Pasta criada: `entrada-AAAA-MM-DD`. As fotos **saem** de `photos/` (deixam a interface).

Exportação manual: botão na galeria ou `POST /api/export-desktop?day=AAAA-MM-DD`.

## Endpoints

| Método | Caminho | Função |
| --- | --- | --- |
| GET | `/` | Galeria HTML |
| GET | `/api/photos?day=&source=` | Lista (filtros opcionais) |
| GET | `/api/events?after=` | Eventos para atualizar a página |
| GET | `/api/settings` | Estado, retenção, URL LAN, ligado/desligado |
| POST | `/api/settings` | Gravar retenção e horas de noite (JSON) |
| POST | `/api/upload` | JPEG cru; cabeçalhos `X-Source`, `X-Burst` |
| GET | `/api/export.zip?day=&source=` | ZIP da vista filtrada |
| POST | `/api/export-desktop?day=` | Mover o dia para o ambiente de trabalho |
| DELETE | `/api/photos` | Apagar todas as fotos da pasta |
| DELETE | `/api/photos/{nome}` | Apagar uma foto |

CORS está aberto (`*`) para acesso na LAN. Não expor 8080 à internet.

## Watchdog no site

`connected` fica verdadeiro só se chegou dados da placa há menos de **8 segundos** (`ALIVE` ou uma foto). Caso contrário a interface mostra **ESP32 desligado**.
