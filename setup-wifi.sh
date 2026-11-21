#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.json"

echo "=================================================="
echo "  RASPI HUNTER FLOATING MENU - TETAPAN WI-FI"
echo "=================================================="
echo ""

if ! command -v nmcli >/dev/null 2>&1; then
    echo "[RALAT] Arahan 'nmcli' tidak ditemui."
    echo "Sila pasang NetworkManager terlebih dahulu:"
    echo "  sudo apt-get update && sudo apt-get install -y network-manager"
    exit 1
fi

# Kesan antaramuka Wi-Fi secara automatik
DEFAULT_IFACE="$(nmcli -t -f DEVICE,TYPE device status 2>/dev/null | awk -F: '$2=="wifi"{print $1; exit}')"
DEFAULT_IFACE="${DEFAULT_IFACE:-wlan0}"

read -r -p "Antaramuka Wi-Fi [${DEFAULT_IFACE}]: " WIFI_IFACE
WIFI_IFACE="${WIFI_IFACE:-$DEFAULT_IFACE}"

# Imbas rangkaian Wi-Fi berhampiran untuk rujukan (pilihan)
echo ""
read -r -p "Mahu imbas senarai Wi-Fi berhampiran sekarang? [Y/n]: " DO_SCAN
DO_SCAN="${DO_SCAN:-Y}"
if [[ "${DO_SCAN}" =~ ^[Yy]$ ]]; then
    echo "Mengimbas Wi-Fi pada ${WIFI_IFACE}..."
    nmcli device wifi rescan ifname "${WIFI_IFACE}" 2>/dev/null || true
    sleep 2
    echo ""
    echo "Senarai Wi-Fi berhampiran:"
    echo "--------------------------------------------------"
    nmcli -f SSID,SIGNAL,SECURITY device wifi list ifname "${WIFI_IFACE}" 2>/dev/null | head -n 20 || echo "(Tidak dapat mengimbas Wi-Fi buat masa ini)"
    echo "--------------------------------------------------"
fi

echo ""
read -r -p "Berapa rangkaian Wi-Fi yang mahu dimasukkan? (1-4) [2]: " WIFI_COUNT
WIFI_COUNT="${WIFI_COUNT:-2}"
if ! [[ "${WIFI_COUNT}" =~ ^[1-4]$ ]]; then
    echo "[RALAT] Sila masukkan nombor antara 1 hingga 4."
    exit 1
fi

TMP_PROFILES="$(mktemp)"
trap 'rm -f "${TMP_PROFILES}"' EXIT

for ((i = 1; i <= WIFI_COUNT; i++)); do
    echo ""
    echo "--- Tetapan Wi-Fi #${i} ---"

    while true; do
        read -r -p "Nama SSID Wi-Fi #${i} (tepat termasuk huruf besar/kecil): " SSID
        if [[ -n "${SSID}" ]]; then
            break
        fi
        echo "SSID tidak boleh kosong."
    done

    read -r -p "Label pada butang menu [${SSID}]: " LABEL
    LABEL="${LABEL:-$SSID}"

    read -r -s -p "Kata laluan (Password) Wi-Fi #${i} (kosongkan jika Open/tiada password): " WIFI_PASS
    echo ""

    CON_NAME="${SSID}"
    PRIO=$((15 - i * 5))
    if ((PRIO < 5)); then
        PRIO=5
    fi

    echo "Menyimpan profil '${CON_NAME}' ke NetworkManager..."
    if nmcli -t -f NAME connection show 2>/dev/null | grep -Fxq "${CON_NAME}"; then
        sudo nmcli connection modify "${CON_NAME}" \
            connection.interface-name "${WIFI_IFACE}" \
            802-11-wireless.ssid "${SSID}" \
            connection.autoconnect yes \
            connection.autoconnect-priority "${PRIO}"
    else
        sudo nmcli connection add \
            type wifi \
            ifname "${WIFI_IFACE}" \
            con-name "${CON_NAME}" \
            ssid "${SSID}" \
            connection.autoconnect yes \
            connection.autoconnect-priority "${PRIO}" >/dev/null
    fi

    if [[ -n "${WIFI_PASS}" ]]; then
        sudo nmcli connection modify "${CON_NAME}" \
            wifi-sec.key-mgmt wpa-psk \
            wifi-sec.psk "${WIFI_PASS}"
    else
        sudo nmcli connection modify "${CON_NAME}" remove 802-11-wireless-security 2>/dev/null || true
    fi

    # Simpan maklumat profil bukan sensitif untuk dibina menjadi config.json
    python3 -c '
import json, sys
path, label, con_name, ssid = sys.argv[1:5]
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps({"label": label, "con_name": con_name, "ssid": ssid}, ensure_ascii=False) + "\n")
' "${TMP_PROFILES}" "${LABEL}" "${CON_NAME}" "${SSID}"

    echo "[OK] Profil '${LABEL}' (SSID: ${SSID}) berjaya disimpan di NetworkManager."
done

# Tetapan saiz skrin & kedudukan butang terapung
echo ""
echo "--- Tetapan Saiz Skrin & Kedudukan Butang ---"
echo "  1) Auto (kesan resolusi skrin secara automatik) [Disyorkan]"
echo "  2) 480x320 (Skrin LCD 3.5 inci)"
echo "  3) 800x480 (Skrin LCD 5 atau 7 inci)"
echo "  4) 1920x1080 (Full HD)"
echo "  5) Manual (masukkan sendiri)"
read -r -p "Pilih pilihan skrin [1]: " SCREEN_OPT
SCREEN_OPT="${SCREEN_OPT:-1}"

SCREEN_W="auto"
SCREEN_H="auto"
BTN_X="auto"
BTN_Y="3"

case "${SCREEN_OPT}" in
    1)
        SCREEN_W="auto"
        SCREEN_H="auto"
        BTN_X="auto"
        ;;
    2)
        SCREEN_W="480"
        SCREEN_H="320"
        BTN_X="345"
        ;;
    3)
        SCREEN_W="800"
        SCREEN_H="480"
        BTN_X="auto"
        ;;
    4)
        SCREEN_W="1920"
        SCREEN_H="1080"
        BTN_X="auto"
        ;;
    5)
        read -r -p "Lebar skrin (px): " SCREEN_W
        read -r -p "Tinggi skrin (px): " SCREEN_H
        read -r -p "Kedudukan X butang (atau 'auto') [auto]: " BTN_X
        BTN_X="${BTN_X:-auto}"
        read -r -p "Kedudukan Y butang [3]: " BTN_Y
        BTN_Y="${BTN_Y:-3}"
        ;;
    *)
        echo "Pilihan tidak sah, menggunakan mod Auto."
        ;;
esac

# Jana config.json (TIADA kata laluan disimpan di sini!)
python3 -c '
import json, sys

tmp_path, out_path, iface, sw, sh, bx, by = sys.argv[1:8]

def parse_dim(val):
    return int(val) if val.isdigit() else "auto"

profiles = []
with open(tmp_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            profiles.append(json.loads(line))

cfg = {
    "title": "KAWALAN SISTEM & WI-FI",
    "button_text": "⚙ MENU",
    "screen_width": parse_dim(sw),
    "screen_height": parse_dim(sh),
    "button_x": parse_dim(bx),
    "button_y": int(by) if by.isdigit() else 3,
    "button_width": 78,
    "button_height": 30,
    "wifi_interface": iface,
    "keep_on_top_ms": 800,
    "wifi_profiles": profiles,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
' "${TMP_PROFILES}" "${CONFIG_FILE}" "${WIFI_IFACE}" "${SCREEN_W}" "${SCREEN_H}" "${BTN_X}" "${BTN_Y}"

echo ""
echo "=================================================="
echo "[SELESAI] Konfigurasi berjaya disimpan ke:"
echo "  ${CONFIG_FILE}"
echo ""
echo "Nota keselamatan:"
echo "  - Kata laluan Wi-Fi disimpan dengan selamat dalam NetworkManager,"
echo "    BUKAN dalam fail config.json."
echo "  - Fail config.json telah diabaikan dalam .gitignore."
echo "=================================================="

# Tawar untuk mulakan semula menu terapung jika sedang berjalan
if pgrep -f "floating-menu.py" >/dev/null 2>&1; then
    echo ""
    read -r -p "Menu terapung sedang berjalan. Mulakan semula sekarang? [Y/n]: " RESTART_NOW
    RESTART_NOW="${RESTART_NOW:-Y}"
    if [[ "${RESTART_NOW}" =~ ^[Yy]$ ]]; then
        "${SCRIPT_DIR}/run-menu.sh" --restart --bg
    fi
fi
