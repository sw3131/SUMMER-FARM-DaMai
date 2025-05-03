import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="新版销售激励（鲜果）--大麦", layout="wide")
st.title("新版销售激励（鲜果）--大麦分析工具")


def load_data(file, name):
    """加载并校验数据（未修改）"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            st.error(f"错误：{name}仅支持.csv或.xlsx格式！")
            return None

        required_cols = {
            "原始数据表": ["订单日期", "商品描述", "商品名称", "一级类目", "客户名称", "sku_id", "bd_name", "销量"],
            "鲜果奖金表": ["关键词", "规格", "存量奖金", "增量奖金"]
        }[name]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"错误：{name}缺少必需列：{missing_cols}")
            return None

        if name == "原始数据表":
            df["订单日期"] = pd.to_datetime(df["订单日期"], format="%Y/%m/%d", errors="coerce")
            if df["订单日期"].isna().any():
                st.warning("注意：原始数据表中存在无法解析的订单日期，已过滤无效日期")
                df = df.dropna(subset=["订单日期"])

        return df

    except Exception as e:
        st.error(f"加载{name}失败：{str(e)}")
        return None


def main():
    st.subheader("1. 上传数据")
    raw_file = st.file_uploader("请上传原始数据表（.csv/.xlsx）", type=["csv", "xls", "xlsx"], key="raw")
    bonus_file = st.file_uploader("请上传鲜果奖金表（.csv/.xlsx）", type=["csv", "xls", "xlsx"], key="bonus")

    if not (raw_file and bonus_file):
        st.info("请先上传原始数据表和鲜果奖金表")
        return

    raw_df = load_data(raw_file, "原始数据表")
    bonus_df = load_data(bonus_file, "鲜果奖金表")
    if raw_df is None or bonus_df is None:
        return

    st.subheader("2. 设置分析参数")
    start_date, end_date = st.date_input(
        "选择奖金时间段（如2025-05-01至2025-05-31）",
        value=(datetime(2025, 5, 1), datetime(2025, 5, 31)),
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    )
    if start_date >= end_date:
        st.error("错误：结束日期需晚于开始日期")
        return

    if st.button("开始分析"):
        with st.spinner("分析中..."):
            # ---------------------- 数据处理核心逻辑 ----------------------
            # 预处理奖金表（清洗规格并重置索引）
            bonus_df = bonus_df.drop_duplicates().reset_index(drop=True)
            bonus_df["规格_clean"] = bonus_df["规格"].str.replace(r"\s+", "", regex=True)

            # 生成笛卡尔积（原始数据 × 奖金表）
            merged_df = raw_df.assign(key=1).merge(bonus_df.assign(key=1), on="key").drop(columns="key")
            merged_df = merged_df.drop_duplicates().reset_index(drop=True)

            # 关键词匹配
            merged_df["关键词匹配"] = merged_df.apply(
                lambda row: row["关键词"] in str(row["商品名称"]), axis=1
            )
            merged_df = merged_df[merged_df["关键词匹配"]].drop_duplicates().reset_index(drop=True)

            # 筛选一级类目为"鲜果"
            merged_df = merged_df[merged_df["一级类目"] == "鲜果"].drop_duplicates().reset_index(drop=True)

            # 预处理商品描述（清洗空格）
            merged_df["商品描述_clean"] = merged_df["商品描述"].str.replace(r"\s+", "", regex=True)

            # 规格匹配
            merged_df["规格匹配"] = merged_df.apply(
                lambda row: row["规格_clean"] in row["商品描述_clean"], axis=1
            )
            merged_df = merged_df.drop_duplicates().reset_index(drop=True)

            # 分离匹配和未匹配规格的记录
            matched = merged_df[merged_df["规格匹配"]].drop_duplicates().reset_index(drop=True)
            unmatched = merged_df[~merged_df["规格匹配"]].drop_duplicates().reset_index(drop=True)

            # 处理未匹配规格（合并"其他"规格）
            other_specs = bonus_df[bonus_df["规格"] == "其他"][["关键词", "规格", "存量奖金", "增量奖金"]]
            if not other_specs.empty:
                unmatched = unmatched[
                    ["订单日期", "商品描述", "商品名称", "一级类目", "客户名称", "sku_id", "bd_name", "销量", "关键词",
                     "规格_clean"]]
                unmatched = unmatched.merge(other_specs, on="关键词", how="left")
                unmatched = unmatched.dropna(subset=["规格"]).drop_duplicates().reset_index(drop=True)
                analysis_df = pd.concat([matched, unmatched], ignore_index=True)
            else:
                analysis_df = matched.reset_index(drop=True)

            if analysis_df.empty:
                st.warning("未匹配到任何符合条件的商品数据")
                return

            # 存量/增量判定
            base_start = start_date - timedelta(days=90)
            base_end = start_date - timedelta(days=1)

            bonus_period = analysis_df[
                (analysis_df["订单日期"] >= pd.Timestamp(start_date)) &
                (analysis_df["订单日期"] <= pd.Timestamp(end_date))
                ].drop_duplicates().reset_index(drop=True)

            base_period = analysis_df[
                (analysis_df["订单日期"] >= pd.Timestamp(base_start)) &
                (analysis_df["订单日期"] <= pd.Timestamp(base_end))
                ].drop_duplicates().reset_index(drop=True)

            bonus_period["唯一标识"] = bonus_period["客户名称"] + "_" + bonus_period["关键词"] + "_" + bonus_period[
                "商品名称"]
            bonus_period = bonus_period.drop_duplicates(subset=["唯一标识"]).reset_index(drop=True)

            base_period["唯一标识"] = base_period["客户名称"] + "_" + base_period["关键词"] + "_" + base_period[
                "商品名称"]
            base_period = base_period.drop_duplicates(subset=["唯一标识"]).reset_index(drop=True)

            existing_ids = set(base_period["唯一标识"].unique())
            bonus_period["类型"] = bonus_period["唯一标识"].apply(
                lambda x: "存量" if x in existing_ids else "增量"
            )

            # 奖金计算（保留两位小数）
            bonus_period["奖金金额"] = bonus_period.apply(
                lambda row: round(row["销量"] * row["存量奖金"], 2) if row["类型"] == "存量"
                else round(row["销量"] * row["增量奖金"], 2), axis=1
            )
            bonus_period = bonus_period.drop_duplicates().reset_index(drop=True)

            # 汇总明细（含商品描述）
            detail_cols = [
                "bd_name", "客户名称", "商品名称", "关键词", "规格", "商品描述",
                "销量", "类型", "奖金金额"
            ]
            detail_df = bonus_period[detail_cols].groupby(
                ["bd_name", "客户名称", "商品名称", "关键词", "规格", "商品描述", "类型"],
                as_index=False
            ).agg({"销量": "sum", "奖金金额": "sum"})
            detail_df["奖金金额"] = detail_df["奖金金额"].round(2)  # 明细保留两位小数
            detail_df = detail_df[detail_df["奖金金额"] > 0].drop_duplicates().reset_index(drop=True)

            # 按BD汇总奖金（新增"共计奖金"列）
            summary_df = detail_df.groupby("bd_name", as_index=False).agg(
                存量奖金总额=pd.NamedAgg(column="奖金金额",
                                         aggfunc=lambda x: x[detail_df["类型"] == "存量"].sum().round(2)),
                增量奖金总额=pd.NamedAgg(column="奖金金额",
                                         aggfunc=lambda x: x[detail_df["类型"] == "增量"].sum().round(2))
            )
            # 计算共计奖金（存量+增量）
            summary_df["共计奖金"] = (summary_df["存量奖金总额"] + summary_df["增量奖金总额"]).round(2)
            summary_df[["存量奖金总额", "增量奖金总额", "共计奖金"]] = summary_df[
                ["存量奖金总额", "增量奖金总额", "共计奖金"]].fillna(0)
            summary_df = summary_df.drop_duplicates().reset_index(drop=True)

            # 计算总计行（含共计奖金）
            total_increment = round(summary_df["增量奖金总额"].sum(), 2)
            total_stock = round(summary_df["存量奖金总额"].sum(), 2)
            total_total = round(total_stock + total_increment, 2)
            total_row = pd.DataFrame({
                "bd_name": ["总计"],
                "存量奖金总额": [total_stock],
                "增量奖金总额": [total_increment],
                "共计奖金": [total_total]
            })
            summary_with_total = pd.concat([summary_df, total_row], ignore_index=True)

            # ---------------------- 页面彩色化样式 ----------------------
            st.markdown("""
            <style>
                .stApp { background-color: #f5f7fa; }
                .stDataFrame th { background-color: #4a90e2; color: white; font-weight: bold; }
                .stDataFrame tr:nth-child(odd) { background-color: #f0f6ff; }
                .stDataFrame tr:nth-child(even) { background-color: #f8faff; }
                .total-row { background-color: #ffe6cc !important; font-weight: bold; }
                h2 { color: #2c3e50; border-bottom: 2px solid #4a90e2; padding-bottom: 8px; }
            </style>
            """, unsafe_allow_html=True)

            # ---------------------- 结果展示 ----------------------
            st.subheader("分析结果")

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("### 奖金统计（含共计）")
                # 高亮总计行，并设置列格式
                styled_summary = summary_with_total.style.apply(
                    lambda row: ['class: total-row' if row.name == len(summary_df) else '' for _ in row],
                    axis=1
                )
                st.dataframe(
                    styled_summary,
                    use_container_width=True,
                    column_config={
                        "存量奖金总额": st.column_config.NumberColumn("存量奖金（元）", format="￥%.2f"),
                        "增量奖金总额": st.column_config.NumberColumn("增量奖金（元）", format="￥%.2f"),
                        "共计奖金": st.column_config.NumberColumn("共计奖金（元）", format="￥%.2f", width="medium")
                    }
                )

            with col2:
                st.markdown("### 奖金明细（含商品描述）")
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    column_config={
                        "bd_name": st.column_config.TextColumn("BD姓名", width="small"),
                        "客户名称": st.column_config.TextColumn("客户名称", width="medium"),
                        "商品名称": st.column_config.TextColumn("商品名称", width="large"),
                        "商品描述": st.column_config.TextColumn("商品描述", width="large"),
                        "销量": st.column_config.NumberColumn("销量", format="%d"),
                        "类型": st.column_config.TextColumn("类型", width="small"),
                        "奖金金额": st.column_config.NumberColumn("奖金金额（元）", format="￥%.2f")
                    }
                )

            # 下载按钮
            st.markdown("---")
            download_col1, download_col2 = st.columns(2)
            with download_col1:
                st.download_button(
                    "下载明细数据",
                    detail_df.to_csv(index=False),
                    "奖金明细.csv",
                    "text/csv",
                    use_container_width=True
                )
            with download_col2:
                st.download_button(
                    "下载统计数据",
                    summary_with_total.to_csv(index=False),
                    "BD奖金统计.csv",
                    "text/csv",
                    use_container_width=True
                )


if __name__ == "__main__":
    main()