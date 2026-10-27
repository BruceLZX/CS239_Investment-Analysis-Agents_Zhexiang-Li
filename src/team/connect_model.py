"""Connect your DeepSeek account to the local Rakazo, once. Run it in your own terminal, from src/:

    .venv/bin/python -m team.connect_model

The key goes from this prompt straight to the local Rakazo, which stores it encrypted; it is never
printed or written to a file. If SEC_USER_AGENT is not set yet, it also asks for the SEC contact.
"""
import getpass
import os

from tools.env import load_env

from .login import save_env
from .profiles import model_choice
from .rakazo_client import Rakazo, RakazoError


def main() -> None:
    load_env()
    model = model_choice()
    with Rakazo(os.environ.get('RAKAZO_URL', 'http://127.0.0.1:5174')) as app:
        key = getpass.getpass('DeepSeek API key (input is hidden): ').strip()
        if not key:
            raise SystemExit('No key entered; nothing changed.')
        try:
            app.rpc('models/connect', {'provider': 'deepseek', 'apiKey': key, 'modelId': model.model_id,
                                       'thinkingLevel': model.thinking_level})
        except RakazoError as error:
            raise SystemExit(f'Could not connect DeepSeek: {error}')
        print(f'Connected DeepSeek ({model.model_id}) to Rakazo.')
    if not os.environ.get('SEC_USER_AGENT'):
        contact = input('Contact for SEC EDGAR requests ("Your Name you@example.com"): ').strip()
        if '@' in contact:
            save_env({'SEC_USER_AGENT': contact})
            print('Saved SEC_USER_AGENT to src/.env.')
        else:
            print('Skipped. The SEC tools need SEC_USER_AGENT in src/.env before a run.')


if __name__ == '__main__':
    main()
