import datetime
import random
import requests
import re
import threading
import time
from hashlib import md5
from time import time as T
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
import sys

# --- CẤU HÌNH ---
MAX_WORKERS = 500       # Số luồng chạy song song
PROXY_TIMEOUT = 5       # Giới hạn thời gian kết nối proxy (giây) - Hàng free nên để thấp
RETRY_DELAY = 1         # Thời gian nghỉ khi hết proxy

# Màu sắc cho Terminal đẹp hơn
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

# --- DANH SÁCH NGUỒN PROXY (HTTP/HTTPS) ---
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-LIST/master/http.txt",
    "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"
]

MEMORY_PROXIES = []

# --- CLASS SIGNATURE (GIỮ NGUYÊN) ---
class Signature:
    def __init__(self, params: str, data: str, cookies: str) -> None:
        self.params = params
        self.data = data
        self.cookies = cookies

    def hash(self, data: str) -> str:
        return str(md5(data.encode()).hexdigest())

    def calc_gorgon(self) -> str:
        gorgon = self.hash(self.params)
        if self.data: gorgon += self.hash(self.data)
        else: gorgon += str("0"*32)
        if self.cookies: gorgon += self.hash(self.cookies)
        else: gorgon += str("0"*32)
        gorgon += str("0"*32)
        return gorgon

    def get_value(self):
        gorgon = self.calc_gorgon()
        return self.encrypt(gorgon)

    def encrypt(self, data: str):
        unix = int(T())
        len = 0x14
        key = [0xDF,0x77,0xB9,0x40,0xB9,0x9B,0x84,0x83,0xD1,0xB9,0xCB,0xD1,0xF7,0xC2,0xB9,0x85,0xC3,0xD0,0xFB,0xC3]
        param_list = []
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(H)
        param_list.extend([0x0, 0x6, 0xB, 0x1C])
        H = int(hex(unix), 16)
        param_list.append((H & 0xFF000000) >> 24)
        param_list.append((H & 0x00FF0000) >> 16)
        param_list.append((H & 0x0000FF00) >> 8)
        param_list.append((H & 0x000000FF) >> 0)
        eor_result_list = []
        for A, B in zip(param_list, key):
            eor_result_list.append(A ^ B)
        for i in range(len):
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % len]
            E = C ^ D
            F = self.rbit(E)
            H = ((F ^ 0xFFFFFFFF) ^ len) & 0xFF
            eor_result_list[i] = H
        result = ""
        for param in eor_result_list:
            result += self.hex_string(param)
        return {"X-Gorgon": ("840280416000" + result), "X-Khronos": str(unix)}

    def rbit(self, num):
        result = ""
        tmp_string = bin(num)[2:]
        while len(tmp_string) < 8: tmp_string = "0" + tmp_string
        for i in range(0, 8): result = result + tmp_string[7 - i]
        return int(result, 2)

    def hex_string(self, num):
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2: tmp_string = "0" + tmp_string
        return tmp_string

    def reverse(self, num):
        tmp_string = self.hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)

# --- QUẢN LÝ PROXY ---
def download_proxies():
    """Tải và gộp proxy từ nhiều nguồn GitHub"""
    global MEMORY_PROXIES
    MEMORY_PROXIES = [] 
    print(f"{Color.YELLOW}[*] Đang quét proxy từ {len(PROXY_SOURCES)} nguồn GitHub...{Color.RESET}")
    
    total_raw = 0
    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                for line in lines:
                    line = line.strip()
                    if line and ':' in line:
                        MEMORY_PROXIES.append(line)
                        total_raw += 1
        except:
            continue

    # Lọc trùng
    MEMORY_PROXIES = list(set(MEMORY_PROXIES))
    print(f"{Color.GREEN}[+] Đã tìm thấy {len(MEMORY_PROXIES)} proxy sống (HTTP).{Color.RESET}")

    if not MEMORY_PROXIES:
        print(f"{Color.RED}[!] Không tải được proxy nào. Vui lòng kiểm tra mạng!{Color.RESET}")
        sys.exit()

def get_random_proxy():
    if not MEMORY_PROXIES: return None
    proxy_line = random.choice(MEMORY_PROXIES)
    try:
        if '|' in proxy_line: proxy_line = proxy_line.split('|')[-1].strip()
        parts = proxy_line.split(':')
        if len(parts) == 2:
            return {"http": f"http://{parts[0]}:{parts[1]}", "https": f"http://{parts[0]}:{parts[1]}"}
        elif len(parts) == 4:
            return {"http": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}", 
                    "https": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"}
    except: return None
    return None

# --- GIẢ LẬP THIẾT BỊ ---
def generate_device_info():
    device_id = str(random.randint(6900000000000000000, 7999999999999999999))
    openudid = secrets.token_hex(20)
    client_uuid = str(uuid.uuid4())
    iid = str(random.randint(6900000000000000000, 7999999999999999999))
    os_major = random.randint(14, 16)
    os_minor = random.randint(0, 5)
    os_version = f"{os_major}.{os_minor}"
    return device_id, openudid, client_uuid, iid, os_version

# --- LUỒNG CHÍNH ---
def worker_task(video_id):
    url_view = 'https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/'
    
    while True:
        proxy = None
        try:
            proxy = get_random_proxy()
            if not proxy: 
                time.sleep(RETRY_DELAY)
                continue

            # Fake Info
            dev_id, open_udid, c_uuid, iid, os_ver = generate_device_info()
            random_hex = secrets.token_hex(16)
            
            # Params
            params = (
                f"pass-region=1&pass-route=1&language=vi&version_code=17.4.0"
                f"&app_name=musical_ly&vid={c_uuid.upper()}"
                f"&app_version=17.4.0&carrier_region=VN&channel=App%20Store"
                f"&mcc_mnc=45201&device_id={dev_id}"
                f"&tz_offset=25200&account_region=VN&sys_region=VN"
                f"&aid=1233&residence=VN&screen_width=1125&uoo=1"
                f"&openudid={open_udid}&os_api=18&os_version={os_ver}"
                f"&app_language=vi&tz_name=Asia%2FHo_Chi_Minh&current_region=VN"
                f"&device_platform=iphone&build_number=174014&device_type=iPhone14,6"
                f"&iid={iid}&idfa=00000000-0000-0000-0000-000000000000"
                f"&locale=vi&cdid={c_uuid.upper()}&content_language="
            )

            data_body = {
                'action_time': int(time.time()),
                'aweme_type': 0,
                'first_install_time': int(time.time()) - random.randint(10000, 999999),
                'item_id': video_id,
                'play_delta': 1,
                'tab_type': 4
            }

            # Ký Gorgon
            sig = Signature(params=params, data=str(data_body), cookies=f'sessionid={random_hex}').get_value()

            headers = {
                'Host': 'api16-core-c-alisg.tiktokv.com',
                'Sdk-Version': '2',
                'Passport-Sdk-Version': '5.12.1',
                'X-Tt-Token': f'01{random_hex}0263ef2c...', 
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': f'TikTok 17.4.0 rv:174014 (iPhone; iOS {os_ver}; vi_VN@calendar=gregorian) Cronet',
                'X-Khronos': sig['X-Khronos'],
                'X-Gorgon': sig['X-Gorgon'],
                'X-Common-Params-V2': params,
            }
            cookies = {'sessionid': random_hex}
            full_url = f"{url_view}?{params}"

            # Gửi Request (Timeout 5s)
            r = requests.post(full_url, data=data_body, headers=headers, cookies=cookies, proxies=proxy, timeout=PROXY_TIMEOUT)
            
            if r.status_code == 200 and r.json().get('status_code') == 0:
                print(f"{Color.GREEN}[+] SUCCESS | Thread {threading.get_ident()} | View Sent!{Color.RESET}")
            else:
                # Proxy connect được nhưng bị chặn hoặc lỗi logic
                # print(f"{Color.YELLOW}[-] Fail Status: {r.status_code}{Color.RESET}")
                pass

        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            # Các lỗi này xảy ra thường xuyên với proxy free -> Bỏ qua không in
            continue
        except Exception as e:
            continue

# --- MAIN ---
if __name__ == "__main__":
    print(f"""
    {Color.GREEN}=== TIKTOK VIEW BOOSTER (MULTI-SOURCE PROXY) ==={Color.RESET}
    """)
    
    link = input('Nhập Link Video TikTok: ')
    
    # Lấy ID
    video_id = ""
    try:
        headers_id = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(link, headers=headers_id, timeout=10, allow_redirects=True)
        if "/video/" in page.url:
            video_id = page.url.split("/video/")[1].split("?")[0]
        else:
            match = re.search(r'"video":\{"id":"(\d+)"', page.text)
            if match: video_id = match.group(1)
    except:
        pass

    if not video_id:
        print(f"{Color.RED}[-] Không lấy được ID Video. Link sai hoặc video private.{Color.RESET}")
        sys.exit()
    
    print(f"{Color.GREEN}[+] Target Video ID: {video_id}{Color.RESET}")

    # Tải Proxy
    download_proxies()

    # Chạy luồng
    print(f"{Color.YELLOW}[*] Đang khởi chạy {MAX_WORKERS} luồng... (Có thể mất vài giây để bắt đầu thấy kết quả){Color.RESET}")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _ in range(MAX_WORKERS):
            executor.submit(worker_task, video_id)
