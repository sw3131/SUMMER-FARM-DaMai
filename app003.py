import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl.styles import numbers

st.title("大麦-数据与策略-月环比智能")
SPECIAL_ITEMS = ['安佳淡奶油', '爱乐薇(铁塔)淡奶油']

uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file is not None:
    raw_df = pd.read_excel(uploaded_file)

    if '下单时间' in raw_df.columns:
        # 数据预处理
        raw_df['月份'] = pd.to_datetime(raw_df['下单时间']).dt.to_period('M')
        latest_month = raw_df['月份'].max()

        # 数据分割
        main_df = raw_df[~raw_df['商品名称'].isin(SPECIAL_ITEMS)].copy()
        special_df = raw_df[raw_df['商品名称'].isin(SPECIAL_ITEMS)].copy()

        results = {}


        # ====== 通用分析函数 ======
        def analyze_data(source_df, group_cols, result_key):
            monthly = source_df.groupby([*group_cols, '月份'])['实付金额'].sum().unstack()
            if len(monthly.columns) >= 2:
                monthly['环比'] = (monthly[latest_month] - monthly[latest_month - 1]) / monthly[
                    latest_month - 1].replace(0, 1)
                results[result_key] = monthly.reset_index()


        # 常规分析
        analyze_data(main_df, ['BD'], 'BD维度分析')
        analyze_data(main_df, ['客户名称', 'BD'], '客户维度分析')
        [analyze_data(main_df, [dim], f'{dim}分析') for dim in ['主营类型', '商品分类', '订单类型']]

        # 特殊商品分析
        if not special_df.empty:
            analyze_data(special_df, ['商品名称'], '特殊商品分析')
            analyze_data(special_df, ['客户名称', 'BD'], '特殊商品客户分析')

        # 结果展示
        for title, df in results.items():
            st.subheader(title)
            df_display = df.copy()
            df_display['环比'] = df_display['环比'].apply(lambda x: f"{x:.2%}")
            st.dataframe(df_display)

        # ====== 修复Excel生成 ======
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in results.items():
                data.to_excel(writer, sheet_name=sheet_name[:31], index=False)

                # 获取工作表对象
                ws = writer.sheets[sheet_name[:31]]

                # 设置百分比格式
                if '环比' in data.columns:
                    col_idx = data.columns.get_loc('环比') + 1  # 列号从1开始
                    for row in range(2, len(data) + 2):  # 从第二行开始
                        cell = ws.cell(row=row, column=col_idx)
                        cell.number_format = numbers.FORMAT_PERCENTAGE_00

        st.download_button(
            "下载分析结果",
            output.getvalue(),
            "analysis_result.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("数据中缺少必要的时间列：'下单时间'")
else:
    st.info("请上传Excel文件开始分析")
