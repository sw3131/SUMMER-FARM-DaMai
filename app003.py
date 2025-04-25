import streamlit as st
import pandas as pd
from io import BytesIO

# 设置页面标题
st.title("大麦-数据与策略-月环比智能")

# 定义需要特殊处理的商品
SPECIAL_ITEMS = ['安佳淡奶油', '爱乐薇(铁塔)淡奶油']

# 文件上传
uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

if uploaded_file is not None:
    # 读取原始数据
    raw_df = pd.read_excel(uploaded_file)

    if '下单时间' in raw_df.columns:
        # 预处理数据
        raw_df['月份'] = pd.to_datetime(raw_df['下单时间']).dt.to_period('M')
        latest_month = raw_df['月份'].max()

        # 创建两个数据集
        main_df = raw_df[~raw_df['商品名称'].isin(SPECIAL_ITEMS)]  # 常规分析用（排除特殊商品）
        special_df = raw_df[raw_df['商品名称'].isin(SPECIAL_ITEMS)]  # 特殊商品分析用

        results = {}

        # ====== 常规分析（排除特殊商品） ======
        # 客户维度分析
        if 'BD' in main_df.columns:
            # BD维度
            monthly_bd = main_df.groupby(['BD', '月份'])['实付金额'].sum().unstack()
            if len(monthly_bd.columns) >= 2:
                monthly_bd['环比'] = ((monthly_bd[latest_month] - monthly_bd[latest_month - 1])
                                      / monthly_bd[latest_month - 1].replace(0, 1)) * 100
                results['BD维度分析'] = monthly_bd.reset_index()

            # 客户+BD维度
            monthly_customer = main_df.groupby(['客户名称', 'BD', '月份'])['实付金额'].sum().unstack()
            if len(monthly_customer.columns) >= 2:
                monthly_customer['环比'] = ((monthly_customer[latest_month] - monthly_customer[latest_month - 1])
                                            / monthly_customer[latest_month - 1].replace(0, 1)) * 100
                results['客户维度分析'] = monthly_customer.reset_index()

        # 其他维度分析
        for dim in ['主营类型', '商品分类', '订单类型']:
            if dim in main_df.columns:
                monthly_dim = main_df.groupby([dim, '月份'])['实付金额'].sum().unstack()
                if len(monthly_dim.columns) >= 2:
                    monthly_dim['环比'] = ((monthly_dim[latest_month] - monthly_dim[latest_month - 1])
                                           / monthly_dim[latest_month - 1].replace(0, 1)) * 100
                    results[f'{dim}分析'] = monthly_dim.reset_index()

        # ====== 特殊商品分析 ======
        if not special_df.empty:
            # 整体分析
            monthly_special = special_df.groupby(['商品名称', '月份'])['实付金额'].sum().unstack()
            if len(monthly_special.columns) >= 2:
                monthly_special['环比'] = ((monthly_special[latest_month] - monthly_special[latest_month - 1])
                                           / monthly_special[latest_month - 1].replace(0, 1)) * 100
                results['特殊商品分析'] = monthly_special.reset_index()

            # 特殊商品的客户分析
            if 'BD' in special_df.columns:
                special_customer = special_df.groupby(['客户名称', 'BD', '月份'])['实付金额'].sum().unstack()
                if len(special_customer.columns) >= 2:
                    special_customer['环比'] = ((special_customer[latest_month] - special_customer[latest_month - 1])
                                                / special_customer[latest_month - 1].replace(0, 1)) * 100
                    results['特殊商品客户分析'] = special_customer.reset_index()

        # ====== 结果展示 ======
        for title, df in results.items():
            st.subheader(title)
            st.dataframe(df.sort_values('环比', ascending=False))

        # 生成Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, data in results.items():
                data.to_excel(writer,
                              sheet_name=sheet_name[:31],
                              index=False,
                              float_format="%.2f%%" if '环比' in data.columns else None)

        st.download_button(
            "下载分析结果",
            data=output.getvalue(),
            file_name="月环比分析报告.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("数据中缺少必要的时间列：'下单时间'")
else:
    st.info("请上传Excel文件开始分析")
