import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import reduce
from multiprocessing import JoinableQueue
from queue import Empty

from ..utils.bar_custom import count_bar, message_bar, sleep_bar
from ..utils.help_func import get_remote_base_path, norm_path
from .file_uploader import (
    create_folder_by_name,
    get_files_by_name,
    get_upload_url,
    upload_file,
)


def get_path(local_paths, remote_base_path):
    file_list = []
    for path in local_paths:
        if os.path.isfile(path):
            name = os.path.basename(path)
            remote_path = norm_path(os.path.join(remote_base_path, name))
            file_list.append((path, "/" + remote_path))
        else:
            base_path, _ = os.path.split(path)
            bar = count_bar(message="个文件夹已完成")
            for root, _, files in os.walk(norm_path(path)):
                for name in files:
                    local_path = os.path.join(root, name)
                    remote_path = norm_path(
                        os.path.join(
                            remote_base_path, root[len(base_path) :].strip("/"), name
                        )
                    )
                    file_list.append((local_path, "/" + remote_path))
                bar.postfix = [root]
                bar.update(1)
            bar.close()
    return file_list


def create_folders(client, dir_list):
    dirs = []
    path_map = {"/": "root"}

    def add_path(x, y):
        rusult = x + "/" + y
        dirs.append(rusult)
        return rusult

    [reduce(add_path, d.split("/")) for d in dir_list]

    dir_sorted = sorted(set(dirs), key=lambda x: len(x))
    try:
        bar = count_bar(message="个文件夹已完成")
        for d in dir_sorted:
            dir_path, dir_name = os.path.split(d)

            base_folder_id = path_map.get(dir_path)
            has_folder = get_files_by_name(client, base_folder_id, dir_name)
            if not has_folder:
                folder = create_folder_by_name(client, base_folder_id, dir_name)
                folder_id = folder.get("id")
            else:
                folder_id = has_folder[0].get("id")

            path_map[d] = folder_id
            bar.postfix = ["gd:" + d]
            bar.update(1)
        bar.close()
        return path_map, True
    except Exception as e:
        return e, False


def put(client, args):
    local_paths = args.rest[:-1]
    remote_base_path = get_remote_base_path(args.rest[-1])

    q = JoinableQueue()
    sleep_q = JoinableQueue()

    file_list = get_path(local_paths, remote_base_path)
    [q.put(i) for i in file_list]

    dir_list = set([os.path.dirname(i[1]) for i in file_list])
    result, status = create_folders(client, dir_list)

    if status is False:
        message_bar(message="创建文件夹时发生错误，稍后重试" + str(result))
        return
    else:
        path_map = result

    def do_task(task):
        sleep_q.join()
        local_path, remote_path = task

        base_dir, name = os.path.split(remote_path)
        parent_id = path_map.get(base_dir)
        status, upload_url, sleep_time = get_upload_url(
            client, parent_id if parent_id else "root", name
        )

        if status == "good":
            result = upload_file(
                local_path=local_path,
                upload_url=upload_url,
                chunk_size=args.chunk,
                step_size=args.step,
                proxies=args.proxies,
            )
            if result is not True:
                q.put(task)
        elif status == "exist":
            message_bar(remote_path="gd:" + remote_path, message="文件已存在")
        else:
            q.put(task)
            message_bar(
                remote_path="gd:" + remote_path, message="发生错误 (稍后重试): " + status
            )

        if sleep_time != 0:
            if sleep_q.empty():
                sleep_q.put(sleep_time)

        q.task_done()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        while True:
            if q._unfinished_tasks._semlock._is_zero():
                break
            elif not sleep_q.empty():
                sleep_time = sleep_q.get()
                sleep_bar(sleep_time=sleep_time)
                sleep_q.task_done()
            else:
                try:
                    task = q.get(timeout=args.sleep_time)
                except Empty:
                    continue
                else:
                    executor.submit(do_task, task)
                    time.sleep(args.sleep_time)

    return client
