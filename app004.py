# app004.py

import streamlit as st
import pandas as pd
from io import BytesIO


def main():
    st.title("客户商品分析工具")
    st.write("""
    本工具允许您上传包含“客户名称”、“主营类型”、“商品名称”、“商品分类”等字段的表格，
    并分析在同一主营类型下，其他客户复购次数不低于10次但该客户未购买的商品及其分类。
    """)

    # 侧边栏：用户可以在此设置复购次数阈值
    st.sidebar.header("设置参数")
    min_purchase_count = st.sidebar.number_input("设置复购次数阈值", min_value=1, value=10)

    uploaded_file = st.file_uploader("上传您的表格文件（支持Excel和CSV）", type=["xlsx", "xls", "csv"])

    if uploaded_file is not None:
        # 判断文件类型并读取数据
        try:
            if uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                st.error("不支持的文件类型。请上传Excel或CSV文件。")
                return
        except Exception as e:
            st.error(f"读取文件时出错: {e}")
            return

        # 检查必要的列是否存在
        required_columns = ["客户名称", "主营类型", "商品名称", "商品分类"]
        if not all(column in df.columns for column in required_columns):
            st.error(f"上传的表格必须包含以下列: {required_columns}")
            return

        st.success("文件上传并读取成功！")
        st.subheader("原始数据预览")
        st.dataframe(df.head())

        # 数据预处理
        # 去除缺失值
        df = df.dropna(subset=required_columns)

        # 确保字段为字符串类型
        df["客户名称"] = df["客户名称"].astype(str)
        df["主营类型"] = df["主营类型"].astype(str)
        df["商品名称"] = df["商品名称"].astype(str)
        df["商品分类"] = df["商品分类"].astype(str)

        # 创建“商品名称”到“商品分类”的映射
        product_category_mapping = df[['商品名称', '商品分类']].drop_duplicates().set_index('商品名称')[
            '商品分类'].to_dict()

        # 计算每个“主营类型”下每个“商品名称”的总购买次数
        total_counts = df.groupby(['主营类型', '商品名称']).size().reset_index(name='purchase_count')

        # 筛选出购买次数不低于用户设定阈值的商品
        popular_products = total_counts[total_counts['purchase_count'] >= min_purchase_count]

        # 创建一个字典：主营类型 -> set(购买次数>=阈值的商品)
        main_type_popular_products = popular_products.groupby('主营类型')['商品名称'].apply(set).to_dict()

        # 按“主营类型”和“客户名称”分组，收集每个客户购买的商品集合
        grouped = df.groupby(['主营类型', '客户名称'])['商品名称'].apply(set).reset_index()

        # 创建一个字典：主营类型 -> {客户名称: set(商品)}
        main_type_dict = {}
        for _, row in grouped.iterrows():
            main_type = row['主营类型']
            customer = row['客户名称']
            products = row['商品名称']
            if main_type not in main_type_dict:
                main_type_dict[main_type] = {}
            main_type_dict[main_type][customer] = products

        # 分析每个客户未购买但同主营类型下购买次数>=阈值的商品及其分类
        result = []

        for main_type, customers in main_type_dict.items():
            # 获取该主营类型下购买次数>=阈值的所有商品
            popular_products_set = main_type_popular_products.get(main_type, set())

            for customer, products in customers.items():
                # 计算未购买的商品
                missing_products = popular_products_set - products
                if missing_products:
                    for product in sorted(missing_products):
                        category = product_category_mapping.get(product, "未知分类")
                        result.append({
                            "客户名称": customer,
                            "主营类型": main_type,
                            "未购买的商品": product,  # 修改此行，移除前缀
                            "商品分类": category
                        })
                else:
                    result.append({
                        "客户名称": customer,
                        "主营类型": main_type,
                        "未购买的商品": "无",
                        "商品分类": ""
                    })

        result_df = pd.DataFrame(result)

        st.subheader("分析结果")
        st.dataframe(result_df)

        # 提供下载按钮
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='分析结果')
            processed_data = output.getvalue()
            return processed_data

        excel_data = to_excel(result_df)

        st.download_button(
            label="下载结果为Excel文件",
            data=excel_data,
            file_name='分析结果.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


if __name__ == "__main__":
    main()
