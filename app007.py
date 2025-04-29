import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO


def check_dependencies():
    """检查必要依赖库是否安装"""
    try:
        import openpyxl
    except ImportError:
        st.error("缺少必要依赖库：openpyxl。请执行以下命令安装：")
        st.code("pip install openpyxl")
        st.stop()


def main():
    # 初始化依赖检查
    check_dependencies()

    st.title("📊 大麦团队-新版佣金工具")
    st.sidebar.header("文件上传")

    # 文件上传组件
    original_file = st.sidebar.file_uploader(
        "1. 上传原始数据表 (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key="original"
    )

    customer_matching_file = st.sidebar.file_uploader(
        "2. 上传客户匹配表 (可选)",
        type=["xlsx", "xls", "csv"],
        key="customer"
    )

    product_matching_file = st.sidebar.file_uploader(
        "3. 上传商品匹配表 (可选)",
        type=["xlsx", "xls", "csv"],
        key="product"
    )

    # 参数设置
    st.sidebar.header("分析设置")
    threshold_days = st.sidebar.number_input(
        "未购买天数阈值",
        min_value=1,
        value=30,
        help="设置判断商品不活跃的未购买天数"
    )
    output_filename = st.sidebar.text_input(
        "输出文件名",
        "分析结果-大麦.xlsx",
        help="自定义结果文件的名称"
    )

    # 操作按钮
    if st.sidebar.button("🚀 开始分析", help="点击开始数据分析"):
        if not original_file:
            st.error("❌ 请先上传原始数据表")
            return

        try:
            # 读取原始数据
            if original_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(original_file)
            else:
                df = pd.read_csv(original_file)

            # 列名标准化处理
            COLUMN_MAPPING = {
                'sku_id': ['sku_id', 'sku'],
                'order_date': ['订单日期', '下单时间','时间'],
                'BD': ['BD', 'bd_name']
            }

            # 自动识别列名
            for standard_name, possible_names in COLUMN_MAPPING.items():
                found = [n for n in possible_names if n in df.columns]
                if found:
                    if found[0] != standard_name:
                        df.rename(columns={found[0]: standard_name}, inplace=True)
                else:
                    if standard_name == 'order_date':
                        st.error(f"❌ 缺少必要日期列，请确保包含以下名称之一：{possible_names}")
                        return

            # 客户匹配处理
            if customer_matching_file:
                customer_df = pd.read_excel(customer_matching_file) if customer_matching_file.name.endswith(
                    ('.xlsx', '.xls')) else pd.read_csv(customer_matching_file)
                if '客户名称' not in customer_df.columns:
                    st.error("⛔ 客户匹配表必须包含「客户名称」列")
                    return
                df = df[df['客户名称'].isin(customer_df['客户名称'])]
                st.success(f"✅ 已匹配 {len(customer_df)} 个客户")

            # 商品匹配处理
            if product_matching_file:
                product_df = pd.read_excel(product_matching_file) if product_matching_file.name.endswith(
                    ('.xlsx', '.xls')) else pd.read_csv(product_matching_file)
                if '商品名称' not in product_df.columns:
                    st.error("⛔ 商品匹配表必须包含「商品名称」列")
                    return
                df = df[df['商品名称'].isin(product_df['商品名称'])]
                st.success(f"✅ 已匹配 {len(product_df)} 个商品")

            # 日期处理
            df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
            if df['order_date'].isnull().any():
                invalid_count = df['order_date'].isnull().sum()
                st.warning(f"⚠️ 发现 {invalid_count} 条无效日期记录，已自动排除")

            # 计算阈值日期
            threshold_date = datetime.now() - timedelta(days=threshold_days)

            # 获取最新购买记录
            latest_purchases = (
                df.sort_values('order_date')
                .drop_duplicates(['客户名称', '商品名称'], keep='last')
                .reset_index(drop=True)
            )

            # 筛选不活跃商品
            inactive_df = latest_purchases[latest_purchases['order_date'] < threshold_date]

            if inactive_df.empty:
                st.balloons()
                st.success(f"🎉 所有商品在过去 {threshold_days} 天都有购买记录")
                return

            # 结果处理
            result_columns = ['客户名称', '商品名称', 'sku_id', 'order_date']
            if 'BD' in df.columns:
                result_columns.insert(3, 'BD')
            if 'm_id' in df.columns:
                result_columns.append('m_id')

            inactive_df = inactive_df[result_columns].rename(
                columns={'order_date': '最后购买日期'}
            )

            # 显示结果
            st.subheader(f"📑 分析结果（共 {len(inactive_df)} 条记录）")
            st.dataframe(
                inactive_df,
                column_config={
                    "最后购买日期": st.column_config.DatetimeColumn(
                        format="YYYY-MM-DD"
                    )
                },
                height=400
            )

            # 生成下载文件
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                inactive_df.to_excel(writer, index=False, sheet_name='不活跃商品')

            st.download_button(
                label="⬇️ 下载分析结果",
                data=output.getvalue(),
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="点击下载Excel格式的分析结果"
            )

        except Exception as e:
            st.error(f"❌ 处理过程中发生错误：{str(e)}")
            st.stop()


if __name__ == "__main__":
    main()
