import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

def main():
    st.title("客户商品购买分析工具")

    st.sidebar.header("上传文件")

    # 上传原始数据表
    original_file = st.sidebar.file_uploader("上传原始数据表（Excel 或 CSV）", type=["xlsx", "xls", "csv"])

    # 上传客户匹配表（可选）
    matching_file = st.sidebar.file_uploader("上传客户匹配表（Excel 或 CSV）（可选）", type=["xlsx", "xls", "csv"])

    # 设置输出文件名
    output_filename = st.sidebar.text_input("输出文件名", "inactive_products.xlsx")

    # 自定义未购买天数阈值（可选）
    threshold_days = st.sidebar.number_input("未购买天数阈值", min_value=1, value=30)

    # 提供一个说明，告知用户客户匹配表是可选的
    st.sidebar.markdown("""
    **说明**：
    - **客户匹配表**为可选项。如果上传此表，分析将仅针对匹配表中的客户。
    - 如果不上传，分析将涵盖所有客户。
    """)

    if st.sidebar.button("开始分析"):
        if not original_file:
            st.error("请上传原始数据表。")
            return

        try:
            # 读取原始数据表
            if original_file.name.endswith(('.xlsx', '.xls')):
                original_df = pd.read_excel(original_file)
            else:
                original_df = pd.read_csv(original_file)

            # 定义可能的列名
            sku_columns = ['sku_id', 'sku']
            order_date_columns = ['订单日期', '下单时间']
            bd_columns = ['BD', 'bd_name']

            # 重命名 'sku' 或 'sku_id' 为 'sku_id'
            sku_present = [col for col in sku_columns if col in original_df.columns]
            if sku_present:
                original_df.rename(columns={sku_present[0]: 'sku_id'}, inplace=True)
                st.info(f"将列 '{sku_present[0]}' 重命名为 'sku_id'。")
            else:
                st.error("原始数据表缺少 'sku_id' 或 'sku' 列。")
                return

            # 重命名 '订单日期' 或 '下单时间' 为 'order_date'
            order_date_present = [col for col in order_date_columns if col in original_df.columns]
            if order_date_present:
                original_df.rename(columns={order_date_present[0]: 'order_date'}, inplace=True)
                st.info(f"将列 '{order_date_present[0]}' 重命名为 'order_date'。")
            else:
                st.error("原始数据表缺少 '订单日期' 或 '下单时间' 列。")
                return

            # 重命名 'bd_name' 为 'BD'（如果存在）
            bd_present = [col for col in bd_columns if col in original_df.columns]
            if bd_present:
                original_df.rename(columns={bd_present[0]: 'BD'}, inplace=True)
                st.info(f"将列 '{bd_present[0]}' 重命名为 'BD'。")
            else:
                st.warning("原始数据表中未找到 'BD' 或 'bd_name' 列。")

            # 确保必要的列存在
            required_original_columns = {'客户名称', '商品名称', 'sku_id', 'BD', 'order_date'}
            required_matching_columns = {'客户名称'}

            missing_original_cols = required_original_columns - set(original_df.columns)
            if missing_original_cols:
                st.error(f"原始数据表缺少以下必要列：{missing_original_cols}")
                return

            # 检查是否存在“m_id”列
            has_m_id = 'm_id' in original_df.columns
            if has_m_id:
                st.info("检测到 'm_id' 列，将包含在结果中。")
            else:
                st.info("未检测到 'm_id' 列，结果中将不包含该列。")

            # 读取并处理客户匹配表（如果上传）
            if matching_file:
                if matching_file.name.endswith(('.xlsx', '.xls')):
                    matching_df = pd.read_excel(matching_file)
                else:
                    matching_df = pd.read_csv(matching_file)

                # 确保匹配表中必要的列存在
                missing_matching_cols = required_matching_columns - set(matching_df.columns)
                if missing_matching_cols:
                    st.error(f"客户匹配表缺少以下必要列：{missing_matching_cols}")
                    return

                # 筛选需要匹配的客户
                matched_customers = original_df[original_df['客户名称'].isin(matching_df['客户名称'])]
                st.success("已根据客户匹配表筛选客户。")
            else:
                # 如果未上传匹配表，则使用所有客户
                matched_customers = original_df.copy()
                st.info("未上传客户匹配表，将分析所有客户的数据。")

            # 转换订单日期为datetime格式
            matched_customers['order_date'] = pd.to_datetime(matched_customers['order_date'], errors='coerce')

            # 检查日期转换是否有NaT值
            if matched_customers['order_date'].isnull().any():
                st.warning("部分订单日期格式不正确，已被转换为NaT。请检查数据。")

            # 获取当前日期
            current_date = datetime.now()

            # 计算阈值日期
            threshold_date = current_date - timedelta(days=int(threshold_days))

            # 获取每个客户-商品的最新订单日期以及对应的sku_id和BD
            latest_orders = matched_customers.sort_values('order_date').drop_duplicates(['客户名称', '商品名称'], keep='last')

            # 筛选超过阈值未购买的商品
            inactive_products = latest_orders[latest_orders['order_date'] < threshold_date]

            if inactive_products.empty:
                st.success(f"所有客户的商品在过去{threshold_days}天内都有购买记录。")
                return

            # 选择需要的列
            result_columns = ['客户名称', '商品名称', 'sku_id', 'BD', 'order_date']
            if has_m_id:
                result_columns.append('m_id')
            inactive_products = inactive_products[result_columns]

            # 重命名“order_date”以明确表示是最后一次购买时间
            inactive_products.rename(columns={'order_date': '最后一次购买日期'}, inplace=True)

            st.subheader("分析结果")
            st.dataframe(inactive_products)

            # 将 DataFrame 写入 BytesIO 对象
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                inactive_products.to_excel(writer, index=False, sheet_name='Inactive Products')
            processed_data = output.getvalue()

            # 提供下载链接
            st.download_button(
                label="下载结果",
                data=processed_data,
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except ImportError as ie:
            st.error(f"导入错误：{ie}. 请确保所有依赖项已正确安装。")
        except Exception as e:
            st.error(f"在处理文件时发生错误：{str(e)}")

if __name__ == "__main__":
    main()
