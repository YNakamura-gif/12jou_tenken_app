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
if 'site_building_numbers' not in st.session_state:
    st.session_state.site_building_numbers = {}  # 現場名と棟名の組み合わせごとの劣化番号を管理
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
        
        # 現場名と棟名の組み合わせキーを作成
        site_building_key = f"{st.session_state.current_site_name}_{st.session_state.current_building_name}" if ('current_site_name' in st.session_state and 'current_building_name' in st.session_state) else "default"
        
        # 編集モードでない場合は、現場名と棟名の組み合わせごとの劣化番号を使用
        if st.session_state.editing_item_index < 0:
            # 現場名と棟名の組み合わせに対する劣化番号を取得または初期化
            if site_building_key not in st.session_state.site_building_numbers:
                st.session_state.site_building_numbers[site_building_key] = 1
            deterioration_number = st.session_state.site_building_numbers[site_building_key]
            # 次の劣化番号を設定
            st.session_state.site_building_numbers[site_building_key] += 1
        else:
            # 編集モードの場合は既存の劣化番号を使用
            deterioration_number = st.session_state.inspection_items[st.session_state.editing_item_index]["deterioration_number"]
        
        new_item = {
            "deterioration_number": deterioration_number,
            "location": st.session_state.temp_location,
            "deterioration_name": st.session_state.temp_deterioration,
            "photo_number": st.session_state.temp_photo,
            "現場名": st.session_state.current_site_name if 'current_site_name' in st.session_state else "",
            "棟名": st.session_state.current_building_name if 'current_building_name' in st.session_state else "",
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
            csv_path = "data/inspection_data.csv"
            if not os.path.exists(csv_path):
                st.error("保存されたデータが見つかりません")
                return False
            
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            row_index = st.session_state.editing_saved_index
            
            if row_index < 0 or row_index >= len(df):
                st.error("編集対象のデータが見つかりません")
                return False
            
            # 基本情報の更新
            inspection_date = st.session_state.inspection_date.strftime("%Y-%m-%d") if 'inspection_date' in st.session_state else datetime.now().strftime("%Y-%m-%d")
            inspector_name = st.session_state.inspector_name if 'inspector_name' in st.session_state else ""
            site_name = st.session_state.current_site_name if 'current_site_name' in st.session_state else ""
            building_name = st.session_state.current_building_name if 'current_building_name' in st.session_state else ""
            remarks = st.session_state.remarks if 'remarks' in st.session_state else ""
            
            # 劣化情報の更新
            location = st.session_state.temp_location if 'temp_location' in st.session_state else ""
            deterioration_name = st.session_state.temp_deterioration if 'temp_deterioration' in st.session_state else ""
            photo_number = st.session_state.temp_photo if 'temp_photo' in st.session_state else ""
            
            # データフレームの更新
            df.loc[row_index, '点検日'] = inspection_date
            df.loc[row_index, '点検者名'] = inspector_name
            df.loc[row_index, '現場名'] = site_name
            df.loc[row_index, '棟名'] = building_name
            df.loc[row_index, '備考'] = remarks
            df.loc[row_index, '場所'] = location
            df.loc[row_index, '劣化名'] = deterioration_name
            df.loc[row_index, '写真番号'] = photo_number
            
            # 更新履歴情報があれば更新
            if '最終更新日時' in df.columns:
                df.loc[row_index, '最終更新日時'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                df['最終更新日時'] = None
                df.loc[row_index, '最終更新日時'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
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
            st.rerun()
    
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
            site_name = st.text_input("現場名", value=default_site, key="site_name_input")
            
            # 現場名が入力されたら、その値をセッションに保存
            if site_name:
                st.session_state.current_site_name = site_name
            
            default_building = st.session_state.editing_saved_row['棟名'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '棟名' in st.session_state.editing_saved_row else ""
            building_name = st.text_input("棟名", value=default_building, key="building_name_input")
            
            # 棟名が入力されたら、その値をセッションに保存
            if building_name:
                st.session_state.current_building_name = building_name
                
                # 現場名と棟名が両方入力されている場合、登録済みの劣化項目を読み込む
                if 'current_site_name' in st.session_state and st.session_state.current_site_name:
                    # 既存のデータを読み込む
                    csv_path = "data/inspection_data.csv"
                    if os.path.exists(csv_path):
                        try:
                            df = pd.read_csv(csv_path, encoding='utf-8-sig')
                            
                            # 現場名と棟名でフィルタリング
                            filtered_df = df[(df['現場名'] == st.session_state.current_site_name) & 
                                            (df['棟名'] == building_name)]
                            
                            if not filtered_df.empty:
                                # 既存の入力項目をクリア（編集モードでない場合のみ）
                                if not ('editing_saved_data' in st.session_state and st.session_state.editing_saved_data):
                                    st.session_state.inspection_items = []
                                    st.session_state.saved_items = []
                                    
                                    # 現場名と棟名の組み合わせキーを作成
                                    site_building_key = f"{st.session_state.current_site_name}_{building_name}"
                                    
                                    # 最大の劣化番号を取得して次の番号を設定
                                    max_deterioration_number = filtered_df['劣化番号'].max()
                                    st.session_state.site_building_numbers[site_building_key] = max_deterioration_number + 1
                                    
                                    # 劣化項目を追加
                                    for _, row in filtered_df.iterrows():
                                        item = {
                                            "deterioration_number": row['劣化番号'],
                                            "location": row['場所'],
                                            "deterioration_name": row['劣化名'],
                                            "photo_number": row['写真番号'],
                                            "現場名": row['現場名'],
                                            "棟名": row['棟名'],
                                            "作成日時": row['最終更新日時'] if '最終更新日時' in row else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "最終更新日時": row['最終更新日時'] if '最終更新日時' in row else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "更新者": row['更新者'] if '更新者' in row else "",
                                            "更新回数": row['更新回数'] if '更新回数' in row else 0
                                        }
                                        st.session_state.inspection_items.append(item)
                                        
                                        # 保存済みリストに追加
                                        item_key = f"{item['deterioration_number']}_{item['location']}_{item['deterioration_name']}_{item['photo_number']}"
                                        st.session_state.saved_items.append(item_key)
                                    
                                    # 読み込み完了メッセージ
                                    st.session_state.items_loaded = True
                                    st.session_state.loaded_items_count = len(filtered_df)
                                    st.session_state.loaded_site_name = st.session_state.current_site_name
                                    st.session_state.loaded_building_name = building_name
                        except Exception as e:
                            st.error(f"データの読み込み中にエラーが発生しました: {str(e)}")
            
            default_remarks = st.session_state.editing_saved_row['備考'] if 'editing_saved_data' in st.session_state and st.session_state.editing_saved_data and '備考' in st.session_state.editing_saved_row else ""
            remarks = st.text_area("備考", value=default_remarks)

    # 劣化項目が読み込まれた場合のメッセージを表示
    if 'items_loaded' in st.session_state and st.session_state.items_loaded:
        st.success(f"現場名「{st.session_state.loaded_site_name}」、棟名「{st.session_state.loaded_building_name}」の登録済み劣化項目（{st.session_state.loaded_items_count}件）を読み込みました。")
        # メッセージは一度だけ表示
        st.session_state.items_loaded = False

    # 現場名と棟名が両方入力されている場合のみ劣化内容セクションを表示
    if ('current_site_name' in st.session_state and st.session_state.current_site_name) and ('current_building_name' in st.session_state and st.session_state.current_building_name):
        # 劣化内容セクション
        with st.container():
            st.subheader("劣化内容")
            
            # 現在の現場名と棟名を表示
            st.info(f"現場名: {st.session_state.current_site_name} / 棟名: {st.session_state.current_building_name} の劣化情報を入力します")
            
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
            
            # ボタンクリック時の処理を直接実行するように変更
            if st.button(button_text, key="add_deterioration_button"):
                # 入力値が空でないか確認
                if location and deterioration_name:
                    # 劣化項目を追加
                    add_item()
                    st.success(f"劣化項目「{location} / {deterioration_name}」を追加しました")
                    st.rerun()  # 画面を更新して追加された項目を表示
                else:
                    st.error("場所と劣化名は必須項目です")
    else:
        # 現場名と棟名が入力されていない場合のメッセージ
        st.warning("劣化情報を入力するには、まず「現場名」と「棟名」を入力してください。")

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
                st.rerun()
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
                    
                    # 現場名と棟名の組み合わせごとに劣化番号を確認し、必要に応じて調整
                    for i, row in enumerate(rows):
                        site_name = row["現場名"]
                        building_name = row["棟名"]
                        
                        # 同じ現場名と棟名の既存データをフィルタリング
                        same_site_building = df_existing[(df_existing["現場名"] == site_name) & (df_existing["棟名"] == building_name)]
                        
                        # 既存データがある場合、劣化番号が重複しないように調整
                        if not same_site_building.empty:
                            # 既存の最大劣化番号を取得
                            existing_max_number = same_site_building["劣化番号"].max()
                            
                            # 新しいデータの劣化番号が既存の最大番号以下の場合、番号を調整
                            if row["劣化番号"] <= existing_max_number:
                                # 劣化番号を既存の最大番号+1に設定
                                df_save.loc[i, "劣化番号"] = existing_max_number + 1
                                
                                # セッション状態の劣化番号も更新
                                site_building_key = f"{site_name}_{building_name}"
                                st.session_state.site_building_numbers[site_building_key] = existing_max_number + 2
                    
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
    
    if auto_refresh and not edit_mode:  # 編集モード中は自動更新しない
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
            
            # 編集モードの場合
            if edit_mode:
                st.info("テーブル内のセルをタップして直接編集できます。行の追加・削除も可能です。編集後は「変更を保存」ボタンをクリックしてください。")
                
                # 行の操作ボタン
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("新しい行を追加", key="add_new_row"):
                        # 新しい空の行を追加
                        new_row = {col: "" for col in df.columns}
                        # 必須フィールドに初期値を設定
                        new_row['点検日'] = datetime.now().strftime("%Y-%m-%d")
                        new_row['劣化番号'] = df['劣化番号'].max() + 1 if not df.empty else 1
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        st.success("新しい行を追加しました。内容を編集してください。")
                
                with col2:
                    if st.button("選択した行を削除", key="delete_selected_rows"):
                        if 'selected_rows' in st.session_state and st.session_state.selected_rows:
                            # 選択された行のインデックスを取得
                            selected_indices = [row.get('_index') for row in st.session_state.selected_rows if row.get('_index') is not None]
                            if selected_indices:
                                # 選択された行を削除
                                df = df.drop(selected_indices).reset_index(drop=True)
                                st.success(f"{len(selected_indices)}行を削除しました")
                            else:
                                st.warning("削除する行が選択されていません")
                        else:
                            st.warning("削除する行を選択してください（行をクリックして選択）")
                
                # データエディタの表示
                try:
                    # データ型を適切に変換
                    # 日付列を文字列として扱う
                    if '点検日' in df.columns:
                        df['点検日'] = df['点検日'].astype(str)
                    
                    # 数値列を適切に変換
                    numeric_cols = ['劣化番号', '更新回数']
                    for col in numeric_cols:
                        if col in df.columns:
                            # NaN値を0に変換してから整数型に
                            df[col] = df[col].fillna(0).astype(int)
                    
                    # まずst.data_editorを試す
                    try:
                        edited_df = st.data_editor(
                            df,
                            key="data_editor",
                            use_container_width=True,
                            num_rows="dynamic",  # 動的な行数
                            disabled=["劣化番号"],  # 劣化番号は編集不可
                            hide_index=False,  # インデックスを表示
                            column_config={
                                # 点検日は文字列として扱う（DateColumnではなくTextColumnを使用）
                                "点検日": st.column_config.TextColumn("点検日", help="YYYY-MM-DD形式で入力してください"),
                                "劣化番号": st.column_config.NumberColumn("劣化番号", help="自動的に割り当てられる番号です"),
                            }
                        )
                    except AttributeError:
                        # st.data_editorが存在しない場合は代替手段を使用
                        st.warning("お使いのStreamlitバージョンではデータエディタがサポートされていません。代替の編集方法を使用します。")
                        st.dataframe(df)
                        edited_df = df.copy()
                except Exception as e:
                    st.error(f"データエディタでエラーが発生しました: {str(e)}")
                    st.warning("代替の編集方法を使用します。")
                    
                # 変更を保存するボタン
                if st.button("変更を保存", key="save_table_edits"):
                    try:
                        # 更新情報を追加
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 更新履歴情報の列がなければ追加
                        if '最終更新日時' not in edited_df.columns:
                            edited_df['最終更新日時'] = None
                        if '更新者' not in edited_df.columns:
                            edited_df['更新者'] = None
                        if '更新回数' not in edited_df.columns:
                            edited_df['更新回数'] = 0
                        
                        # 変更された行を特定して更新情報を設定
                        for idx in edited_df.index:
                            edited_df.at[idx, '最終更新日時'] = current_time
                            # 点検者名があれば更新者として使用、なければ「不明」
                            edited_df.at[idx, '更新者'] = edited_df.at[idx, '点検者名'] if pd.notna(edited_df.at[idx, '点検者名']) else "不明"
                            # 更新回数を増やす
                            if pd.notna(edited_df.at[idx, '更新回数']):
                                edited_df.at[idx, '更新回数'] = int(edited_df.at[idx, '更新回数']) + 1
                            else:
                                edited_df.at[idx, '更新回数'] = 1
                        
                        # CSVに保存
                        edited_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        st.success("変更を保存しました")
                        st.rerun()  # 画面を更新
                    except Exception as e:
                        st.error(f"保存中にエラーが発生しました: {str(e)}")
            else:
                # 通常の表示モード（編集不可）
                st.dataframe(df)
            
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