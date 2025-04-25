import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
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
    df['月份'] = pd.to_datetime(df['下单时间']).dt.to_period('M')
    df['商品名称'] = df['商品名称'].fillna('未知商品')
    return df


def calculate_growth(df, group_cols):
    # 安全计算环比增长率
    try:
        # 确保有两个月份数据
        months = sorted(df['月份'].unique())
        if len(months) < 2:
            return pd.DataFrame()

        latest = months[-1]
        previous = months[-2]

        grouped = df.groupby([*group_cols, '月份'])['实付金额'].sum().unstack()
        grouped = grouped[[previous, latest]].copy()

        # 计算环比增长率
        grouped['环比'] = np.where(
            grouped[previous] > 0,
            (grouped[latest] - grouped[previous]) / grouped[previous],
            np.nan
        )
        return grouped.reset_index()
    except Exception as e:
        st.error(f"分析失败：{str(e)}")
        return pd.DataFrame()


def format_percentage(val):
    # 格式化百分比显示
    if pd.isnull(val):
        return "N/A"
    return f"{val:.2%}"


# 文件上传
uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file:
    try:
        # 数据准备
        raw_df = process_data(uploaded_file)
        main_df = raw_df[~raw_df['商品名称'].isin(SPECIAL_ITEMS)]
        special_df = raw_df[raw_df['商品名称'].isin(SPECIAL_ITEMS)]

        results = {}

        # ====== 完整维度分析 ======
        # 常规分析
        for dim_type in DIMENSION_CONFIG['常规分析']:
            cols = DIMENSION_CONFIG['常规分析'][dim_type]
            analysis = calculate_growth(main_df, cols)
            if not analysis.empty:
                results[dim_type] = analysis

        # 特殊分析
        if not special_df.empty:
            for dim_type in DIMENSION_CONFIG['特殊分析']:
                cols = DIMENSION_CONFIG['特殊分析'][dim_type]
                analysis = calculate_growth(special_df, cols)
                if not analysis.empty:
                    results[dim_type] = analysis

        # 结果展示
        if not results:
            st.warning("未生成有效分析结果")
            st.stop()

        for title, df in results.items():
            st.subheader(title)
            display_df = df.copy()
            # 格式化显示
            display_df['环比'] = display_df['环比'].apply(format_percentage)
            display_df.columns = [str(col) for col in display_df.columns]  # 处理Period类型列名
            st.dataframe(display_df)

        # 生成Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in results.items():
                export_df = data.copy()
                export_df.columns = [str(col) for col in export_df.columns]

                # 写入Excel
                export_df.to_excel(
                    writer,
                    sheet_name=sheet_name[:30],
                    index=False,
                    na_rep='N/A'
                )

                # 设置百分比格式
                ws = writer.sheets[sheet_name[:30]]
                if '环比' in export_df.columns:
                    col_idx = export_df.columns.get_loc('环比') + 1
                    for row in range(2, len(export_df) + 2):
                        cell = ws.cell(row=row, column=col_idx)
                        if pd.notnull(export_df.iloc[row - 2]['环比']):
                            cell.number_format = numbers.FORMAT_PERCENTAGE_00
                        else:
                            cell.value = 'N/A'

        st.download_button(
            "下载完整报告",
            output.getvalue(),
            "analysis_report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"处理失败：{str(e)}")
else:
    st.info("请上传Excel文件开始分析")
