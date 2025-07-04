# ⏱️ SkewKiller

**A single-command tool that synchronizes your system time with a Domain Controller (or any NTP server) and immediately executes a command — ideal for resolving Kerberos clock skew issues.**

---

## 🚀 Features

- Syncs system time with an NTP server or Domain Controller.
- Fallback to manual NTP protocol if `ntpdate` is unavailable.
- Automatically stops conflicting time services.
- Sets system and hardware clock.
- Immediately executes a given command (e.g., Kerberos authentication tools).
- Designed for Red Team / Penetration Testing / Active Directory environments.

---

## ✨ Key Highlights

### 1. NTP Time Synchronization
- Uses raw socket communication to retrieve time from a specified NTP server (typically a Domain Controller).
- Calculates and accounts for network latency to improve time accuracy.

### 2. Multiple Time Setting Methods
Tries up to three methods for setting system time:
- `settimeofday` (via `libc`)
- `clock_settime` (via `libc`)
- Fallback to `date` command

---

## 🛠️ Setup

```bash
git clone https://github.com/K4TANA302/skewkiller.git
cd skewkiller
chmod +x skewkiller.py
sudo mv skewkiller.py /usr/local/bin/skewkiller
```
```
sudo skewkiller <domain_controller_ip> "<command>"
sudo skewkiller 192.168.1.10 "kinit user@DOMAIN.LOCAL"
```

