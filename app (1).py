import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import os

st.set_page_config(page_title="陸上部 跳躍ブロック データ管理システム", layout="wide")
st.title("🏃‍♂️ 陸上部 跳躍ブロック データ管理システム")

DB_FILE = 'land_and_field.db'

# -------------------------------------------------------------------
# データベース接続 ＆ 自動初期化処理（DBがない場合自動作成）
# -------------------------------------------------------------------
def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS athletes (
        選手ID INTEGER PRIMARY KEY AUTOINCREMENT,
        氏名 TEXT NOT NULL,
        学年 TEXT NOT NULL,
        専門種目 TEXT NOT NULL
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS control_tests (
        テストID INTEGER PRIMARY KEY AUTOINCREMENT,
        選手ID INTEGER,
        実施時期 TEXT,
        カテゴリ TEXT,
        テスト種目名 TEXT,
        記録 REAL,
        FOREIGN KEY(選手ID) REFERENCES athletes(選手ID)
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS training_logs (
        ログID INTEGER PRIMARY KEY AUTOINCREMENT,
        日付 TEXT,
        選手ID INTEGER,
        練習カテゴリ TEXT,
        メニュー名 TEXT,
        数値記録 REAL,
        単位 TEXT,
        練習強度_RPE INTEGER,
        備考 TEXT,
        FOREIGN KEY(選手ID) REFERENCES athletes(選手ID)
    );
    ''')

    cursor.execute("SELECT COUNT(*) FROM athletes")
    if cursor.fetchone()[0] == 0:
        sample_athletes = [
            ('山田 太郎', '3年', '走幅跳'),
            ('佐藤 健太', '2年', '三段跳'),
            ('鈴木 華', '1年', '走高跳'),
            ('田中 蓮', '4年', '棒高跳')
        ]
        cursor.executemany("INSERT INTO athletes (氏名, 学年, 専門種目) VALUES (?, ?, ?)", sample_athletes)

    conn.commit()
    conn.close()

# アプリ起動時に必ず実行
init_db()

# -------------------------------------------------------------------
# UI・メニュー処理
# -------------------------------------------------------------------
menu = st.sidebar.selectbox("メニュー選択", [
    "📝 CT記録入力（マネージャー用）", 
    "🏋️ 練習メニュー一括入力（マネージャー用）", 
    "📊 CT記録閲覧・グラフ", 
    "📈 個人別練習量データ閲覧",
    "⚙️ 選手情報の登録・一覧（名簿管理）"
])

# 1. CT記録入力
if menu == "📝 CT記録入力（マネージャー用）":
    st.header("📝 コントロールテスト記録の新規追加・更新")
    
    conn = get_connection()
    athletes_df = pd.read_sql_query("SELECT 選手ID, 氏名, 学年, 専門種目 FROM athletes", conn)
    conn.close()
    
    if not athletes_df.empty:
        athletes_df['表示名'] = athletes_df['氏名'] + " (" + athletes_df['学年'] + " / " + athletes_df['専門種目'] + ")"
        athlete_dict = dict(zip(athletes_df['表示名'], athletes_df['選手ID']))
        
        selected_label = st.selectbox("選手を選択", list(athlete_dict.keys()))
        selected_athlete_id = athlete_dict[selected_label]
        
        col1, col2 = st.columns(2)
        with col1:
            period = st.selectbox("実施時期", ["CT①", "CT②", "CT③", "CT④", "その他（自由記入）"])
            if period == "その他（自由記入）":
                period = st.text_input("実施時期を入力（例：夏季合宿CT）", value="")
                
            cat_option = st.selectbox("カテゴリ", ["スタンディングジャンプ", "ランニングジャンプ", "リフティング", "Sprint", "その他（自由記入）"])
            if cat_option == "その他（自由記入）":
                category = st.text_input("カテゴリ名を記述", value="")
            else:
                category = cat_option

        with col2:
            test_option = st.selectbox("テスト種目名", ["立幅跳（m）", "立三段跳（m）", "立五段跳（m）", "Sq 1RM（kg）", "60m SD（sec）", "その他（自由記入）"])
            if test_option == "その他（自由記入）":
                test_name = st.text_input("テスト種目名を記述", value="")
            else:
                test_name = test_option
                
            score = st.number_input("記録（数値）", value=0.0, step=0.01)
        
        if st.button("データベースに保存"):
            if not period or not category or not test_name:
                st.warning("すべての項目を入力してください。")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO control_tests (選手ID, 実施時期, カテゴリ, テスト種目名, 記録)
                    VALUES (?, ?, ?, ?, ?)
                ''', (selected_athlete_id, period, category, test_name, score))
                conn.commit()
                conn.close()
                st.success("記録を正常に保存しました！")

# 2. 練習メニュー一括入力
elif menu == "🏋️ 練習メニュー一括入力（マネージャー用）":
    st.header("🏋️ 練習メニューグループ一括入力")
    conn = get_connection()
    athletes_df = pd.read_sql_query("SELECT 選手ID, 氏名, 学年, 専門種目 FROM athletes", conn)
    conn.close()
    
    st.subheader("1. 対象選手の選択（フィルター）")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        grades = ["すべて"] + list(athletes_df['学年'].unique())
        selected_grade = st.selectbox("学年で絞り込み", grades)
    with col_f2:
        events = ["すべて"] + list(athletes_df['専門種目'].unique())
        selected_event = st.selectbox("専門種目で絞り込み", events)
        
    filtered_df = athletes_df.copy()
    if selected_grade != "すべて":
        filtered_df = filtered_df[filtered_df['学年'] == selected_grade]
    if selected_event != "すべて":
        filtered_df = filtered_df[filtered_df['専門種目'] == selected_event]
        
    target_ids = st.multiselect(
        "対象選手（チェックを外すことで個別除外が可能）", 
        options=list(filtered_df['選手ID']),
        default=list(filtered_df['選手ID']),
        format_func=lambda x: f"{filtered_df[filtered_df['選手ID']==x]['氏名'].values[0]} ({filtered_df[filtered_df['選手ID']==x]['学年'].values[0]}/{filtered_df[filtered_df['専門種目']==x]['専門種目'].values[0]})"
    )
    
    st.markdown("---")
    st.subheader("2. 練習内容の入力")
    col1, col2 = st.columns(2)
    with col1:
        log_date = st.date_input("実施日", date.today())
        train_category = st.selectbox("練習カテゴリ", ["助走・跳躍", "ウエイトトレーニング", "スプリント・SD", "補強・サーキット", "休養・ケア", "その他（自由記入）"])
        if train_category == "その他（自由記入）":
            train_category = st.text_input("練習カテゴリ名を記述", value="")
            
        menu_options = ["全助走跳躍", "短助走跳躍", "ハーフスクワット", "クリーン", "60m SD", "その他（自由記入）"]
        selected_menu_option = st.selectbox("メニュー名（選択）", menu_options)
        
        if selected_menu_option == "その他（自由記入）":
            final_menu_name = st.text_input("メニュー名を直接記述してください", value="")
        else:
            final_menu_name = selected_menu_option

    with col2:
        val_record = st.number_input("数量・重量・距離等の数値", value=0.0, step=1.0)
        unit = st.selectbox("単位", ["本", "kg", "m", "セット", "分", "回"])
        rpe = st.slider("練習強度 RPE (1:楽〜10:限界)", 1, 10, 7)
        memo = st.text_input("備考・コンディション等", value="")
        
    if st.button("選択した選手全員に一括保存"):
        if not target_ids:
            st.warning("対象選手が選択されていません。")
        elif not final_menu_name:
            st.warning("メニュー名を入力してください。")
        else:
            conn = get_connection()
            cursor = conn.cursor()
            for a_id in target_ids:
                cursor.execute('''
                    INSERT INTO training_logs (日付, 選手ID, 練習カテゴリ, メニュー名, 数値記録, 単位, 練習強度_RPE, 備考)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (str(log_date), a_id, train_category, final_menu_name, val_record, unit, rpe, memo))
            conn.commit()
            conn.close()
            st.success(f"{len(target_ids)} 名の選手に『{final_menu_name}』の練習記録を一括登録しました！")

# 3. CT記録閲覧
elif menu == "📊 CT記録閲覧・グラフ":
    st.header("📊 選手別コントロールテスト記録")
    conn = get_connection()
    athletes_df = pd.read_sql_query("SELECT 選手ID, 氏名 FROM athletes", conn)
    athlete_dict = dict(zip(athletes_df['氏名'], athletes_df['選手ID']))
    
    selected_athlete = st.selectbox("表示する選手", list(athlete_dict.keys()))
    selected_id = athlete_dict[selected_athlete]
    
    query = "SELECT 実施時期, カテゴリ, テスト種目名, 記録 FROM control_tests WHERE 選手ID = ?"
    df_result = pd.read_sql_query(query, conn, params=(selected_id,))
    conn.close()
    
    if not df_result.empty:
        st.dataframe(df_result, use_container_width=True)
        test_list = df_result['テスト種目名'].unique()
        selected_test = st.selectbox("グラフ化する種目", test_list)
        
        df_test = df_result[df_result['テスト種目名'] == selected_test]
        fig, ax = plt.subplots()
        ax.plot(df_test['実施時期'], df_test['記録'], marker='o', color='blue')
        ax.set_title(f"{selected_athlete} - {selected_test}")
        st.pyplot(fig)
    else:
        st.info("登録されたコントロールテストデータがありません。")

# 4. 個人別練習量データ閲覧
elif menu == "📈 個人別練習量データ閲覧":
    st.header("📈 個人別 練習ログ・積算データ確認")
    conn = get_connection()
    athletes_df = pd.read_sql_query("SELECT 選手ID, 氏名 FROM athletes", conn)
    athlete_dict = dict(zip(athletes_df['氏名'], athletes_df['選手ID']))
    
    selected_athlete = st.selectbox("確認したい選手を選択", list(athlete_dict.keys()))
    selected_id = athlete_dict[selected_athlete]
    
    query = '''
    SELECT 日付, 練習カテゴリ, メニュー名, 数値記録, 単位, 練習強度_RPE AS RPE, 備考
    FROM training_logs
    WHERE 選手ID = ?
    ORDER BY 日付 DESC
    '''
    df_logs = pd.read_sql_query(query, conn, params=(selected_id,))
    conn.close()
    
    if not df_logs.empty:
        st.subheader(f"{selected_athlete} 選手の練習履歴")
        st.dataframe(df_logs, use_container_width=True)
        
        st.subheader("練習カテゴリ別 合計・回数集計")
        summary_df = df_logs.groupby(['練習カテゴリ', 'メニュー名'])['数値記録'].sum().reset_index()
        summary_df.rename(columns={'数値記録': '合計数値'}, inplace=True)
        st.table(summary_df)
    else:
        st.info("この選手の練習データはまだ登録されていません。")

# 5. 選手情報の登録・一覧
elif menu == "⚙️ 選手情報の登録・一覧（名簿管理）":
    st.header("⚙️ 選手名簿の確認・新規選手登録")
    
    conn = get_connection()
    athletes_df = pd.read_sql_query("SELECT 選手ID, 氏名, 学年, 専門種目 FROM athletes", conn)
    conn.close()
    
    st.subheader("📋 登録済み選手一覧")
    st.dataframe(athletes_df, use_container_width=True)
    
    st.markdown("---")
    st.subheader("➕ 新しい選手を追加登録")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_name = st.text_input("選手氏名", value="")
    with col2:
        new_grade = st.selectbox("学年", ["1年", "2年", "3年", "4年", "大学院", "その他"])
    with col3:
        new_event = st.selectbox("専門種目", ["走幅跳", "三段跳", "走高跳", "棒高跳", "その他"])
        if new_event == "その他":
            new_event = st.text_input("専門種目名を記述", value="")
            
    if st.button("新入部員・選手を保存"):
        if not new_name:
            st.warning("選手氏名を入力してください。")
        else:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO athletes (氏名, 学年, 専門種目)
                VALUES (?, ?, ?)
            ''', (new_name, new_grade, new_event))
            conn.commit()
            conn.close()
            st.success(f"選手『{new_name} ({new_grade}/{new_event})』を登録しました！メニューを切り替えると反映されます。")
