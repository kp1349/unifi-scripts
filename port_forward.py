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
PORT_FORWARD_FILE = "port_forward.yaml"

def login_and_get_session():
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

def load_port_forward_rules(yaml_file):
    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)
    return config.get("port_forwards", [])

def create_port_forward(rule, cookies, csrf_token):
    url = f"https://{ROUTER_IP}/proxy/network/api/s/default/rest/portforward"
    headers = {
        "Content-Type": "application/json",
        "X-Csrf-Token": csrf_token
    }

    protocols = [rule["protocol"]] if rule["protocol"] in ["tcp", "udp"] else ["tcp", "udp"]
    for proto in protocols:
        payload = {
            "enabled": True,
            "name": rule["name"],
            "dst_port": str(rule["dst_port"]),
            "forward_ip": rule["forward_ip"],
            "forward_port": str(rule["forward_port"]),
            "proto": proto,
            "dst_interface": "wan",
            "src": "any",
            "forward_nat": True,
            "site_id": "default"
        }

        response = requests.post(url, headers=headers, cookies=cookies, json=payload, verify=False)
        print(f"📡 Creating: {rule['name']} ({proto}) → {rule['forward_ip']}:{rule['forward_port']} from WAN:{rule['dst_port']}")
        print(f"Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    try:
        cookies, csrf_token = login_and_get_session()
        rules_to_add = load_port_forward_rules(PORT_FORWARD_FILE)

        for rule in rules_to_add:
            create_port_forward(rule, cookies, csrf_token)

        print("✅ Port forward processing complete.")

    except Exception as e:
        print("❌ Error:", e)
