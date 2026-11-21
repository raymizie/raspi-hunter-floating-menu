#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_FILE="${HOME}/.config/autostart/raspi-hunter-floating-menu.desktop"
LOCAL_BIN_LINK="${HOME}/.local/bin/raspi-hunter-menu"

echo "Menghentikan RasPi Hunter Floating Menu..."
"${SCRIPT_DIR}/run-menu.sh" --stop || true

if [[ -f "${AUTOSTART_FILE}" ]]; then
    rm -f "${AUTOSTART_FILE}"
    echo "[OK] Autostart dipadam: ${AUTOSTART_FILE}"
fi

if [[ -L "${LOCAL_BIN_LINK}" ]]; then
    rm -f "${LOCAL_BIN_LINK}"
    echo "[OK] Pautan dipadam: ${LOCAL_BIN_LINK}"
fi

echo ""
echo "[SELESAI] Autostart dan pautan telah dibuang."
echo "Nota: Profil Wi-Fi dalam NetworkManager dan folder projek ini tidak dipadam."
