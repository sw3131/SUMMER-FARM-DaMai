import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from openpyxl.styles import numbers

st.title("大麦-数据与策略-月环比智能")
SPECIAL_ITEMS = ['安佳淡奶油', '爱乐薇(铁塔)淡奶油']

# 配置需要分析的维度
DIMENSIONS = {
    '常规分析': {
        'BD维度分析': ['BD'],
        '客户维度分析': ['客户名称', 'BD'],
        '主营类型分析': ['主营类型'],
        '商品分类分析': ['商品分类'],
        '订单类型分析': ['订单类型']
    },
    '特殊分析': {
        '特殊商品分析': ['商品名称'],
        '特殊商品客户分析': ['客户名称', 'BD']
    }
}


def safe_analyze(source_df, group_cols, months_needed=2):
    """安全分析函数，包含错误处理"""
    try:
        # 检查必要列是否存在
        missing_cols = [col for col in group_cols if col not in source_df.columns]
        if missing_cols:
            raise ValueError(f"缺少必要列：{missing_cols}")

        if source_df.empty:
            return pd.DataFrame()

        # 获取有效月份
        valid_months = source_df['月份'].unique()
        if len(valid_months) < months_needed:
            raise ValueError("月份数据不足")

        # 执行分组计算
        monthly = source_df.groupby([*group_cols, '月份'])['实付金额'].sum().unstack()
        latest = max(valid_months)
        prev = sorted(valid_months)[-2]  # 确保取到前一个有效月份

        # 计算环比（自动处理零值）
        monthly['环比'] = np.where(
            monthly[prev] > 0,
            (monthly[latest] - monthly[prev]) / monthly[prev],
            np.nan  # 零基期标记为缺失值
        )
        return monthly.reset_index().replace([np.inf, -np.inf], np.nan)

    except Exception as e:
        st.error(f"分析失败：{str(e)}")
        return pd.DataFrame()


uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if '下单时间' not in df.columns:
        st.error("缺少关键列：下单时间")
        st.stop()

    # 预处理数据
    df['月份'] = pd.to_datetime(df['下单时间']).dt.to_period('M')
    df['商品名称'] = df['商品名称'].fillna('未知商品')  # 处理空值

    # 分离数据集
    main_df = df[~df['商品名称'].isin(SPECIAL_ITEMS)].copy()
    special_df = df[df['商品名称'].isin(SPECIAL_ITEMS)].copy()

    results = {}

    # 执行常规分析
    for name, cols in DIMENSIONS['常规分析'].items():
        analysis_df = safe_analyze(main_df, cols)
        if not analysis_df.empty:
            results[name] = analysis_df

    # 执行特殊分析
    if not special_df.empty:
        for name, cols in DIMENSIONS['特殊分析'].items():
            analysis_df = safe_analyze(special_df, cols)
            if not analysis_df.empty:
                results[name] = analysis_df

    # 展示结果
    if results:
        for name, df in results.items():
            st.subheader(name)
            display_df = df.copy()
            # 处理空值显示
            display_df['环比'] = display_df['环比'].apply(
                lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A"
            )
            st.dataframe(display_df)

        # 生成Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for name, data in results.items():
                data.to_excel(writer, sheet_name=name[:30], index=False)
                ws = writer.sheets[name[:30]]

                # 设置百分比格式
                if '环比' in data.columns:
                    col_idx = data.columns.get_loc('环比') + 1
                    for row in range(2, len(data) + 2):
                        cell = ws.cell(row=row, column=col_idx)
                        if pd.notnull(data.iloc[row - 2]['环比']):
                            cell.number_format = numbers.FORMAT_PERCENTAGE_00
                        else:
                            cell.value = "N/A"

        st.download_button(
            "下载完整报告",
            output.getvalue(),
            "analysis_report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("未生成有效分析结果，请检查输入数据")

else:
    st.info("请上传Excel文件开始分析")
