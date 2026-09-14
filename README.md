# beta-security-lab

**Versão:** beta 0.2.0  
**Autor:** [candeias.dev](https://github.com/candeiassantiago393-spec)  
**Repositório:** https://github.com/candeiassantiago393-spec/beta-security-lab  
**Página do projeto:** https://candeiassantiago393-spec.github.io/beta-security-lab/

Sistema local de captura na entrada de um escritório. Uma [LILYGO T-Camera S3 OV5640](https://github.com/Xinyuan-LilyGO/LilyGo-Cam-ESP32S3) detecta movimento, tira fotografias e envia-as por USB (ou Wi-Fi de recurso) para um computador fixo, onde uma galeria web permite consultar, filtrar, exportar e apagar as imagens.

As fotografias **nunca** são enviadas para o GitHub nem para a cloud. O [GitHub Pages](https://candeiassantiago393-spec.github.io/beta-security-lab/) documenta o projeto; a galeria com fotos corre no PC (`http://IP-DA-TORRE:8080`).

---

## Índice da documentação

| Documento | Conteúdo |
| --- | --- |
| [Visão e funcionalidades](docs/visao.md) | O que o sistema faz, o que não faz, horário dia/noite |
| [Hardware](docs/hardware.md) | Kit, pinos, botões, OLED, alimentação |
| [Instalação](docs/instalacao.md) | Python, firmware, primeira utilização |
| [Servidor e API](docs/servidor.md) | Pasta de fotos, endpoints, exportação diária |
| [Interface](docs/interface.md) | Galeria, filtros, ZIP, avisos no Windows |
| [Firmware](docs/firmware.md) | Comportamento da placa, protocolo série, Wi-Fi |
| [Configuração](docs/configuracao.md) | `config.json` campo a campo |
| [Problemas frequentes](docs/troubleshooting.md) | USB, OLED, PIR, Pages vs galeria |
| [Privacidade](docs/privacidade.md) | Dados locais, o que não entra no Git |

---

## Arranque rápido

1. Ligar a T-Camera S3 à torre por USB-C.
2. Na pasta do projeto:

```powershell
py -3 -m pip install -r requirements.txt
.\start.ps1
```

3. Abrir `http://127.0.0.1:8080` neste PC, ou `http://IP-DA-TORRE:8080` noutro dispositivo na mesma rede.
4. **De dia** (08:00–20:00, predefinição): toque curto em **PWR** para armar o PIR. **À noite** arma sozinho.

Gravar o firmware outra vez:

```powershell
py -3 -m platformio run -d firmware -t upload
```

Se o upload falhar: manter **BOOT**, carregar **RST**, largar **BOOT**, repetir.

---

## Estrutura do repositório

```
beta-security-lab/
├── firmware/          Firmware PlatformIO (ESP32-S3)
├── server/            FastAPI + galeria HTML/JS
├── docs/              Documentação detalhada
├── photos/            Imagens locais (não versionadas)
├── config.example.json
├── start.ps1
└── README.md
```

---

## Estado

Projeto em **beta**. Hardware e software funcionam em conjunto no PC de desenvolvimento; horários, Wi-Fi e exportação diária devem ser validados no sítio de instalação (teto, cabo, rede).
