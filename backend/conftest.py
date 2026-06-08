"""pytest 設定。このファイルの存在により backend/ が import パスに入り、

`pytest` でも `python -m pytest` でも `app` パッケージを解決できる。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
