#!/usr/bin/env python3
"""
SkewKiller - Sync system time with NTP server, execute command, restore time
"""
import socket
import struct
import time
import subprocess
import sys
import os
import ctypes
import ctypes.util
import argparse
import signal
from datetime import datetime
from typing import Optional


class CustomTimeManager:
    """Manages system time synchronization with NTP servers"""
    
    def __init__(self, server_ip: str, verbose: bool = False):
        self.server_ip = server_ip
        self.verbose = verbose
        self.original_time = None
        self.original_timezone_offset = None
        self.is_root = os.geteuid() == 0
        
        # Initialize libc for system calls
        try:
            libc_name = ctypes.util.find_library('c')
            self.libc = ctypes.CDLL(libc_name or 'libc.so.6')
        except Exception as e:
            self.log(f"Failed to load libc: {e}")
            self.libc = None

        # Define time structures
        class TimeSpec(ctypes.Structure):
            _fields_ = [('tv_sec', ctypes.c_long), ('tv_nsec', ctypes.c_long)]

        class TimeVal(ctypes.Structure):
            _fields_ = [('tv_sec', ctypes.c_long), ('tv_usec', ctypes.c_long)]

        self.TimeSpec = TimeSpec
        self.TimeVal = TimeVal

    def log(self, message: str):
        """Log message with timestamp if verbose mode is enabled"""
        if self.verbose:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message}")

    def save_current_time(self) -> bool:
        """Save the current system time for later restoration"""
        try:
            self.original_time = time.time()
            self.original_timezone_offset = time.timezone
            self.log(f"Saved original time: {datetime.fromtimestamp(self.original_time)}")
            return True
        except Exception as e:
            self.log(f"Failed to save current time: {e}")
            return False

    def validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False

    def get_ntp_time(self) -> Optional[float]:
        """Get time from NTP server"""
        if not self.validate_ip(self.server_ip):
            self.log(f"Invalid IP address: {self.server_ip}")
            return None
            
        try:
            self.log(f"Requesting time from NTP server: {self.server_ip}")
            
            # Create NTP packet
            ntp_packet = bytearray(48)
            ntp_packet[0] = 0x1B  # NTP version 3, mode 3 (client)
            
            # Create socket
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(10)
            
            # Send request and measure time
            send_time = time.time()
            client.sendto(ntp_packet, (self.server_ip, 123))
            
            # Receive response
            response, server_address = client.recvfrom(1024)
            receive_time = time.time()
            client.close()
            
            if len(response) < 48:
                self.log("Invalid NTP response: packet too short")
                return None
            
            # Extract transmit timestamp (bytes 40-47)
            transmit_timestamp = struct.unpack('!II', response[40:48])
            ntp_seconds = transmit_timestamp[0]
            ntp_fraction = transmit_timestamp[1]
            
            # Convert NTP timestamp to Unix timestamp
            # NTP epoch starts at 1900-01-01, Unix epoch starts at 1970-01-01
            # Difference is 2208988800 seconds
            unix_timestamp = ntp_seconds - 2208988800
            unix_timestamp += ntp_fraction / (2**32)
            
            # Adjust for network delay
            network_delay = (receive_time - send_time) / 2
            adjusted_timestamp = unix_timestamp - network_delay
            
            self.log(f"NTP server time: {datetime.fromtimestamp(adjusted_timestamp)}")
            self.log(f"Network delay: {network_delay:.4f} seconds")
            
            return adjusted_timestamp
            
        except socket.timeout:
            self.log(f"Timeout connecting to NTP server {self.server_ip}")
            return None
        except socket.gaierror as e:
            self.log(f"DNS resolution failed for {self.server_ip}: {e}")
            return None
        except Exception as e:
            self.log(f"Error getting NTP time: {e}")
            return None

    def set_system_time(self, timestamp: float) -> bool:
        """Set system time using multiple methods"""
        if not self.is_root:
            self.log("Error: Root privileges required to set system time")
            return False

        if not self.libc:
            self.log("Error: libc not available for system calls")
            return False

        self.log(f"Setting system time to: {datetime.fromtimestamp(timestamp)}")
        
        # Method 1: Try settimeofday
        try:
            tv = self.TimeVal()
            tv.tv_sec = int(timestamp)
            tv.tv_usec = int((timestamp - int(timestamp)) * 1_000_000)
            
            if self.libc.settimeofday(ctypes.byref(tv), None) == 0:
                self.log("System time set successfully using settimeofday")
                return True
        except Exception as e:
            self.log(f"settimeofday failed: {e}")

        # Method 2: Try clock_settime
        try:
            ts = self.TimeSpec()
            ts.tv_sec = int(timestamp)
            ts.tv_nsec = int((timestamp - int(timestamp)) * 1_000_000_000)
            
            if self.libc.clock_settime(0, ctypes.byref(ts)) == 0:
                self.log("System time set successfully using clock_settime")
                return True
        except Exception as e:
            self.log(f"clock_settime failed: {e}")

        # Method 3: Use date command as fallback
        try:
            date_str = datetime.fromtimestamp(timestamp).strftime("%m%d%H%M%Y.%S")
            result = subprocess.run(['date', date_str], capture_output=True, text=True)
            if result.returncode == 0:
                self.log("System time set successfully using date command")
                return True
            else:
                self.log(f"date command failed: {result.stderr}")
        except Exception as e:
            self.log(f"date command failed: {e}")

        self.log("All methods to set system time failed")
        return False

    def sync_time_with_server(self) -> bool:
        """Synchronize system time with NTP server"""
        if not self.is_root:
            self.log("Error: Root privileges required for time synchronization")
            return False
            
        server_time = self.get_ntp_time()
        if server_time is None:
            self.log("Failed to get time from NTP server")
            return False
            
        local_time = time.time()
        time_diff = abs(server_time - local_time)
        self.log(f"Time difference: {time_diff:.4f} seconds")
        
        if time_diff < 0.1:  # Less than 100ms difference
            self.log("System time is already synchronized (difference < 100ms)")
            return True
            
        return self.set_system_time(server_time)

    def restore_original_time(self) -> bool:
        """Restore the original system time"""
        if self.original_time is None:
            self.log("No original time saved")
            return False
            
        if not self.is_root:
            self.log("Error: Root privileges required to restore time")
            return False
            
        try:
            # Calculate how much time has elapsed since we saved the original time
            current_execution_time = time.time()
            execution_duration = current_execution_time - self.original_time
            
            # The restore time should be the original time plus the execution duration
            # This accounts for the time that has actually passed
            restore_time = self.original_time + execution_duration
            
            self.log(f"Restoring to original time + execution duration: {datetime.fromtimestamp(restore_time)}")
            return self.set_system_time(restore_time)
            
        except Exception as e:
            self.log(f"Failed to restore original time: {e}")
            return False


def execute_command(command: str, verbose: bool = False) -> bool:
    """Execute shell command with real-time output"""
    if verbose:
        print(f"Executing command: {command}")
    
    try:
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output line by line
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        return_code = process.wait()
        
        if verbose:
            print(f"Command completed with return code: {return_code}")
            
        return return_code == 0
        
    except KeyboardInterrupt:
        if verbose:
            print("Command interrupted by user")
        process.terminate()
        return False
    except Exception as e:
        print(f"Error executing command: {e}")
        return False


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print("\nReceived interrupt signal. Cleaning up...")
    sys.exit(1)


def main():
    """Main function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="SkewKiller - Synchronize system time with NTP server, execute command, then restore time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo ./skewkiller 192.168.1.1 "ls -la"
  sudo ./skewkiller -v 8.8.8.8 "python3 my_script.py"
  sudo ./skewkiller --verbose pool.ntp.org "make test"
        """
    )
    
    parser.add_argument('server_ip', help='NTP server IP address or hostname')
    parser.add_argument('command', help='Command to execute after time sync')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Check root privileges
    if os.geteuid() != 0:
        print("Error: SkewKiller requires root privileges to modify system time.")
        print("Please run with sudo: sudo ./skewkiller ...")
        sys.exit(1)
    
    # Validate inputs
    if not args.server_ip.strip():
        print("Error: Server IP cannot be empty")
        sys.exit(1)
        
    if not args.command.strip():
        print("Error: Command cannot be empty")
        sys.exit(1)
    
    # Create time manager
    time_manager = CustomTimeManager(args.server_ip, args.verbose)
    
    try:
        print(f"SkewKiller: Starting time synchronization with {args.server_ip}...")
        
        # Save current time
        if not time_manager.save_current_time():
            print("Error: Failed to save current system time")
            sys.exit(1)
        
        # Sync with NTP server
        if not time_manager.sync_time_with_server():
            print("Error: Failed to synchronize time with NTP server")
            sys.exit(1)
        
        print("Time synchronized successfully. Executing command...")
        
        # Execute the command
        success = execute_command(args.command, args.verbose)
        
        if success:
            print("Command executed successfully.")
        else:
            print("Command execution failed or returned non-zero exit code.")
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Always try to restore original time
        print("SkewKiller: Restoring original system time...")
        if time_manager.restore_original_time():
            print("Original time restored successfully.")
        else:
            print("Warning: Failed to restore original system time.")
    
    print("SkewKiller operation completed.")


if __name__ == "__main__":
    main()

