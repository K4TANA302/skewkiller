#!/usr/bin/env python3
"""
Single Command Time Sync and Execute
Synchronizes system time with domain controller and immediately runs your command
Usage: sudo python3 skewkiller.py <server_ip> '<command>'
"""

import socket
import struct
import time
import subprocess
import sys
import os
import ctypes
import ctypes.util
from datetime import datetime, timezone

class CustomTimeManager:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.original_time = None
        self.original_timezone_offset = None
        self.is_root = os.geteuid() == 0
        
        # Load libc for system calls
        libc_name = ctypes.util.find_library('c')
        if libc_name:
            self.libc = ctypes.CDLL(libc_name)
        else:
            self.libc = ctypes.CDLL('libc.so.6')  # Fallback
            
        # Define time structures
        class TimeSpec(ctypes.Structure):
            _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long)
            ]
        
        class TimeVal(ctypes.Structure):
            _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_usec', ctypes.c_long)
            ]
            
        self.TimeSpec = TimeSpec
        self.TimeVal = TimeVal

    def save_current_time(self):
        """Save current system time using pure Python"""
        try:
            self.original_time = time.time()
            self.original_timezone_offset = time.timezone
            
            print(f"💾 Saved original time: {datetime.fromtimestamp(self.original_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💾 Saved timezone offset: {self.original_timezone_offset} seconds")
            return True
        except Exception as e:
            print(f"❌ Failed to save current time: {e}")
            return False

    def get_ntp_time(self):
        """Get time from NTP server using raw socket communication"""
        try:
            print(f"🔄 Connecting to NTP server {self.server_ip}...")
            
            # Create NTP request packet
            ntp_packet = bytearray(48)
            ntp_packet[0] = 0x1B  # LI=0, VN=3, Mode=3 (client)
            
            # Create socket and send request
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(10)
            
            send_time = time.time()
            client.sendto(ntp_packet, (self.server_ip, 123))
            
            # Receive response
            response, address = client.recvfrom(1024)
            receive_time = time.time()
            client.close()
            
            if len(response) < 48:
                raise Exception("Invalid NTP response")
            
            # Parse NTP timestamp (seconds since 1900-01-01)
            transmit_timestamp = struct.unpack('!II', response[40:48])
            ntp_seconds = transmit_timestamp[0]
            ntp_fraction = transmit_timestamp[1]
            
            # Convert to Unix timestamp (seconds since 1970-01-01)
            unix_timestamp = ntp_seconds - 2208988800  # NTP epoch offset
            unix_timestamp += ntp_fraction / (2**32)
            
            # Account for network delay
            network_delay = (receive_time - send_time) / 2
            server_time = unix_timestamp - network_delay
            
            print(f"✅ Retrieved time from NTP server: {datetime.fromtimestamp(server_time).strftime('%Y-%m-%d %H:%M:%S')}")
            return server_time
            
        except Exception as e:
            print(f"❌ Failed to get NTP time: {e}")
            return None

    def set_system_time(self, timestamp):
        """Set system time using direct system calls"""
        if not self.is_root:
            print("❌ Root privileges required to set system time!")
            return False
            
        try:
            print(f"🕐 Setting system time to: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Method 1: Try using settimeofday system call
            try:
                tv = self.TimeVal()
                tv.tv_sec = int(timestamp)
                tv.tv_usec = int((timestamp - int(timestamp)) * 1000000)
                
                # settimeofday system call
                result = self.libc.settimeofday(ctypes.byref(tv), None)
                if result == 0:
                    print("✅ System time set using settimeofday")
                    return True
                else:
                    print(f"⚠ settimeofday failed with code: {result}")
            except Exception as e:
                print(f"⚠ settimeofday method failed: {e}")
            
            # Method 2: Try using clock_settime system call
            try:
                ts = self.TimeSpec()
                ts.tv_sec = int(timestamp)
                ts.tv_nsec = int((timestamp - int(timestamp)) * 1000000000)
                
                # clock_settime system call (CLOCK_REALTIME = 0)
                result = self.libc.clock_settime(0, ctypes.byref(ts))
                if result == 0:
                    print("✅ System time set using clock_settime")
                    return True
                else:
                    print(f"⚠ clock_settime failed with code: {result}")
            except Exception as e:
                print(f"⚠ clock_settime method failed: {e}")
            
            # Method 3: Fallback to date command
            try:
                dt = datetime.fromtimestamp(timestamp)
                date_str = dt.strftime("%m%d%H%M%Y.%S")
                result = subprocess.run(['date', date_str], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ System time set using date command")
                    return True
                else:
                    print(f"⚠ date command failed: {result.stderr}")
            except Exception as e:
                print(f"⚠ date command method failed: {e}")
            
            print("❌ All time setting methods failed!")
            return False
            
        except Exception as e:
            print(f"❌ Failed to set system time: {e}")
            return False

    def sync_time_with_server(self):
        """Synchronize system time with NTP server"""
        if not self.is_root:
            print("❌ Root privileges required for time synchronization!")
            return False
            
        # Get time from NTP server
        server_time = self.get_ntp_time()
        if server_time is None:
            return False
            
        # Set system time
        return self.set_system_time(server_time)

    def restore_original_time(self):
        """Restore the original system time"""
        if self.original_time is None:
            print("⚠ No original time saved to restore")
            return False
            
        try:
            print("\n🔄 Restoring original system time...")
            
            # Calculate elapsed time during execution
            current_time = time.time()
            elapsed_time = current_time - self.original_time
            
            # Calculate what the original time should be now
            restore_time = self.original_time + elapsed_time
            
            print(f"🕐 Elapsed time during execution: {elapsed_time:.2f} seconds")
            print(f"🔄 Restoring to adjusted original time...")
            
            if self.set_system_time(restore_time):
                print("✅ Original system time restored successfully!")
                return True
            else:
                print("❌ Failed to restore original time")
                return False
                
        except Exception as e:
            print(f"❌ Time restoration failed: {e}")
            return False

def execute_command(command):
    """Execute the provided command with real-time output"""
    try:
        print(f"🚀 Executing command: {command}")
        print("=" * 60)
        
        # Start the process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output in real-time
        success = True
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Wait for process to complete
        return_code = process.wait()
        
        print("=" * 60)
        print(f"Command completed with exit code: {return_code}")
        
        return return_code == 0
        
    except Exception as e:
        print(f"❌ Command execution failed: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: sudo python3 custom_time_sync.py <server_ip> '<command>'")
        print("\nExamples:")
        print("  sudo python3 custom_time_sync.py 192.168.1.10 'kinit user@DOMAIN.COM'")
        print("  sudo python3 custom_time_sync.py 10.0.0.1 'ldapsearch -H ldap://dc.example.com'")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    command = ' '.join(sys.argv[2:])
    
    print("🎯 CUSTOM TIME SYNC, EXECUTE, AND RESTORE")
    print("=" * 60)
    print(f"🌐 NTP Server: {server_ip}")
    print(f"📝 Command: {command}")
    print("=" * 60)
    
    # Check root privileges
    if os.geteuid() != 0:
        print("❌ ERROR: This script requires root privileges!")
        print(f"Run: sudo python3 {sys.argv[0]} {server_ip} '{command}'")
        sys.exit(1)
    
    # Initialize time manager
    time_manager = CustomTimeManager(server_ip)
    command_success = False
    
    try:
        # Step 1: Save current time
        print("\n💾 STEP 1: Saving current system time...")
        if not time_manager.save_current_time():
            print("❌ Failed to save current time!")
            sys.exit(1)
        
        print(f"🕐 Current system time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 2: Sync with server
        print(f"\n🔄 STEP 2: Synchronizing with NTP server...")
        if not time_manager.sync_time_with_server():
            print("❌ Time synchronization failed!")
            print("🤔 Continue with command execution anyway? (y/N): ", end='')
            if input().lower() != 'y':
                sys.exit(1)
        
        print(f"🕐 Synchronized time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 3: Execute command
        print(f"\n🚀 STEP 3: Executing command...")
        command_success = execute_command(command)
        
        if command_success:
            print("✅ Command executed successfully!")
        else:
            print("⚠ Command execution completed with errors")
    
    except KeyboardInterrupt:
        print("\n⚠ Operation interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Step 4: Always restore original time
        print(f"\n🔄 STEP 4: Restoring original system time...")
        if time_manager.restore_original_time():
            print(f"🕐 Current system time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("❌ Failed to restore original time!")
            print("⚠ Manual time restoration may be required")
    
    # Final status
    if command_success:
        print("\n🎉 MISSION ACCOMPLISHED!")
        print("✅ Time synced → Command executed → Time restored")
    else:
        print("\n⚠ PARTIAL SUCCESS")
        print("✅ Time synced → ❌ Command failed → ✅ Time restored")

if __name__ == "__main__":
    main()
