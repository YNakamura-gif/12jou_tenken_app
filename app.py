import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="12条点検 Web アプリ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'inspection_items' not in st.session_state:
    st.session_state.inspection_items = []
if 'current_deterioration_number' not in st.session_state:
    st.session_state.current_deterioration_number = 1

# データ保存用ディレクトリの作成
if not os.path.exists('data'):
    os.makedirs('data')

# タブの作成
tab_input, tab_view = st.tabs(["点検入力", "データ閲覧"])

with tab_input:
    st.header("点検情報入力")
    
    # 基本情報セクション
    with st.container():
        st.subheader("基本情報")
        col1, col2 = st.columns(2)
        
        with col1:
            inspection_date = st.date_input("点検日", value=datetime.now())
            inspector_name = st.text_input("点検者名")
        
        with col2:
            site_id = st.text_input("現場ID")
            remarks = st.text_area("備考")

    # 劣化内容セクション
    with st.container():
        st.subheader("劣化内容")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            location = st.text_input("場所")
        with col2:
            deterioration_name = st.text_input("劣化名")
        with col3:
            photo_number = st.text_input("写真番号")

        if st.button("劣化項目を追加"):
            new_item = {
                "deterioration_number": st.session_state.current_deterioration_number,
                "location": location,
                "deterioration_name": deterioration_name,
                "photo_number": photo_number
            }
            st.session_state.inspection_items.append(new_item)
            st.session_state.current_deterioration_number += 1

    # 現在の入力項目一覧
    if st.session_state.inspection_items:
        st.subheader("入力済み劣化項目")
        df = pd.DataFrame(st.session_state.inspection_items)
        st.dataframe(df)

    # 保存ボタン
    if st.button("保存"):
        data = {
            "inspection_date": inspection_date.strftime("%Y-%m-%d"),
            "inspector_name": inspector_name,
            "site_id": site_id,
            "remarks": remarks,
            "deterioration_items": st.session_state.inspection_items
        }
        
        # CSVファイルへの保存
        df_save = pd.DataFrame([{
            "点検日": data["inspection_date"],
            "点検者名": data["inspector_name"],
            "現場ID": data["site_id"],
            "備考": data["remarks"],
            "劣化データ": json.dumps(data["deterioration_items"], ensure_ascii=False)
        }])
        
        csv_path = "data/inspection_data.csv"
        if os.path.exists(csv_path):
            df_existing = pd.read_csv(csv_path, encoding='utf-8-sig')
            df_save = pd.concat([df_existing, df_save], ignore_index=True)
        
        df_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        st.success("データを保存しました")
        
        # 入力項目のクリア
        st.session_state.inspection_items = []
        st.session_state.current_deterioration_number = 1

with tab_view:
    st.header("データ閲覧")
    
    csv_path = "data/inspection_data.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 検索フィルター
        search_term = st.text_input("検索（点検日、現場ID、点検者名など）")
        if search_term:
            mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            df = df[mask]
        
        st.dataframe(df)
        
        # CSVダウンロード
        if not df.empty:
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="CSVダウンロード",
                data=csv,
                file_name="inspection_data.csv",
                mime="text/csv"
            )
    else:
        st.info("保存されたデータがありません") 