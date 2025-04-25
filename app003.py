import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from openpyxl.styles import numbers

st.title("大麦-数据与策略-月环比智能")
SPECIAL_ITEMS = ['安佳淡奶油', '爱乐薇(铁塔)淡奶油']

# 配置所有分析维度
DIMENSION_CONFIG = {
    '常规分析': {
        'BD维度': ['BD'],
        '客户维度': ['客户名称', 'BD'],
        '商品维度': ['商品名称'],
        '主营类型': ['主营类型'],
        '商品分类': ['商品分类'],
        '订单类型': ['订单类型']
    },
    '特殊分析': {
        '特殊商品': ['商品名称'],
        '特殊商品客户': ['客户名称', 'BD']
    }
}


def process_data(uploaded_file):
    # 读取并预处理数据
    df = pd.read_excel(uploaded_file)
    df = df.dropna(subset=['下单时间'])
    df['下单时间'] = pd.to_datetime(df['下单时间'])
    df['商品名称'] = df['商品名称'].fillna('未知商品')
    return df


def calculate_comparison(base_df, period1, period2, group_cols):
    """核心计算函数"""
    try:
        # 筛选时间段数据
        df_period1 = base_df[base_df['下单时间'].between(period1[0], period1[1])]
        df_period2 = base_df[base_df['下单时间'].between(period2[0], period2[1])]

        # 分组聚合
        group1 = df_period1.groupby(group_cols)['实付金额'].sum().reset_index()
        group2 = df_period2.groupby(group_cols)['实付金额'].sum().reset_index()

        # 合并数据
        merged = pd.merge(
            group1,
            group2,
            on=group_cols,
            how='outer',
            suffixes=('_期段1', '_期段2')
        ).fillna(0)

        # 计算环比
        merged['环比增长率'] = np.where(
            merged['实付金额_期段1'] != 0,
            (merged['实付金额_期段2'] - merged['实付金额_期段1']) / merged['实付金额_期段1'],
            np.inf  # 期段1为零时标记无限大
        )
        return merged
    except Exception as e:
        st.error(f"计算失败：{str(e)}")
        return pd.DataFrame()


# 文件上传
uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file:
    try:
        raw_df = process_data(uploaded_file)

        # 时间段选择
        st.sidebar.header("分析设置")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            p1_start = st.date_input("期段1开始日期", datetime(2024, 3, 1))
            p1_end = st.date_input("期段1结束日期", datetime(2024, 3, 20))
        with col2:
            p2_start = st.date_input("期段2开始日期", datetime(2024, 4, 1))
            p2_end = st.date_input("期段2结束日期", datetime(2024, 4, 19))

        # 转换日期类型
        period1 = (pd.to_datetime(p1_start), pd.to_datetime(p1_end))
        period2 = (pd.to_datetime(p2_start), pd.to_datetime(p2_end))

        # 验证时间逻辑
        if period1[0] >= period1[1] or period2[0] >= period2[1]:
            st.error("结束日期必须晚于开始日期")
            st.stop()
        if period2[0] <= period1[1]:
            st.warning("警告：分析期段存在时间重叠")

        # 数据分割
        main_df = raw_df[~raw_df['商品名称'].isin(SPECIAL_ITEMS)]
        special_df = raw_df[raw_df['商品名称'].isin(SPECIAL_ITEMS)]

        results = {}

        # ====== 常规分析 ======
        for dim_type in DIMENSION_CONFIG['常规分析']:
            group_cols = DIMENSION_CONFIG['常规分析'][dim_type]
            analysis = calculate_comparison(main_df, period1, period2, group_cols)
            if not analysis.empty:
                results[dim_type] = analysis

        # ====== 特殊分析 ======
        if not special_df.empty:
            for dim_type in DIMENSION_CONFIG['特殊分析']:
                group_cols = DIMENSION_CONFIG['特殊分析'][dim_type]
                analysis = calculate_comparison(special_df, period1, period2, group_cols)
                if not analysis.empty:
                    results[dim_type] = analysis

        # 结果展示
        if not results:
            st.warning("所选时间段无有效数据")
            st.stop()

        for title, df in results.items():
            st.subheader(f"{title} ({p1_start}~{p1_end} vs {p2_start}~{p2_end})")

            # 格式化显示
            display_df = df.copy()
            display_df['环比增长率'] = display_df['环比增长率'].apply(
                lambda x: "新增" if x == np.inf else f"{x:.2%}" if x != -np.inf else "N/A"
            )
            # 重命名列
            display_df.columns = [
                col.replace('_期段1', f' ({p1_start}-{p1_end})')
                .replace('_期段2', f' ({p2_start}-{p2_end})')
                for col in display_df.columns
            ]
            st.dataframe(display_df)

        # 生成Excel报告
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in results.items():
                export_df = data.copy()
                # 处理无限大值
                export_df['环比增长率'] = export_df['环比增长率'].replace(
                    [np.inf, -np.inf],
                    ['新增', 'N/A']
                )
                # 写入Excel
                export_df.to_excel(
                    writer,
                    sheet_name=sheet_name[:30],
                    index=False,
                    header=[
                        f"{col}期段1" if '_期段1' in col else
                        f"{col}期段2" if '_期段2' in col else
                        col
                        for col in export_df.columns
                    ]
                )

                # 设置百分比格式
                ws = writer.sheets[sheet_name[:30]]
                for col_idx, col_name in enumerate(export_df.columns, 1):
                    if '环比增长率' in col_name:
                        for row in range(2, len(export_df) + 2):
                            cell = ws.cell(row=row, column=col_idx)
                            if export_df.iloc[row - 2]['环比增长率'] not in ['新增', 'N/A']:
                                cell.number_format = numbers.FORMAT_PERCENTAGE_00

        st.download_button(
            "下载分析报告",
            output.getvalue(),
            file_name="custom_period_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"系统错误：{str(e)}")
else:
    st.info("请上传Excel文件开始分析")
