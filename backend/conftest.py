"""pytest 設定。このファイルの存在により backend/ が import パスに入り、

`pytest` でも `python -m pytest` でも `app` パッケージを解決できる。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# テスト用のダミー AWS 環境（moto 利用時に boto3 がリージョン/資格情報を要求するため）。
# 既存の環境変数は上書きしない（ローカルの設定を尊重）。
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
