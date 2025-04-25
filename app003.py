import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from openpyxl.styles import numbers

st.title("大麦-数据与策略-月环比智能")
SPECIAL_ITEMS = ['安佳淡奶油', '爱乐薇(铁塔)淡奶油']


def clean_data(df):
    """数据清洗函数"""
    # 处理关键字段缺失值
    df = df.dropna(subset=['下单时间'], how='any').copy()
    df['商品名称'] = df['商品名称'].fillna('未知商品')
    df['BD'] = df['BD'].fillna('未知部门')
    df['客户名称'] = df['客户名称'].fillna('未知客户')
    df['实付金额'] = pd.to_numeric(df['实付金额'], errors='coerce').fillna(0)
    return df


def safe_groupby(df, group_cols, month_range=2):
    """安全分组函数"""
    try:
        # 确保至少两个月数据
        months = df['月份'].unique()
        if len(months) < month_range:
            return pd.DataFrame()

        latest = max(months)
        prev = sorted(months)[-month_range]

        # 分组计算
        grouped = df.groupby(group_cols + ['月份'])['实付金额'].sum().unstack()
        grouped = grouped[[prev, latest]].copy()

        # 计算环比（自动处理缺失值）
        grouped['环比'] = np.where(
            (grouped[prev] > 0) & (grouped[latest].notnull()),
            (grouped[latest] - grouped[prev]) / grouped[prev],
            np.nan
        )
        return grouped.reset_index()

    except Exception as e:
        st.error(f"分组分析失败：{str(e)}")
        return pd.DataFrame()


def format_display(df):
    """结果格式化"""
    df = df.copy()
    # 处理空值显示
    df = df.fillna({'环比': np.nan, '实付金额': 0})
    # 转换百分比显示
    if '环比' in df.columns:
        df['环比'] = df['环比'].apply(
            lambda x: f"{x:.2%}" if not pd.isnull(x) else "N/A"
        )
    # 转换月份格式
    for col in df.columns:
        if isinstance(col, pd.Period):
            df.rename(columns={col: str(col)}, inplace=True)
    return df


# 文件上传
uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file:
    try:
        # 读取并清洗数据
        raw_df = pd.read_excel(uploaded_file)
        raw_df = clean_data(raw_df)

        if '下单时间' not in raw_df.columns:
            raise ValueError("必须包含'下单时间'列")

        # 添加月份信息
        raw_df['月份'] = pd.to_datetime(raw_df['下单时间']).dt.to_period('M')

        # 分割数据集
        main_df = raw_df[~raw_df['商品名称'].isin(SPECIAL_ITEMS)]
        special_df = raw_df[raw_df['商品名称'].isin(SPECIAL_ITEMS)]

        results = {}

        # ====== 常规分析 ======
        # BD维度
        bd_analysis = safe_groupby(main_df, ['BD'])
        if not bd_analysis.empty:
            results['BD维度分析'] = bd_analysis

        # 客户维度
        customer_analysis = safe_groupby(main_df, ['客户名称', 'BD'])
        if not customer_analysis.empty:
            results['客户维度分析'] = customer_analysis

        # ====== 特殊分析 ======
        if not special_df.empty:
            special_analysis = safe_groupby(special_df, ['商品名称'])
            if not special_analysis.empty:
                results['特殊商品分析'] = special_analysis

        # ====== 结果展示 ======
        if not results:
            st.warning("没有可分析的数据，请检查输入文件")
            st.stop()

        for name, df in results.items():
            st.subheader(name)
            display_df = format_display(df)
            st.dataframe(display_df)

        # ====== 生成Excel ======
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in results.items():
                export_df = data.copy()
                # 处理月份列名
                export_df.columns = [str(col) for col in export_df.columns]
                # 处理空值
                export_df = export_df.fillna({'环比': np.nan})

                export_df.to_excel(
                    writer,
                    sheet_name=sheet_name[:30],
                    index=False,
                    na_rep='N/A'  # 关键设置：将NaN转为N/A
                )

                # 设置数字格式
                ws = writer.sheets[sheet_name[:30]]
                if '环比' in export_df.columns:
                    col_idx = export_df.columns.get_loc('环比') + 1
                    for row in range(2, len(export_df) + 2):
                        cell = ws.cell(row=row, column=col_idx)
                        if pd.notnull(export_df.iloc[row - 2]['环比']):
                            cell.number_format = numbers.FORMAT_PERCENTAGE_00
                        else:
                            cell.value = 'N/A'  # 显式设置单元格值

        st.download_button(
            "下载分析报告",
            output.getvalue(),
            file_name="analysis_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"系统错误：{str(e)}")
        st.stop()
else:
    st.info("请上传Excel文件开始分析")
