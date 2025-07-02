#!/usr/bin/env python3
"""
Single Command Time Sync and Execute
Synchronizes system time with domain controller and immediately runs your command.
Usage: sudo python3 skewkiller.py <dc_ip> <command>
"""

import socket
import struct
import time
import subprocess
import sys
import os
from datetime import datetime

class QuickTimeSync:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.is_root = os.geteuid() == 0

    def sync_with_ntpdate(self):
        try:
            print(f"🔄 Syncing time with {self.server_ip} using ntpdate...")
            result = subprocess.run(['ntpdate', '-s', self.server_ip],
                                    capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print("✅ Time synchronized successfully with ntpdate")
                return True
            else:
                print(f"❌ ntpdate failed: {result.stderr}")
        except FileNotFoundError:
            print("⚠️  ntpdate not found, trying manual NTP sync...")
        except Exception as e:
            print(f"❌ ntpdate error: {e}")
        return False

    def manual_ntp_sync(self):
        try:
            print(f"🔄 Manual NTP sync with {self.server_ip}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(10)
            ntp_packet = bytearray(48)
            ntp_packet[0] = 0x1B
            send_time = time.time()
            client.sendto(ntp_packet, (self.server_ip, 123))
            response, address = client.recvfrom(1024)
            receive_time = time.time()
            client.close()

            if len(response) >= 48:
                transmit_timestamp = struct.unpack('!II', response[40:48])
                ntp_seconds = transmit_timestamp[0]
                ntp_fraction = transmit_timestamp[1]
                unix_timestamp = ntp_seconds - 2208988800
                unix_timestamp += ntp_fraction / (2**32)
                network_delay = (receive_time - send_time) / 2
                server_time = unix_timestamp - network_delay
                dt = datetime.fromtimestamp(server_time)
                date_str = dt.strftime("%m%d%H%M%Y.%S")

                print(f"🕐 Setting system time to: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                result = subprocess.run(['date', date_str],
                                        capture_output=True, text=True, check=True)

                try:
                    subprocess.run(['hwclock', '--systohc'],
                                   capture_output=True, check=True, timeout=5)
                    print("✅ System and hardware time synchronized")
                except:
                    print("✅ System time synchronized (hardware clock sync failed)")
                return True

        except Exception as e:
            print(f"❌ Manual NTP sync failed: {e}")
        return False

    def force_time_sync(self):
        if not self.is_root:
            print("❌ ERROR: Root privileges required to sync system time!")
            print(f"Run: sudo python3 {sys.argv[0]} {self.server_ip} '<command>'")
            return False

        print(f"🚀 Force syncing system time with {self.server_ip}...")

        # Force timezone to UTC and disable NTP
        subprocess.run(['timedatectl', 'set-timezone', 'UTC'], capture_output=True)
        subprocess.run(['timedatectl', 'set-ntp', 'false'], capture_output=True)

        # Stop conflicting time services
        subprocess.run(['systemctl', 'stop', 'ntp'], capture_output=True)
        subprocess.run(['systemctl', 'stop', 'systemd-timesyncd'], capture_output=True)

        if self.sync_with_ntpdate():
            return True

        if self.manual_ntp_sync():
            return True

        try:
            print("🔄 Trying aggressive time sync...")
            for attempt in range(3):
                try:
                    result = subprocess.run(['ntpdate', '-B', '-s', '-u', self.server_ip],
                                            capture_output=True, text=True, timeout=20)
                    if result.returncode == 0:
                        print(f"✅ Time sync successful on attempt {attempt + 1}")
                        return True
                except:
                    continue

            result = subprocess.run(['ntpdate', '-s', '-b', '-u', self.server_ip],
                                    capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                print("✅ Time sync successful with backup method")
                return True

        except Exception as e:
            print(f"❌ Aggressive sync failed: {e}")

        print("❌ All time sync methods failed!")
        print("💡 Try manually:")
        print(f"   sudo ntpdate -s {self.server_ip}")
        print(f"   sudo timedatectl set-ntp false")
        print(f"   sudo date -s 'YYYY-MM-DD HH:MM:SS'")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: sudo python3 skewkiller.py <domain_controller_ip> '<command>'")
        sys.exit(1)

    dc_ip = sys.argv[1]
    command = ' '.join(sys.argv[2:])

    print("🎯 ONE-COMMAND TIME SYNC AND EXECUTE")
    print("="*60)
    print(f"🌐 Domain Controller: {dc_ip}")
    print(f"📝 Command to execute: {command}")
    print("="*60)

    if os.geteuid() != 0:
        print("❌ ERROR: This script requires root privileges!")
        print(f"Run: sudo python3 {sys.argv[0]} {dc_ip} '{command}'")
        sys.exit(1)

    print(f"🕐 Current system time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕐 Current system UTC time: {subprocess.run(['date', '-u'], capture_output=True, text=True).stdout.strip()}")

    sync_client = QuickTimeSync(dc_ip)

    print("\n🔄 STEP 1: Synchronizing system time...")
    if not sync_client.force_time_sync():
        print("❌ Time sync failed! Kerberos will likely fail.")
        print("🤔 Continue anyway? (y/N): ", end='')
        if input().lower() != 'y':
            sys.exit(1)

    print(f"🕐 New system time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕐 New system UTC time: {subprocess.run(['date', '-u'], capture_output=True, text=True).stdout.strip()}")

    print(f"\n🚀 STEP 2: Executing command immediately...")
    print("="*60)

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())

        stdout, stderr = process.communicate()

        if stdout:
            print(stdout)
        if stderr:
            print("❌ STDERR:")
            print(stderr)

        print("="*60)
        print(f"✅ Command completed with exit code: {process.returncode}")

        if process.returncode == 0:
            print("🎉 SUCCESS! No more Kerberos clock skew errors!")
        else:
            print("⚠️  Command failed - check output above")

    except Exception as e:
        print(f"❌ Command execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
