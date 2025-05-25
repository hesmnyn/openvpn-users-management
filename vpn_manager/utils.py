import os
import telnetlib
from decouple import config
import subprocess

from vpn_manager.models import VPNUser

# Management interface connection settings (configure via env vars)
MGMT_HOST = config('OPENVPN_MGMT_HOST', default='127.0.0.1')
MGMT_PORT = int(config('OPENVPN_MGMT_PORT', default=7505))
MGMT_TIMEOUT = int(config('OPENVPN_MGMT_TIMEOUT', default=5))  # seconds
OPEN_VPN_LOG = config('OPEN_VPN_LOG', default='/var/log/openvpn/status.log')

def get_connected_usernames():
    """
    Connects to the OpenVPN management interface via Telnet, issues 'status',
    and returns a set of usernames (common names) currently connected.
    """
    users = set()
    try:
        # Open Telnet connection to the management interface
        tn = telnetlib.Telnet(MGMT_HOST, MGMT_PORT, timeout=MGMT_TIMEOUT)
        # Read and discard the initial banner line(s)
        # The banner typically ends with a newline, so read until newline
        tn.read_until(b"\n", timeout=MGMT_TIMEOUT)
        # Send the 'status' command
        tn.write(b"status\n")
        # Read response until the 'END' marker followed by newline
        raw_output = tn.read_until(b"END\n", timeout=MGMT_TIMEOUT)
        output = raw_output.decode('utf-8', errors='ignore')
        # Close the Telnet connection
        tn.close()
        # Parse each line for CLIENT_LIST entries
        for line in output.splitlines():
            if line.startswith('CLIENT_LIST'):
                parts = line.split(',')
                if len(parts) > 1:
                    users.add(parts[1])
    except Exception:
        # On error (timeout, connection refused), return an empty set
        return set()
    return users

def get_client_info():
    """
    Connects to the OpenVPN management interface via Telnet,
    issues 'status', and returns a dict mapping username -> {
        'real_address': <Real Address>,
        'virtual_address': <Virtual Address>
    } for all currently connected clients.
    """
    info = {}
    try:
        with open(OPEN_VPN_LOG, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('CLIENT_LIST'):
                    parts = line.split(',')
                    # parts: ['CLIENT_LIST', username, real_addr, virt_addr, ...]
                    if len(parts) >= 4:
                        _, username, real_addr, virt_addr = parts[:4]
                        info[username] = {
                            'real_address': real_addr,
                            'virtual_address': virt_addr,
                        }
    except Exception:
        # On any error, return what we have (possibly empty)
        pass
    return info

def get_connected_usernames_from_file():
    """
    Reads the OpenVPN status log file and returns a set of usernames (common names) currently connected.
    """
    users = set()
    try:
        # Open and read the status log file
        with open(OPEN_VPN_LOG, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Parse lines starting with CLIENT_LIST
                if line.startswith('CLIENT_LIST'):
                    parts = line.strip().split(',')
                    if len(parts) > 1:
                        users.add(parts[1])
    except Exception:
        # On error (file not found, permission issue), return an empty set
        return set()
    return users


def kill_user(username):
    """Admin view to send kill command via Telnet or via sacli if has_access_server_user"""
    user = VPNUser.objects.get(username=username)
    if user.has_access_server_user:
        try:
            # Run the sacli command
            subprocess.run(
                ['sacli', '-u', username, 'DisconnectUser'],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            # Log e.stderr or handle error as needed
            return False
    else:
        try:
            # Connect to management interface
            tn = telnetlib.Telnet(MGMT_HOST, MGMT_PORT, timeout=MGMT_TIMEOUT)
            # Read and discard the initial banner line
            tn.read_until(b"\n", timeout=MGMT_TIMEOUT)
            # Send kill command for the common name
            cmd = f"kill {username}\n".encode('utf-8')
            tn.write(cmd)
            # Optionally read until the END marker to confirm
            tn.read_until(b"END\n", timeout=MGMT_TIMEOUT)
            tn.close()
            return True
        except Exception as e:
            return False


def create_user_sacli_commands(username: str, password: str):
    try:
        # 1. Set user_auth_type to local
        subprocess.run([
            'sacli', '-u', username,
            '--key', 'user_auth_type',
            '--value', 'local',
            'UserPropPut'
        ], check=True)

        # 2. Set local password
        subprocess.run([
            'sacli', '-u', username,
            '--new_pass', password,
            'SetLocalPassword'
        ], check=True)

        # 3. Set prop_autologin to true
        subprocess.run([
            'sacli', '-u', username,
            '--key', 'prop_autologin',
            '--value', 'true',
            'UserPropPut'
        ], check=True)

        return True

    except subprocess.CalledProcessError as e:
        # Optionally log e.stdout or e.stderr here
        print(f"Error running sacli command: {e}")
        return False
    

def prop_deny_user_sacli_commands(username: str, value: str = "false"):
    try:
        subprocess.run([
            'sacli',
            '-u', username,
            '-k', 'prop_deny',
            '-v', value,
            'UserPropPut'
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting prop_deny for {username}: {e}")
        return False