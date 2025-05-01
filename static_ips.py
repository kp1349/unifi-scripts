import requests
from http.cookiejar import MozillaCookieJar
import os
import yaml
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings()

# Load environment variables
load_dotenv()
ROUTER_IP = os.getenv("ROUTER_IP")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
COOKIE_FILE = "cookies.txt"
YAML_FILE = "static_ips.yaml"

def login_and_get_session():
    """Logs in to UniFi OS and returns session cookies and CSRF token."""
    jar = MozillaCookieJar(COOKIE_FILE)
    session = requests.Session()
    session.cookies = jar
    session.verify = False

    login_url = f"https://{ROUTER_IP}/api/auth/login"
    response = session.post(login_url, json={"username": USERNAME, "password": PASSWORD})
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.status_code} - {response.text}")
    print("✅ Logged in")

    stat_url = f"https://{ROUTER_IP}/proxy/network/api/s/default/stat/sta"
    stat_response = session.get(stat_url)
    csrf_token = stat_response.headers.get("X-Csrf-Token")
    if not csrf_token:
        raise RuntimeError("❌ CSRF token not found in response headers.")

    jar.save(ignore_discard=True, ignore_expires=True)
    return jar, csrf_token

def list_clients(cookies, csrf_token):
    """Returns a dict of connected MAC addresses."""
    url = f"https://{ROUTER_IP}/proxy/network/api/s/default/stat/sta"
    headers = {
        "Content-Type": "application/json",
        "X-Csrf-Token": csrf_token
    }
    response = requests.get(url, headers=headers, cookies=cookies, verify=False)
    clients = response.json().get("data", [])
    macs = {client["mac"].lower(): client for client in clients}
    return macs

def assign_static_ip(mac, ip, cookies, csrf_token):
    """Assigns a static IP to a known MAC address."""
    mac_clean = mac.replace(":", "").lower()
    url = f"https://{ROUTER_IP}/proxy/network/api/s/default/rest/user/{mac_clean}"

    headers = {
        "Content-Type": "application/json",
        "X-Csrf-Token": csrf_token
    }

    payload = {
        "use_fixedip": True,
        "fixed_ip": ip
    }

    response = requests.put(url, headers=headers, cookies=cookies, json=payload, verify=False)
    print(f"📡 PUT Status for {mac} → {ip}: {response.status_code}")
    print(response.text)

def load_static_ip_config(yaml_file):
    """Loads static IPs from a YAML file."""
    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)
    return config.get("static_ips", [])

if __name__ == "__main__":
    try:
        cookies, csrf_token = login_and_get_session()
        clients = list_clients(cookies, csrf_token)
        static_ips = load_static_ip_config(YAML_FILE)

        for entry in static_ips:
            mac = entry["mac"].lower()
            ip = entry["ip"]
            if mac in clients:
                print(f"✅ Assigning {ip} to {mac}")
                assign_static_ip(mac, ip, cookies, csrf_token)
            else:
                print(f"❌ Skipping {mac} — not currently connected.")

    except Exception as e:
        print("❌ Error:", e)
