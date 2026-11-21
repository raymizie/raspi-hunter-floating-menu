#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="${HOME}/.config/autostart"
AUTOSTART_FILE="${AUTOSTART_DIR}/raspi-hunter-floating-menu.desktop"
LOCAL_BIN="${HOME}/.local/bin"

echo "=================================================="
echo "  PEMASANGAN RASPI HUNTER FLOATING MENU (SSH)"
echo "=================================================="
echo ""

# 1. Semak & pasang pakej keperluan
MISSING_PKGS=()
python3 -c "import tkinter" 2>/dev/null || MISSING_PKGS+=("python3-tk")
command -v nmcli >/dev/null 2>&1 || MISSING_PKGS+=("network-manager")

if ((${#MISSING_PKGS[@]} > 0)); then
    echo "[1/5] Memasang pakej diperlukan: ${MISSING_PKGS[*]}"
    sudo apt-get update
    sudo apt-get install -y "${MISSING_PKGS[@]}"
else
    echo "[1/5] Semua pakej keperluan (python3-tk, network-manager) sudah terpasang."
fi

# 2. Pastikan skrip boleh dilaksanakan
echo "[2/5] Menetapkan kebenaran skrip..."
chmod +x \
    "${SCRIPT_DIR}/floating-menu.py" \
    "${SCRIPT_DIR}/setup-wifi.sh" \
    "${SCRIPT_DIR}/run-menu.sh" \
    "${SCRIPT_DIR}/uninstall.sh"

# 3. Cipta pautan perintah mudah di ~/.local/bin
echo "[3/5] Menyediakan perintah 'raspi-hunter-menu' di ${LOCAL_BIN}..."
mkdir -p "${LOCAL_BIN}"
ln -sf "${SCRIPT_DIR}/run-menu.sh" "${LOCAL_BIN}/raspi-hunter-menu"

# 4. Sediakan config.json jika belum wujud
if [[ ! -f "${SCRIPT_DIR}/config.json" ]]; then
    echo "[4/5] Menyalin templat config.example.json -> config.json..."
    cp "${SCRIPT_DIR}/config.example.json" "${SCRIPT_DIR}/config.json"
else
    echo "[4/5] Fail config.json sedia ada dikekalkan."
fi

# 5. Pasang Autostart menu terapung sahaja (tidak mengubah tetapan full screen sedia ada)
echo "[5/5] Memasang autostart menu terapung di ${AUTOSTART_FILE}..."
mkdir -p "${AUTOSTART_DIR}"
cat > "${AUTOSTART_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=RasPi Hunter Floating Menu
Comment=Menu terapung Wi-Fi & kawalan sistem
Exec=${SCRIPT_DIR}/run-menu.sh
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "=================================================="
echo "[BERJAYA] Pemasangan RasPi Hunter Floating Menu selesai!"
echo "=================================================="
echo ""
echo "Langkah seterusnya:"
echo "  1) Isi SSID & kata laluan Wi-Fi anda:"
echo "       cd ${SCRIPT_DIR} && ./setup-wifi.sh"
echo ""
echo "  2) Lancarkan terus di atas skrin sedia ada melalui SSH (tanpa reboot):"
echo "       ${SCRIPT_DIR}/run-menu.sh --restart --bg"
echo ""
echo "  Nota: Jika peranti anda menggunakan skrip permulaan/startx tersendiri"
echo "        (bukan ~/.config/autostart), cuma tambahkan 1 baris ini dalam skrip anda:"
echo "        ${SCRIPT_DIR}/run-menu.sh --bg"
echo ""

if [[ -t 0 ]]; then
    read -r -p "Mahu jalankan tetapan Wi-Fi (./setup-wifi.sh) sekarang? [Y/n]: " RUN_WIFI
    RUN_WIFI="${RUN_WIFI:-Y}"
    if [[ "${RUN_WIFI}" =~ ^[Yy]$ ]]; then
        "${SCRIPT_DIR}/setup-wifi.sh"
    fi
fi
