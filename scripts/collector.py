import requests
import base64
import re
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration - Added more reliable sources
SOURCES = [
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/IranianCypherpunks/sub/main/sub",
    "https://raw.githubusercontent.com/vfarid/v2ray-share/main/configs.txt",
    "https://raw.githubusercontent.com/iboxz/free-v2ray-collector/main/main/mix.txt",
    "https://raw.githubusercontent.com/Lidatong/v2ray_rules/master/all.txt",
    "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/all.txt"
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def check_ping(config):
    """Improved TCP ping check with better parsing and timeout handling"""
    try:
        # Support for different protocols
        if config.startswith("vmess://"):
            # VMess is base64 encoded, need to decode to find address
            try:
                v_data = base64.b64decode(config[8:]).decode('utf-8')
                host = re.search(r'"add":"([^"]+)"', v_data).group(1)
                port = int(re.search(r'"port":"?(\d+)"?', v_data).group(1))
            except: return False
        else:
            # VLESS, Trojan, SS
            host_port = re.search(r'@([^:/]+):(\d+)', config)
            if not host_port: return False
            host = host_port.group(1)
            port = int(host_port.group(2))
        
        # DNS Resolution check
        try:
            ip = socket.gethostbyname(host)
        except: return False

        # TCP Connect check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5) # Faster timeout for better quality
        start_time = time.time()
        result = sock.connect_ex((ip, port))
        end_time = time.time()
        sock.close()
        
        if result == 0:
            latency = int((end_time - start_time) * 1000)
            return latency < 1000 # Only keep configs with < 1s latency
    except:
        pass
    return False

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def collect():
    all_configs = []
    for source in SOURCES:
        try:
            response = requests.get(source, timeout=15)
            if response.status_code == 200:
                content = response.text
                if "://" not in content[:50]:
                    try: content = base64.b64decode(content).decode('utf-8')
                    except: pass
                all_configs.extend(content.splitlines())
        except: pass

    unique_configs = list(set([c.strip() for c in all_configs if "://" in c]))
    
    # Parallel testing with more workers
    valid_configs = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(check_ping, unique_configs))
        for config, is_valid in zip(unique_configs, results):
            if is_valid: valid_configs.append(config)
    
    categories = {"vless": [], "vmess": [], "trojan": [], "ss": [], "mix": valid_configs}
    for config in valid_configs:
        if config.startswith("vless://"): categories["vless"].append(config)
        elif config.startswith("vmess://"): categories["vmess"].append(config)
        elif config.startswith("trojan://"): categories["trojan"].append(config)
        elif config.startswith("ss://"): categories["ss"].append(config)

    os.makedirs("configs", exist_ok=True)
    for cat, configs in categories.items():
        with open(f"configs/{cat}.txt", "w") as f: f.write("\n".join(configs))
        with open(f"configs/{cat}_sub.txt", "w") as f:
            f.write(base64.b64encode("\n".join(configs).encode('utf-8')).decode('utf-8'))

    msg = (
        "🚀 *Freedom V2Ray Updated!*\n\n"
        f"✅ High-Speed Configs: `{len(valid_configs)}` \n"
        f"🔹 VLESS: `{len(categories['vless'])}` \n"
        f"🔹 VMESS: `{len(categories['vmess'])}` \n"
        f"🔹 Trojan: `{len(categories['trojan'])}` \n"
        f"🔹 Shadowsocks: `{len(categories['ss'])}` \n\n"
        "⏱ Update Interval: `2 Hours` \n"
        "🌐 [View on GitHub](https://github.com/MahanKenway/Freedom-V2Ray)"
    )
    send_telegram_msg(msg)

if __name__ == "__main__":
    collect()
