import os
import telnetlib

# Management interface connection settings (configure via env vars)
MGMT_HOST = os.getenv('OPENVPN_MGMT_HOST', '127.0.0.1')
MGMT_PORT = int(os.getenv('OPENVPN_MGMT_PORT', 7505))
MGMT_TIMEOUT = int(os.getenv('OPENVPN_MGMT_TIMEOUT', 5))  # seconds
OPEN_VPN_LOG = os.getenv('OPEN_VPN_LOG', '/var/log/openvpn/status.log')

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
    """Admin view to send kill command via Telnet"""
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
        # self.message_user(request, f"Sent kill command for {obj.username}", messages.SUCCESS)
    except Exception as e:
        # print(e)
        return False
        # self.message_user(request, f"Error sending kill command for {obj.username}: {e}", messages.ERROR)
    # Redirect back to changelist
    # return redirect(request.META.get('HTTP_REFERER', 'admin:index'))