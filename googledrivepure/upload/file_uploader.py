import json
import os

import requests

from ..utils.bar_custom import message_bar, upload_bar
from ..utils.help_func import get_data, get_headers


def create_folder_by_name(client, parent_id, name):
    data = json.dumps(
        {
            "name": name,
            "parents": [parent_id],
            "mimeType": "application/vnd.google-apps.folder",
        }
    )
    headers = get_headers(client)
    r = requests.post(
        client.drive_url, headers=headers, data=data, proxies=client.proxies
    )
    files = r.json()
    return files


def get_files_by_name(client, parent_id, name, file_type="folder"):
    params = {
        "q": "'{parent_id}' in parents and "
        "name = '{name}' and "
        "mimeType {file_type} 'application/vnd.google-apps.folder' and "
        "not trashed".format(
            parent_id=parent_id,
            file_type=("=" if file_type == "folder" else "!="),
            name=name.replace("'", r"\'"),
        )
    }
    headers = get_headers(client)
    r = requests.get(
        client.drive_url, headers=headers, params=params, proxies=client.proxies
    )
    files = r.json().get("files", [])
    return files


def get_upload_url(client, parent_id, name):
    try:
        API_HOST = "https://www.googleapis.com/upload/drive/v3/files"
        exist_file = get_files_by_name(client, parent_id, name, file_type="file")
        if exist_file:
            return "exist", "", 0

        params = {"uploadType": "resumable"}
        headers = get_headers(client)
        data = json.dumps({"name": name, "parents": [parent_id]})

        r = requests.post(
            API_HOST, headers=headers, data=data, params=params, proxies=client.proxies
        )
        code = r.status_code
        error = r.json().get("error", {})
        mes = "{}:{}".format(
            error.get("code"), error.get("errors", ["UnknownError"])[0].get("reason"),
        )
        if code == 200:
            return "good", r.headers.get("Location"), 0
        elif code == 429 or "LimitExceeded" in mes:
            sleep_time = r.headers.get("Retry-After", 1)
            return "sleep", "", int(sleep_time)
        else:
            return mes, "", 0

    except Exception as e:
        return str(e), "", 0


def upload_piece(
    upload_url, local_path, file_range, file_size, step_size, bar, proxies
):
    start, end = file_range
    content_length = end - start + 1
    headers = {
        "Content-Range": "bytes {}-{}/{}".format(start, end, file_size),
        "Content-Length": str(content_length),
    }

    with open(local_path, "rb") as f:
        f.seek(file_range[0])
        file_piece = f.read(content_length)

        data = get_data(file_piece, bar, step_size=step_size)
        req = requests.put(upload_url, headers=headers, data=data, proxies=proxies)
        return req.status_code


def upload_file(local_path, upload_url, chunk_size, step_size, proxies=None):
    try:
        file_size = os.path.getsize(local_path)
        if file_size == 0:
            message_bar(remote_path=local_path, message="发生错误 (稍后重试): 文件为空")
        range_list = [[i, i + chunk_size - 1] for i in range(0, file_size, chunk_size)]
        range_list[-1][-1] = file_size - 1

        bar = upload_bar(total=file_size, path=local_path)
        for file_range in range_list:
            code = upload_piece(
                upload_url=upload_url,
                local_path=local_path,
                file_range=file_range,
                file_size=file_size,
                step_size=step_size,
                bar=bar,
                proxies=proxies,
            )
            if code not in (200, 201, 308):
                bar.close()
                return False
        bar.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    pass
