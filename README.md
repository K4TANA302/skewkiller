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

## 🛠️ Requirements

- Python 3.x
- Root privileges (required to change system time)
- Linux system with:
  - `ntpdate` (optional but preferred)
  - `timedatectl`, `hwclock`, and `date` commands

---
## Setup
```
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



