import streamlit as st
import pandas as pd


# 计算分析函数
def analyze_data(df, target_increase_pct, min_rank, max_rank):
    # 1. 过滤掉“商品名称”列中的指定商品
    filtered_df = df[~df['商品名称'].isin(['爱乐薇(铁塔)淡奶油', '安佳淡奶油'])]

    # 2. 动态列名匹配
    # 确保列名正确匹配，如果需要，可以进行列名替换
    df.columns = df.columns.str.strip()  # 清除列名中的空格

    # 识别列名称
    cust_id_col = 'cust_id' if 'cust_id' in df.columns else 'm_id'
    date_col = '日期' if '日期' in df.columns else '下单时间'
    gmv_col = '实付GMV' if '实付GMV' in df.columns else '实付金额'

    # 3. 汇总“实付GMV”的总和值
    total_gmv = filtered_df[gmv_col].sum()

    # 4. 转换“日期”列为日期格式
    filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], errors='coerce')

    # 5. 计算每个客户的月平均值
    filtered_df['年-月'] = filtered_df[date_col].dt.to_period('M')

    # 按客户、月度和BD汇总GMV
    monthly_gmv = filtered_df.groupby([cust_id_col, '客户名称', '年-月', 'BD'])[gmv_col].sum().reset_index()

    # 计算每个客户的月平均GMV，按照BD维度
    customer_avg_gmv = monthly_gmv.groupby(['BD', cust_id_col, '客户名称'])[gmv_col].mean().reset_index()
    customer_avg_gmv = customer_avg_gmv.rename(columns={gmv_col: '月平均GMV'})

    # 6. 计算每个BD名下客户的月平均GMV排名
    customer_avg_gmv['排名'] = customer_avg_gmv.groupby('BD')['月平均GMV'].rank(method='min', ascending=False)

    # 7. 筛选根据用户输入的排名区间
    filtered_customers = customer_avg_gmv[
        (customer_avg_gmv['排名'] >= min_rank) & (customer_avg_gmv['排名'] <= max_rank)]

    # 8. 计算客户目标值（目标上涨百分比）
    filtered_customers['目标'] = filtered_customers['月平均GMV'] * (1 + target_increase_pct / 100)

    return total_gmv, filtered_customers


# Streamlit应用
def main():
    st.title("GMV数据分析工具")

    # 文件上传功能
    uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"])

    if uploaded_file is not None:
        # 读取Excel文件
        df = pd.read_excel(uploaded_file)

        # 显示上传的文件数据
        st.write("上传的数据预览:")
        st.dataframe(df.head())

        # 输入客户目标上涨百分比
        target_increase_pct = st.number_input(
            "请输入客户目标上涨百分比（例如：10表示目标上涨10%）",
            min_value=0,
            max_value=100,
            value=10
        )

        # 输入排名区间
        min_rank = st.number_input("请输入最小排名（例如：11）", min_value=1, value=11)
        max_rank = st.number_input("请输入最大排名（例如：50）", min_value=1, value=50)

        # 执行数据分析
        total_gmv, filtered_customers = analyze_data(df, target_increase_pct, min_rank, max_rank)

        # 显示总GMV值
        st.subheader("实付GMV总和值:")
        st.write(total_gmv)

        # 显示用户选定排名区间的客户及其目标值
        st.subheader(f"排名在{min_rank}到{max_rank}名之间的客户及其目标值:")
        st.write(filtered_customers)

        # 提供下载按钮，允许用户下载分析结果
        result_file = "目标客户分析结果_with_cust_id.xlsx"
        filtered_customers.to_excel(result_file, index=False)

        st.download_button(
            label="下载分析结果",
            data=open(result_file, "rb").read(),
            file_name=result_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


if __name__ == "__main__":
    main()
