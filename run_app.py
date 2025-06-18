#!/usr/bin/env python3
"""
社内情報特化型生成AI検索アプリ起動スクリプト
PDF警告を完全に抑制してアプリを起動します
"""

import os
import sys
import warnings
import subprocess
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# 環境変数での警告抑制
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["PYPDF_VERBOSE"] = "0"
os.environ["FITZ_LOGGING"] = "0"
os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"

# すべての警告を抑制
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")

# 特定の警告を個別に抑制
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*wrong pointing object.*")
warnings.filterwarnings("ignore", message=".*custom sys.excepthook.*")
warnings.filterwarnings("ignore", message=".*Ignoring wrong pointing object.*")

# PyPDF2/PyMuPDF関連の警告を抑制
warnings.filterwarnings("ignore", module="pypdf")
warnings.filterwarnings("ignore", module="PyPDF2")
warnings.filterwarnings("ignore", module="fitz")


class SuppressStdout:
    """標準出力を抑制するコンテキストマネージャー"""

    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr


def main():
    """メイン関数"""
    print("🔍 社内情報特化型生成AI検索アプリを起動します...")
    print("⚠️  PDF警告抑制モードで実行中...")

    try:
        # Streamlitアプリを起動
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "main.py",
            "--server.headless=true",
        ]

        # 環境変数を設定してプロセスを起動
        env = os.environ.copy()
        env.update(
            {"PYTHONWARNINGS": "ignore", "PYPDF_VERBOSE": "0", "FITZ_LOGGING": "0"}
        )

        subprocess.run(cmd, env=env)

    except KeyboardInterrupt:
        print("\n✅ アプリケーションを終了しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
