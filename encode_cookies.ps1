# cookies.txtをBase64エンコードするPowerShellスクリプト

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "YouTube Cookies Base64エンコーダー" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ファイルパスを入力
$cookiesPath = Read-Host "cookies.txtのパスを入力してください（例: C:\Users\YourName\Downloads\cookies.txt）"

# ファイルが存在するか確認
if (-Not (Test-Path $cookiesPath)) {
    Write-Host "❌ エラー: ファイルが見つかりません: $cookiesPath" -ForegroundColor Red
    exit
}

Write-Host "✓ ファイルが見つかりました" -ForegroundColor Green
Write-Host ""

# Base64エンコード
Write-Host "Base64エンコード中..." -ForegroundColor Yellow
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($cookiesPath))

# クリップボードにコピー
$base64 | Set-Clipboard

Write-Host "✅ Base64エンコード完了！" -ForegroundColor Green
Write-Host "✅ クリップボードにコピーしました" -ForegroundColor Green
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "1. Renderダッシュボードを開く: https://dashboard.render.com"
Write-Host "2. youtube-clipper サービスを選択"
Write-Host "3. Environment タブをクリック"
Write-Host "4. 新しい環境変数を追加:"
Write-Host "   Key: YOUTUBE_COOKIES"
Write-Host "   Value: [Ctrl+V でペースト]"
Write-Host "5. Save Changes をクリック"
Write-Host ""
Write-Host "Base64文字列の最初の50文字:" -ForegroundColor Yellow
Write-Host $base64.Substring(0, [Math]::Min(50, $base64.Length))
Write-Host "..." -ForegroundColor Gray
Write-Host ""
