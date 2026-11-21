#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SCRIPT="${SCRIPT_DIR}/floating-menu.py"
LOG_FILE="${HOME}/raspi-hunter-floating-menu.log"

RESTART=0
BACKGROUND=0

for arg in "$@"; do
    case "${arg}" in
        --restart|-r)
            RESTART=1
            ;;
        --bg|-b)
            BACKGROUND=1
            ;;
        --stop)
            pkill -f "${APP_SCRIPT}" 2>/dev/null || pkill -f "floating-menu.py" 2>/dev/null || true
            echo "[OK] RasPi Hunter Floating Menu dihentikan."
            exit 0
            ;;
        --help|-h)
            echo "Penggunaan: $0 [--restart] [--bg] [--stop]"
            echo "  --restart, -r  Hentikan proses lama dan lancarkan semula"
            echo "  --bg, -b       Jalankan di latar belakang (sesuai melalui SSH)"
            echo "  --stop         Hentikan menu terapung"
            exit 0
            ;;
    esac
done

# Pastikan pemboleh ubah paparan X11 ditetapkan (penting apabila dilancarkan melalui SSH)
export DISPLAY="${DISPLAY:-:0}"
if [[ -z "${XAUTHORITY:-}" && -f "${HOME}/.Xauthority" ]]; then
    export XAUTHORITY="${HOME}/.Xauthority"
fi

if ((RESTART == 1)); then
    pkill -f "${APP_SCRIPT}" 2>/dev/null || pkill -f "floating-menu.py" 2>/dev/null || true
    sleep 0.5
elif pgrep -f "${APP_SCRIPT}" >/dev/null 2>&1; then
    echo "[INFO] RasPi Hunter Floating Menu sudah berjalan. Gunakan '--restart' untuk mulakan semula."
    exit 0
fi

if ((BACKGROUND == 1)); then
    nohup python3 "${APP_SCRIPT}" >>"${LOG_FILE}" 2>&1 </dev/null &
    disown || true
    sleep 0.5
    if pgrep -f "${APP_SCRIPT}" >/dev/null 2>&1; then
        echo "[OK] RasPi Hunter Floating Menu dilancarkan pada DISPLAY=${DISPLAY}."
        echo "     Log: ${LOG_FILE}"
    else
        echo "[AMARAN] Proses mungkin gagal bermula. Semak log: ${LOG_FILE}"
        exit 1
    fi
else
    exec python3 "${APP_SCRIPT}"
fi
