#!/usr/bin/env python3
"""
Hook PreToolUse -- heurística de secrets/credenciales, no un scanner real.

Corre antes de Write/Edit/Bash y busca patrones que *sugieren* una
credencial cruda (API keys de formatos conocidos, connection strings con
password embebido, bloques de llave privada) en el contenido que se va a
escribir o el comando que se va a ejecutar.

LIMITACIÓN CONOCIDA -- léela antes de confiar en esto:
Esto es un regex heurístico, no un secret scanner real (gitleaks, trufflehog,
etc.). Tiene falsos negativos (secrets con formato no reconocido) y falsos
positivos (un placeholder de ejemplo que matchea el patrón). Su único trabajo
es hacer una pausa visible antes de una escritura sospechosa -- no reemplaza
un scanner dedicado en CI ni la revisión de `security-reviewer`.

Exit code 0 = permitir. Exit code 2 = bloquear y mostrar el motivo a Claude.
"""
import json
import re
import sys

PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_api_key_asignada": re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"][A-Za-z0-9_\-./+=]{16,}['\"]"),
    "private_key_block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "connection_string_con_password": re.compile(r"(?i)(postgres|postgresql|mysql|oracle|jdbc)://[^\s'\"@]*:[^\s'\"@]{4,}@"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
}

# Rutas donde estos patrones son esperados y no deben bloquear (ajustar por proyecto)
ALLOWLIST_SUBSTRINGS = ["test", "fixture", "mock", "example", ".md", ".env.example"]


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # si no podemos parsear el input, no bloqueamos por error propio

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool_name in ("Write", "Edit"):
        target_path = str(tool_input.get("file_path", ""))
        text = str(tool_input.get("content", "")) + str(tool_input.get("new_string", ""))
    elif tool_name == "Bash":
        target_path = ""
        text = str(tool_input.get("command", ""))
    else:
        sys.exit(0)

    if any(s in target_path.lower() for s in ALLOWLIST_SUBSTRINGS):
        sys.exit(0)

    hits = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    if hits:
        print(
            f"[check_secrets_patterns] Posible secret/credencial detectada ({', '.join(hits)}) "
            f"en una escritura hacia '{target_path or tool_name}'. Esto es una heurística, "
            f"no una confirmación -- verifica si es un secret real antes de continuar, o si es un "
            f"falso positivo (dato de prueba, ejemplo en docs) procede conscientemente.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
