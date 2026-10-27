"""Sign in to Rakazo and save the session, so other scripts never handle a password.

From agent-team/:

    .venv/bin/python -m team.login                # your own account: prompts for email and password
    .venv/bin/python -m team.login --local-test   # a test account that exists only in this machine's Rakazo

The local test account's generated password is stored in agent-team/.env (gitignored) and never printed.
"""
import argparse
import getpass
import os
import secrets

from tools.env import ENV_FILE, load_env

from .rakazo_client import SESSION_FILE, Rakazo

TEST_EMAIL = 'owner@cs239-agent-team.test'


def save_env(values: dict[str, str]) -> None:
    """Set keys in agent-team/.env, replacing earlier values and keeping the rest."""
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    kept = [line for line in lines if line.split('=', 1)[0].strip() not in values]
    ENV_FILE.write_text('\n'.join(kept + [f'{key}={value}' for key, value in values.items()]) + '\n')
    ENV_FILE.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--local-test', action='store_true',
                        help='create or reuse a test account that exists only in the local Rakazo')
    args = parser.parse_args()
    load_env()
    url = os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')
    with Rakazo(url) as app:
        if args.local_test:
            email, password = os.environ.get('RAKAZO_TEST_EMAIL'), os.environ.get('RAKAZO_TEST_PASSWORD')
            if not (email and password):
                email, password = TEST_EMAIL, secrets.token_urlsafe(24)
                app.sign_up('CS239 agent team', email, password)
                save_env({'RAKAZO_TEST_EMAIL': email, 'RAKAZO_TEST_PASSWORD': password})
                print(f'Created the local test account {email}; its password is in agent-team/.env.')
        else:
            email = input('Rakazo account email: ').strip()
            password = getpass.getpass('Rakazo password: ')
        app.login(email, password)
        print(f'Signed in to {url}; {len(app.bots())} bots in this space. Session saved to {SESSION_FILE}.')


if __name__ == '__main__':
    main()
