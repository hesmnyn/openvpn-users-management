# client_info_api.py
"""FastAPI app exposing get_client_info and kill_user using sacli."""
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import subprocess
import json
import re

SACLI = '/usr/sbin/sacli'

app = FastAPI()

def get_client_info():
    """
    Retrieves client info from both OpenVPN log file and from users with 
    `has_access_server_user = True` using the sacli command, 
    and returns a dictionary of {username: {real_address, virtual_address}}.
    """
    info = {}
    # 2. Retrieve connected users with `has_access_server_user = True` using sacli command
    try:
        # Execute the sacli command and parse the output
        result = subprocess.run(
            f"{SACLI} VPNStatus | /usr/bin/jq '.openvpn_0.client_list'",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,  # Run the command in a shell to handle the pipe
            check=True
            )
        client_list = json.loads(result.stdout)
        
        for client in client_list:
            # client is usually a list: [username, real_addr, virt_addr, ...]
            username = str(client[0]).replace("_AUTOLOGIN", "")
            real_addr = client[1] if len(client) > 1 else None
            virt_addr = client[2] if len(client) > 2 else None
            info[username] = {
                'real_address': real_addr,
                'virtual_address': virt_addr,
            }
    except Exception as e:
        print(f"Error fetching client info from sacli: {e}")

    return info


def kill_user(username: str):
    """
    Disconnect a user via sacli. Returns (ok, error_message).
    """
    try:
        completed = subprocess.run(
            [SACLI, "-u", username, "DisconnectUser"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return True, None
    except subprocess.CalledProcessError as e:
        # sacli returned non-zero
        err = e.stderr.strip() if e.stderr else str(e)
        return False, err
    except Exception as e:
        return False, str(e)


@app.get("/client-info")
def client_info():
    try:
        return get_client_info()
    except Exception as exc:  # Repackage unexpected issues as 500 errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --- Disconnect API ---

# Option A: path param (simple curl)
@app.get("/client/{username}/disconnect")
def disconnect_user(username: str):
    # Basic username hygiene (alnum, _, ., -) – adjust to your auth rules
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        raise HTTPException(status_code=400, detail="Invalid username format.")
    ok, err = kill_user(username)
    if ok:
        return {"ok": True, "username": username, "message": "Disconnected."}
    raise HTTPException(status_code=500, detail=err or "Failed to disconnect user.")
