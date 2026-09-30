import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

# ページ設定
st.set_page_config(page_title="陸上部 跳躍ブロック データ管理システム", layout="wide")

# 既存の破損・古いDBとの衝突を避けるため新しいファイル名に指定
DB_FILE = "jump_team_v2.db"

# ---------------------------------------------------------
# 1. データベース初期化・取得処理
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 選手マスターテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT,
            event TEXT
        )
    ''')
    
    # 練習記録テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_logs (
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

    # CTテスト記録テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS ct_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            date TEXT,
            standing_long_jump REAL,
            standing_triple_jump REAL,
            medicine_ball_throw REAL,
            sprint_30m REAL,
            memo TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )
    ''')
    
    # 初期データ（空の場合のみ）
    c.execute("SELECT COUNT(*) FROM athletes")
    if c.fetchone()[0] == 0:
        sample_athletes = [
            ('山田 太郎', '3年', '走幅跳'),
            ('佐藤 花子', '2年', '走高跳'),
            ('鈴木 一郎', '1年', '三段跳')
        ]
        c.executemany("INSERT INTO athletes (name, grade, event) VALUES (?, ?, ?)", sample_athletes)
        conn.commit()
        
    conn.close()

def get_connection():
    return sqlite3.connect(DB_FILE)

def load_athletes():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT id, name, grade, event FROM athletes")
        rows = c.fetchall()
        df = pd.DataFrame(rows, columns=["選手ID", "氏名", "学年", "専門種目"])
    except Exception:
        df = pd.DataFrame(columns=["選手ID", "氏名", "学年", "専門種目"])
    finally:
        conn.close()
    return df

# ---------------------------------------------------------
# 2. サイドバー（プルダウン形式でメニュー選択）
# ---------------------------------------------------------
st.sidebar.title("🏃‍♂️ システムメニュー")

# プルダウン（selectbox）によるページ選択
page = st.sidebar.selectbox(
    "機能を選択してください",
    [
        "🏋️ 練習メニュー一括入力", 
        "⏱️️ CTテスト記録", 
        "👤 選手登録・管理", 
        "📊 練習・テスト記録の確認"
    ]
)

st.title("🏃‍♂️ 陸上部 跳躍ブロック データ管理システム")

# ---------------------------------------------------------
# ページ1: 練習メニュー一括入力
# ---------------------------------------------------------
if page == "🏋️ 練習メニュー一括入力":
    st.header("🏋️ 練習メニューグループ一括入力")
    df_athletes = load_athletes()

    if df_athletes.empty:
        st.warning("登録されている選手がいません。「👤 選手登録・管理」から選手を追加してください。")
    else:
        st.subheader("1. 対象選手の選択（フィルター）")
        col1, col2 = st.columns(2)
        
        with col1:
            grades = ["すべて"] + [g for g in df_athletes["学年"].dropna().unique() if g]
            selected_grade = st.selectbox("学年で絞り込み", grades)
            
        with col2:
            events = ["すべて"] + [e for e in df_athletes["専門種目"].dropna().unique() if e]
            selected_event = st.selectbox("専門種目で絞り込み", events, key="event_filter")

        filtered_df = df_athletes.copy()
        if selected_grade != "すべて":
            filtered_df = filtered_df[filtered_df["学年"] == selected_grade]
        if selected_event != "すべて":
            filtered_df = filtered_df[filtered_df["専門種目"] == selected_event]

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

# ---------------------------------------------------------
# ページ2: CTテスト記録
# ---------------------------------------------------------
elif page == "⏱️ CTテスト記録":
    st.header("⏱️ CTテスト（コントロールテスト）記録")
    df_athletes = load_athletes()
    
    if df_athletes.empty:
        st.warning("登録されている選手がいません。")
    else:
        with st.form("ct_test_form"):
            ct_date = st.date_input("実施日", date.today())
            
            athlete_dict = {f"{row['氏名']} ({row['学年']}/{row['専門種目']})": row['選手ID'] for _, row in df_athletes.iterrows()}
            selected_athlete_name = st.selectbox("選手を選択", list(athlete_dict.keys()))
            selected_athlete_id = athlete_dict[selected_athlete_name]
            
            col1, col2 = st.columns(2)
            with col1:
                slj = st.number_input("立ち幅跳び (m)", min_value=0.0, value=0.0, step=0.01)
                stj = st.number_input("立ち三段跳び (m)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                mb = st.number_input("メディシンボール投げ (m)", min_value=0.0, value=0.0, step=0.1)
                sprint_30 = st.number_input("30m走 (秒)", min_value=0.0, value=0.0, step=0.01)
                
            ct_memo = st.text_area("テスト備考・コンディション", placeholder="例: 接地感覚良好、追風1.2m")
            
            submit_ct = st.form_submit_button("CTテスト結果を保存")
            
            if submit_ct:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO ct_tests 
                    (athlete_id, date, standing_long_jump, standing_triple_jump, medicine_ball_throw, sprint_30m, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (selected_athlete_id, str(ct_date), slj, stj, mb, sprint_30, ct_memo))
                conn.commit()
                conn.close()
                st.success("CTテストの記録を保存しました！")

# ---------------------------------------------------------
# ページ3: 選手登録・管理
# ---------------------------------------------------------
elif page == "👤 選手登録・管理":
    st.header("👤 選手登録・管理")
    
    with st.form("add_athlete_form", clear_on_submit=True):
        name = st.text_input("氏名")
        grade = st.selectbox("学年", ["1年", "2年", "3年", "4年", "その他"])
        event = st.selectbox("専門種目", ["走幅跳", "走高跳", "三段跳", "棒高跳", "その他"])
        submit_athlete = st.form_submit_button("選手を追加")
        
        if submit_athlete:
            if name.strip():
                init_db()
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO athletes (name, grade, event) VALUES (?, ?, ?)", (name.strip(), grade, event))
                    conn.commit()
                    st.success(f"{name.strip()} 選手を登録しました！")
                except Exception as e:
                    st.error(f"登録エラー: {e}")
                finally:
                    conn.close()
            else:
                st.error("氏名を入力してください。")
                
    st.markdown("---")
    st.subheader("登録済み選手一覧")
    df_athletes = load_athletes()
    st.dataframe(df_athletes, use_container_width=True)

# ---------------------------------------------------------
# ページ4: 練習・テスト記録の確認
# ---------------------------------------------------------
elif page == "📊 練習・テスト記録の確認":
    st.header("📊 記録データの確認")
    
    tab1, tab2 = st.tabs(["🏋️ 練習記録一覧", "⏱️ CTテスト結果一覧"])
    
    conn = get_connection()
    
    with tab1:
        query_p = '''
            SELECT 
                p.date AS 日付,
                a.name AS 氏名,
                a.grade AS 学年,
                a.event AS 専門種目,
                p.menu_name AS メニュー名,
                p.set_num AS セット数,
                p.distance_or_weight AS "距離(m)/重量(kg)",
                p.reps_or_time AS "回数/タイム(秒)",
                p.memo AS メモ
            FROM practice_logs p
            JOIN athletes a ON p.athlete_id = a.id
            ORDER BY p.date DESC, p.id DESC
        '''
        try:
            df_p = pd.read_sql_query(query_p, conn)
            if df_p.empty:
                st.info("練習記録はまだありません。")
            else:
                st.dataframe(df_p, use_container_width=True)
        except Exception:
            st.info("練習記録はまだありません。")

    with tab2:
        query_ct = '''
            SELECT 
                c.date AS 実施日,
                a.name AS 氏名,
                a.grade AS 学年,
                a.event AS 専門種目,
                c.standing_long_jump AS "立ち幅跳び(m)",
                c.standing_triple_jump AS "立ち三段跳び(m)",
                c.medicine_ball_throw AS "メディシンボール(m)",
                c.sprint_30m AS "30m走(秒)",
                c.memo AS 備考
            FROM ct_tests c
            JOIN athletes a ON c.athlete_id = a.id
            ORDER BY c.date DESC, c.id DESC
        '''
        try:
            df_ct = pd.read_sql_query(query_ct, conn)
            if df_ct.empty:
                st.info("CTテストの記録はまだありません。")
            else:
                st.dataframe(df_ct, use_container_width=True)
        except Exception:
            st.info("CTテストの記録はまだありません。")
            
    conn.close()
