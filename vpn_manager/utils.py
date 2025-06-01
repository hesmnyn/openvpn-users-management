import os
import telnetlib
from decouple import config
import subprocess
from django.conf import settings


from vpn_manager.models import VPNUser

# Management interface connection settings (configure via env vars)
MGMT_HOST = config('OPENVPN_MGMT_HOST', default='127.0.0.1')
MGMT_PORT = int(config('OPENVPN_MGMT_PORT', default=7505))
MGMT_TIMEOUT = int(config('OPENVPN_MGMT_TIMEOUT', default=5))  # seconds
OPEN_VPN_LOG = config('OPEN_VPN_LOG', default='/var/log/openvpn/status.log')

SACLI = settings.SACLI_FULL_PATH

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
    Retrieves client info from both OpenVPN log file and from users with 
    `has_access_server_user = True` using the sacli command, 
    and returns a dictionary of {username: {real_address, virtual_address}}.
    """
    info = {}

    # 1. Read from OpenVPN log
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
        pass  # If reading the log fails, proceed with only the sacli results

    # 2. Retrieve connected users with `has_access_server_user = True` using sacli command
    try:
        # Execute the sacli command and parse the output
        result = subprocess.run(
            [SACLI, "VPNStatus", "|", "jq", ".openvpn_0.client_list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        client_list = json.loads(result.stdout)
        
        for client in client_list:
            username = client[0].replace("_AUTOLOGIN", "")  # Username is at index 0 in the client info
            real_addr = client[1]  # Real Address is at index 1
            virt_addr = client[2]  # Virtual Address is at index 2

            # Add to the info dictionary
            info[username] = {
                'real_address': real_addr,
                'virtual_address': virt_addr,
            }
    except Exception as e:
        print(f"Error fetching client info from sacli: {e}")

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


def kill_user(username, has_access_server_user):
    """Admin view to send kill command via Telnet or via sacli if has_access_server_user"""
    if has_access_server_user:
        try:
            # Run the sacli command
            subprocess.run(
                [SACLI, '-u', username, 'DisconnectUser'],
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
            SACLI, '-u', username,
            '--key', 'user_auth_type',
            '--value', 'local',
            'UserPropPut'
        ], check=True)

        # 2. Set local password
        subprocess.run([
            SACLI, '-u', username,
            '--new_pass', password,
            'SetLocalPassword'
        ], check=True)

        # 3. Set prop_autologin to true
        subprocess.run([
            SACLI, '-u', username,
            '--key', 'prop_autologin',
            '--value', 'true',
            'UserPropPut'
        ], check=True)

        return True

    except subprocess.CalledProcessError as e:
        # Optionally log e.stdout or e.stderr here
        print(f"Error running sacli command: {e}")
        return False
    

def prop_deny_user_sacli_commands(username: str, value: str):
    try:
        subprocess.run([
            SACLI,
            '-u', username,
            '-k', 'prop_deny',
            '-v', value,
            'UserPropPut'
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting prop_deny for {username}: {e}")
        return False