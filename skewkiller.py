#!/usr/bin/env python3
import socket
import struct
import time
import subprocess
import sys
import os
import ctypes
import ctypes.util
from datetime import datetime


class CustomTimeManager:
    def __init__(self, server_ip, verbose=False):
        self.server_ip = server_ip
        self.verbose = verbose
        self.original_time = None
        self.original_timezone_offset = None
        self.is_root = os.geteuid() == 0

        libc_name = ctypes.util.find_library('c')
        self.libc = ctypes.CDLL(libc_name or 'libc.so.6')

        class TimeSpec(ctypes.Structure):
            _fields_ = [('tv_sec', ctypes.c_long), ('tv_nsec', ctypes.c_long)]

        class TimeVal(ctypes.Structure):
            _fields_ = [('tv_sec', ctypes.c_long), ('tv_usec', ctypes.c_long)]

        self.TimeSpec = TimeSpec
        self.TimeVal = TimeVal

    def log(self, message):
        pass  # Disabled

    def save_current_time(self):
        try:
            self.original_time = time.time()
            self.original_timezone_offset = time.timezone
            return True
        except:
            return False

    def get_ntp_time(self):
        try:
            ntp_packet = bytearray(48)
            ntp_packet[0] = 0x1B
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(10)
            send_time = time.time()
            client.sendto(ntp_packet, (self.server_ip, 123))
            response, _ = client.recvfrom(1024)
            receive_time = time.time()
            client.close()
            if len(response) < 48:
                return None
            transmit_timestamp = struct.unpack('!II', response[40:48])
            ntp_seconds = transmit_timestamp[0]
            ntp_fraction = transmit_timestamp[1]
            unix_timestamp = ntp_seconds - 2208988800
            unix_timestamp += ntp_fraction / (2**32)
            network_delay = (receive_time - send_time) / 2
            return unix_timestamp - network_delay
        except:
            return None

    def set_system_time(self, timestamp):
        if not self.is_root:
            return False
        try:
            try:
                tv = self.TimeVal()
                tv.tv_sec = int(timestamp)
                tv.tv_usec = int((timestamp - int(timestamp)) * 1_000_000)
                if self.libc.settimeofday(ctypes.byref(tv), None) == 0:
                    return True
            except:
                pass
            try:
                ts = self.TimeSpec()
                ts.tv_sec = int(timestamp)
                ts.tv_nsec = int((timestamp - int(timestamp)) * 1_000_000_000)
                if self.libc.clock_settime(0, ctypes.byref(ts)) == 0:
                    return True
            except:
                pass
            try:
                date_str = datetime.fromtimestamp(timestamp).strftime("%m%d%H%M%Y.%S")
                result = subprocess.run(['date', date_str], capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False
        except:
            return False

    def sync_time_with_server(self):
        if not self.is_root:
            return False
        server_time = self.get_ntp_time()
        if server_time is None:
            return False
        return self.set_system_time(server_time)

    def restore_original_time(self):
        if self.original_time is None:
            return False
        try:
            elapsed_time = time.time() - self.original_time
            restore_time = self.original_time + elapsed_time
            return self.set_system_time(restore_time)
        except:
            return False

def execute_command(command, verbose=False):
    try:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
            universal_newlines=True
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        return process.wait() == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    verbose = False
    args = sys.argv[1:]
    if '-v' in args:
        verbose = True
        args.remove('-v')
    if len(args) < 2:
        sys.exit(1)

    server_ip = args[0]
    command = ' '.join(args[1:])

    if os.geteuid() != 0:
        sys.exit(1)

    time_manager = CustomTimeManager(server_ip, verbose)
    try:
        if not time_manager.save_current_time():
            sys.exit(1)
        time_manager.sync_time_with_server()
        execute_command(command, verbose)
    except:
        pass
    finally:
        time_manager.restore_original_time()

if __name__ == "__main__":
    main()
