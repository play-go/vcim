# VoxelCore Instances Manager

**VoxelCore Instances Manager (VCIM)** - проект призванный **стандартизировать** подход к разработке лаунчеров, а также **упростить** их разработку

## Функции
* Установка собранных исходников VoxelCore из GitHub
* Возможность подкачки версий из разных репозиториев GitHub
* Запуск установленных instance
* Возможность настроить код так, что не обязательно держать его в папке с instance и кэш (объяснение будет в документации)
* Вывод информации как в json, так и в терминал текстом

# Требования

* Python >= 3.12.11

### Python библиотеки

* sqlitedict
* typer
* requests

```
pip install sqlitedict typer requests
```
или
```
pip install -r requirements.txt
```

# Использование

```
python vcim.py [OPTIONS] COMMAND [ARGS]...
```

```
python vcim.py --help
```

# Сборка проекта

```
nuitka --onefile --follow-imports --include-package=rich --include-module=rich._unicode_data --nofollow-import-to=cryptography --python-flag=no_site vcim.py
```
Сборка через pyinstaller не желательна, т.к скорость оставляет желать лучшего

# Roadmap

* Документация
* Команда build чтобы билдить VoxelCore
* Команда watch чтобы смотреть за изменениями в папках и выводом в консоль изменений в json
* MacOS поддержка
