import asyncio
from pathlib import Path

from conf import BASE_DIR
from myUtils.account_manager import get_current_account, get_account_cookie_path
from uploader.baijiahao_uploader.main import baijiahao_setup

if __name__ == '__main__':
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'baijiahao')
    account_file.parent.mkdir(parents=True, exist_ok=True)
    cookie_setup = asyncio.run(baijiahao_setup(str(account_file), handle=True))
