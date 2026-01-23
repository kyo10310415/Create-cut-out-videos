import requests
import base64

# 画像URLからダウンロード
url = "https://www.genspark.ai/api/files/s/Y7fvxnCZ"
response = requests.get(url)

if response.status_code == 200:
    # レスポンスがJSONの場合、base64データを抽出
    try:
        data = response.json()
        if 'data' in data:
            # base64データをデコード
            image_data = base64.b64decode(data['data'])
            with open('/home/user/webapp/assets/opening_background.png', 'wb') as f:
                f.write(image_data)
            print("✓ 画像をダウンロードしました")
        else:
            # 直接画像データの場合
            with open('/home/user/webapp/assets/opening_background.png', 'wb') as f:
                f.write(response.content)
            print("✓ 画像をダウンロードしました（直接）")
    except:
        # JSONではない場合、直接保存
        with open('/home/user/webapp/assets/opening_background.png', 'wb') as f:
            f.write(response.content)
        print("✓ 画像をダウンロードしました（バイナリ）")
else:
    print(f"✗ ダウンロード失敗: {response.status_code}")
