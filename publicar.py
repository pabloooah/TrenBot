#!/usr/bin/env python3
"""Sube al repo los datos de la web, que es lo que dispara el despliegue.

Vercel está conectado a este repositorio: no hace falta ningún token ni
llamar a su CLI, basta con que el commit llegue a main.
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
FICHEROS = ["historico.json", "avisos.json", os.path.join("web", "datos.json"),
            os.path.join("data", "ryanair_version.json"),
            os.path.join("data", "wizz_version.json"),
            os.path.join("data", "wizz_horarios.json")]


def git(*a):
    return subprocess.run(("git",) + a, cwd=RAIZ, capture_output=True,
                          text=True, timeout=120)


def main():
    hay = [f for f in FICHEROS if os.path.exists(os.path.join(RAIZ, f))]
    git("add", *hay)
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("sin cambios que publicar")
        return 0
    if git("commit", "-m", "chore: precios actualizados").returncode != 0:
        print("no se pudo commitear")
        return 1
    git("fetch", "origin", "main")
    if git("rebase", "origin/main").returncode != 0:
        git("rebase", "--abort")
        print("conflicto al rebasar; se reintenta en la siguiente vuelta")
        return 1
    if git("push", "origin", "main").returncode != 0:
        print("no se pudo subir")
        return 1
    print("publicado (Vercel desplegará solo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
