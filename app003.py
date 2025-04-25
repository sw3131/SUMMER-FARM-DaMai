import streamlit as st
import pandas as pd
from io import BytesIO

# 设置页面标题
st.title("大麦-数据与策略-月环比智能")

# 文件上传
uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file is not None:
    # 读取Excel文件
    df = pd.read_excel(uploaded_file)

    # 确保列名存在并转换日期格式
    if '下单时间' in df.columns:
        df['下单时间'] = pd.to_datetime(df['下单时间'])
        df['月份'] = df['下单时间'].dt.to_period('M')
        latest_month = df['月份'].max()

        results = {}

        # ---- 原分析逻辑保持不变 ----
        # 客户维度分析，包括BD列
        if 'BD' in df.columns:
            monthly_data_bd = df.groupby(['BD', '月份']).agg({'实付金额': 'sum'}).reset_index()
            comparison_bd = monthly_data_bd[monthly_data_bd['月份'].isin([latest_month, latest_month - 1])]

            if comparison_bd.shape[0] >= 2:
                pivot_table_bd = comparison_bd.pivot(index='BD', columns='月份', values='实付金额')
                pivot_table_bd['环比'] = (pivot_table_bd[latest_month] - pivot_table_bd[latest_month - 1]) / \
                                         pivot_table_bd[latest_month - 1] * 100
                pivot_table_bd = pivot_table_bd.reset_index().sort_values(by='环比', ascending=False)
                results['BD维度分析'] = pivot_table_bd

        # 客户维度分析
        if 'BD' in df.columns:
            monthly_data_customer = df.groupby(['客户名称', 'BD', '月份']).agg({'实付金额': 'sum'}).reset_index()
            comparison_customer = monthly_data_customer[
                monthly_data_customer['月份'].isin([latest_month, latest_month - 1])]

            if comparison_customer.shape[0] >= 2:
                pivot_table_customer = comparison_customer.pivot(index=['客户名称', 'BD'], columns='月份',
                                                                 values='实付金额')
                pivot_table_customer['环比'] = (pivot_table_customer[latest_month] - pivot_table_customer[
                    latest_month - 1]) / pivot_table_customer[latest_month - 1] * 100
                pivot_table_customer = pivot_table_customer.reset_index().sort_values(by='环比', ascending=False)
                results['客户维度分析'] = pivot_table_customer

        # 其他维度分析
        for column_name in ['商品名称', '主营类型', '商品分类', '订单类型']:
            if column_name in df.columns:
                monthly_data = df.groupby([column_name, '月份']).agg({'实付金额': 'sum'}).reset_index()
                comparison = monthly_data[monthly_data['月份'].isin([latest_month, latest_month - 1])]

                if comparison.shape[0] >= 2:
                    pivot_table = comparison.pivot(index=column_name, columns='月份', values='实付金额')
                    pivot_table['环比'] = (pivot_table[latest_month] - pivot_table[latest_month - 1]) / pivot_table[
                        latest_month - 1] * 100
                    pivot_table = pivot_table.reset_index().sort_values(by='环比', ascending=False)
                    results[column_name] = pivot_table

        # ---- 显示分析结果保持不变 ----
        for key, value in results.items():
            st.subheader(key)
            st.dataframe(value)

        # ====== 关键修复部分 ======
        # 将多个DataFrame写入Excel的不同sheet
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, df in results.items():
                # 处理无效的sheet名称字符
                clean_sheet_name = sheet_name.replace(':', '_').replace('\\', '_')[:31]  # 限制长度
                df.to_excel(writer, sheet_name=clean_sheet_name, index=False)

        # 获取字节数据
        excel_data = output.getvalue()

        # 下载按钮
        st.download_button(
            label="下载分析结果",
            data=excel_data,  # 直接使用字节流
            file_name="analysis_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Excel文件中缺少必要的列：'下单时间'")
else:
    st.info("请上传一个Excel文件")