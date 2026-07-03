"""Фаза Verify: самопроверка сгенерированного проекта перед выдачей пользователю."""

import ast

REQUIRED_FILES = ["README.md", "requirements.txt", "Dockerfile", "app/main.py"]


def verify_files(files: dict[str, str]) -> tuple[bool, str]:
    """Возвращает (успех, markdown-отчёт)."""
    lines = ["# Verification Report", ""]
    ok = True

    for required in REQUIRED_FILES:
        if required in files:
            lines.append(f"- [x] `{required}` присутствует")
        else:
            lines.append(f"- [ ] `{required}` ОТСУТСТВУЕТ")
            ok = False

    lines.append("")
    lines.append("## Синтаксис Python")
    for path, content in sorted(files.items()):
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content)
            lines.append(f"- [x] `{path}` — OK")
        except SyntaxError as exc:
            lines.append(f"- [ ] `{path}` — SyntaxError: {exc.msg} (строка {exc.lineno})")
            ok = False

    todos = [path for path, content in files.items() if "TODO" in content or "FIXME" in content]
    lines.append("")
    lines.append("## TODO / FIXME")
    if todos:
        ok = False
        lines.extend(f"- [ ] найден TODO/FIXME в `{p}`" for p in todos)
    else:
        lines.append("- [x] не найдено")

    lines.append("")
    lines.append(f"**Итог: {'ПРОЙДЕНО' if ok else 'ПРОВАЛЕНО'}** — файлов: {len(files)}")
    return ok, "\n".join(lines)
