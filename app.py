# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib.parse

st.set_page_config(page_title="FIREシミュレーター", page_icon="🔥", layout="wide")

import datetime
BASE_YEAR = datetime.date.today().year

# ===================== モバイル対応CSS =====================
st.markdown("""
<style>
/* スマホ（768px以下）向け調整 */
@media (max-width: 768px) {

    /* メインエリアの左右余白を縮小 */
    .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
        padding-top: 16px !important;
        max-width: 100% !important;
    }

    /* カラムを縦積みに */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* タブのラベルを小さく */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.75em !important;
        padding: 6px 8px !important;
    }

    /* ヒーローセクションのフォントサイズを縮小 */
    .hero-title { font-size: 1.6em !important; }

    /* スライダーのタッチ操作を改善 */
    [data-testid="stSlider"] {
        padding-top: 8px !important;
        padding-bottom: 8px !important;
    }

    /* メトリクスを見やすく */
    [data-testid="metric-container"] {
        padding: 8px !important;
    }

    /* ボタンをフルワイドに */
    .stDownloadButton button, .stButton button {
        width: 100% !important;
    }

    /* サイドバーを開いたときの幅を最適化 */
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 320px !important;
    }
}

/* タブレット（1024px以下）向け調整 */
@media (max-width: 1024px) {
    .block-container {
        padding-left: 20px !important;
        padding-right: 20px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ===================== ユーティリティ =====================
def _sf(val, default=0.0):
    """NaN・None・空文字を安全にfloatへ変換"""
    try:
        v = float(val)
        return default if (v != v) else v
    except (TypeError, ValueError):
        return default

def calc_takehome(gross_annual, spouse_deduct=0, dependents=0, ideco_annual=0):
    """年収→手取り概算（日本の税制）
    spouse_deduct: 配偶者控除額（円）
    dependents:   一般扶養控除の人数（38万円/人）
    ideco_annual: iDeCo掛金年額（円）
    """
    health   = min(gross_annual * 0.0998, 696_000)
    pension  = min(gross_annual * 0.0915, 716_400)
    employ   = gross_annual * 0.006
    social   = health + pension + employ
    if   gross_annual <= 1_625_000: deduct = 550_000
    elif gross_annual <= 1_800_000: deduct = gross_annual * 0.4 - 100_000
    elif gross_annual <= 3_600_000: deduct = gross_annual * 0.3 + 80_000
    elif gross_annual <= 6_600_000: deduct = gross_annual * 0.2 + 440_000
    elif gross_annual <= 8_500_000: deduct = gross_annual * 0.1 + 1_100_000
    else:                           deduct = 1_950_000
    extra_deduct = spouse_deduct + dependents * 380_000 + ideco_annual
    taxable = max(0, gross_annual - social - deduct - 480_000 - extra_deduct)
    if   taxable <= 1_950_000:  it = taxable * 0.05
    elif taxable <= 3_300_000:  it = taxable * 0.10 - 97_500
    elif taxable <= 6_950_000:  it = taxable * 0.20 - 427_500
    elif taxable <= 9_000_000:  it = taxable * 0.23 - 636_000
    elif taxable <= 18_000_000: it = taxable * 0.33 - 1_536_000
    elif taxable <= 40_000_000: it = taxable * 0.40 - 2_796_000
    else:                       it = taxable * 0.45 - 4_796_000
    it *= 1.021
    rt = taxable * 0.10 + 5_000
    return gross_annual - social - it - rt

# ===================== ヘッダー =====================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 40px 32px 32px 32px;
    margin-bottom: 24px;
">
    <h1 style="color: white; font-size: 2.4em; margin: 0 0 8px 0;">🔥 FIREシミュレーター</h1>
    <p style="color: #aac4e8; font-size: 1.1em; margin: 0 0 28px 0;">
        昇進・教育費・習い事まで設定できる、日本一解像度の高い無料FIREシミュレーター
    </p>
    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
        <div style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 18px; color: white; font-size: 0.9em;">
            ⚡ <b>6項目</b>で即シミュレーション
        </div>
        <div style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 18px; color: white; font-size: 0.9em;">
            🧮 年収→手取り<b>自動計算</b>
        </div>
        <div style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 18px; color: white; font-size: 0.9em;">
            🎓 教育費・昇進まで<b>細かく設定</b>
        </div>
        <div style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 18px; color: white; font-size: 0.9em;">
            📊 グラフで<b>リアルタイム</b>確認
        </div>
        <div style="background: rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 18px; color: white; font-size: 0.9em;">
            💾 設定を<b>保存・読み込み</b>可能
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== モード切り替え =====================
mode = st.radio("モードを選択", ["⚡ かんたんモード", "⚙️ 詳細モード"], horizontal=True)
st.divider()

# ===================== かんたんモード =====================
if mode == "⚡ かんたんモード":
    st.subheader("⚡ かんたんモード")
    st.caption("6項目を入力するだけでFIREプランが分かります。")

    s1, s2, s3 = st.columns(3)
    with s1:
        easy_age_now  = st.number_input("現在の年齢", 20, 70, 30, key="e_age")
        easy_fire_age = st.slider("🔥 FIRE目標年齢", 40, 75, 50, key="e_fage")
    with s2:
        easy_income   = st.number_input("世帯手取り月収（万円）", 10, 200, 40, key="e_inc")  # 参考表示用
        easy_invest   = st.slider("毎月の積立額（万円）", 0, 50, 10, key="e_inv")
    with s3:
        easy_assets   = st.number_input("現在の金融資産（万円）", 0, 10000, 300, key="e_ast")
        easy_fire_exp = st.slider("FIRE後の月額生活費（万円）", 10, 60, 25, key="e_exp")

    easy_return = st.select_slider(
        "運用利回り",
        options=["2%（超保守的）", "3%（保守的）", "5%（標準）", "7%（積極的）", "10%（攻撃的）"],
        value="5%（標準）",
        key="e_ret"
    )
    rate_map = {"2%（超保守的）": 0.02, "3%（保守的）": 0.03, "5%（標準）": 0.05,
                "7%（積極的）": 0.07, "10%（攻撃的）": 0.10}
    easy_rate = rate_map[easy_return]

    # シミュレーション
    fire_target_easy = easy_fire_exp * 10_000 * 12 / 0.04  # かんたんモードは4%ルール固定
    years_e  = list(range(BASE_YEAR, BASE_YEAR + 60))
    assets_e = easy_assets * 10_000
    results_e = []
    for i, yr in enumerate(years_e):
        age = easy_age_now + i
        assets_e = assets_e * (1 + easy_rate) + easy_invest * 10_000 * 12
        results_e.append({"年度": yr, "年齢": age, "資産": round(assets_e), "目標": round(fire_target_easy)})
    df_e = pd.DataFrame(results_e)

    # FIRE達成年齢
    achieved_e = df_e[df_e["資産"] >= df_e["目標"]]
    fire_row_e = df_e[df_e["年齢"] == easy_fire_age]
    assets_at_fire = fire_row_e["資産"].values[0] if not fire_row_e.empty else 0
    gap_e = assets_at_fire - fire_target_easy

    # 結果バナー
    if gap_e >= 0:
        st.markdown(f"""
<div style="background: linear-gradient(135deg, #1b5e20, #2e7d32);
     border-radius: 12px; padding: 20px 28px; margin-bottom: 16px; color: white;">
    <div style="font-size: 1.8em; font-weight: bold;">✅ {easy_fire_age}歳FIREは達成できます！</div>
    <div style="font-size: 1.1em; margin-top: 6px; color: #c8e6c9;">
        目標額より <b>{gap_e/10_000:.0f}万円</b> 上回る見込みです。
    </div>
</div>""", unsafe_allow_html=True)
    else:
        lack = abs(gap_e)
        months = max(1, (easy_fire_age - easy_age_now) * 12)
        extra = lack / months
        achieve_age = achieved_e.iloc[0]["年齢"] if not achieved_e.empty else None
        msg = f"現在のペースだと <b>{achieve_age}歳</b> でFIRE達成できます。" if achieve_age else "現在のペースでは期間内の達成が難しい状況です。"
        st.markdown(f"""
<div style="background: linear-gradient(135deg, #b71c1c, #c62828);
     border-radius: 12px; padding: 20px 28px; margin-bottom: 16px; color: white;">
    <div style="font-size: 1.8em; font-weight: bold;">❌ {easy_fire_age}歳FIREには {lack/10_000:.0f}万円 不足</div>
    <div style="font-size: 1.1em; margin-top: 6px; color: #ffcdd2;">
        毎月 <b>+{extra/10_000:.1f}万円</b> の積立増または収入増が必要です。<br>{msg}
    </div>
</div>""", unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    k1.metric("必要資産額（4%ルール）", f"{fire_target_easy/10_000:.0f}万円")
    k2.metric(f"{easy_fire_age}歳時点の資産（試算）", f"{assets_at_fire/10_000:.0f}万円")
    if gap_e >= 0:
        k3.metric("目標との差", f"+{gap_e/10_000:.0f}万円 ✅", delta="達成")
    else:
        k3.metric("目標との差", f"{gap_e/10_000:.0f}万円 ❌", delta="不足", delta_color="inverse")

    # グラフ
    x_e = [f"{r['年度']}({r['年齢']}歳)" for _, r in df_e.iterrows()]
    fig_e = go.Figure()
    fig_e.add_trace(go.Scatter(x=x_e, y=df_e["資産"]/10_000,
        name="資産推移", line=dict(color="#2196F3", width=3),
        fill="tozeroy", fillcolor="rgba(33,150,243,0.1)"))
    fig_e.add_trace(go.Scatter(x=x_e, y=df_e["目標"]/10_000,
        name="FIRE目標", line=dict(color="#F44336", width=2, dash="dash")))
    fire_e_idx = easy_fire_age - easy_age_now
    if 0 <= fire_e_idx < len(x_e):
        fig_e.add_vline(x=fire_e_idx, line_dash="dot", line_color="orange",
                        annotation_text="🔥 FIRE目標")
    if not achieved_e.empty:
        a_idx = achieved_e.iloc[0]["年齢"] - easy_age_now
        if 0 <= a_idx < len(x_e):
            fig_e.add_vline(x=a_idx, line_dash="dot", line_color="green",
                            annotation_text=f"✅ FIRE達成({achieved_e.iloc[0]['年齢']}歳)")
    fig_e.update_layout(height=400, yaxis_title="万円",
                        legend=dict(orientation="h", y=1.05), margin=dict(t=40))
    st.plotly_chart(fig_e, use_container_width=True)

    # 診断コメント
    if gap_e >= 0:
        st.success(f"✅ 現在のペースで **{easy_fire_age}歳FIRE** は達成可能です！")
    else:
        lack = abs(gap_e)
        months = (easy_fire_age - easy_age_now) * 12
        extra = lack / months if months > 0 else 0
        st.error(f"❌ **{lack/10_000:.0f}万円** 不足。毎月 **+{extra/10_000:.1f}万円** の積立増か収入増が必要です。")
        if not achieved_e.empty:
            st.info(f"💡 現在のペースだと **{achieved_e.iloc[0]['年齢']}歳** でFIRE達成できます。")

    # SNSシェア
    st.divider()
    share_text = (
        f"🔥 FIREシミュレーターで試算しました！\n"
        f"目標: {easy_fire_age}歳FIRE\n"
        f"必要資産: {fire_target_easy/10_000:.0f}万円\n"
        f"{'✅ 達成ペース！' if gap_e >= 0 else f'❌ {abs(gap_e)/10_000:.0f}万円不足'}\n"
        f"#FIRE #資産形成 #FIREシミュレーター"
    )
    encoded = urllib.parse.quote(share_text)
    col_s1, col_s2 = st.columns(2)
    col_s1.link_button("𝕏 (Twitter) でシェア",
        f"https://twitter.com/intent/tweet?text={encoded}", use_container_width=True)
    col_s2.link_button("📘 LINEでシェア",
        f"https://social-plugins.line.me/lineit/share?url=https://fire-simulator.streamlit.app&text={encoded}",
        use_container_width=True)

    invest_ratio = easy_invest / easy_income * 100 if easy_income > 0 else 0
    st.caption(f"💡 積立比率: 月収 {easy_income}万円 に対して {easy_invest}万円 = **{invest_ratio:.0f}%**（目安: 20〜30%）")
    st.divider()
    st.caption("📊 より細かい設定（昇進・退職金・教育費・保険など）は **詳細モード** をお試しください。")

# ===================== 詳細モード =====================
else:
    # ---- _loaded_cfg の展開（rerun後の先頭で処理） ----
    if "_loaded_cfg" in st.session_state:
        _cfg = st.session_state["_loaded_cfg"]
        _scalar_keys = [
            "d_age_now", "d_fire_age", "d_return", "d_ideco_ret", "d_other_ret",
            "d_inflation", "d_fire_monthly", "d_fire_rule", "d_fire_rate_custom",
            "d_spouse", "d_deps", "d_ideco_m", "c_gross", "c_bpct",
            "d_has_ret", "d_ret_amt", "d_ret_age", "d_wife_cur",
            "d_has_side", "d_cur_nisa", "d_cur_ideco", "d_cur_dep",
            "d_cur_other", "d_nisa_used", "d_has_loan", "d_loan_bal",
            "d_loan_pmt", "d_loan_type", "d_loan_rate", "d_loan_rate_f",
            "d_rate_chg_age", "d_mgmt_fee",
            "d_num_children",
            *[f"birth_{i}" for i in range(3)],
            *[f"elem_{i}"  for i in range(3)],
            *[f"mid_{i}"   for i in range(3)],
            *[f"high_{i}"  for i in range(3)],
            *[f"uni_{i}"   for i in range(3)],
            *[f"as_{i}"    for i in range(3)],
            *[f"ae_{i}"    for i in range(3)],
            *[f"ac_{i}"    for i in range(3)],
            # 支出タブ
            "d_exp_food", "d_exp_eatout", "d_exp_daily", "d_exp_clothes", "d_exp_medical",
            "d_exp_gas", "d_exp_carmaint", "d_exp_transit", "d_exp_phone", "d_exp_subscr",
            "d_exp_hobby", "d_exp_travel", "d_exp_social", "d_exp_misc",
            # 保険タブ
            "d_ins_b_life", "d_ins_b_life_end", "d_ins_b_med", "d_ins_b_other",
            "wl", "wle", "wm", "wo",
            # 収支サマリー
            "d_my_living",
        ]
        for _k in _scalar_keys:
            if _k in _cfg:
                st.session_state[_k] = _cfg[_k]
        _tbl_keys = ["tbl_milestones", "tbl_wife", "tbl_invest", "tbl_car", "tbl_renov", "tbl_side"]
        for _tk in _tbl_keys:
            if _tk in _cfg:
                st.session_state[_tk] = _cfg[_tk]
        del st.session_state["_loaded_cfg"]
        st.rerun()

    # ---- 保存・読み込み用データ準備（サイドバー外で先に計算） ----
    import json as _json
    _scalar_save_keys = [
        "d_age_now", "d_fire_age", "d_return", "d_ideco_ret", "d_other_ret",
        "d_inflation", "d_fire_monthly", "d_fire_rule", "d_fire_rate_custom",
        "d_spouse", "d_deps", "d_ideco_m", "c_gross", "c_bpct",
        "d_has_ret", "d_ret_amt", "d_ret_age", "d_wife_cur",
        "d_has_side", "d_cur_nisa", "d_cur_ideco", "d_cur_dep",
        "d_cur_other", "d_nisa_used", "d_has_loan", "d_loan_bal",
        "d_loan_pmt", "d_loan_type", "d_loan_rate", "d_loan_rate_f",
        "d_rate_chg_age", "d_mgmt_fee",
        "d_num_children",
        *[f"birth_{i}" for i in range(3)],
        *[f"elem_{i}"  for i in range(3)],
        *[f"mid_{i}"   for i in range(3)],
        *[f"high_{i}"  for i in range(3)],
        *[f"uni_{i}"   for i in range(3)],
        *[f"as_{i}"    for i in range(3)],
        *[f"ae_{i}"    for i in range(3)],
        *[f"ac_{i}"    for i in range(3)],
    ]
    _save_data = {k: st.session_state[k] for k in _scalar_save_keys if k in st.session_state}
    for _tk, _tv in {
        "tbl_milestones": st.session_state.get("tbl_milestones"),
        "tbl_wife":       st.session_state.get("tbl_wife"),
        "tbl_invest":     st.session_state.get("tbl_invest"),
        "tbl_car":        st.session_state.get("tbl_car"),
        "tbl_renov":      st.session_state.get("tbl_renov"),
        "tbl_side":       st.session_state.get("tbl_side"),
    }.items():
        if _tv is not None:
            _save_data[_tk] = _tv

    # ---- 読み込みエリア（メイン画面上部・折りたたみ） ----
    with st.expander("📂 設定を読み込む（保存済みファイルがある場合）"):
        _uploaded = st.file_uploader(
            "保存したJSONファイルを選択してください",
            type="json",
            label_visibility="visible",
        )
        if _uploaded is not None:
            try:
                _loaded = _json.loads(_uploaded.read().decode("utf-8"))
                st.session_state["_loaded_cfg"] = _loaded
                st.rerun()
            except Exception as _e:
                st.error(f"読み込みエラー: {_e}")

    with st.sidebar:
        # ---- 保存ボタンのみ ----
        st.download_button(
            label="💾 設定を保存 (.json)",
            data=_json.dumps(_save_data, ensure_ascii=False, indent=2),
            file_name="fire_simulator_config.json",
            mime="application/json",
            use_container_width=True,
            help="現在の設定をJSONファイルとして保存します",
        )
        st.divider()
        st.header("🎯 基本設定")
        boss_age_now = st.number_input("あなたの現在の年齢", 20, 70, 30, key="d_age_now")
        fire_age     = st.slider("🔥 FIRE目標年齢", 40, 75, 50, key="d_fire_age")
        fire_year    = BASE_YEAR + (fire_age - boss_age_now)
        st.caption(f"FIRE目標: **{fire_year}年**")

        st.divider()
        st.header("📈 運用・経済")
        return_rate  = st.slider("NISA 利回り（%）", 0.0, 15.0, 5.0, 0.1, key="d_return",
            help="長期インデックス投資の目安は4〜7%。保守的に5%がおすすめ。") / 100
        ideco_return = st.slider("iDeCo 利回り（%）", 0.0, 15.0, 5.0, 0.1, key="d_ideco_ret") / 100
        other_return = st.slider("その他投資 利回り（%）", 0.0, 15.0, 3.0, 0.1, key="d_other_ret") / 100
        inflation    = st.slider("インフレ率（%）", 0.0, 5.0, 1.5, 0.1, key="d_inflation",
            help="日本の長期平均インフレ率は1〜2%。日銀目標は2%。") / 100

        st.divider()
        st.header("🔥 FIRE後の設計")
        fire_monthly = st.number_input("FIRE後 月額生活費（万円）", 10, 100, 25, key="d_fire_monthly") * 10_000
        fire_rule    = st.selectbox("取り崩しルール",
            ["4%ルール", "3.5%ルール", "3%ルール", "カスタム"],
            key="d_fire_rule",
            help="4%ルール: 資産の4%を毎年取り崩しても長期的に資産が維持されるという経験則。")
        if fire_rule == "カスタム":
            fire_rate = st.number_input("取り崩し率（%）", 1.0, 10.0, 4.0, 0.1, key="d_fire_rate_custom") / 100
        else:
            fire_rate = {"4%ルール": 0.04, "3.5%ルール": 0.035, "3%ルール": 0.03}[fire_rule]
        fire_target = fire_monthly * 12 / fire_rate
        st.metric("必要資産額", f"{fire_target/10_000:.0f}万円")

    tab_income, tab_expense, tab_housing, tab_edu, tab_ins, tab_asset, tab_result = st.tabs([
        "💼 収入", "💸 支出", "🏠 住宅・ローン", "🎓 教育費", "🛡️ 保険", "📈 資産・運用", "📊 結果・分析"
    ])

    # ===================== 収入 =====================
    with tab_income:
        st.subheader("💼 収入の設計")

        # --- 手取り計算の条件（全計算に共通で使う） ---
        st.markdown("#### 🔧 手取り計算の条件")
        cond1, cond2, cond3 = st.columns(3)
        with cond1:
            spouse_status = st.radio(
                "配偶者控除",
                ["なし", "あり（配偶者年収103万以下）", "配偶者特別控除（103〜201万円）"],
                help="配偶者の年収によって本人の所得控除額が変わります",
                key="d_spouse",
            )
            spouse_deduct_amt = {"なし": 0,
                                 "あり（配偶者年収103万以下）": 380_000,
                                 "配偶者特別控除（103〜201万円）": 260_000}[spouse_status]
        with cond2:
            dep_count = st.number_input(
                "扶養家族（16歳以上）の人数", 0, 5, 0,
                help="一般扶養控除38万円/人（19〜22歳は特定扶養控除63万円/人ですが、ここでは38万円で近似）",
                key="d_deps",
            )
        with cond3:
            ideco_monthly_calc = st.number_input(
                "iDeCo掛金（万円/月）", 0.0, 2.3, 0.0, 0.1,
                help="掛金全額が所得控除になります（会社員の上限: 2.3万円/月）",
                key="d_ideco_m",
            )
        ideco_annual_calc = ideco_monthly_calc * 10_000 * 12

        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 現在の収入")
            current_gross_input = st.number_input(
                "現在の年収（万円）", 200, 3000, 500, 10, key="c_gross") * 10_000
            current_bonus_pct = st.slider(
                "ボーナスの割合（%）", 0, 50, 20, key="c_bpct",
                help="例: 年収500万のうちボーナスが100万 → 20%")

            _th_now = calc_takehome(current_gross_input, spouse_deduct_amt, dep_count, ideco_annual_calc)
            current_monthly = _th_now * (1 - current_bonus_pct / 100) / 12
            current_bonus   = _th_now * current_bonus_pct / 100

            th_c1, th_c2, th_c3 = st.columns(3)
            th_c1.metric("手取り年収",      f"{_th_now/10_000:.0f}万円")
            th_c2.metric("手取り月収",      f"{current_monthly/10_000:.1f}万円")
            th_c3.metric("手取りボーナス計", f"{current_bonus/10_000:.0f}万円")
            _eff_now = (current_gross_input - _th_now) / current_gross_input * 100 if current_gross_input > 0 else 0
            st.caption(f"税・社保の実効負担率: {_eff_now:.1f}%")

            st.divider()
            st.markdown("#### 🚀 昇進・年収マイルストーン")
            st.caption("昇進・転職のタイミングを年収とボーナス割合で入力。手取りは上の条件設定をもとに自動計算します。")
            _milestone_default_records = [
                {"あなたの年齢": 35, "想定年収（万円）": 600.0, "ボーナス割合（%）": 20.0, "メモ": "例：昇格"},
                {"あなたの年齢": 40, "想定年収（万円）": 700.0, "ボーナス割合（%）": 20.0, "メモ": "例：主任"},
                {"あなたの年齢": 45, "想定年収（万円）": 800.0, "ボーナス割合（%）": 22.0, "メモ": "例：係長"},
                {"あなたの年齢": 50, "想定年収（万円）": 900.0, "ボーナス割合（%）": 25.0, "メモ": "例：課長"},
            ]
            milestones_df = st.data_editor(
                pd.DataFrame(st.session_state.get("tbl_milestones", _milestone_default_records)),
                num_rows="dynamic", use_container_width=True,
                column_config={
                    "あなたの年齢":    st.column_config.NumberColumn(min_value=boss_age_now, max_value=70),
                    "想定年収（万円）": st.column_config.NumberColumn(format="%.0f"),
                    "ボーナス割合（%）": st.column_config.NumberColumn(format="%.0f", min_value=0, max_value=50,
                                         help="年収全体に対するボーナスの割合"),
                    "メモ":            st.column_config.TextColumn(),
                }
            )

            # 手取り計算プレビュー
            _preview_rows = []
            for _, _row in milestones_df.dropna(subset=["あなたの年齢"]).iterrows():
                _g  = _sf(_row["想定年収（万円）"]) * 10_000
                _bp = _sf(_row["ボーナス割合（%）"]) / 100
                if _g > 0:
                    _th = calc_takehome(_g, spouse_deduct_amt, dep_count, ideco_annual_calc)
                    _preview_rows.append({
                        "年齢":             int(_sf(_row["あなたの年齢"])),
                        "年収（万）":        f"{_g/10_000:.0f}",
                        "手取り月収（万）":  f"{_th*(1-_bp)/12/10_000:.1f}",
                        "手取りボーナス（万）": f"{_th*_bp/10_000:.0f}",
                        "実効税率":         f"{(_g-_th)/_g*100:.1f}%",
                        "メモ":             _row["メモ"],
                    })
            if _preview_rows:
                st.caption("📊 手取り自動計算結果（シミュレーションはこの値を使用）:")
                st.dataframe(pd.DataFrame(_preview_rows), use_container_width=True, hide_index=True)

        with c2:
            st.markdown("#### 💰 退職金")
            has_retirement = st.checkbox("退職金あり", value=True, key="d_has_ret")
            retirement_amt = st.number_input("退職金 手取り（万円）", 0, 5000, 500, key="d_ret_amt",
                help="勤続年数20年以下: 40万×勤続年数、20年超: 800万+70万×(勤続-20年)が退職所得控除の目安") * 10_000 if has_retirement else 0
            retirement_age = st.number_input("退職金 受取年齢", boss_age_now, 70, fire_age, key="d_ret_age") if has_retirement else fire_age

            st.markdown("#### 💡 副業・その他収入")
            has_side = st.checkbox("副業あり", value=False, key="d_has_side")
            if has_side:
                _side_default_records = [{"開始年齢": 35, "終了年齢": 50, "年収（万円）": 50.0, "内容": "副業"}]
                side_df = st.data_editor(
                    pd.DataFrame(st.session_state.get("tbl_side", _side_default_records)),
                    num_rows="dynamic", use_container_width=True,
                )
                side_records = side_df.to_dict("records")
                st.session_state["tbl_side"] = side_records
            else:
                side_records = []

            st.markdown("#### 👩 配偶者・パートナーの収入")
            wife_current = st.number_input("現在の年収 手取り（万円）", 0, 500, 200, key="d_wife_cur") * 10_000
            _wife_default_records = [
                {"あなたの年齢": 38, "配偶者の年収 手取り（万円）": 220.0, "メモ": "子供小学校〜"},
                {"あなたの年齢": 45, "配偶者の年収 手取り（万円）": 250.0, "メモ": "フルタイム安定"},
            ]
            wife_df = st.data_editor(
                pd.DataFrame(st.session_state.get("tbl_wife", _wife_default_records)),
                num_rows="dynamic", use_container_width=True,
            )

    # ===================== 支出 =====================
    with tab_expense:
        st.subheader("💸 月次支出の詳細設定")
        st.caption("月額（万円）で入力。インフレは自動反映。")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 🍚 食・日常")
            exp_food    = st.slider("食費（自炊）", 0.0, 20.0, 4.0, 0.5, key="d_exp_food")
            exp_eatout  = st.slider("外食・テイクアウト", 0.0, 20.0, 2.0, 0.5, key="d_exp_eatout")
            exp_daily   = st.slider("日用品・消耗品", 0.0, 10.0, 1.0, 0.5, key="d_exp_daily")
            exp_clothes = st.slider("被服・美容", 0.0, 10.0, 1.0, 0.5, key="d_exp_clothes")
            exp_medical = st.slider("医療・薬代", 0.0, 10.0, 0.5, 0.5, key="d_exp_medical")
        with c2:
            st.markdown("#### 🚗 交通・通信")
            exp_gas      = st.slider("ガソリン代", 0.0, 10.0, 1.0, 0.5, key="d_exp_gas")
            exp_carmaint = st.slider("車維持費（月均し）", 0.0, 10.0, 1.0, 0.5, key="d_exp_carmaint")
            exp_transit  = st.slider("電車・バス等", 0.0, 10.0, 0.5, 0.5, key="d_exp_transit")
            exp_phone    = st.slider("スマホ・通信費", 0.0, 5.0, 0.5, 0.1, key="d_exp_phone")
            exp_subscr   = st.slider("サブスク", 0.0, 5.0, 0.3, 0.1, key="d_exp_subscr")
        with c3:
            st.markdown("#### 🎉 娯楽・その他")
            exp_hobby   = st.slider("趣味・娯楽", 0.0, 20.0, 1.0, 0.5, key="d_exp_hobby")
            exp_travel  = st.number_input("旅行（年額 万円）", 0.0, 300.0, 15.0, 1.0, key="d_exp_travel")
            exp_social  = st.slider("交際費・ギフト", 0.0, 10.0, 1.0, 0.5, key="d_exp_social")
            exp_misc    = st.slider("雑費・その他", 0.0, 10.0, 1.0, 0.5, key="d_exp_misc")

        monthly_living_base = (
            exp_food + exp_eatout + exp_daily + exp_clothes + exp_medical
            + exp_gas + exp_carmaint + exp_transit + exp_phone + exp_subscr
            + exp_hobby + exp_social + exp_misc
        ) * 10_000 + exp_travel * 10_000 / 12

        st.divider()
        cols = st.columns(3)
        cols[0].metric("月次生活費合計", f"{monthly_living_base/10_000:.1f}万円")
        cols[1].metric("年間合計", f"{monthly_living_base*12/10_000:.0f}万円")
        cols[2].metric(f"10年後（インフレ{inflation*100:.1f}%）", f"{monthly_living_base*12*(1+inflation)**10/10_000:.0f}万円")

        st.divider()
        st.markdown("#### 🚗 車の買い替え計画")
        _car_default_records = [{"あなたの年齢": 55, "費用（万円）": 300, "メモ": "次の車"}]
        car_df = st.data_editor(
            pd.DataFrame(st.session_state.get("tbl_car", _car_default_records)),
            num_rows="dynamic", use_container_width=True,
        )
        st.markdown("#### 🏠 住宅特別支出（リフォーム等）")
        _renov_default_records = [
            {"あなたの年齢": 50, "費用（万円）": 100, "メモ": "大規模修繕"},
            {"あなたの年齢": 65, "費用（万円）": 200, "メモ": "老後リフォーム"},
        ]
        renov_df = st.data_editor(
            pd.DataFrame(st.session_state.get("tbl_renov", _renov_default_records)),
            num_rows="dynamic", use_container_width=True,
        )

    # ===================== 住宅 =====================
    with tab_housing:
        st.subheader("🏠 住宅ローン設定")
        c1, c2 = st.columns(2)
        with c1:
            has_loan = st.checkbox("住宅ローンあり", value=True, key="d_has_loan")
            if has_loan:
                loan_balance_now = st.number_input("現在のローン残債（万円）", 0, 10000, 3000, key="d_loan_bal") * 10_000
                monthly_loan_pmt = st.number_input("月次返済額（万円）", 0.0, 50.0, 10.0, 0.01, key="d_loan_pmt") * 10_000
                loan_type        = st.selectbox("金利タイプ", ["変動金利", "固定金利（全期間）"], key="d_loan_type")
                loan_rate_now    = st.slider("現在の金利（%）", 0.1, 5.0, 1.0, 0.05, key="d_loan_rate") / 100
                if loan_type == "変動金利":
                    loan_rate_future = st.slider("将来の想定金利（%）", 0.1, 5.0, 2.0, 0.05, key="d_loan_rate_f",
                        help="日本では2024年以降、段階的な利上げが進んでいます。") / 100
                    rate_change_age  = st.number_input("金利が上昇する年齢", boss_age_now, 70, 40, key="d_rate_chg_age")
                else:
                    loan_rate_future = loan_rate_now
                    rate_change_age  = 999
                mgmt_fee = st.number_input("管理費・修繕積立（月額 万円）", 0.0, 20.0, 2.0, 0.1, key="d_mgmt_fee") * 10_000
            else:
                loan_balance_now = monthly_loan_pmt = loan_rate_now = loan_rate_future = mgmt_fee = 0
                rate_change_age = 999

        with c2:
            if has_loan:
                b = loan_balance_now
                payoff_year = BASE_YEAR + 50
                payoff_age  = boss_age_now + 50
                for i in range(50):
                    age = boss_age_now + i
                    r   = loan_rate_future if age >= rate_change_age else loan_rate_now
                    interest  = b * r
                    principal = monthly_loan_pmt * 12 - interest
                    b = max(0, b - principal)
                    if b == 0:
                        payoff_year = BASE_YEAR + i
                        payoff_age  = age
                        break
                st.metric("月次返済額", f"{monthly_loan_pmt/10_000:.2f}万円")
                st.metric("現在残債",   f"{loan_balance_now/10_000:.0f}万円")
                st.metric("完済予定",   f"{payoff_year}年（{payoff_age}歳）")
                if fire_age < payoff_age:
                    b2 = loan_balance_now
                    for i in range(fire_age - boss_age_now):
                        age2 = boss_age_now + i
                        r2   = loan_rate_future if age2 >= rate_change_age else loan_rate_now
                        b2   = max(0, b2 - (monthly_loan_pmt * 12 - b2 * r2))
                    st.warning(f"⚠️ FIRE時点でローン残債 **{b2/10_000:.0f}万円** が残ります。")

    # ===================== 教育費 =====================
    with tab_edu:
        st.subheader("🎓 子どもの教育費設定")
        num_children = st.selectbox("子どもの人数", [0, 1, 2, 3], index=0, key="d_num_children")

        ELEM_COST = {"公立": 80_000, "私立": 900_000}
        MID_COST  = {"公立": 180_000, "私立": 900_000}
        HIGH_COST = {"公立": 350_000, "私立": 900_000}
        UNI_COST  = {
            "国公立（自宅）": 600_000, "国公立（自宅外）": 1_200_000,
            "私立文系（自宅）": 1_100_000, "私立文系（自宅外）": 1_900_000,
            "私立理系（自宅）": 1_400_000, "私立理系（自宅外）": 2_200_000,
            "行かない": 0,
        }

        children = []
        names    = ["第1子", "第2子", "第3子"]
        defaults = [
            {"birth": 2020, "elem": "公立", "mid": "公立", "high": "公立", "uni": "私立文系（自宅）", "act_start": 5,  "act_end": 15, "act": 1.0},
            {"birth": 2023, "elem": "公立", "mid": "公立", "high": "公立", "uni": "私立文系（自宅）", "act_start": 5,  "act_end": 15, "act": 1.0},
            {"birth": 2026, "elem": "公立", "mid": "公立", "high": "公立", "uni": "私立文系（自宅）", "act_start": 5,  "act_end": 15, "act": 1.0},
        ]

        for i in range(num_children):
            d = defaults[i]
            with st.expander(f"👧 {names[i]}の設定", expanded=True):
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    birth = st.number_input("生年（西暦）", 2010, 2040, d["birth"], key=f"birth_{i}")
                    elem  = st.selectbox("小学校", ["公立", "私立"], key=f"elem_{i}")
                    mid   = st.selectbox("中学校", ["公立", "私立"], key=f"mid_{i}")
                    high  = st.selectbox("高校",   ["公立", "私立"], key=f"high_{i}")
                    uni   = st.selectbox("大学",   list(UNI_COST.keys()), index=2, key=f"uni_{i}")
                with cc2:
                    act_start = st.number_input("習い事 開始年齢", 0, 18, d["act_start"], key=f"as_{i}")
                    act_end   = st.number_input("習い事 終了年齢", 0, 22, d["act_end"],   key=f"ae_{i}")
                    act_cost  = st.number_input("習い事 月額（万円）", 0.0, 20.0, d["act"], 0.1, key=f"ac_{i}") * 10_000
                with cc3:
                    total_edu_cost = ELEM_COST[elem]*6 + MID_COST[mid]*3 + HIGH_COST[high]*3 + UNI_COST[uni]*4
                    st.metric("教育費総額（概算）", f"{total_edu_cost/10_000:.0f}万円")
                children.append({"birth": birth, "elem": elem, "mid": mid, "high": high, "uni": uni,
                                  "act_start": act_start, "act_end": act_end, "act_cost": act_cost})

    # ===================== 保険 =====================
    with tab_ins:
        st.subheader("🛡️ 保険料の設定")
        ic1, ic2 = st.columns(2)
        with ic1:
            st.markdown("#### 本人")
            ins_b_life     = st.number_input("死亡保険（月額 円）",    0, 100000, 10000, key="d_ins_b_life")
            ins_b_life_end = st.number_input("死亡保険 終了年齢",      boss_age_now, 100, 65, key="d_ins_b_life_end")
            ins_b_med      = st.number_input("医療保険（月額 円）",    0, 50000, 2000, key="d_ins_b_med")
            ins_b_other    = st.number_input("その他（月額 円）",      0, 50000, 0, key="d_ins_b_other")
        with ic2:
            st.markdown("#### 配偶者")
            ins_w_life     = st.number_input("死亡保険（月額 円）",    0, 100000, 8000, key="wl")
            ins_w_life_end = st.number_input("死亡保険 終了年齢",      boss_age_now, 100, 65, key="wle")
            ins_w_med      = st.number_input("医療保険（月額 円）",    0, 50000, 2000, key="wm")
            ins_w_other    = st.number_input("その他（月額 円）",      0, 50000, 0,    key="wo")

        total_ins = ins_b_life + ins_b_med + ins_b_other + ins_w_life + ins_w_med + ins_w_other
        st.divider()
        ci1, ci2 = st.columns(2)
        ci1.metric("保険料合計（月）", f"{total_ins:,}円")
        ci2.metric("年額", f"{total_ins*12/10_000:.1f}万円")
        if total_ins > 30000:
            st.warning("⚠️ 月3万円超。見直しで年10〜20万円削減の可能性あり。")

    # ===================== 資産・運用 =====================
    with tab_asset:
        st.subheader("📈 資産・運用設定")
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown("#### 現在の資産")
            current_nisa    = st.number_input("NISA残高（万円）",      0, 10000, 100, key="d_cur_nisa") * 10_000
            current_ideco   = st.number_input("iDeCo残高（万円）",     0, 10000, 0,   key="d_cur_ideco") * 10_000
            current_deposit = st.number_input("預金残高（万円）",       0, 10000, 200, key="d_cur_dep") * 10_000
            current_other   = st.number_input("その他投資残高（万円）", 0, 10000, 0,   key="d_cur_other") * 10_000

            st.markdown("#### 積立ペース（年齢別に変更可能）")
            _invest_default_records = [
                {"あなたの年齢": 30, "NISA（万円/月）": 5.0,  "iDeCo（万円/月）": 0.0, "その他投資（万円/月）": 0.0, "メモ": "現在"},
                {"あなたの年齢": 35, "NISA（万円/月）": 8.0,  "iDeCo（万円/月）": 2.3, "その他投資（万円/月）": 0.0, "メモ": "昇格後"},
                {"あなたの年齢": 40, "NISA（万円/月）": 12.0, "iDeCo（万円/月）": 2.3, "その他投資（万円/月）": 2.0, "メモ": "さらに昇格"},
                {"あなたの年齢": 45, "NISA（万円/月）": 15.0, "iDeCo（万円/月）": 2.3, "その他投資（万円/月）": 5.0, "メモ": "管理職"},
            ]
            invest_df = st.data_editor(
                pd.DataFrame(st.session_state.get("tbl_invest", _invest_default_records)),
                num_rows="dynamic", use_container_width=True,
                column_config={
                    "あなたの年齢": st.column_config.NumberColumn(min_value=boss_age_now, max_value=70),
                    "NISA（万円/月）": st.column_config.NumberColumn(format="%.1f", min_value=0.0, max_value=30.0, help="新NISA上限: 月30万（年360万）"),
                    "iDeCo（万円/月）": st.column_config.NumberColumn(format="%.1f", min_value=0.0, max_value=2.3, help="会社員の上限: 月2.3万円"),
                    "その他投資（万円/月）": st.column_config.NumberColumn(format="%.1f", min_value=0.0, max_value=50.0),
                    "メモ": st.column_config.TextColumn(),
                }
            )
            current_invest_row = invest_df.dropna(subset=["あなたの年齢"])
            current_invest_row = current_invest_row[current_invest_row["あなたの年齢"] <= boss_age_now]
            if not current_invest_row.empty:
                row = current_invest_row.iloc[-1]
                monthly_nisa_now  = _sf(row["NISA（万円/月）"]) * 10_000
                monthly_ideco_now = _sf(row["iDeCo（万円/月）"]) * 10_000
                monthly_other_now = _sf(row["その他投資（万円/月）"]) * 10_000
            else:
                monthly_nisa_now = monthly_ideco_now = monthly_other_now = 0
            total_inv = monthly_nisa_now + monthly_ideco_now + monthly_other_now
            st.caption(f"現在の積立合計: 月 {total_inv/10_000:.1f}万円")

        with ac2:
            st.markdown("#### NISA枠の確認")
            nisa_used = st.number_input("新NISA 使用済み枠（万円）", 0, 1800, 100, key="d_nisa_used")
            nisa_remaining = 1800 - nisa_used
            st.metric("残り枠", f"{nisa_remaining}万円 / 1,800万円")
            if monthly_nisa_now > 0:
                months_left = nisa_remaining / (monthly_nisa_now / 10_000)
                st.caption(f"月{monthly_nisa_now/10_000:.0f}万円積立で あと{months_left:.0f}ヶ月（{months_left/12:.1f}年）で満額")

            st.markdown("#### 生活防衛資金")
            emergency_target = monthly_living_base * 6
            st.metric("推奨（6ヶ月分）", f"{emergency_target/10_000:.0f}万円")
            if current_deposit < emergency_target:
                st.warning(f"⚠️ 現在の預金 {current_deposit/10_000:.0f}万円 は不足しています。")
            else:
                invest_ready = current_deposit - emergency_target
                st.success(f"✅ 防衛資金確保後、追加投資可能額: {invest_ready/10_000:.0f}万円")

    # ===================== 収支サマリー（サイドバー） =====================
    with st.sidebar:
        st.divider()
        st.subheader("💰 収支サマリー（月次・現在）")

        _living_total_m = monthly_living_base / 10_000
        _my_living_m = st.slider(
            "生活費のうち自己負担（万円/月）",
            0.0, max(_living_total_m, 0.5),
            min(_living_total_m, round(_living_total_m * 0.3 * 2) / 2),
            0.5, key="d_my_living",
            help="生活費合計のうち自分の収入から払う分。残りは配偶者負担とみなします。"
        )
        _spouse_living_m = _living_total_m - _my_living_m

        _income_m  = current_monthly / 10_000
        _loan_m    = monthly_loan_pmt / 10_000 if has_loan else 0.0
        _ins_m     = total_ins / 10_000
        _available = _income_m - _loan_m - _ins_m - _my_living_m

        st.markdown("**👤 自分の収支**")
        st.markdown(
            f"| 項目 | 月額 |\n"
            f"|------|------|\n"
            f"| 手取り月収 | **{_income_m:.1f}万円** |\n"
            f"| − ローン返済 | {_loan_m:.1f}万円 |\n"
            f"| − 保険料 | {_ins_m:.1f}万円 |\n"
            f"| − 生活費（自己負担） | {_my_living_m:.1f}万円 |\n"
            f"| **投資可能額** | **{_available:.1f}万円** |"
        )
        _inv_total_m = total_inv / 10_000
        if _available > 0:
            if _inv_total_m > 0:
                _ratio = _inv_total_m / _available * 100
                if _inv_total_m <= _available:
                    st.success(f"✅ 積立 {_inv_total_m:.1f}万 / 投資可能額 {_available:.1f}万（{_ratio:.0f}%）")
                else:
                    st.error(f"⚠️ 積立 {_inv_total_m:.1f}万 が投資可能額 {_available:.1f}万 を超えています")
            else:
                st.info(f"💡 投資可能額 {_available:.1f}万円。資産タブで積立額を設定してください。")
        else:
            st.error(f"⚠️ 収支がマイナス。月 {abs(_available):.1f}万円 の赤字です。")

        if wife_current > 0:
            _wife_income_m = wife_current / 10_000 / 12
            _wife_surplus  = _wife_income_m - _spouse_living_m
            st.markdown("**👩 配偶者の収支**")
            st.markdown(
                f"| 項目 | 月額 |\n"
                f"|------|------|\n"
                f"| 手取り月収 | **{_wife_income_m:.1f}万円** |\n"
                f"| − 生活費（配偶者負担） | {_spouse_living_m:.1f}万円 |\n"
                f"| **余剰** | **{_wife_surplus:.1f}万円** |"
            )
            if _wife_surplus < 0:
                st.warning("⚠️ 配偶者収支がマイナス。生活費の自己負担を増やすか生活費を見直してください。")

    # ===================== シミュレーション =====================
    def get_income_for_age(age):
        monthly = current_monthly
        bonus   = current_bonus
        try:
            valid = milestones_df.dropna(subset=["あなたの年齢"])
            for _, row in valid.sort_values("あなたの年齢").iterrows():
                if age >= _sf(row["あなたの年齢"]):
                    g  = _sf(row["想定年収（万円）"]) * 10_000
                    bp = _sf(row["ボーナス割合（%）"]) / 100
                    if g > 0:
                        th = calc_takehome(g, spouse_deduct_amt, dep_count, ideco_annual_calc)
                        monthly = th * (1 - bp) / 12
                        bonus   = th * bp
        except Exception:
            pass
        return monthly, bonus

    def get_wife_income_for_age(age):
        w = wife_current
        try:
            wdf = wife_df.dropna(subset=["あなたの年齢"])
            for _, row in wdf.sort_values("あなたの年齢").iterrows():
                if age >= _sf(row["あなたの年齢"]):
                    v = _sf(row["配偶者の年収 手取り（万円）"])
                    if v > 0: w = v * 10_000
        except Exception:
            pass
        return w

    def get_side_income(age):
        total = 0
        for r in side_records:
            try:
                if _sf(r["開始年齢"]) <= age <= _sf(r["終了年齢"]):
                    total += _sf(r["年収（万円）"]) * 10_000
            except Exception:
                pass
        return total

    def get_invest_for_age(age):
        nisa_m = ideco_m = other_m = 0.0
        try:
            valid = invest_df.dropna(subset=["あなたの年齢"])
            for _, row in valid.sort_values("あなたの年齢").iterrows():
                if _sf(row["あなたの年齢"]) <= age:
                    nisa_m  = _sf(row["NISA（万円/月）"])  * 10_000
                    ideco_m = _sf(row["iDeCo（万円/月）"]) * 10_000
                    other_m = _sf(row["その他投資（万円/月）"]) * 10_000
        except Exception:
            pass
        return nisa_m, ideco_m, other_m

    def get_edu_cost(year):
        total = 0
        for ch in children:
            birth = ch["birth"]
            age   = year - birth
            if 0 <= age <= 2:   total += 17_800 * 12
            elif 3 <= age <= 5: pass
            elif 6 <= age <= 11: total += ELEM_COST[ch["elem"]]
            elif 12 <= age <= 14: total += MID_COST[ch["mid"]]
            elif 15 <= age <= 17: total += HIGH_COST[ch["high"]]
            elif 18 <= age <= 21: total += UNI_COST[ch["uni"]]
        return total

    def get_activity_cost(year):
        total = 0
        for ch in children:
            age = year - ch["birth"]
            if ch["act_start"] <= age <= ch["act_end"]:
                total += ch["act_cost"] * 12
        return total

    def get_insurance(age):
        total = ins_b_med + ins_b_other + ins_w_med + ins_w_other
        if age < ins_b_life_end: total += ins_b_life
        if age < ins_w_life_end: total += ins_w_life
        return total * 12

    def get_special_expense(age):
        total = 0
        try:
            for _, row in car_df.dropna(subset=["あなたの年齢"]).iterrows():
                if int(_sf(row["あなたの年齢"])) == age:
                    total += _sf(row["費用（万円）"]) * 10_000
        except Exception:
            pass
        try:
            for _, row in renov_df.dropna(subset=["あなたの年齢"]).iterrows():
                if int(_sf(row["あなたの年齢"])) == age:
                    total += _sf(row["費用（万円）"]) * 10_000
        except Exception:
            pass
        return total

    def simulate():
        years   = list(range(BASE_YEAR, BASE_YEAR + 55))
        nisa    = current_nisa
        ideco   = current_ideco
        deposit = current_deposit
        other   = current_other
        loan_b  = loan_balance_now
        results = []

        for year in years:
            age     = boss_age_now + (year - BASE_YEAR)
            retired = age >= fire_age
            yrs     = year - BASE_YEAR

            # 収入
            if not retired:
                monthly, bonus = get_income_for_age(age)
                wife_yr   = get_wife_income_for_age(age)
                side_yr   = get_side_income(age)
                ret_bonus = retirement_amt if age == retirement_age else 0
                income    = monthly * 12 + bonus + wife_yr + side_yr + ret_bonus
            else:
                income = 0

            # ローン
            loan_rate = loan_rate_future if age >= rate_change_age else loan_rate_now
            if loan_b > 0:
                interest  = loan_b * loan_rate
                principal = monthly_loan_pmt * 12 - interest
                loan_b    = max(0, loan_b - principal)
                loan_pmt_yr = monthly_loan_pmt * 12
            else:
                loan_pmt_yr = 0

            # 支出
            ins     = get_insurance(age)
            living  = monthly_living_base * 12 * (1 + inflation) ** yrs
            edu     = get_edu_cost(year)
            act     = get_activity_cost(year)
            special = get_special_expense(age)
            mgmt    = mgmt_fee * 12

            if not retired:
                expense = loan_pmt_yr + mgmt + ins + living + edu + act + special
            else:
                expense = fire_monthly * 12 * (1 + inflation) ** yrs + loan_pmt_yr + mgmt + special

            balance = income - expense

            # 積立
            _n, _i, _o = get_invest_for_age(age)
            invest_nisa  = _n * 12 if not retired else 0
            invest_ideco = _i * 12 if not retired else 0
            invest_other = _o * 12 if not retired else 0

            nisa   = nisa  * (1 + return_rate)  + invest_nisa
            ideco  = ideco * (1 + ideco_return) + invest_ideco
            other  = other * (1 + other_return) + invest_other

            surplus = balance - invest_nisa - invest_ideco - invest_other
            deposit = deposit + (surplus * 0.7 if surplus > 0 else surplus)

            net_assets = nisa + ideco + max(0, deposit) + other - loan_b

            results.append({
                "年度": year, "年齢": age, "FIRE": "🔥" if retired else "",
                "世帯収入": round(income), "住宅ローン": round(loan_pmt_yr),
                "管理費等": round(mgmt), "保険料": round(ins), "生活費": round(living),
                "教育費": round(edu), "習い事": round(act), "特別支出": round(special),
                "支出合計": round(expense), "年間収支": round(balance),
                "NISA残高": round(nisa), "iDeCo残高": round(ideco),
                "預金残高": round(deposit), "その他投資": round(other),
                "ローン残債": round(loan_b), "純資産": round(net_assets),
                "FIRE目標": round(fire_target),
            })
        return pd.DataFrame(results)

    # テーブルデータをsession_stateへ同期（保存時に利用）
    st.session_state["tbl_milestones"] = milestones_df.to_dict("records")
    st.session_state["tbl_wife"]       = wife_df.to_dict("records")
    st.session_state["tbl_invest"]     = invest_df.to_dict("records")
    st.session_state["tbl_car"]        = car_df.to_dict("records")
    st.session_state["tbl_renov"]      = renov_df.to_dict("records")

    df = simulate()

    # ===================== 結果 =====================
    with tab_result:
        st.subheader("📊 シミュレーション結果")

        fire_row    = df[df["年齢"] == fire_age]
        fire_assets = fire_row["純資産"].values[0] if not fire_row.empty else 0
        gap         = fire_assets - fire_target

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("FIRE目標年", f"{fire_year}年（{fire_age}歳）")
        k2.metric("FIRE時点の純資産", f"{fire_assets/10_000:.0f}万円")
        if gap >= 0:
            k3.metric("目標との差", f"+{gap/10_000:.0f}万円 ✅", delta="達成")
        else:
            k3.metric("目標との差", f"{gap/10_000:.0f}万円 ❌", delta="不足", delta_color="inverse")
        achieved = df[(df["純資産"] >= df["FIRE目標"]) & (df["FIRE"] == "")]["年齢"]
        if not achieved.empty:
            a_age = achieved.iloc[0]
            k4.metric("実際にFIRE可能", f"{a_age}歳（{BASE_YEAR + (a_age - boss_age_now)}年）")
        else:
            k4.metric("実際にFIRE可能", "期間内未達成")

        st.divider()

        # グラフ
        x_labels = [f"{r['年度']}<br>({r['年齢']}歳)" for _, r in df.iterrows()]
        fig = make_subplots(rows=3, cols=1,
            subplot_titles=("純資産推移（万円）", "収入 vs 支出（万円）", "支出内訳（万円）"),
            vertical_spacing=0.1, row_heights=[0.4, 0.3, 0.3])

        fig.add_trace(go.Scatter(x=x_labels, y=df["純資産"]/10_000, name="純資産",
            line=dict(color="#2196F3", width=3), fill="tozeroy",
            fillcolor="rgba(33,150,243,0.1)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=x_labels, y=df["NISA残高"]/10_000, name="NISA",
            line=dict(color="#4CAF50", width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=x_labels, y=df["FIRE目標"]/10_000, name="FIRE目標",
            line=dict(color="#F44336", width=2, dash="dash")), row=1, col=1)

        fire_idx = fire_age - boss_age_now
        if 0 <= fire_idx < len(x_labels):
            fig.add_vline(x=fire_idx, line_dash="dot", line_color="orange",
                          annotation_text="🔥FIRE", row=1, col=1)

        fig.add_trace(go.Bar(x=x_labels, y=df["世帯収入"]/10_000, name="世帯収入",
            marker_color="#66BB6A"), row=2, col=1)
        fig.add_trace(go.Bar(x=x_labels, y=df["支出合計"]/10_000, name="支出合計",
            marker_color="#EF5350"), row=2, col=1)

        fig.add_trace(go.Bar(x=x_labels, y=df["住宅ローン"]/10_000, name="ローン",
            marker_color="#FF7043"), row=3, col=1)
        fig.add_trace(go.Bar(x=x_labels, y=df["生活費"]/10_000, name="生活費",
            marker_color="#42A5F5"), row=3, col=1)
        fig.add_trace(go.Bar(x=x_labels, y=df["教育費"]/10_000, name="教育費",
            marker_color="#AB47BC"), row=3, col=1)
        fig.add_trace(go.Bar(x=x_labels, y=df["保険料"]/10_000, name="保険料",
            marker_color="#FFA726"), row=3, col=1)
        fig.add_trace(go.Bar(x=x_labels, y=df["特別支出"]/10_000, name="特別支出",
            marker_color="#26C6DA"), row=3, col=1)

        fig.update_layout(height=900, barmode="stack",
            legend=dict(orientation="h", y=1.03), margin=dict(t=60, b=20))
        fig.update_yaxes(title_text="万円")
        st.plotly_chart(fig, use_container_width=True)

        # 診断
        st.divider()
        d1, d2 = st.columns(2)
        with d1:
            if gap >= 0:
                st.success(f"✅ **{fire_age}歳FIREは達成可能です。**\n\n純資産 {fire_assets/10_000:.0f}万円 ＞ 目標 {fire_target/10_000:.0f}万円")
            else:
                remaining_months = max(1, (fire_age - boss_age_now) * 12)
                extra_pm = abs(gap) / remaining_months
                st.error(f"❌ **{abs(gap)/10_000:.0f}万円不足。**\n\n毎月 **+{extra_pm/10_000:.1f}万円** の積立増 or 収入増が必要です。")
        with d2:
            if not df[df["教育費"] > 0].empty:
                max_edu_row = df.loc[df["教育費"].idxmax()]
                st.info(f"📚 教育費のピーク: **{int(max_edu_row['年度'])}年（{int(max_edu_row['年齢'])}歳）** に **{max_edu_row['教育費']/10_000:.0f}万円/年**")
            loan_at_fire = fire_row["ローン残債"].values[0] if not fire_row.empty else 0
            if loan_at_fire > 0:
                st.warning(f"🏠 FIRE時点のローン残債: **{loan_at_fire/10_000:.0f}万円**")

        # SNSシェア
        st.divider()
        share_msg = (
            f"🔥 FIREシミュレーターで試算しました！\n"
            f"目標: {fire_age}歳FIRE / 必要資産: {fire_target/10_000:.0f}万円\n"
            f"{'✅ 達成ペース！' if gap >= 0 else f'❌ {abs(gap)/10_000:.0f}万円不足'}\n"
            f"#FIRE #資産形成 #FIREシミュレーター"
        )
        encoded_msg = urllib.parse.quote(share_msg)
        sc1, sc2 = st.columns(2)
        sc1.link_button("𝕏 (Twitter) でシェア",
            f"https://twitter.com/intent/tweet?text={encoded_msg}", use_container_width=True)
        sc2.link_button("📘 LINEでシェア",
            f"https://social-plugins.line.me/lineit/share?url=https://fire-simulator.streamlit.app&text={encoded_msg}",
            use_container_width=True)

        # 詳細テーブル
        with st.expander("📋 年度別詳細データ"):
            disp = df.copy()
            money_cols = ["世帯収入","住宅ローン","管理費等","保険料","生活費","教育費","習い事",
                          "特別支出","支出合計","年間収支","NISA残高","iDeCo残高","預金残高",
                          "その他投資","ローン残債","純資産","FIRE目標"]
            for col in money_cols:
                disp[col] = disp[col].apply(lambda x: f"{x/10_000:.0f}万")
            st.dataframe(disp.set_index("年度"), use_container_width=True)

# ===================== フッター（免責事項） =====================
st.divider()
st.caption(
    "⚠️ **免責事項** | "
    "本ツールは情報提供・教育目的のシミュレーションであり、特定の金融商品の購入を推奨するものではありません。"
    "計算結果は将来の運用成果を保証しません。投資判断はご自身の責任で行ってください。"
    "本ツールはユーザーの入力データをサーバーに保存しません。"
)
