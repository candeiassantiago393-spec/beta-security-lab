# Instalação

Requisitos: Windows, Python 3, cabo USB-C, T-Camera S3, este repositório.

## 1. Código

```powershell
git clone https://github.com/candeiassantiago393-spec/beta-security-lab.git
cd beta-security-lab
```

## 2. Configuração

Copiar o exemplo e ajustar a porta COM se necessário:

```powershell
copy config.example.json config.json
```

Não colocar a password Wi-Fi no Git. Ver [configuração](configuracao.md).

## 3. Firmware

[PlatformIO](https://platformio.org/) via Python:

```powershell
py -3 -m pip install platformio
py -3 -m platformio run -d firmware -t upload
```

Placa no PlatformIO: ESP32-S3 Dev Module equivalente (`esp32-s3-devkitc-1`), flash 16 MB, PSRAM OPI, USB CDC ligado. Definições em `firmware/platformio.ini`.

O `upload_port` está como `COM8`. Se o Windows atribuir outra porta, alterar esse campo.

## 4. Servidor no PC

```powershell
py -3 -m pip install -r requirements.txt
.\start.ps1
```

O servidor escuta em **0.0.0.0:8080** (este PC e a rede local). A firewall do Windows pode pedir autorização na primeira vez — aceitar, senão o telemóvel e o Wi-Fi de recurso não entram.

A interface indica o URL de rede (por exemplo `http://192.168.1.x:8080`).

## 5. Primeira utilização

1. OLED: *A iniciar…* e depois *PIR a aquecer…* (~12 s).
2. Com o `start.ps1` a correr, o OLED deixa de mostrar `PC offline`.
3. De dia: PWR curto até aparecer *Aguardando*.
4. Passar à frente da câmara: três fotos na galeria e aviso no Windows.

## Dependências Python

Ver `requirements.txt`: FastAPI, Uvicorn, pyserial, pydantic, winotify (notificações Windows).
