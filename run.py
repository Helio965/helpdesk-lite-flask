"""Ponto de entrada para desenvolvimento.

Permite executar a aplicação sem instalar o pacote (layout ``src/``):

    python run.py

E também serve de alvo para o Flask CLI:

    flask --app run.py db upgrade
    flask --app run.py seed
"""

import os
import sys

# Garante que ``src/`` esteja no path mesmo sem ``pip install -e .``.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from helpdesk import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
