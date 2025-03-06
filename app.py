import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import jaconv

# ページ設定
st.set_page_config(
    page_title="12条点検 Web アプリ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# マスターデータの読み込み
def load_master_data():
    try:
        master_path = "data/master_data.csv"
        if os.path.exists(master_path):
            # 複数のエンコーディングを試行
            encodings = ['utf-8', 'shift_jis', 'cp932', 'utf-8-sig']
            for encoding in encodings:
                try:
                    df = pd.read_csv(master_path, encoding=encoding)
                    # 場所と劣化名のマッピングを作成
                    locations_dict = dict(zip(df['場所よみ'], df['場所']))
                    deteriorations_dict = dict(zip(df['劣化名よみ'], df['劣化名']))
                    return (
                        df['場所'].unique().tolist(),
                        df['劣化名'].unique().tolist(),
                        locations_dict,
                        deteriorations_dict,
                        df['場所よみ'].unique().tolist(),
                        df['劣化名よみ'].unique().tolist()
                    )
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    st.error(f"マスターデータの読み込みエラー: {str(e)}")
                    continue
            
            st.error("適切なエンコーディングが見つかりませんでした。")
            return [], [], {}, {}, [], []
        else:
            st.warning("マスターデータファイルが見つかりません。デフォルトの選択肢を使用します。")
            # デフォルトの選択肢を提供
            default_locations = ["1階廊下", "2階廊下", "屋上", "外壁", "階段", "玄関", "機械室", "駐車場"]
            default_deteriorations = ["ひび割れ", "剥離", "漏水", "腐食", "変形", "欠損", "さび", "変色"]
            return default_locations, default_deteriorations, {}, {}, [], []
    except Exception as e:
        st.error(f"予期せぬエラー: {str(e)}")
        return [], [], {}, {}, [], []

# 予測変換機能
def get_suggestions(input_text, options, yomi_options, mapping_dict):
    if not input_text:
        return []
    
    # 入力をひらがなに変換
    input_hira = jaconv.kata2hira(jaconv.normalize(input_text))
    
    # 候補を探す
    suggestions = []
    
    # 読み仮名での検索
    for yomi in yomi_options:
        if yomi.startswith(input_hira):
            suggestions.append(mapping_dict[yomi])
    
    # 通常の検索（元の表記でも検索可能に）
    for opt in options:
        opt_hira = jaconv.kata2hira(jaconv.normalize(opt))
        if opt_hira.startswith(input_hira):
            if opt not in suggestions:  # 重複を避ける
                suggestions.append(opt)
    
    return suggestions

# セッション状態の初期化
if 'inspection_items' not in st.session_state:
    st.session_state.inspection_items = []
if 'current_deterioration_number' not in st.session_state:
    st.session_state.current_deterioration_number = 1
if 'editing_item_index' not in st.session_state:
    st.session_state.editing_item_index = -1
if 'editing_location' not in st.session_state:
    st.session_state.editing_location = ""
if 'editing_deterioration' not in st.session_state:
    st.session_state.editing_deterioration = ""
if 'editing_photo' not in st.session_state:
    st.session_state.editing_photo = ""
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'saved_items' not in st.session_state:
    st.session_state.saved_items = []
if 'editing_saved_data' not in st.session_state:
    st.session_state.editing_saved_data = False
if 'editing_saved_row' not in st.session_state:
    st.session_state.editing_saved_row = {}
if 'editing_saved_index' not in st.session_state:
    st.session_state.editing_saved_index = -1
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "input"

def add_item():
    if 'temp_location' in st.session_state and 'temp_deterioration' in st.session_state and 'temp_photo' in st.session_state:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_item = {
            "deterioration_number": st.session_state.current_deterioration_number if st.session_state.editing_item_index < 0 else st.session_state.inspection_items[st.session_state.editing_item_index]["deterioration_number"],
            "location": st.session_state.temp_location,
            "deterioration_name": st.session_state.temp_deterioration,
            "photo_number": st.session_state.temp_photo,
            "作成日時": current_time,
            "最終更新日時": current_time,
            "更新者": st.session_state.inspector_name if 'inspector_name' in st.session_state else "",
            "更新回数": 0
        }
        
        if st.session_state.editing_item_index >= 0:
            # 編集モードの場合は既存のアイテムを更新
            st.session_state.inspection_items[st.session_state.editing_item_index] = new_item
            st.session_state.editing_item_index = -1  # 編集モードを終了
            # 編集用の値をクリア
            st.session_state.editing_location = ""
            st.session_state.editing_deterioration = ""
            st.session_state.editing_photo = ""
        else:
            # 新規追加モード
            st.session_state.inspection_items.append(new_item)
            st.session_state.current_deterioration_number += 1
        
        # 入力欄をクリア
        st.session_state.temp_location = ""
        st.session_state.temp_deterioration = ""
        st.session_state.temp_photo = ""
        
        # フォーム送信フラグを設定
        st.session_state.form_submitted = True

def edit_item(index):
    st.session_state.editing_item_index = index
    item = st.session_state.inspection_items[index]
    st.session_state.editing_location = item["location"]
    st.session_state.editing_deterioration = item["deterioration_name"]
    st.session_state.editing_photo = item["photo_number"]
    
    # 編集時に保存済みリストから削除
    item_key = f"{item['deterioration_number']}_{item['location']}_{item['deterioration_name']}_{item['photo_number']}"
    if item_key in st.session_state.saved_items:
        st.session_state.saved_items.remove(item_key)

def delete_item(index):
    item = st.session_state.inspection_items[index]
    
    # 削除時に保存済みリストから削除
    item_key = f"{item['deterioration_number']}_{item['location']}_{item['deterioration_name']}_{item['photo_number']}"
    if item_key in st.session_state.saved_items:
        st.session_state.saved_items.remove(item_key)
    
    del st.session_state.inspection_items[index]
    # 劣化番号を振り直す
    for i, item in enumerate(st.session_state.inspection_items):
        item["deterioration_number"] = i + 1
    st.session_state.current_deterioration_number = len(st.session_state.inspection_items) + 1

def update_saved_data():
    if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data:
        try:
            # CSVファイルを読み込む
            csv_path = "data/inspection_data.csv"
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            
            # 編集対象の行を取得
            row_index = st.session_state.editing_saved_index
            
            # 更新データの作成
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # データフレームの更新
            df.loc[row_index, '点検日'] = inspection_date.strftime("%Y-%m-%d")
            df.loc[row_index, '点検者名'] = inspector_name
            df.loc[row_index, '現場名'] = site_name
            df.loc[row_index, '棟名'] = building_name
            df.loc[row_index, '備考'] = remarks
            df.loc[row_index, '場所'] = st.session_state.temp_location
            df.loc[row_index, '劣化名'] = st.session_state.temp_deterioration
            df.loc[row_index, '写真番号'] = st.session_state.temp_photo
            
            # 更新履歴情報があれば更新
            if '最終更新日時' in df.columns:
                df.loc[row_index, '最終更新日時'] = current_time
            else:
                df['最終更新日時'] = None
                df.loc[row_index, '最終更新日時'] = current_time
                
            if '更新者' in df.columns:
                df.loc[row_index, '更新者'] = inspector_name
            else:
                df['更新者'] = None
                df.loc[row_index, '更新者'] = inspector_name
                
            if '更新回数' in df.columns:
                df.loc[row_index, '更新回数'] = int(df.loc[row_index, '更新回数']) + 1 if pd.notna(df.loc[row_index, '更新回数']) else 1
            else:
                df['更新回数'] = 0
                df.loc[row_index, '更新回数'] = 1
            
            # CSVに保存
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # 編集モードを終了
            st.session_state.editing_saved_data = False
            st.session_state.editing_saved_row = {}
            st.session_state.editing_saved_index = -1
            
            return True
        except Exception as e:
            st.error(f"データの更新中にエラーが発生しました: {str(e)}")
            return False
    return False

# データ保存用ディレクトリの作成
if not os.path.exists('data'):
    os.makedirs('data')

# マスターデータの読み込み
locations, deterioration_types, locations_dict, deteriorations_dict, locations_yomi, deteriorations_yomi = load_master_data()

# タブの作成
if st.session_state.active_tab == "input":
    tab_input, tab_view = st.tabs(["点検入力", "データ閲覧"])
    st.session_state.active_tab = "input"
else:
    tab_view, tab_input = st.tabs(["データ閲覧", "点検入力"])
    st.session_state.active_tab = "view"

with tab_input:
    st.header("点検情報入力")
    
    # 保存済みデータ編集モードの場合の表示
    if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data:
        st.info("保存済みデータの編集モードです")
        
        # 編集対象のデータを表示
        row = st.session_state.editing_saved_row
        st.write(f"編集対象: {row['点検日']} - {row['現場名']} - {row['場所']} - {row['劣化名']}")
        
        # キャンセルボタン
        if st.button("編集をキャンセル", key="cancel_edit"):
            st.session_state.editing_saved_data = False
            st.session_state.editing_saved_row = {}
            st.session_state.editing_saved_index = -1
            st.experimental_rerun()
    
    # 基本情報セクション
    with st.container():
        st.subheader("基本情報")
        col1, col2 = st.columns(2)
        
        with col1:
            # 編集モードの場合は保存済みの値を初期値に設定
            default_date = datetime.strptime(st.session_state.editing_saved_row['点検日'], "%Y-%m-%d").date() if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '点検日' in st.session_state.editing_saved_row else datetime.now()
            inspection_date = st.date_input("点検日", value=default_date)
            
            default_inspector = st.session_state.editing_saved_row['点検者名'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '点検者名' in st.session_state.editing_saved_row else ""
            inspector_name = st.text_input("点検者名", value=default_inspector)
        
        with col2:
            default_site = st.session_state.editing_saved_row['現場名'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '現場名' in st.session_state.editing_saved_row else ""
            site_name = st.text_input("現場名", value=default_site)
            
            default_building = st.session_state.editing_saved_row['棟名'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '棟名' in st.session_state.editing_saved_row else ""
            building_name = st.text_input("棟名", value=default_building)
            
            default_remarks = st.session_state.editing_saved_row['備考'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '備考' in st.session_state.editing_saved_row else ""
            remarks = st.text_area("備考", value=default_remarks)

    # 劣化内容セクション
    with st.container():
        st.subheader("劣化内容")
        
        col1, col2, col3 = st.columns(3)
        
        # フォーム送信後に入力欄をクリア
        if st.session_state.form_submitted:
            st.session_state.location_input = ""
            st.session_state.deterioration_input = ""
            st.session_state.photo_number_input = ""
            st.session_state.form_submitted = False
        
        with col1:
            # 編集モードの場合は保存済みの値を初期値に設定
            default_location = st.session_state.editing_saved_row['場所'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '場所' in st.session_state.editing_saved_row else st.session_state.editing_location
            location = st.text_input(
                "場所",
                key="location_input",
                value=default_location,
                help="ひらがなで入力してください（例：いっかい）"
            )
            if location:
                location_suggestions = get_suggestions(location, locations, locations_yomi, locations_dict)
                if location_suggestions:
                    selected_location = st.selectbox(
                        "場所の候補",
                        ["入力値を使用"] + location_suggestions,
                        key="location_suggestions"
                    )
                    if selected_location != "入力値を使用":
                        location = selected_location

        with col2:
            # 編集モードの場合は保存済みの値を初期値に設定
            default_deterioration = st.session_state.editing_saved_row['劣化名'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '劣化名' in st.session_state.editing_saved_row else st.session_state.editing_deterioration
            deterioration_name = st.text_input(
                "劣化名",
                key="deterioration_input",
                value=default_deterioration,
                help="ひらがなで入力してください（例：ひび）"
            )
            if deterioration_name:
                deterioration_suggestions = get_suggestions(deterioration_name, deterioration_types, deteriorations_yomi, deteriorations_dict)
                if deterioration_suggestions:
                    selected_deterioration = st.selectbox(
                        "劣化名の候補",
                        ["入力値を使用"] + deterioration_suggestions,
                        key="deterioration_suggestions"
                    )
                    if selected_deterioration != "入力値を使用":
                        deterioration_name = selected_deterioration

        with col3:
            # 編集モードの場合は保存済みの値を初期値に設定
            default_photo = st.session_state.editing_saved_row['写真番号'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '写真番号' in st.session_state.editing_saved_row else st.session_state.editing_photo
            photo_number = st.text_input(
                "写真番号",
                key="photo_number_input",
                value=default_photo
            )

        # 一時的に値を保存
        st.session_state.temp_location = location
        st.session_state.temp_deterioration = deterioration_name
        st.session_state.temp_photo = photo_number

        # 編集モード時のボタンテキストを変更
        button_text = "更新" if st.session_state.editing_item_index >= 0 else "劣化項目を追加"
        if st.button(button_text, on_click=add_item):
            pass  # 実際の処理はコールバック関数で行う

    # 現在の入力項目一覧
    if st.session_state.inspection_items:
        st.subheader("入力済み劣化項目")
        
        # スマホ表示に最適化したコンパクトなレイアウト
        for i, item in enumerate(st.session_state.inspection_items):
            with st.container():
                # 保存済みかどうかを判定
                item_key = f"{item['deterioration_number']}_{item['location']}_{item['deterioration_name']}_{item['photo_number']}"
                is_saved = item_key in st.session_state.saved_items
                
                # 保存済み項目は背景色を変える
                if is_saved:
                    container_style = """
                    <style>
                    .saved-item {
                        background-color: #e6f3ff;
                        padding: 5px;
                        border-radius: 5px;
                        border-left: 3px solid #1E88E5;
                    }
                    </style>
                    <div class="saved-item">
                    """
                    st.markdown(container_style, unsafe_allow_html=True)
                
                cols = st.columns([0.6, 0.2, 0.2])
                
                # 項目情報を1列目にまとめて表示
                with cols[0]:
                    status_badge = "🔵 " if is_saved else ""
                    st.markdown(f"""
                    {status_badge}**No.{item['deterioration_number']}**: {item['location']} / {item['deterioration_name']} / {item['photo_number']}
                    """)
                
                # 編集ボタン
                with cols[1]:
                    st.button(
                        "編集",
                        key=f"edit_{i}",
                        on_click=edit_item,
                        args=(i,),
                        use_container_width=True
                    )
                
                # 削除ボタン
                with cols[2]:
                    st.button(
                        "削除",
                        key=f"delete_{i}",
                        on_click=delete_item,
                        args=(i,),
                        use_container_width=True
                    )
                
                # 保存済み項目のHTMLを閉じる
                if is_saved:
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # 項目間の区切り線（オプション）
                if i < len(st.session_state.inspection_items) - 1:
                    st.markdown("---")

    # 保存ボタン
    if st.button("保存"):
        # 編集モードの場合
        if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data:
            if update_saved_data():
                st.success("データを更新しました")
                st.session_state.active_tab = "view"  # データ閲覧タブに切り替え
                st.experimental_rerun()
        else:
            # 既存の新規保存処理
            # 劣化データを展開して保存用のデータフレームを作成
            rows = []
            newly_saved_items = []
            
            for item in st.session_state.inspection_items:
                # 既に保存済みの項目はスキップ
                item_key = f"{item['deterioration_number']}_{item['location']}_{item['deterioration_name']}_{item['photo_number']}"
                if item_key in st.session_state.saved_items:
                    continue
                    
                rows.append({
                    "点検日": inspection_date.strftime("%Y-%m-%d"),
                    "点検者名": inspector_name,
                    "現場名": site_name,
                    "棟名": building_name,
                    "備考": remarks,
                    "劣化番号": item["deterioration_number"],
                    "場所": item["location"],
                    "劣化名": item["deterioration_name"],
                    "写真番号": item["photo_number"]
                })
                
                # 保存済みリストに追加
                newly_saved_items.append(item_key)
            
            # 保存するデータがある場合のみ処理
            if rows:
                df_save = pd.DataFrame(rows)
                
                csv_path = "data/inspection_data.csv"
                if os.path.exists(csv_path):
                    df_existing = pd.read_csv(csv_path, encoding='utf-8-sig')
                    df_save = pd.concat([df_existing, df_save], ignore_index=True)
                
                df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                # 保存済みリストを更新
                st.session_state.saved_items.extend(newly_saved_items)
                
                st.success(f"{len(rows)}件のデータを保存しました。入力データはそのまま残っています。必要に応じて編集・削除できます。")
            else:
                st.info("保存するデータがありません。すべての項目は既に保存済みです。")

with tab_view:
    st.header("データ閲覧")
    
    # 自動更新の設定
    col1, col2 = st.columns([1, 3])
    with col1:
        auto_refresh = st.checkbox("自動更新（10秒ごと）", value=False)
    with col2:
        edit_mode = st.checkbox("編集モード", value=False)
    
    if auto_refresh:
        st.markdown("""
        <meta http-equiv="refresh" content="10">
        """, unsafe_allow_html=True)
    
    csv_path = "data/inspection_data.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 検索フィルター
        search_term = st.text_input("検索（点検日、現場名、点検者名など）")
        if search_term:
            mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            df = df[mask]
        
        # データが存在する場合のみ表示
        if not df.empty:
            st.write(f"合計 {len(df)} 件のデータがあります")
            
            # 編集モードの場合は選択列を追加
            if edit_mode:
                # 一意のIDを各行に付与（インデックスを使用）
                df['選択'] = df.index
                selected_row = st.selectbox(
                    "編集するデータを選択",
                    options=df.index,
                    format_func=lambda i: f"{df.loc[i, '点検日']} - {df.loc[i, '現場名']} - {df.loc[i, '場所']} - {df.loc[i, '劣化名']}"
                )
                
                if st.button("選択したデータを編集"):
                    # 選択したデータを編集用にセッションに保存
                    st.session_state.editing_saved_data = True
                    st.session_state.editing_saved_row = df.loc[selected_row].to_dict()
                    st.session_state.editing_saved_index = selected_row
                    st.session_state.active_tab = "input"  # 点検入力タブに切り替え
                    st.experimental_rerun()
            
            # データフレームの表示
            st.dataframe(df.drop(columns=['選択']) if edit_mode and '選択' in df.columns else df)
            
            # CSVダウンロード
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="CSVダウンロード",
                data=csv,
                file_name="inspection_data.csv",
                mime="text/csv"
            )
        else:
            st.info("検索条件に一致するデータがありません")
    else:
        st.info("保存されたデータがありません")