# RasPi Hunter Floating Menu

**RasPi Hunter Floating Menu** ialah aplikasi **menu terapung (*floating always-on-top*) sahaja** untuk Raspberry Pi yang sudah berjalan dalam mod skrin penuh (*full screen*).

Projek ini **tidak mengubah tetapan skrin penuh sedia ada anda** — ia hanya menambah butang terapung `⚙ MENU` di atas paparan semasa untuk menukar rangkaian Wi-Fi serta mengawal **Restart** dan **Shutdown** dengan mudah melalui skrin sentuh.

## Ciri-Ciri Utama

- **Menu Terapung Sahaja (`⚙ MENU`)**: Sentiasa kekal di atas paparan *full screen* sedia ada dan boleh diseret (*drag*) ke mana-mana bahagian skrin.
- **Penukar Wi-Fi Pantas**: Memaparkan SSID Wi-Fi aktif serta alamat IP semasa, dan membolehkan penukaran pantas antara 1 hingga 4 rangkaian Wi-Fi (contoh: Wi-Fi Rumah & Hotspot Telefon).
- **Keutamaan Autoconnect Kekal**: Wi-Fi yang dipilih akan diberi keutamaan tertinggi supaya kekal bersambung selepas *reboot*.
- **Kawalan Kuasa Selamat**: Butang **Restart** dan **Shutdown** dengan pengesahan (*Ya / Batal*) untuk mengelakkan tersentuh secara tidak sengaja.
- **Privasi & Selamat untuk Git**: Kata laluan Wi-Fi disimpan terus di dalam **NetworkManager** (bukan dalam kod atau `config.json`), dan `config.json` diabaikan melalui `.gitignore`.

---

## Keperluan Sistem

- Raspberry Pi OS (Bookworm / Trixie) atau Linux berasaskan Debian
- Paparan **X11** yang sedia berjalan
- **NetworkManager** (`nmcli`) untuk pengurusan Wi-Fi
- **Python 3** bersama **Tkinter** (`python3-tk`)
- Akses **SSH** (untuk pemasangan dan tetapan Wi-Fi tanpa perlu keluar daripada paparan skrin penuh)

---

## Panduan Pemasangan Lengkap Melalui SSH

Semua langkah di bawah dijalankan sepenuhnya melalui **SSH**.

### Langkah 1: Log masuk ke Raspberry Pi melalui SSH

```bash
ssh PENGGUNA@ALAMAT_IP_RASPI
```

*(Contoh: `ssh pi@192.168.1.50`)*

### Langkah 2: Pasang Git (jika belum ada) & muat turun repositori

```bash
sudo apt-get update && sudo apt-get install -y git
git clone <URL_REPO_GIT_ANDA> ~/raspi-hunter-floating-menu
cd ~/raspi-hunter-floating-menu
```

### Langkah 3: Jalankan skrip pemasangan automatik

```bash
chmod +x install.sh
./install.sh
```

Skrip `install.sh` akan:
1. Memasang pakej keperluan (`python3-tk` dan `network-manager`) jika belum terpasang.
2. Menyediakan kebenaran pelaksanaan bagi semua skrip.
3. Mencipta fail `config.json` daripada templat `config.example.json`.
4. Memasang autostart menu terapung di `~/.config/autostart/raspi-hunter-floating-menu.desktop`.
5. Menawarkan untuk terus menjalankan `./setup-wifi.sh` bagi mengisi SSID dan kata laluan Wi-Fi anda.

---

## Panduan Mengisi Wi-Fi SSID & Kata Laluan (Password)

Anda boleh menggunakan **Cara 1 (Automatik)** atau **Cara 2 (Manual)** melalui SSH.

### Cara 1: Wizard Interaktif Melalui SSH (Disyorkan)

```bash
cd ~/raspi-hunter-floating-menu
./setup-wifi.sh
```

Ikuti arahan pada terminal SSH:
1. Sahkan antaramuka Wi-Fi (lalai: `wlan0`).
2. Pilih `Y` jika mahu imbas senarai Wi-Fi berhampiran untuk menyemak ejaan SSID.
3. Masukkan bilangan rangkaian Wi-Fi (1 hingga 4).
4. Masukkan **SSID**, **Label Butang**, dan **Kata Laluan (Password)** *(kata laluan disembunyikan semasa ditaip)*.
5. Pilih saiz skrin (`Auto`, `480x320` untuk LCD 3.5", `800x480`, `1920x1080`, atau manual).

Skrip ini akan menyimpan kata laluan dengan selamat ke dalam **NetworkManager** dan menjana `config.json` secara automatik.

---

### Cara 2: Tetapan Manual Melalui SSH (`nmcli` + `config.json`)

#### A. Daftar SSID & kata laluan dalam NetworkManager

Gantikan `NAMA_SSID_1` / `KATA_LALUAN_1` dengan maklumat Wi-Fi anda:

```bash
# Wi-Fi Pertama
sudo nmcli connection add type wifi ifname wlan0 \
  con-name "NAMA_SSID_1" ssid "NAMA_SSID_1" \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "KATA_LALUAN_1" \
  connection.autoconnect yes connection.autoconnect-priority 10

# Wi-Fi Kedua (contoh: Hotspot Telefon)
sudo nmcli connection add type wifi ifname wlan0 \
  con-name "NAMA_SSID_2" ssid "NAMA_SSID_2" \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "KATA_LALUAN_2" \
  connection.autoconnect yes connection.autoconnect-priority 5
```

Semak senarai profil yang tersimpan:

```bash
nmcli connection show
```

*(Pastikan nilai `con_name` dalam `config.json` sama dengan lajur `NAME`.)*

#### B. Sunting `config.json`

```bash
cd ~/raspi-hunter-floating-menu
cp -n config.example.json config.json
nano config.json
```

Contoh kandungan `config.json`:

```json
{
  "title": "KAWALAN SISTEM & WI-FI",
  "button_text": "⚙ MENU",
  "screen_width": "auto",
  "screen_height": "auto",
  "button_x": "auto",
  "button_y": 3,
  "button_width": 78,
  "button_height": 30,
  "wifi_interface": "wlan0",
  "keep_on_top_ms": 800,
  "wifi_profiles": [
    {
      "label": "WiFi Rumah",
      "con_name": "NAMA_SSID_1",
      "ssid": "NAMA_SSID_1"
    },
    {
      "label": "Hotspot",
      "con_name": "NAMA_SSID_2",
      "ssid": "NAMA_SSID_2"
    }
  ]
}
```

Tekan `Ctrl + O` -> `Enter` untuk simpan, kemudian `Ctrl + X` untuk keluar.

> **Tip Skrin LCD 3.5" (480×320):**
> Tetapkan `"screen_width": 480`, `"screen_height": 320`, `"button_x": 345`, dan `"button_y": 3` supaya butang terapung terletak kemas di bahagian atas kanan.

---

## Menjalankan & Mengawal Menu Terapung Melalui SSH

Anda boleh memaparkan, memulakan semula, atau menghentikan menu terapung terus melalui SSH tanpa perlu *reboot* peranti:

```bash
# Lancarkan atau mulakan semula di atas skrin utama (:0)
~/raspi-hunter-floating-menu/run-menu.sh --restart --bg

# Hentikan menu terapung
~/raspi-hunter-floating-menu/run-menu.sh --stop

# Semak log jika berlaku ralat
cat ~/raspi-hunter-floating-menu.log
```

### Autostart pada Skrip Permulaan Sedia Ada (Jika Tidak Menggunakan Desktop Autostart)

Skrip `./install.sh` sudah memasang autostart di `~/.config/autostart/raspi-hunter-floating-menu.desktop`.

Jika peranti anda tidak menggunakan folder `~/.config/autostart` (contohnya dilancarkan melalui skrip permulaan atau `.xinitrc` sedia ada), cuma tambahkan **1 baris ini** ke dalam skrip permulaan sedia ada anda:

```bash
~/raspi-hunter-floating-menu/run-menu.sh --bg
```

---

## Penyelesaian Masalah (Troubleshooting)

### 1. Butang terapung tidak muncul di atas skrin penuh
Semak sama ada paparan X11 sedang aktif pada `:0`:
```bash
DISPLAY=:0 xset q >/dev/null && echo "X11 Aktif" || echo "X11 Tidak Aktif"
```
Jika Raspberry Pi OS anda menggunakan **Wayland**, tukar ke **X11** melalui `sudo raspi-config` -> **Advanced Options** -> **Wayland** -> **X11 (Openbox)** supaya tetingkap terapung sentiasa kekal di atas paparan skrin penuh.

### 2. Gagal tukar Wi-Fi atau Restart/Shutdown (Masalah Kebenaran)
Jika pengguna anda tidak mempunyai *passwordless sudo* untuk `nmcli` dan `systemctl`, jalankan arahan berikut melalui SSH:

```bash
sudo tee /etc/sudoers.d/raspi-hunter-floating-menu >/dev/null <<EOF
${USER} ALL=(ALL) NOPASSWD: /usr/bin/nmcli, /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff
EOF
sudo chmod 440 /etc/sudoers.d/raspi-hunter-floating-menu
```

### 3. Antaramuka Wi-Fi bukan `wlan0`
Semak nama antaramuka Wi-Fi dengan:
```bash
nmcli device status
```
Kemudian ubah nilai `"wifi_interface"` di dalam `config.json`.

---

## Nyahpasang (Uninstall)

```bash
cd ~/raspi-hunter-floating-menu
./uninstall.sh
```

## Lesen

Projek ini dilesenkan di bawah lesen [MIT](LICENSE).
