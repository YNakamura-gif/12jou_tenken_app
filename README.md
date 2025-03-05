# 12条点検 Web アプリ

このアプリケーションは、建物の12条点検を効率的に行うためのWebアプリケーションです。点検データの入力、保存、閲覧が可能で、予測変換機能により入力の手間を軽減します。

## 機能

- 点検基本情報（点検日、点検者名、現場ID、備考）の入力
- 劣化内容（場所、劣化名、写真番号）の入力と管理
- 入力済み劣化項目の編集・削除
- 予測変換機能（ひらがな入力による候補表示）
- データのCSV保存と閲覧
- CSVデータのダウンロード

## 必要条件

- Python 3.8以上
- 必要なパッケージ（requirements.txtに記載）

## インストール方法

1. リポジトリをクローンまたはダウンロードします。

```bash
git clone <リポジトリURL>
cd 12jou_tenken_app
```

2. 仮想環境を作成し、アクティベートします。

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. 必要なパッケージをインストールします。

```bash
pip install -r requirements.txt
```

## 使用方法

1. アプリケーションを起動します。

```bash
streamlit run app.py
```

2. ブラウザで http://localhost:8501 にアクセスします。

3. 「点検入力」タブで点検情報を入力します。
   - 基本情報（点検日、点検者名、現場ID、備考）を入力
   - 劣化内容（場所、劣化名、写真番号）を入力
   - 「劣化項目を追加」ボタンで項目を追加
   - 必要に応じて項目を編集・削除
   - 「保存」ボタンでデータを保存

4. 「データ閲覧」タブで保存したデータを閲覧・検索・ダウンロードできます。

## データ構造

### マスターデータ (data/master_data.csv)

場所と劣化名のマスターデータです。以下の列を含みます：

- 場所: 点検場所（例：1階廊下、屋上）
- 場所よみ: 場所のひらがな読み（例：いっかいろうか、おくじょう）
- 劣化名: 劣化の種類（例：ひび割れ、漏水）
- 劣化名よみ: 劣化名のひらがな読み（例：ひびわれ、ろうすい）

### 点検データ (data/inspection_data.csv)

点検結果のデータです。以下の列を含みます：

- 点検日: 点検を実施した日付
- 点検者名: 点検を実施した担当者名
- 現場ID: 点検現場の識別子
- 備考: 点検に関する備考
- 劣化番号: 劣化項目の通し番号
- 場所: 劣化が見つかった場所
- 劣化名: 劣化の種類
- 写真番号: 関連する写真の番号

## デプロイ方法

### ローカル環境でのデプロイ

上記の「使用方法」の手順に従ってください。

### Streamlit Cloudでのデプロイ

1. GitHubにリポジトリをプッシュします。

2. [Streamlit Cloud](https://streamlit.io/cloud) にアクセスし、アカウントを作成またはログインします。

3. 「New app」ボタンをクリックし、以下の情報を入力します：
   - Repository: GitHubのリポジトリURL
   - Branch: main（または使用するブランチ）
   - Main file path: app.py

4. 「Deploy」ボタンをクリックしてデプロイします。

### Herokuでのデプロイ

1. Herokuアカウントを作成し、Heroku CLIをインストールします。

2. プロジェクトルートに `Procfile` を作成します：

```
web: sh setup.sh && streamlit run app.py
```

3. `setup.sh` ファイルを作成します：

```bash
mkdir -p ~/.streamlit/

echo "\
[general]\n\
email = \"your-email@example.com\"\n\
" > ~/.streamlit/credentials.toml

echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml
```

4. Herokuにデプロイします：

```bash
heroku login
heroku create your-app-name
git push heroku main
```

## トラブルシューティング

- **エラー: ModuleNotFoundError** - 必要なパッケージがインストールされていません。`pip install -r requirements.txt` を実行してください。
- **CSVファイルが読み込めない** - ファイルのエンコーディングを確認してください。UTF-8またはShift-JISでエンコードされている必要があります。
- **予測変換が機能しない** - `jaconv` パッケージがインストールされていることを確認してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 作者

[あなたの名前]

## 謝辞

このプロジェクトは以下のライブラリを使用しています：
- Streamlit
- Pandas
- jaconv 