# Made by KaBoT. Discord: @kabot
# This project/code is licensed under the Apache 2.0 license

import requests, tempfile, zipfile, shutil, json, subprocess, re, os, time
from pathlib import Path
from sqlitedict import SqliteDict
import typer
from rich import print
from rich.progress import (
    track,
    Progress,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TextColumn,
    BarColumn,
    SpinnerColumn,
)
from typing import Annotated, Literal
from enum import Enum
import platform as pl

# Сюда можно поместить свой путь до папки с нужным содержимым. Пример "путь/до/папок"
CONFIGURED_PATH = False


if CONFIGURED_PATH:
    os.chdir(CONFIGURED_PATH)

if Path("vcim.db").exists():
    db = SqliteDict("vcim.db", autocommit=True)
    os.chdir(db["dir"])
else:
    db = None


app = typer.Typer(
    help="**VoxelCore Instances Manager (VCIM)** - проект призванный **стандартизировать** подход к разработке лаунчеров, а также **упростить** их разработку",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

instances = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")
app.add_typer(instances, name="instances", help="Категория комманд для истансов")

cache = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")
app.add_typer(cache, name="cache", help="Категория комманд для управления кэш-ем")

repo = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")
app.add_typer(
    repo, name="repo", help="Категория комманд для управления репозиториями GitHub"
)


def process_handler(process: subprocess.Popen):
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            i = output.strip()
            tmatch = re.match(r"^\[(\w)\]\s+([\d/: .+-]+)\s+\[(.*?)\]\s+(.*)$", i)

            if tmatch:
                match tmatch.group(1):
                    case "I":
                        t = "[blue][I][/blue]"
                    case "W":
                        t = "[yellow][W][/yellow]"
                    case "E":
                        t = "[red][E][/red]"
                    case _:
                        t = f"[{tmatch.group(1)}]"
                print(
                    f"{t} {tmatch.group(2)} [bright_black][{tmatch.group(3)}][/bright_black] {tmatch.group(4)}"
                )
            else:
                print(i)
            # print(f"{i[0]} {i[1]} {i[2]} {}")
    return_code = process.poll()
    print(f"Игра завершилась с кодом: {return_code}")


def format_seconds(seconds: int):
    hours = seconds // 3600
    remaining_seconds = seconds % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    parts = []
    if hours > 0:
        parts.append(
            f"{hours} час{'ов' if hours % 10 in (0, 5, 6, 7, 8, 9) or 11 <= hours % 100 <= 19 else 'а' if hours % 10 in (2, 3, 4) else ''}"
        )
    if minutes > 0:
        parts.append(
            f"{minutes} минут{'а' if minutes % 10 == 1 and minutes != 11 else 'ы' if minutes % 10 in (2, 3, 4) and not 11 <= minutes % 100 <= 19 else ''}"
        )
    if seconds > 0 or not parts:
        parts.append(
            f"{seconds} секунд{'а' if seconds % 10 == 1 and seconds != 11 else 'ы' if seconds % 10 in (2, 3, 4) and not 11 <= seconds % 100 <= 19 else ''}"
        )
    return ", ".join(parts)


def asset_worker(assets: list):
    res = {}
    for asset in assets:
        match asset["content_type"]:
            case "application/x-apple-diskimage":
                res["macos"] = asset["browser_download_url"]
            case "application/zip":
                res["windows"] = asset["browser_download_url"]
            case "application/octet-stream":
                res["linux"] = asset["browser_download_url"]
    return res


def init_checker():
    if db != None:
        Path("instances").mkdir(mode=0o777, exist_ok=True)
        Path("cache").mkdir(mode=0o777, exist_ok=True)
        return None
    else:
        print(
            "Файл датабазы не найден!\nПропишите vcim init перед тем как что-то делать в этой папке!"
        )
        raise typer.Exit(code=1)


@app.command(short_help="Инициирование VCIM. Используйте перед запуском других комманд")
def init(
    platform: (
        Annotated[
            Literal["windows", "linux", "macos"], typer.Option(case_sensitive=False)
        ]
        | Literal["windows", "linux", "macos"]
    ) = None,
):
    """
    Инициирование VCIM. Используйте перед запуском других комманд

    --platform (windows | linux | macos)  записывает определённую платформу в датабазу
    """
    if platform == None:
        platform = pl.system()
        if platform == "Windows":
            platform = platform.lower()
        elif platform == "Linux":
            platform = platform.lower()
        elif platform == "Darwin":
            platform = "macos"
        else:
            print(f":x: Нестандартное имя системы! Невозможно инициировать VCIM")
            raise typer.Exit(code=2)
        print(f"Платформа: {platform}")

    if platform == "macos":
        print(
            ":x: На данный момент VCIM не работает на macos. Если вы хотите помочь, напишите создателю"
        )
        raise typer.Exit(code=1)

    global db
    if db == None:
        print("Создаю дб файл...", end=" ")
        db = SqliteDict("vcim.db", autocommit=True)
        print("✅")
        db["dir"] = Path("").resolve()
        print("Создаю необходимые папки... ", end=" ")
        Path("instances").mkdir(mode=0o777, exist_ok=True)
        print("✅", end=" ")
        Path("cache").mkdir(mode=0o777, exist_ok=True)
        print("✅")
        print("Установка стандартных репозиториев в датабазу...", end=" ")
        db["repos"] = [
            "https://api.github.com/repos/MihailRis/VoxelEngine-Cpp/releases"
        ]
        db["platform"] = platform
        print("✅")
        print("Установка завершена!")
        print("Синхронизация версий с гитхаб...")
        gitupdate()
    else:
        print("В этой папке vcim уже инициирован")


@repo.command(name="recovery")
def reporecovery():
    """
    Восстановить стандартные ссылки на репозитории
    """
    init_checker()
    db["repos"] = ["https://api.github.com/repos/MihailRis/VoxelEngine-Cpp/releases"]
    print(":white_check_mark: Восстановлено!")


@repo.command(name="list")
def rlist():
    """
    Выдать все ссылки находящиеся в датабазе
    """
    init_checker()
    for i in range(len(db["repos"])):
        print(f"{i}. {db["repos"][i]}")


@repo.command(name="versions")
def verlist(asjson: bool = False):
    """
    Версии VoxelCore находящиеся в ДБ и которые можно скачать
    """
    init_checker()
    if asjson:
        print(json.dumps(list(db["versions"].keys())))
    else:
        print(", ".join(db["versions"]))


@repo.command(name="add")
def repoadd(link: str):
    """
    Добавить ссылку на репозиторий GitHub откуда собирать версии (валидации пока нет)
    """
    init_checker()
    reps: list = db["repos"]
    reps.append(link)
    db["repos"] = reps


@repo.command(name="remove")
def reporemove(number: int):
    """
    Удалить ссылку из датабазы

    Коды ошибок:
    - 1 (Не удалось найти ссылку)
    """
    init_checker()
    try:
        reps: list = db["repos"]
        reps.pop(number)
        db["repos"] = reps
        print(":wastebasket: Ссылка удалена")
    except IndexError:
        print(":x: Не удалось найти ссылку под этим номером")
        raise typer.Exit(code=1)


@app.command(name="sync", short_help="Синхронизация версий с гитхаб репозиториями")
@repo.command(name="sync", short_help="Синхронизация версий с гитхаб репозиториями")
def gitupdate():
    """
    Синхронизация версий с гитхаб репозиториями

    Коды ошибок:
    - 1 (Ошибка во время синхронизации и соединение не установлено)
    - 2 (Ошибка во время синхронизации, но соединение установлено)
    """
    init_checker()
    versions = {}
    with Progress(
        SpinnerColumn(spinner_name="boxBounce"),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        for repo in db["repos"]:

            task_id = progress.add_task(f"[cyan]{repo}")
            try:
                req = requests.get(
                    repo,
                    headers={
                        "Content-Type": "application/vnd.github+json",
                    },
                )
                if req.ok:

                    for i in req.json():
                        versions[i["name"].replace("v", "")] = {
                            "assets": asset_worker(i["assets"]),
                        }
                    progress.update(
                        task_id, description=f"[green]{repo}", completed=True
                    )
                else:
                    progress.update(task_id, description=f"[red]{repo}")
                    print(
                        f":x: Ошибка во время синхронизации c {req.url} ({req.status_code})"
                    )
                    raise typer.Exit(code=2)
            except Exception as e:
                progress.update(task_id, description=f"[red]{repo}")
                print(f":x: Ошибка во время синхронизации c {repo} ({e})")
                raise typer.Exit(code=1)
    db["versions"] = versions
    print(f"Синхронизированно {len(versions.keys())} версий!")


@instances.command(
    short_help="Установить инстанс с версией VERSION, в папку с навазнием NAME"
)
@app.command(
    short_help="Установить инстанс с версией VERSION, в папку с навазнием NAME"
)
def install(
    name: Annotated[str, typer.Option(prompt="Имя нового инстанса")] | str,
    version: (
        Annotated[str, typer.Option(prompt='Версия для нового инстанса "x.x.x"')] | str
    ),
    custom_name: (
        Annotated[str, typer.Option(prompt="Имя инстанса для лаунчеров")] | str
    ) = None,
    group: (
        Annotated[str, typer.Option(prompt="Имя инстанса для лаунчеров")] | str
    ) = None,
    platform: Annotated[
        Literal["windows", "linux", "macos"], typer.Option(case_sensitive=False)
    ] = None,
):
    """
    Установить инстанс с версией VERSION, в папку с навазнием NAME

    --custom_name (text)  добавляет кастномное имя для лаунчеров (не название папки)

    --group (text)  добавляет инстанс в группу

    --platform (windows | linux | macos)  скачивает определённую к платформе версию для инстанса

    Коды ошибок:
    - 1 (Версия не доступна)
    - 2 (Инстанс уже существует)
    """
    init_checker()
    versions = db["versions"]
    platform = db["platform"] if platform == None else platform
    if name.lower() in [
        item.name.lower() for item in Path("instances").iterdir() if item.is_dir()
    ]:
        print(":x: Такой инстанс уже существует!")
        raise typer.Exit(code=2)
    if version in versions.keys():
        if f"{platform}_{version}" in [
            item.name for item in Path("cache").iterdir() if item.is_dir()
        ]:
            print("Версия найдена в cache. Беру её за основу")
            if platform == "windows":
                execfile = "VoxelCore.exe"
            elif platform == "linux":
                execfile = "voxelcore.AppImage"
            else:
                execfile = "voxelcore.dmg"
                print(
                    "Данная версия VCIM не работает с macos версией. Но установка продолжится"
                )
        else:
            print("Версия не найдена в cache. Скачиваю из интернета")
            with tempfile.NamedTemporaryFile(
                delete=False, dir=Path(""), mode="wb"
            ) as temp_file:
                Path(temp_file.name).chmod(mode=0o777)
                print("Temp файл создан")
                response = requests.get(
                    versions[version]["assets"][platform], stream=True
                )
                with Progress(
                    TextColumn("[bold blue]{task.description}", justify="right"),
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>1.1f}%",
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    speed_estimate_period=1,
                ) as progress:
                    total_size = int(response.headers.get("content-length", 0))
                    task_id = progress.add_task(f"[cyan]{version}", total=total_size)
                    if response.status_code == 200:
                        print("Соединение установлено! Скачиваю версию")
                        for chunk in response.iter_content(chunk_size=8192):
                            temp_file.write(chunk)
                            progress.update(task_id, advance=len(chunk))
                    else:
                        progress.update(
                            task_id,
                            completed=total_size,
                            description=f"[red]{version}",
                        )
                        print(f":x: Не удалось установить версию из интернета!")
                        raise typer.Exit(code=response.status_code)
                    progress.update(
                        task_id,
                        completed=total_size,
                        description=f"[green]{version}",
                    )
                temp_file_path = temp_file.name
            print("Версия скачалась. Добавляю в cache")
            version_folder = Path(f"cache/{platform}_{version}")
            version_folder.mkdir(mode=0o777, parents=True)
            if platform == "windows":
                execfile = "VoxelCore.exe"
                with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                    zip_ref.extractall(f"cache/{platform}_{version}/")
                Path(temp_file_path).unlink()
            elif platform == "linux":
                execfile = "voxelcore.AppImage"
                shutil.move(
                    temp_file_path,
                    Path(f"cache/{platform}_{version}/voxelcore.AppImage"),
                )
            else:
                execfile = "voxelcore.dmg"
                print(
                    "Данная версия VCIM не работает с macos версией. Но установка продолжится"
                )
                shutil.move(
                    temp_file_path, Path(f"cache/{platform}_{version}/voxelcore.dmg")
                )
            print("Версия записана в кэш")
        shutil.copytree(f"cache/{platform}_{version}", f"instances/{name}")
        print("Создаю файл для лаучнеров")
        with open(f"instances/{name}/launcher.json", "w", encoding="utf-8") as file:
            json.dump(
                {
                    "version": version,
                    "name": name if custom_name == None else custom_name,
                    "timeplayed": 0,
                    "executable_file": execfile,
                    "group": group if group != None else "",
                    "args": "",
                    "description": "",
                },
                file,
                ensure_ascii=False,
                indent=4,
            )
        print(f":white_check_mark: Инстанс {name} на версии {version} установлен!")
    else:
        print(
            f"Версия {version} не обнаружена. Попробуйте обновить репозитории через vcim gitupdate"
        )
        print("Список доступных версий: ")
        print(", ".join(versions.keys()))
        raise typer.Exit(code=1)


@instances.command(
    short_help="Запуск инстанса с названием папки NAME (регистр учитывается)"
)
def run(
    name,
    platform: Annotated[
        Literal["windows", "linux", "macos"], typer.Option(case_sensitive=False)
    ] = None,
    sendjson: bool = False,
):
    """
    Запуск инстанса с названием папки NAME (регистр учитывается)

    --platform (windows | linux | macos)  если нужно запустить не стандартную версию для вашей операционной системы

    --sendjson  отправляет новые данные из launcher.json после закрытия приложения

    Коды ошибок:
    - 1 (Инстанс не существует)
    - 2 (Не надйен файл который нужно запустить)
    - 3 (Запуск игры на макос, пока что не поддерживается)
    """
    init_checker()
    if name in [item.name for item in Path("instances").iterdir() if item.is_dir()]:
        with open(f"instances/{name}/launcher.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        oldpath = Path().resolve()
        path = Path(f"instances/{name}").resolve()
        if data["exec_file"] == "":
            print(":x: exec_file пуст. Нечего запускать")
            raise typer.Exit(2)
        os.chdir(path)
        ftime = round(time.time())
        match db["platform"] if platform == None else platform:
            case "windows":
                process = subprocess.Popen(
                    [
                        f"{path}/{data["exec_file"]}",
                        "--dir",
                        path,
                        *(data["args"].split()),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    text=True,
                    bufsize=1,
                )
            case "linux":

                subprocess.run(
                    ["chmod", "+x", f"{path}/{data["exec_file"]}"],
                )
                process = subprocess.Popen(
                    [
                        f"{path}/{data["exec_file"]}",
                        "--dir",
                        path,
                        *(data["args"].split()),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            case _:
                print(
                    ":x: На данный момент VCIM не работает на macos. Если вы хотите помочь, напишите создателю"
                )
                raise typer.Exit(3)
        process_handler(process)
        plustime = int(round(time.time())) - ftime
        os.chdir(oldpath)
        with open(f"instances/{name}/launcher.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        with open(f"instances/{name}/launcher.json", "w", encoding="utf-8") as file:
            data["timeplayed"] += plustime
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )
        print(f"Сыгранное время: {format_seconds(plustime)}")
        if sendjson:
            print(json.dumps(data))
    else:
        print(":x: Такого инстанса не существует! (регистр учитывается)")
        raise typer.Exit(code=1)


@instances.command()
def remove(name: Annotated[str, typer.Option(prompt="Имя инстанса")] | str):
    """
    Удалить инстанс с названием папки NAME (регистр учитывается)

    Коды ошибок:
    - 1 (Инстанс не существует)
    """
    init_checker()
    if name in [item.name for item in Path("instances").iterdir() if item.is_dir()]:
        shutil.rmtree(Path(f"instances/{name}"))
        print(f":wastebasket: Инстанс {name} удалён!")
    else:
        print(":x: Такого инстанса не существует! (регистр учитывается)")
        raise typer.Exit(code=1)


@instances.command(
    short_help="Показывает полную информацию о инстансе с названием папки NAME (регистр учитывается)"
)
def info(
    name: Annotated[str, typer.Option(prompt="Имя инстанса")] | str,
    asjson: bool = False,
):
    """
    Показывает полную информацию о инстансе с названием папки NAME (регистр учитывается)

    --asjson для вывода данных в json

    Коды ошибок:
    - 1 (Инстанс не существует)
    """
    init_checker()
    if name in [item.name for item in Path("instances").iterdir() if item.is_dir()]:
        with open(f"instances/{name}/launcher.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        if asjson:
            print(
                json.dumps(
                    {
                        "name": data["name"],
                        "name_vcim": name,
                        "path": str(Path(f"instances/{name}").resolve()),
                        "group": data["group"],
                        "version": data["version"],
                        "executable_file": data["exec_file"],
                        "args": data["args"],
                        "description": data["description"],
                        "timeplayed": data["timeplayed"],
                    },
                    ensure_ascii=False,
                    indent=4,
                )
            )
        else:
            print(f"Название (для лаунчеров): {data['name']}")
            print(f"Название (для vcim): {name}")
            print(f"Версия voxelcore: {data["version"]}")
            print(f"Файл запуска: {data["exec_file"]}")
            print(
                f"Параметры запуска: {data["args"] if data["args"] != "" else "[italic]Пусто[/italic]"}"
            )
            print("---")
            print(
                f"Группа: {data["group"] if data["group"] != "" else "[italic]Пусто[/italic]"}"
            )
            print(f"Время сыграно: {format_seconds(data["timeplayed"])}")
            print(
                f"Описание: {data["description"] if data["description"] != "" else "[italic]Пусто[/italic]"}"
            )
    else:
        print(":x: Такого инстанса не существует! (регистр учитывается)")
        raise typer.Exit(code=1)


@instances.command(short_help="Вывести короткие данные о всех инстансах")
def ilist(asjson: bool = False):
    """
    Вывести короткие данные о всех инстансах

    --asjson для вывода данных в json
    """
    init_checker()
    res = []
    for item in Path("instances").iterdir():
        if item.is_dir():
            with open(
                f"{item.absolute()}/launcher.json", "r", encoding="utf-8"
            ) as file:
                data = json.load(file)
            res.append(
                {
                    "name": data["name"],
                    "name_vcim": item.name,
                    "version": data["version"],
                    "group": data["group"],
                }
            )
    if asjson:
        print(json.dumps(res))
    else:
        for i in res:
            print(f"• [bold]{i["name"]} ({i["name_vcim"]})[/bold]")
            print(f"Версия: {i["version"]}")
            print(
                f"Группа: {i["group"] if i["group"] != "" else "[italic]Пусто[/italic]"}"
            )


@instances.command(
    name="clear", short_help="Удалить все инстансы (т.е удалить папку instances)"
)
def clear_inst(
    confirm: Annotated[
        bool,
        typer.Option(
            prompt="Вы уверены? Эта комманда удалит все ваши инстансы, миры, моды и прочее",
        ),
    ],
):
    """
    Удалить все инстансы (т.е удалить папку instances)
    """
    init_checker()
    if confirm:
        shutil.rmtree(Path("instances/"))
        print(":wastebasket: Все инстансы удалены!")


@cache.command(name="clear", short_help="Очистить весь кэш (т.е удалить папку cahce)")
def clear_cache(
    confirm: Annotated[
        bool,
        typer.Option(
            prompt="Вы уверены? Эта комманда удалит кэш",
        ),
    ],
):
    """
    Очистить весь кэш (т.е удалить папку cahce)
    """
    init_checker()
    if confirm:
        shutil.rmtree(Path("cache/"))
        print(":wastebasket: Весь кэш удалён!")


if __name__ == "__main__":
    app()
