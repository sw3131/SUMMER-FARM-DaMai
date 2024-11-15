import streamlit as st
import pandas as pd
import os
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 上传文件的目录
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def read_file(file_path):
    """根据文件扩展名读取文件，支持CSV和XLSX格式。"""
    _, ext = os.path.splitext(file_path)
    try:
        if ext.lower() == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='warn')
        elif ext.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
        return df
    except Exception as e:
        logger.error(f"读取文件 {file_path} 时出错: {e}")
        raise e

# Streamlit页面标题
st.title("文件上传与数据匹配工具")

# 上传文件
st.subheader("请上传基础文件和匹配文件")

base_file = st.file_uploader("上传基础文件 (CSV 或 Excel 格式)", type=['csv', 'xlsx', 'xls'])
match_file = st.file_uploader("上传匹配文件 (CSV 或 Excel 格式)", type=['csv', 'xlsx', 'xls'])

# 如果文件上传成功
if base_file and match_file:
    try:
        # 保存上传的文件
        base_path = os.path.join(UPLOAD_FOLDER, base_file.name)
        match_path = os.path.join(UPLOAD_FOLDER, match_file.name)

        with open(base_path, 'wb') as f:
            f.write(base_file.getbuffer())
        with open(match_path, 'wb') as f:
            f.write(match_file.getbuffer())

        # 读取文件
        base_df = read_file(base_path)
        match_df = read_file(match_path)

        # 检查必要的列是否存在
        required_columns_base = {'客户名称', '商品名称', 'm_id', 'BD', 'sku', '下单时间'}
        required_columns_match = {'商品名称'}

        missing_base = required_columns_base - set(base_df.columns)
        if missing_base:
            raise ValueError(f"基础表缺少必要的列: {', '.join(missing_base)}")

        missing_match = required_columns_match - set(match_df.columns)
        if missing_match:
            raise ValueError(f"匹配表缺少必要的列: {', '.join(missing_match)}")

        # 确保 '下单时间' 转换为 datetime 类型
        base_df['下单时间'] = pd.to_datetime(base_df['下单时间'], errors='coerce')

        # 移除无法解析的日期
        base_df = base_df.dropna(subset=['下单时间'])

        # 匹配数据
        matched_customers = base_df[base_df['商品名称'].isin(match_df['商品名称'])]

        # 选择需要的列
        matched_customers = matched_customers[['客户名称', '商品名称', 'm_id', 'BD', 'sku', '下单时间']]

        # 获取每个客户和商品的最后一次下单时间
        result_df = matched_customers.sort_values('下单时间').groupby(['客户名称', '商品名称']).agg({
            'm_id': 'first',
            'BD': 'first',
            'sku': 'first',
            '下单时间': 'max'
        }).reset_index()

        # 重命名 '下单时间' 为 '最后一次下单时间'
        result_df = result_df.rename(columns={'下单时间': '最后一次下单时间'})

        # 检查结果是否为空
        if result_df.empty:
            st.write("没有匹配到任何客户购买过指定的商品。")
        else:
            # 显示结果并提供下载链接
            st.write("匹配结果如下：")
            st.dataframe(result_df)

            # 保存结果
            result_path = os.path.join(UPLOAD_FOLDER, 'matched_results.csv')
            result_df.to_csv(result_path, index=False, encoding='utf-8-sig')

            # 提供下载链接
            st.download_button(
                label="下载匹配结果",
                data=open(result_path, 'rb').read(),
                file_name='matched_results.csv',
                mime='text/csv'
            )

    except Exception as e:
        logger.error(f"处理文件时出错: {e}")
        st.error(f"发生错误: {e}")
