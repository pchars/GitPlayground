"""Validators for level-0 terminal sandbox tasks (no git)."""

from __future__ import annotations


def _command_roots_logged(*roots: str, message: str) -> str:
    roots_literal = ", ".join(repr(root.lower()) for root in roots)
    return (
        "from pathlib import Path\n"
        "import sys\n"
        "log = Path('.gp/commands.log')\n"
        "lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []\n"
        "roots_logged = {\n"
        "    line.strip().split()[0].lower()\n"
        "    for line in lines\n"
        "    if line.strip()\n"
        "}\n"
        f"needed = {{{roots_literal}}}\n"
        "if not needed & roots_logged:\n"
        f"    print({message!r})\n"
        "    sys.exit(1)\n"
        "print('OK')\n"
    )


def _file_exists(path: str, *, message: str) -> str:
    return (
        "from pathlib import Path\n"
        "import sys\n"
        f"path = Path({path!r})\n"
        "if not path.is_file():\n"
        f"    print({message!r})\n"
        "    sys.exit(1)\n"
        "print('OK')\n"
    )


def _file_contains(path: str, needle: str, *, message: str) -> str:
    return (
        "from pathlib import Path\n"
        "import sys\n"
        f"path = Path({path!r})\n"
        "if not path.is_file():\n"
        f"    print({message!r})\n"
        "    sys.exit(1)\n"
        f"if {needle!r} not in path.read_text(encoding='utf-8'):\n"
        f"    print({message!r})\n"
        "    sys.exit(1)\n"
        "print('OK')\n"
    )


def _combo_validator(body: str) -> str:
    return (
        "from pathlib import Path\n"
        "import sys\n"
        f"{body}\n"
        "print('OK')\n"
    )


TERMINAL_TASK_VALIDATORS: dict[str, str] = {
    "sandbox_pwd": _command_roots_logged("pwd", message="Выполни команду pwd."),
    "sandbox_ls": _command_roots_logged("ls", message="Выполни команду ls."),
    "sandbox_whoami": _command_roots_logged("whoami", message="Выполни команду whoami."),
    "sandbox_clear": _command_roots_logged("clear", message="Выполни команду clear."),
    "sandbox_mkdir": _combo_validator(
        "log = Path('.gp/commands.log')\n"
        "lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []\n"
        "roots_logged = {line.strip().split()[0].lower() for line in lines if line.strip()}\n"
        "if 'mkdir' not in roots_logged:\n"
        "    print('Создай каталог командой mkdir.')\n"
        "    sys.exit(1)\n"
        "if not Path('practice').is_dir():\n"
        "    print('Каталог practice должен существовать.')\n"
        "    sys.exit(1)"
    ),
    "sandbox_touch": _combo_validator(
        "log = Path('.gp/commands.log')\n"
        "lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []\n"
        "roots_logged = {line.strip().split()[0].lower() for line in lines if line.strip()}\n"
        "if 'touch' not in roots_logged:\n"
        "    print('Создай файл командой touch.')\n"
        "    sys.exit(1)\n"
        "if not Path('practice/notes.txt').is_file():\n"
        "    print('Файл practice/notes.txt должен существовать.')\n"
        "    sys.exit(1)"
    ),
    "sandbox_echo_write": _file_contains(
        "practice/notes.txt",
        "GitPlayground",
        message="В practice/notes.txt должна быть строка GitPlayground (echo … > файл).",
    ),
    "sandbox_cat": _command_roots_logged("cat", message="Прочитай файл командой cat."),
    "sandbox_echo_append": _file_contains(
        "practice/notes.txt",
        "sandbox",
        message="В practice/notes.txt должна быть строка sandbox (echo … >> файл).",
    ),
    "sandbox_type_empty": _file_exists(
        "practice/blank.txt",
        message="Создай пустой файл practice/blank.txt через type nul > …",
    ),
    "sandbox_head": _command_roots_logged("head", message="Выполни head для файла."),
    "sandbox_tail": _command_roots_logged("tail", message="Выполни tail для файла."),
    "sandbox_wc": _command_roots_logged("wc", message="Выполни wc -l для файла."),
    "sandbox_cp": _file_exists(
        "practice/copy.txt",
        message="Скопируй файл в practice/copy.txt командой cp.",
    ),
    "sandbox_mv": _file_exists(
        "practice/backup.txt",
        message="Переименуй или перемести файл в practice/backup.txt командой mv.",
    ),
    "sandbox_find": _command_roots_logged("find", message="Найди файлы командой find."),
    "sandbox_rm": _combo_validator(
        "log = Path('.gp/commands.log')\n"
        "lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []\n"
        "roots_logged = {line.strip().split()[0].lower() for line in lines if line.strip()}\n"
        "if 'rm' not in roots_logged:\n"
        "    print('Удали файл командой rm.')\n"
        "    sys.exit(1)\n"
        "if Path('practice/blank.txt').exists():\n"
        "    print('Файл practice/blank.txt должен быть удалён.')\n"
        "    sys.exit(1)"
    ),
    "sandbox_nano": _command_roots_logged(
        "nano",
        "edit",
        message="Открой файл в редакторе: nano путь или edit путь.",
    ),
}
