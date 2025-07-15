import os

def writeCode(file_name: str, line_from: int, line_to: int, code: str | list[str]) -> None:
    try:
        with open(file_name, "r") as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    if isinstance(code, str):
        code_lines = code.splitlines(keepends=True)
    else:
        code_lines = [line if line.endswith('\n') else line + '\n' for line in code]

    line_from = max(0, line_from)
    line_to = min(len(lines) - 1, line_to) if lines else -1

    if lines:
        new_lines = lines[:line_from] + code_lines + lines[line_to + 1:]
    else:
        new_lines = code_lines

    with open(file_name, "w") as file:
        file.writelines(new_lines)

    print(f"\n✅ Code written to `{file_name}` between lines {line_from} and {line_to}.\n")
