import datetime as dt
import os
from collections import defaultdict

import requests

API_BASE = "https://json.medrating.org"
API_USERS = f"{API_BASE}/users"
API_TODOS = f"{API_BASE}/todos"
MAX_TASK_TITLE_LEN = 48
OUT_DIR = 'tasks'
# If setted to True get creation time from actual file metadata
# If False datetime will be recieved directly from report text
TIME_FROM_CTIME = True


def get_data(url):
    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def make_report_for_all_users(todos):
    all_completed_tasks = defaultdict(list)
    all_uncompleted_tasks = defaultdict(list)
    for task in todos:
        try:
            if task['completed']:
                all_completed_tasks[task['userId']].append(task['title'])
            else:
                all_uncompleted_tasks[task['userId']].append(task['title'])
        except KeyError:
            continue
    return all_completed_tasks, all_uncompleted_tasks


def format_report(user, user_completed, user_uncompleted, completed_n, uncompleted_n, all_n):
    format_title = (
        lambda title: title
        if len(title) <= MAX_TASK_TITLE_LEN
        else title[:MAX_TASK_TITLE_LEN] + '...'
    )

    user_completed = map(format_title, user_completed)
    user_uncompleted = map(format_title, user_uncompleted)
    now_time = dt.datetime.now().strftime("%d.%m.%Y %H:%M")
    newline = '\n'

    return (f"Отчёт для {user['company']['name']}.\n"
            f"{user['name']} <{user['email']}> {now_time}\n"
            f"Всего задач: {all_n}"
            f"\n\n"
            f"Завершённые задачи({completed_n}):\n"
            f"{newline.join(user_completed)}\n"
            f"\n\n"
            f"Оставшиеся задачи({uncompleted_n}):\n"
            f"{newline.join(user_uncompleted)}\n"
            )


if TIME_FROM_CTIME:
    def get_ctime(user):
        try:
            creation_time = os.path.getctime(
                f"{OUT_DIR}/{user['username']}.txt"
            )
            formatted_ctime = dt.datetime.fromtimestamp(
                creation_time).strftime('%d.%m.%Y %H:%M')
            return formatted_ctime
        except OSError:
            return None
else:
    def get_ctime(user):
        try:
            with open(f"{OUT_DIR}/{user['username']}.txt", "r") as f:
                prev_date = f.readline().rstrip().rsplit(None, 2)[-2:]
                return ' '.join(prev_date)
        except (OSError, IOError):
            return None


def save_report_to_file(user, user_completed, user_uncompleted, prev_date):
    report_name = f"{OUT_DIR}/{user['username']}.txt"
    completed_tasks = len(user_completed)
    uncompleted_tasks = len(user_uncompleted)
    all_n = completed_tasks + uncompleted_tasks

    with open(f"{report_name}.new", "w") as f:
        f.write(format_report(user, user_completed, user_uncompleted, completed_tasks, uncompleted_tasks, all_n))

    if prev_date:
        date_fname = dt.datetime.strptime(
            prev_date,
            "%d.%m.%Y %H:%M"
        ).strftime("%Y-%m-%dT%H_%M")
        os.rename(
            report_name,
            f"{OUT_DIR}/old_{user['username']}_{date_fname}.txt"
        )
    os.rename(f"{report_name}.new", report_name)


def full_report(users, all_completed_tasks, all_uncompleted_tasks):
    for user in users:
        save_report_to_file(
            user,
            all_completed_tasks.get(user['id'], []),
            all_uncompleted_tasks.get(user['id'], []),
            get_ctime(user)
        )

    all_ids = set([user['id'] for user in users])
    completed_ids = set(all_completed_tasks.keys())
    uncompleted_ids = set(all_uncompleted_tasks.keys())

    if all_ids == completed_ids.union(uncompleted_ids):
        return

    print("== Extra ==")
    print("Users with no tasks: ")
    print(", ".join(list(all_ids.difference(
        completed_ids.union(uncompleted_ids)))))
    print("User ids from task with no user description: ")
    print(", ".join(list(
        completed_ids.union(uncompleted_ids).difference(all_ids)
    )))


def main():
    users = get_data(API_USERS)
    todos = get_data(API_TODOS)
    all_completed_tasks, all_uncompleted_tasks = (
        make_report_for_all_users(todos)
    )

    try:
        os.makedirs(OUT_DIR, exist_ok=True)
    except OSError:
        raise OSError("Can't create destination directory tasks!")

    full_report(users, all_completed_tasks, all_uncompleted_tasks)


if __name__ == '__main__':
    main()
