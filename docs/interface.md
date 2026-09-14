# Interface

Página servida em `/` (`server/static/`).

## Elementos

- Estado: **ESP32 ligado** ou **ESP32 desligado**.
- URL de rede local.
- Filtro **dia** e **origem** (todas / PIR / manual / Wi-Fi).
- Horas de noite e retenção (horas); botão Guardar.
- **Exportar ZIP** — descarrega o filtro atual.
- **Pasta no ambiente de trabalho** — move o dia escolhido (ou hoje).
- **Apagar tudo** / apagar uma miniatura.

A lista atualiza sozinha (~1,5 s) quando entra foto, exportação ou apagamento.

## Avisos no Windows

Toast via `winotify` (ou PowerShell de recurso). Dispara em captura **manual** e no **primeiro** frame de uma série PIR, para não repetir três avisos.

## GitHub Pages

https://candeiassantiago393-spec.github.io/beta-security-lab/ é a **página pública do repositório**. Não lista fotografias. Para a galeria usar sempre o IP do PC com o servidor a correr.
