import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO


def calculate_commission():
    st.set_page_config(
        page_title="新版销售激励--大麦",
        page_icon="💰",
        layout="wide"
    )

    # ================== 界面样式优化 ==================
    st.markdown("""
    <style>
    .css-18e3th9 {padding: 2rem 1rem 10rem;}
    .reportview-container .main .block-container {max-width: 1200px;}
    .st-bq {border-radius: 8px;}
    .st-cb {background-color: #f0f2f6;}
    .stButton>button {border-radius: 4px; transition: all 0.3s;}
    .stButton>button:hover {transform: scale(1.05);}
    .stProgress > div > div > div {background-color: #2196f3;}
    </style>
    """, unsafe_allow_html=True)

    st.title("💰 新版销售激励(标品)计算--大麦")
    st.caption("v2.0 | 大麦数智化平台")

    # ================== 分步操作界面 ==================
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1.expander("📤 1. 上传数据", expanded=True):
            raw_file = st.file_uploader("原始数据表", type=["xlsx", "csv"], key="raw")
            bonus_file = st.file_uploader("标品奖金表", type=["xlsx", "csv"], key="bonus")

        with col2.expander("📅 2. 设置周期", expanded=True):
            start_date = st.date_input("奖金开始日期", value=datetime(2025, 5, 2))
            end_date = st.date_input("奖金结束日期", value=datetime(2025, 5, 31))

        with col3.expander("💡 使用说明"):
            st.markdown("""
            1. 原始数据表需包含：
               - 订单日期、商品描述、商品名称、SKU等
            2. 标品奖金表需包含：
               - 商品名称、SKU、存量/增量佣金
            3. 日期范围不超过31天
            """)

    if st.button("🚀 开始智能分析", use_container_width=True, type="primary"):
        if not raw_file or not bonus_file:
            st.error("❗ 请先上传两个数据文件！")
            return

        with st.spinner('⏳ 数据解析中...'):
            try:
                # ================== 数据处理逻辑 ==================
                raw_df = pd.read_excel(raw_file) if raw_file.name.endswith('.xlsx') else pd.read_csv(raw_file)
                bonus_df = pd.read_excel(bonus_file) if bonus_file.name.endswith('.xlsx') else pd.read_csv(bonus_file)

                # 数据校验与预处理
                raw_df['sku_id'] = pd.to_numeric(raw_df['sku_id'], errors='coerce')
                bonus_df['SKU'] = pd.to_numeric(bonus_df['SKU'], errors='coerce')
                merged_df = pd.merge(raw_df, bonus_df, left_on=['商品名称', 'sku_id'], right_on=['商品名称', 'SKU'])

                # 日期处理与筛选
                merged_df['订单日期'] = pd.to_datetime(merged_df['订单日期'], format='%Y/%m/%d', errors='coerce')
                start_dt = pd.Timestamp(start_date)
                end_dt = pd.Timestamp(end_date)
                period_mask = (merged_df['订单日期'] >= start_dt) & (merged_df['订单日期'] <= end_dt)
                period_orders = merged_df[period_mask].copy()

                # 存量/增量判断
                lookback_start = start_dt - timedelta(days=90)

                def check_history(row):
                    client_mask = (merged_df['客户名称'] == row['客户名称']) & \
                                  (merged_df['商品名称'] == row['商品名称']) & \
                                  (merged_df['订单日期'] >= lookback_start) & \
                                  (merged_df['订单日期'] < start_dt)
                    return '存量' if any(client_mask) else '增量'

                period_orders['类型'] = period_orders.apply(check_history, axis=1)

                # 奖金计算
                period_orders['奖金'] = period_orders.apply(
                    lambda x: x['销量'] * x['存量佣金'] if x['类型'] == '存量' else x['销量'] * x['增量佣金'], axis=1)

                # ================== 结果生成 ==================
                # 汇总统计（增加总计行）
                summary_df = period_orders.groupby('bd_name').agg(
                    总奖金=('奖金', 'sum'),
                    存量奖金=('奖金', lambda x: x[period_orders.loc[x.index, '类型'] == '存量'].sum()),
                    增量奖金=('奖金', lambda x: x[period_orders.loc[x.index, '类型'] == '增量'].sum())
                ).reset_index()

                # 添加总计行
                total = summary_df.sum(numeric_only=True)
                total['bd_name'] = '总计'
                summary_df = pd.concat([summary_df, pd.DataFrame([total])], ignore_index=True)

                # 明细数据
                detail_df = period_orders[[
                    '客户名称', '商品名称', '商品描述', 'sku_id',
                    'bd_name', '销量', '奖金', '类型'
                ]]

                # ================== 结果展示 ==================
                st.success("✅ 分析完成！")

                # 关键指标卡
                col1, col2, col3 = st.columns(3)
                col1.metric("总奖金金额", f"¥{summary_df['总奖金'].iloc[-1]:,.2f}")
                col2.metric("涉及BD人数", f"{len(summary_df) - 1} 人")
                col3.metric("总订单数", f"{len(detail_df)} 笔")

                # 双栏布局
                tab1, tab2 = st.tabs(["📊 奖金汇总", "📋 明细数据"])

                with tab1:
                    st.dataframe(
                        summary_df.style.format({
                            '总奖金': '¥{:,.2f}',
                            '存量奖金': '¥{:,.2f}',
                            '增量奖金': '¥{:,.2f}'
                        }, na_rep="-"),
                        use_container_width=True,
                        height=400
                    )

                with tab2:
                    st.dataframe(
                        detail_df.style.format({
                            '销量': '{:,}',
                            '奖金': '¥{:,.2f}'
                        }),
                        use_container_width=True,
                        height=600
                    )

                # ================== 整合下载功能 ==================
                with BytesIO() as output:
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        summary_df.to_excel(writer, sheet_name='奖金汇总', index=False)
                        detail_df.to_excel(writer, sheet_name='明细数据', index=False)
                    output.seek(0)

                    st.download_button(
                        label="📥 下载完整分析报告 (Excel)",
                        data=output,
                        file_name=f'销售激励分析_{start_date}至{end_date}.xlsx',
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"❌ 处理错误：{str(e)}")
                st.error("常见问题：\n1. 日期格式错误\n2. SKU匹配失败\n3. 数值列包含非数字字符")


if __name__ == "__main__":
    calculate_commission()
