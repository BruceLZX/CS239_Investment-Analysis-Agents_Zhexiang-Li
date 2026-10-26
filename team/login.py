"""Sign in to Rakazo once. The session is saved, so other scripts never handle your password.

Run it in your own terminal, from agent-team/:  .venv/bin/python -m team.login
"""
import getpass
import os

from tools.env import load_env

from .rakazo_client import SESSION_FILE, Rakazo


def main() -> None:
    load_env()
    url = os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')
    email = input('Rakazo account email: ').strip()
    password = getpass.getpass('Rakazo password: ')
    with Rakazo(url) as app:
        app.login(email, password)
        print(f'Signed in to {url}; {len(app.bots())} bots in this space. Session saved to {SESSION_FILE}.')


if __name__ == '__main__':
    main()
