import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# 设置页面配置
st.set_page_config(
    page_title="生鲜食材报价工具-鑫旺科技",
    page_icon="🛒",
    layout="wide"
)

# 添加标题和说明
st.title("🛒 生鲜食材报价工具-鑫旺科技")
st.write("这个工具可以帮助您根据成本价格和毛利率自动计算客户报价，并预测综合毛利率。开发-大麦")
st.divider()

# 初始化会话状态
if 'cost_price_df' not in st.session_state:
    st.session_state.cost_price_df = None
if 'quote_file_df' not in st.session_state:
    st.session_state.quote_file_df = None
if 'margin_df' not in st.session_state:
    st.session_state.margin_df = None
if 'customer_type' not in st.session_state:
    st.session_state.customer_type = None
if 'quote_results' not in st.session_state:
    st.session_state.quote_results = None
if 'avg_gross_margin' not in st.session_state:
    st.session_state.avg_gross_margin = None
if 'has_quantity' not in st.session_state:
    st.session_state.has_quantity = False


@st.cache_data
def clean_product_name(name):
    """清理商品名称，移除括号及其中的内容"""
    if pd.isna(name):
        return ""
    # 移除括号及其中的内容
    cleaned = re.sub(r'\(.*?\)', '', str(name))
    # 移除多余的空格
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.lower()  # 转为小写，方便匹配


@st.cache_data
def fuzzy_match_product(quote_name, cost_names, threshold=80):
    """模糊匹配商品名称"""
    if not cost_names or len(cost_names) == 0:
        return None, 0

    # 清理报价表中的商品名称
    cleaned_quote_name = clean_product_name(quote_name)

    # 如果清理后为空，直接返回None
    if not cleaned_quote_name:
        return None, 0

    # 在成本表中查找最匹配的商品
    match = process.extractOne(cleaned_quote_name, cost_names)

    if match[1] >= threshold:
        return match[0], match[1]
    return None, 0


def load_data(file):
    """加载不同格式的表格文件"""
    file_ext = os.path.splitext(file.name)[1].lower()

    try:
        if file_ext == '.xlsx':
            return pd.read_excel(file)
        elif file_ext == '.csv':
            return pd.read_csv(file)
        elif file_ext == '.xls':
            return pd.read_excel(file)
        else:
            st.error(f"不支持的文件格式: {file_ext}")
            return None
    except Exception as e:
        st.error(f"文件读取错误: {str(e)}")
        return None


def calculate_quote():
    """计算报价和综合毛利率"""
    # 检查是否所有必要数据都已加载
    if (st.session_state.cost_price_df is None or
            st.session_state.quote_file_df is None or
            st.session_state.margin_df is None or
            st.session_state.customer_type is None):
        st.warning("请先完成所有必要的文件上传和选项选择")
        return

    # 数据预处理
    cost_price_df = st.session_state.cost_price_df.copy()
    quote_file_df = st.session_state.quote_file_df.copy()
    margin_df = st.session_state.margin_df.copy()

    # 检查必要的列是否存在
    required_cost_columns = ['商品名称', '商品分类', '成本价']
    if not all(col in cost_price_df.columns for col in required_cost_columns):
        st.error("成本价格表缺少必要的列，请确保包含：商品名称、商品分类、成本价")
        return

    required_margin_columns = ['序号', '商品分类', '线上客户毛利率', '线下客户毛利率']
    if not all(col in margin_df.columns for col in required_margin_columns):
        st.error("总部毛利率参考表缺少必要的列，请确保包含：序号、商品分类、线上客户毛利率、线下客户毛利率")
        return

    if '商品名称' not in quote_file_df.columns:
        st.error("待报价文件缺少必要的列：商品名称")
        return

    # 检查是否有待报价文件包含数量列
    has_quantity = '数量' in quote_file_df.columns
    st.session_state.has_quantity = has_quantity

    # 根据客户类型选择相应的毛利率列
    margin_column = '线上客户毛利率' if st.session_state.customer_type == '线上客户' else '线下客户毛利率'

    # 将毛利率从百分比转换为小数（如果需要）
    if margin_df[margin_column].dtype == object:
        margin_df[margin_column] = margin_df[margin_column].str.replace('%', '').astype(float) / 100
    elif margin_df[margin_column].max() > 1:  # 如果是百分比形式的整数
        margin_df[margin_column] = margin_df[margin_column] / 100

    # 准备成本表中的商品名称用于模糊匹配
    cost_price_df['cleaned_name'] = cost_price_df['商品名称'].apply(clean_product_name)
    cost_names = cost_price_df['cleaned_name'].tolist()

    # 创建结果列表
    results = []

    # 遍历待报价文件中的每个商品
    for _, row in quote_file_df.iterrows():
        product_name = row['商品名称']
        quantity = row['数量'] if has_quantity else 1

        # 进行模糊匹配
        matched_name, score = fuzzy_match_product(product_name, cost_names)

        if matched_name:
            # 找到匹配的成本记录
            cost_row = cost_price_df[cost_price_df['cleaned_name'] == matched_name].iloc[0]

            # 找到对应的毛利率
            margin_row = margin_df[margin_df['商品分类'] == cost_row['商品分类']]
            if not margin_row.empty:
                margin_rate = margin_row.iloc[0][margin_column]
                if margin_rate < 1:  # 确保毛利率是小数形式且小于1
                    quote_price = cost_row['成本价'] / (1 - margin_rate)
                    total = round(quote_price * quantity, 2) if has_quantity else "无"
                else:
                    margin_rate = "无"
                    quote_price = "无"
                    total = "无"
            else:
                margin_rate = "无"
                quote_price = "无"
                total = "无"

            results.append({
                '原始商品名称': product_name,
                '匹配商品名称': cost_row['商品名称'],
                '匹配度': f"{score}%",
                '商品分类': cost_row['商品分类'],
                '成本价': cost_row['成本价'],
                margin_column: round(margin_rate * 100, 2) if margin_rate != "无" and isinstance(margin_rate,
                                                                                                 float) else margin_rate,
                '报价': round(quote_price, 2) if quote_price != "无" else "无",
                '数量': quantity if has_quantity else "无",
                '总计': total
            })
        else:
            # 未找到匹配项
            results.append({
                '原始商品名称': product_name,
                '匹配商品名称': "无",
                '匹配度': "0%",
                '商品分类': "无",
                '成本价': "无",
                margin_column: "无",
                '报价': "无",
                '数量': quantity if has_quantity else "无",
                '总计': "无"
            })

    # 创建结果DataFrame
    quote_df = pd.DataFrame(results)

    # 计算预测综合毛利率 (考虑数量因素)
    if has_quantity and not quote_df.empty:
        # 创建一个临时DataFrame来计算加权平均毛利率
        temp_df = quote_df[quote_df['商品分类'] != "无"].copy()

        if not temp_df.empty:
            # 将毛利率转换为数值
            temp_df[margin_column] = pd.to_numeric(temp_df[margin_column], errors='coerce')
            temp_df = temp_df.dropna(subset=[margin_column])

            if not temp_df.empty:
                # 计算每个商品的销售额
                temp_df['销售额'] = temp_df['报价'] * temp_df['数量']

                # 获取总销售额
                total_sales = temp_df['销售额'].sum()

                # 计算每个商品对总毛利率的贡献
                temp_df['毛利贡献'] = temp_df[margin_column] * temp_df['销售额']

                # 计算加权平均毛利率
                weighted_avg_margin = temp_df['毛利贡献'].sum() / total_sales if total_sales > 0 else 0
                st.session_state.avg_gross_margin = weighted_avg_margin
            else:
                st.session_state.avg_gross_margin = 0
        else:
            st.session_state.avg_gross_margin = 0
    else:
        # 如果没有数量列，使用原来的计算方法
        margin_df['分类组'] = margin_df['序号'].apply(lambda x: '主要' if 1 <= x <= 7 else '次要')
        main_group_avg = margin_df[margin_df['分类组'] == '主要'][margin_column].mean()
        secondary_group_avg = margin_df[margin_df['分类组'] == '次要'][margin_column].mean()
        st.session_state.avg_gross_margin = (main_group_avg * 0.85) + (secondary_group_avg * 0.15)

    # 保存结果到会话状态
    st.session_state.quote_results = quote_df


# 文件上传区域
st.header("1. 上传文件")

col1, col2 = st.columns(2)

with col1:
    cost_file = st.file_uploader("上传成本价格表", type=['xlsx', 'xls', 'csv'])
    if cost_file is not None:
        st.session_state.cost_price_df = load_data(cost_file)
        if st.session_state.cost_price_df is not None:
            st.success("成本价格表上传成功！")
            st.dataframe(st.session_state.cost_price_df.head())

with col2:
    margin_file = st.file_uploader("上传总部毛利率参考表", type=['xlsx', 'xls', 'csv'])
    if margin_file is not None:
        st.session_state.margin_df = load_data(margin_file)
        if st.session_state.margin_df is not None:
            st.success("总部毛利率参考表上传成功！")
            st.dataframe(st.session_state.margin_df.head())

# 客户类型选择
st.header("2. 选择客户类型")
customer_type = st.radio(
    "请选择客户类型",
    ('线上客户', '线下客户')
)
st.session_state.customer_type = customer_type

# 待报价文件上传
st.header("3. 上传待报价文件")
quote_file = st.file_uploader("上传待报价文件", type=['xlsx', 'xls', 'csv'])
if quote_file is not None:
    st.session_state.quote_file_df = load_data(quote_file)
    if st.session_state.quote_file_df is not None:
        st.success("待报价文件上传成功！")

        # 检查是否有待报价文件包含数量列
        if '数量' in st.session_state.quote_file_df.columns:
            st.info("检测到文件包含'数量'列，将在结果中计算'总计'并基于数量优化综合毛利率计算。")

        st.dataframe(st.session_state.quote_file_df.head())

# 计算报价按钮
st.header("4. 计算报价")
if st.button("计算报价", use_container_width=True):
    calculate_quote()

# 显示结果
if st.session_state.quote_results is not None:
    st.header("5. 报价结果")
    st.subheader(f"客户类型: {st.session_state.customer_type}")

    # 根据是否有数量列显示不同的综合毛利率说明
    if st.session_state.has_quantity:
        st.subheader(f"加权综合毛利率: {st.session_state.avg_gross_margin:.2%}")
        st.caption("*加权综合毛利率基于各商品销售数量计算得出")
    else:
        st.subheader(f"预测综合毛利率: {st.session_state.avg_gross_margin:.2%}")
        st.caption("*预测综合毛利率基于序号1-7分类占85%，其余分类占15%计算得出")

    st.dataframe(st.session_state.quote_results)

    # 提供下载功能
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.quote_results.to_excel(writer, index=False, sheet_name='报价结果')

        # 添加综合毛利率信息
        summary_sheet = writer.book.create_sheet('综合毛利率')
        summary_sheet['A1'] = '客户类型'
        summary_sheet['B1'] = st.session_state.customer_type
        summary_sheet['A2'] = '综合毛利率'
        summary_sheet['B2'] = f"{st.session_state.avg_gross_margin:.2%}"
        if st.session_state.has_quantity:
            summary_sheet['A3'] = '计算方式'
            summary_sheet['B3'] = '基于销售数量的加权平均'
        else:
            summary_sheet['A3'] = '计算方式'
            summary_sheet['B3'] = '序号1-7分类占85%，其余分类占15%'

    output.seek(0)
    st.download_button(
        label="下载报价结果",
        data=output,
        file_name=f"{st.session_state.customer_type}_报价结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # 显示匹配统计信息
    total_products = len(st.session_state.quote_results)
    matched_products = sum(1 for val in st.session_state.quote_results['匹配商品名称'] if val != "无")

    st.info(
        f"匹配统计: 在{total_products}个商品中，成功匹配{matched_products}个，匹配率为{round(matched_products / total_products * 100, 2)}%")

st.divider()
st.info("提示：所有表格文件需确保列名与要求一致，否则可能导致计算错误。模糊匹配可能存在一定误差，请检查匹配结果。")
