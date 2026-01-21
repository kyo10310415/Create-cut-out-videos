@echo off
REM YouTube Clipper ローカルワーカー起動スクリプト (Windows)

echo ========================================
echo YouTube Clipper - ローカルワーカー
echo ========================================
echo.

REM カレントディレクトリをスクリプトの場所に変更
cd /d %~dp0

REM 仮想環境をアクティベート
if exist venv\Scripts\activate.bat (
    echo 仮想環境をアクティベート中...
    call venv\Scripts\activate.bat
) else (
    echo エラー: 仮想環境が見つかりません
    echo 先に以下を実行してください:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements_worker.txt
    pause
    exit /b 1
)

REM .env.worker ファイルの確認
if not exist .env.worker (
    echo エラー: .env.worker ファイルが見つかりません
    echo .env.worker.example をコピーして .env.worker を作成してください
    pause
    exit /b 1
)

echo.
echo ワーカーを起動しています...
echo.

REM ワーカーを起動
python local_worker.py

echo.
echo ワーカーが停止しました
pause
