import re
import socket
import urllib.parse
from bs4 import BeautifulSoup
import uuid

host = "hw1.alexbers.com"
port = 80
user = "fb6a088fcac1ae7bdccbd1ce06655c72"

method = "GET"
next_path = "/"
body = ""
headers = {
    "Host": host,
    "Cookie": f"user={user}",
    "Connection": "close"
}

step_counter = 1

while True:
    print(f"Шаг {step_counter}: Отправляем {method} запрос на {next_path} ...")

    headers_str = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
    request = f"{method} {next_path} HTTP/1.1\r\n{headers_str}\r\n\r\n{body}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.send(request.encode())

    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    sock.close()

    _, _, body_part = response.partition(b"\r\n\r\n")
    html_text = body_part.decode("utf-8", errors="ignore")

    if "Шаг #" not in html_text:
        print("\n=== КОНЕЦ! ===")
        print(html_text)
        break

    soup = BeautifulSoup(html_text, "html.parser")

    link_tag = soup.find("a")
    addr_text = soup.find(string=re.compile("адресу"))

    if link_tag and 'href' in link_tag.attrs:
        next_path = link_tag["href"]
    elif addr_text:
        code_tag = addr_text.find_next("code")
        next_path = code_tag.text.strip() if code_tag else "/"
    else:
        next_path = "/"

    markers = {
        "headers": "следующие заголовки",
        "form_data": "следующие данные формы",
        "cookies": "выставлены cookie",
        "params": "следующие параметры запроса",
        "files": "Загрузите файлы"
    }

    parsed_data = {"headers": {}, "form_data": {}, "cookies": {}, "params": {}, "files": {}}

    for key, marker in markers.items():
        text_node = soup.find(string=re.compile(marker))
        if text_node:
            table = text_node.find_next('table')
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        parsed_data[key][cols[0].text.strip()] = cols[1].text.strip()

    method = "POST" if parsed_data["form_data"] or parsed_data["files"] else "GET"

    if parsed_data["params"]:
        query_string = urllib.parse.urlencode(parsed_data["params"])
        next_path = f"{next_path}?{query_string}"

    headers = {
        "Host": host,
        "Connection": "close"
    }

    cookie_list = [f"user={user}"]
    for k, v in parsed_data["cookies"].items():
        cookie_list.append(f"{k}={v}")
    headers["Cookie"] = "; ".join(cookie_list)

    for k, v in parsed_data["headers"].items():
        headers[k] = v

    body = ""
    if method == "POST":
        if parsed_data["files"]:
            print(f"  [!] Прикрепляем файлы к запросу: {list(parsed_data['files'].keys())}")
            boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
            body_parts = []

            for fname, fcontent in parsed_data["files"].items():
                body_parts.append(f"--{boundary}")
                body_parts.append(f'Content-Disposition: form-data; name="{fname}"; filename="{fname}"')
                body_parts.append("Content-Type: application/octet-stream")
                body_parts.append("")
                body_parts.append(fcontent)

            for k, v in parsed_data["form_data"].items():
                body_parts.append(f"--{boundary}")
                body_parts.append(f'Content-Disposition: form-data; name="{k}"')
                body_parts.append("")
                body_parts.append(v)

            body_parts.append(f"--{boundary}--")
            body_parts.append("")

            body = "\r\n".join(body_parts)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        else:
            body = urllib.parse.urlencode(parsed_data["form_data"])
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Content-Length"] = str(len(body.encode('utf-8')))

    step_counter += 1