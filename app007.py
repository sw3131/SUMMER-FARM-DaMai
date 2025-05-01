import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# 需要类目限制的关键词（精确匹配）
CATEGORY_RESTRICTED_KEYWORDS = {'草莓', '西瓜', '芒果', '芒'}


def check_dependencies():
    """检查必要依赖库是否安装"""
    try:
        import openpyxl
    except ImportError:
        st.error("缺少必要依赖库：openpyxl。请执行以下命令安装：")
        st.code("pip install openpyxl")
        st.stop()


def smart_product_filter(df, search_terms):
    """（保持原有函数不变）"""
    # ...（保持原函数内容不变）...


def main():
    check_dependencies()

    st.title("💡 新版佣金工具--大麦")
    st.sidebar.header("文件上传")

    # 文件上传组件（保持原样不变）
    # ...

    if st.sidebar.button("🚀 开始分析"):
        if not original_file:
            st.error("❌ 请先上传原始数据表")
            return

        try:
            # 读取原始数据（保持原样不变）
            # ...

            # 新增列名映射（在COLUMN_MAPPING中添加cust_id）
            COLUMN_MAPPING = {
                'sku_id': ['sku_id', 'sku'],
                'order_date': ['订单日期', '下单时间'],
                'BD': ['BD', 'bd_name'],
                '类目': ['类目', 'category'],
                'cust_id': ['cust_id', '客户ID']  # 新增cust_id列映射
            }

            # 自动识别列名（保持原逻辑）
            missing_columns = []
            for standard_name, possible_names in COLUMN_MAPPING.items():
                found = [n for n in possible_names if n in df.columns]
                if found:
                    if found[0] != standard_name:
                        df.rename(columns={found[0]: standard_name}, inplace=True)
                else:
                    if standard_name in ['类目', 'order_date']:  # cust_id不作为必填列
                        missing_columns.append(standard_name)

            # 结果列配置（修改result_columns）
            result_columns = ['cust_id', '客户名称', '商品名称', '类目', 'sku_id', 'order_date']
            if 'BD' in df.columns:
                result_columns.insert(5, 'BD')
            if 'm_id' in df.columns:
                result_columns.append('m_id')

            # 后续处理保持原样，但确保保留cust_id列
            latest_purchases = (
                df.sort_values('order_date')
                .drop_duplicates(['客户名称', '商品名称'], keep='last')
                .reset_index(drop=True)
            )

            inactive_df = latest_purchases[latest_purchases['order_date'] < threshold_date]

            # 确保输出包含cust_id
            inactive_df = inactive_df[result_columns].rename(
                columns={'order_date': '最后购买日期'}
            )

            # ...（剩余代码保持原样）...

        except Exception as e:
            st.error(f"❌ 处理过程中发生错误：{str(e)}")
            st.stop()


if __name__ == "__main__":
    main()
