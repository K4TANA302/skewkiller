# SkewKiller

SkewKiller is a powerful time synchronization tool that allows you to temporarily sync your system time with an NTP server, execute a command, and then restore the original system time. This is particularly useful for testing time-sensitive applications or working with systems that have time skew issues.

## Features

- **NTP Time Synchronization**: Connects to any NTP server to get accurate time
- **Temporary Time Changes**: Preserves and restores original system time
- **Command Execution**: Runs any shell command with the synchronized time
- **Multiple Time Setting Methods**: Uses settimeofday, clock_settime, and date command as fallbacks
- **Network Delay Compensation**: Accounts for network latency in time calculations
- **Verbose Logging**: Detailed logging for troubleshooting and monitoring
- **Signal Handling**: Graceful cleanup on interruption

## Requirements

- Python 3.6 or higher
- Root privileges (required for system time modification)
- Network access to NTP servers

## Installation

1. Download the `skewkiller` script
2. Make it executable:
   ```bash
   chmod +x skewkiller
   ```

## Usage

```bash
sudo ./skewkiller [OPTIONS] SERVER_IP COMMAND
```

### Arguments

- `SERVER_IP`: NTP server IP address or hostname
- `COMMAND`: Command to execute after time synchronization

### Options

- `-v, --verbose`: Enable verbose logging
- `-h, --help`: Show help message

### Examples

```bash
# Basic usage with IP address
sudo ./skewkiller 192.168.1.1 "ls -la"

# Using public NTP server with verbose output
sudo ./skewkiller -v pool.ntp.org "python3 test_script.py"

# Running a build command with synchronized time
sudo ./skewkiller --verbose time.google.com "make test"

# Testing time-sensitive applications
sudo ./skewkiller 8.8.8.8 "python3 time_sensitive_app.py"
```

## How It Works

1. **Save Current Time**: Records the current system time for later restoration
2. **NTP Query**: Connects to the specified NTP server to get accurate time
3. **Time Synchronization**: Sets the system time to match the NTP server
4. **Command Execution**: Runs your specified command with the synchronized time
5. **Time Restoration**: Restores the original system time (accounting for elapsed execution time)

## NTP Protocol

SkewKiller implements the NTP (Network Time Protocol) client functionality:
- Uses NTP version 3 in client mode
- Handles network delay compensation
- Supports both IP addresses and hostnames
- Timeout protection for network operations

## Time Setting Methods

The tool uses multiple methods to set system time for maximum compatibility:

1. **settimeofday()**: Primary method using libc system call
2. **clock_settime()**: Alternative libc method
3. **date command**: Fallback using system date command

## Error Handling

- **Root Privilege Check**: Ensures the script runs with necessary permissions
- **Network Validation**: Validates IP addresses and handles DNS resolution
- **Timeout Protection**: Prevents hanging on unresponsive NTP servers
- **Signal Handling**: Graceful cleanup on CTRL+C or termination
- **Time Restoration**: Always attempts to restore original time, even on errors

## Security Considerations

- Requires root privileges to modify system time
- Validates NTP server responses to prevent time injection attacks
- Uses secure system calls for time modification
- Implements proper signal handling for cleanup

## Troubleshooting

### Permission Errors
Ensure you're running with root privileges:
```bash
sudo ./skewkiller server_ip "command"
```

### NTP Server Timeout
Try different NTP servers:
- `pool.ntp.org` (public NTP pool)
- `time.google.com` (Google's NTP)
- `time.cloudflare.com` (Cloudflare's NTP)
- `time.apple.com` (Apple's NTP)


