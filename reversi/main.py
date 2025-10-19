"""
Tkinter GUI で起動するためのスクリプト。

通常の起動は `python -m reversi.gui_tk` でも可能ですが、
このファイルを直接実行した場合でも GUI が開くようにしています。
相対インポートを優先し、失敗時は親ディレクトリを `sys.path` に追加して
`reversi.gui_tk` を解決できるようにしています。
"""

try:
    # パッケージ内からの相対 import（推奨ルート）
    from .gui_tk import main  # type: ignore
except Exception:
    # 単体ファイル実行に対応: python def/reversi/main.py
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from reversi.gui_tk import main

if __name__ == "__main__":
    main()
