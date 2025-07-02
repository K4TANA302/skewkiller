# ⏱️ SkewKiller

**A single-command tool that synchronizes your system time with a Domain Controller (or any NTP server) and immediately executes a command — ideal for resolving Kerberos clock skew issues.**

---

## 🚀 Features

- Sync system time with an NTP server or domain controller.
- Fallback to manual NTP protocol if `ntpdate` is unavailable.
- Automatically stops conflicting time services.
- Sets system and hardware clock.
- Immediately executes a given command (e.g., Kerberos authentication tools).
- Designed for Red Team / Penetration Testing / AD environments.

---
## ✨ Key Features

### 1. Time Backup & Restore
- Saves your system’s original timestamp and timezone offset.
- After command execution, it restores the original time, minimizing forensic artifacts or detection.

### 2. NTP Time Synchronization
- Uses raw socket communication to retrieve time from a specified NTP server (typically a Domain Controller).
- Calculates and accounts for network latency to adjust time more accurately.

### 3. Multiple Time Setting Methods
Tries up to three methods for setting system time:
- `settimeofday` (via `libc`)
- `clock_settime` (via `libc`)
- Fallback to `date` command

---
## Setup
```
git clone https://github.com/K4TANA302/skewkiller.git
cd skewkiller
chmod +x skewkiller.py
mv skewkiller.py /usr/local/bin/skewkiller
```
## 📦 Usage

```bash

sudo skewkiller  <domain_controller_ip> "<command>"
```
⚙️ How it Works

    Attempts to sync time using ntpdate.

    If not available, performs a manual NTP request and sets the system time.

    Disables and stops systemd time services to prevent overrides.

    Updates hardware clock with new time.

    Runs your provided command and prints the output.



