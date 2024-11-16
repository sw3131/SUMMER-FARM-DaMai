import streamlit as st
import pandas as pd
from PIL import Image
import io
import os

# 设置页面配置
st.set_page_config(
    page_title="大麦-数据策略工具-购买周期",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 显示LOGO
def display_logo():
    if os.path.exists("logo.png"):
        try:
            logo = Image.open("logo.png")
            logo = logo.resize((400, 140), Image.LANCZOS)  # 根据需要调整大小
            st.image(logo, use_column_width=True)
        except Exception as e:
            st.warning(f"无法加载logo.png 文件：{e}")
    else:
        st.warning("未找到 logo.png 文件，程序将继续运行但不显示LOGO。")

display_logo()

st.title("大麦-数据策略工具-购买周期")

# 上传文件
st.header("上传需要分析的表格文件")
uploaded_file = st.file_uploader("选择一个Excel文件（.xlsx）", type=["xlsx"])

# 输入商品名称
st.header("输入商品名称")
product_name = st.text_input("请输入要查询的商品名称：")

# 定义数据分析函数
def analyze_data(df, product_name):
    required_columns = ['商品名称', '下单时间', '客户名称', 'BD']
    if not all(column in df.columns for column in required_columns):
        st.error(f"Excel文件缺少必要的列：{required_columns}")
        return None

    # 根据商品名称严格匹配过滤数据
    filtered_data = df[df['商品名称'] == product_name].copy()
    if filtered_data.empty:
        st.warning("查询不到此商品，请重新输入。")
        return None

    # 转换下单时间格式并排序
    filtered_data['下单时间'] = pd.to_datetime(filtered_data['下单时间'], errors='coerce')
    filtered_data = filtered_data.dropna(subset=['下单时间'])
    filtered_data = filtered_data.sort_values(['客户名称', '下单时间'])

    # 计算客户购买周期
    filtered_data['购买间隔(天)'] = filtered_data.groupby('客户名称')['下单时间'].diff().dt.days

    # 获取每位客户的最近一次下单时间
    recent_order = filtered_data.groupby('客户名称')['下单时间'].max().reset_index()
    recent_order.rename(columns={'下单时间': '最近一次下单时间'}, inplace=True)

    # 汇总结果并增加 BD 信息和商品名称
    summary = filtered_data.groupby(['客户名称', 'BD'])['购买间隔(天)'].agg(['mean', 'min', 'max']).reset_index()
    summary.rename(columns={
        'mean': '平均购买周期(天)',
        'min': '最短购买周期(天)',
        'max': '最长购买周期(天)'
    }, inplace=True)

    summary = pd.merge(summary, recent_order, on='客户名称', how='left')
    summary['预测购买时间'] = summary['最近一次下单时间'] + pd.to_timedelta(summary['平均购买周期(天)'], unit='D')
    summary['预测购买时间'] = summary['预测购买时间'].dt.strftime('%Y年%m月%d日')

    summary['商品名称'] = product_name

    summary = summary.dropna(subset=['平均购买周期(天)', '最短购买周期(天)', '最长购买周期(天)'])
    summary = summary[
        (summary['平均购买周期(天)'] != 0) |
        (summary['最短购买周期(天)'] != 0) |
        (summary['最长购买周期(天)'] != 0)
    ]

    return summary

# 处理查询
if st.button("查询"):
    if uploaded_file is None:
        st.warning("请先上传文件。")
    elif not product_name.strip():
        st.warning("请输入要查询的商品名称。")
    else:
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            result = analyze_data(df, product_name.strip())
            if result is not None:
                st.success("分析完成！")
                st.dataframe(result)

                # 提供下载功能
                towrite = io.BytesIO()
                result.to_excel(towrite, index=False, engine='openpyxl')
                towrite.seek(0)
                st.download_button(
                    label="下载结果为Excel",
                    data=towrite,
                    file_name=f"分析结果_{product_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"处理文件时发生错误：{e}")

# 提示信息
st.markdown("""
---
**注意事项：**
- 请确保上传的Excel文件包含以下列：`商品名称`, `下单时间`, `客户名称`, `BD`。
- `下单时间` 列应为日期格式。
- `logo.png` 文件应与 `app.py` 位于同一目录下。
""")
