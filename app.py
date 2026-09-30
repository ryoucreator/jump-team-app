import sqlite3
import pandas as pd
import streamlit as st
from datetime import date
import os

# ページ設定
st.set_page_config(page_title="陸上部 跳躍ブロック データ管理システム", layout="wide")

DB_FILE = "land_and_field.db"

# ---------------------------------------------------------
# 1. データベース初期化・接続処理（自動修復機能付き）
# ---------------------------------------------------------
def init_and_get_athletes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 構造の不一致によるエラーを防ぐため、athletesテーブルが存在するか確認
    try:
        c.execute("SELECT id, name, grade, event FROM athletes")
    except sqlite3.OperationalError:
        # テーブルが存在しない、または古い構造の場合は一度テーブルを作り直す
        c.execute("DROP TABLE IF EXISTS athletes")
        c.execute("DROP TABLE IF EXISTS practice_logs")
        
        c.execute('''
            CREATE TABLE athletes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade TEXT,
                event TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE practice_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER,
                date TEXT,
                menu_name TEXT,
                set_num INTEGER,
                distance_or_weight REAL,
                reps_or_time REAL,
                memo TEXT,
                FOREIGN KEY (athlete_id) REFERENCES athletes(id)
            )
        ''')
        
        # サンプルデータの投入
        sample_athletes = [
            ('山田 太郎', '3年', '走幅跳'),
            ('佐藤 花子', '2年', '走高跳'),
            ('鈴木 一郎', '1年', '三段跳')
        ]
        c.executemany("INSERT INTO athletes (name, grade, event) VALUES (?, ?, ?)", sample_athletes)
        conn.commit()
        
        c.execute("SELECT id, name, grade, event FROM athletes")

    rows = c.fetchall()
    conn.close()
    
    df = pd.DataFrame(rows, columns=["選手ID", "氏名", "学年", "専門種目"])
    return df

def get_connection():
    return sqlite3.connect(DB_FILE)

# ---------------------------------------------------------
# 2. アプリメイン画面
# ---------------------------------------------------------
st.title("🏃‍♂️ 陸上部 跳躍ブロック データ管理システム")
st.header("🏋️ 練習メニューグループ一括入力")

# 選手データの読み込み
df_athletes = init_and_get_athletes()

if df_athletes.empty:
    st.warning("登録されている選手がいません。")
else:
    st.subheader("1. 対象選手の選択（フィルター）")
    
    col1, col2 = st.columns(2)
    
    with col1:
        grades = ["すべて"] + [g for g in df_athletes["学年"].dropna().unique() if g]
        selected_grade = st.selectbox("学年で絞り込み", grades)
        
    with col2:
        events = ["すべて"] + [e for e in df_athletes["専門種目"].dropna().unique() if e]
        selected_event = st.selectbox("専門種目で絞り込み", events, key="event_filter")

    # フィルター適用
    filtered_df = df_athletes.copy()
    if selected_grade != "すべて":
        filtered_df = filtered_df[filtered_df["学年"] == selected_grade]
    if selected_event != "すべて":
        filtered_df = filtered_df[filtered_df["専門種目"] == selected_event]

    # 表示用フォーマット関数
    def format_athlete(athlete_id):
        match = df_athletes[df_athletes["選手ID"] == athlete_id]
        if not match.empty:
            row = match.iloc[0]
            return f"{row['氏名']} ({row['学年']}/{row['専門種目']})"
        return f"ID:{athlete_id}"

    athlete_options = filtered_df["選手ID"].tolist()
    
    target_ids = st.multiselect(
        "対象選手（チェックを外すことで個別除外が可能）",
        options=athlete_options,
        default=athlete_options,
        format_func=format_athlete
    )

    st.markdown("---")
    st.subheader("2. 練習メニューの入力")

    with st.form("practice_form"):
        p_date = st.date_input("日付", date.today())
        menu_name = st.text_input("メニュー名", placeholder="例: 助走踏切ドリル, ウエイトスクワット")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            set_num = st.number_input("セット数 / 本数", min_value=1, value=1, step=1)
        with col_b:
            distance_or_weight = st.number_input("距離(m) または 重量(kg)", min_value=0.0, value=0.0, step=0.5)
        with col_c:
            reps_or_time = st.number_input("回数 または タイム(秒)", min_value=0.0, value=0.0, step=0.1)
            
        memo = st.text_area("メモ・注意事項", placeholder="例: 踏切位置の意識、接地時の軸の維持など")
        
        submit = st.form_submit_button("一括登録する")

        if submit:
            if not target_ids:
                st.error("対象選手が1人も選択されていません。")
            elif not menu_name:
                st.error("メニュー名を入力してください。")
            else:
                conn = get_connection()
                c = conn.cursor()
                for a_id in target_ids:
                    c.execute('''
                        INSERT INTO practice_logs 
                        (athlete_id, date, menu_name, set_num, distance_or_weight, reps_or_time, memo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (a_id, str(p_date), menu_name, set_num, distance_or_weight, reps_or_time, memo))
                conn.commit()
                conn.close()
                st.success(f"{len(target_ids)}名分の練習記録を一括登録しました！")
