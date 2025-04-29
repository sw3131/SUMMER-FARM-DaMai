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
    """
    智能商品筛选（严格模式）：
    - 精确匹配预设关键词
    - 仅当搜索词完全匹配预设关键词时应用类目限制
    """
    # 预处理
    df_clean = df.assign(
        clean_name=df['商品名称'].str.lower().str.strip().fillna(''),
        category_lower=df['类目'].str.lower().str.strip()
    )

    # 分离关键词类型
    restricted_terms = []
    normal_terms = []

    # 精确匹配判断
    for term in map(str.strip, map(str, search_terms)):
        term_lower = term.lower()
        if term_lower in {kw.lower() for kw in CATEGORY_RESTRICTED_KEYWORDS}:
            restricted_terms.append(term_lower)
        else:
            normal_terms.append(term_lower)

    # 构建匹配条件
    conditions = []

    # 类目限制条件（鲜果类目 + 精确关键词匹配）
    if restricted_terms:
        restr_cond = (df_clean['category_lower'] == '鲜果')
        name_cond = pd.Series(False, index=df.index)
        for term in restricted_terms:
            # 精确包含匹配（非子字符串匹配）
            name_cond |= df_clean['clean_name'].str.contains(
                term, regex=False, case=False
            )
        conditions.append(restr_cond & name_cond)

    # 普通条件（全类目模糊匹配）
    if normal_terms:
        normal_cond = pd.Series(False, index=df.index)
        for term in normal_terms:
            normal_cond |= df_clean['clean_name'].str.contains(
                term, regex=False, case=False
            )
        conditions.append(normal_cond)

    # 组合条件（OR逻辑）
    if conditions:
        combined_cond = pd.concat(conditions, axis=1).any(axis=1)
        return df[combined_cond]

    return df


def main():
    check_dependencies()

    st.title("💡 新版佣金工具--大麦团队")
    st.sidebar.header("文件上传")

    # 文件上传组件
    original_file = st.sidebar.file_uploader(
        "1. 原始数据表 (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key="original"
    )

    customer_matching_file = st.sidebar.file_uploader(
        "2. 客户匹配表 (可选)",
        type=["xlsx", "xls", "csv"],
        key="customer"
    )

    product_matching_file = st.sidebar.file_uploader(
        "3. 商品匹配表 (可选)",
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

    if st.sidebar.button("🚀 开始分析"):
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
                'BD': ['BD', 'bd_name'],
                '类目': ['类目', 'category']
                'm_id': ['m_id', 'cust_id']
            }

            # 自动识别列名
            missing_columns = []
            for standard_name, possible_names in COLUMN_MAPPING.items():
                found = [n for n in possible_names if n in df.columns]
                if found:
                    if found[0] != standard_name:
                        df.rename(columns={found[0]: standard_name}, inplace=True)
                else:
                    if standard_name in ['类目', 'order_date']:
                        missing_columns.append(standard_name)

            if missing_columns:
                st.error(f"❌ 缺少必要列：{', '.join(missing_columns)}")
                return

            # 客户匹配处理
            if customer_matching_file:
                customer_df = pd.read_excel(customer_matching_file) if customer_matching_file.name.endswith(
                    ('.xlsx', '.xls')) else pd.read_csv(customer_matching_file)
                if '客户名称' not in customer_df.columns:
                    st.error("⛔ 客户匹配表必须包含「客户名称」列")
                    return
                df = df[df['客户名称'].isin(customer_df['客户名称'])]
                st.success(f"✅ 客户精确匹配完成（匹配到 {len(customer_df)} 个客户）")

            # 商品智能匹配
            if product_matching_file:
                product_df = pd.read_excel(product_matching_file) if product_matching_file.name.endswith(
                    ('.xlsx', '.xls')) else pd.read_csv(product_matching_file)
                if '商品名称' not in product_df.columns:
                    st.error("⛔ 商品匹配表必须包含「商品名称」列")
                    return

                search_terms = product_df['商品名称'].dropna().astype(str).unique()
                original_count = len(df)

                try:
                    df = smart_product_filter(df, search_terms)
                except KeyError as e:
                    st.error(f"❌ 数据列缺失：{str(e)}")
                    return

                # 统计匹配情况
                matched_restricted = [t for t in search_terms if
                                      t.lower() in {kw.lower() for kw in CATEGORY_RESTRICTED_KEYWORDS}]
                matched_normal = [t for t in search_terms if
                                  t.lower() not in {kw.lower() for kw in CATEGORY_RESTRICTED_KEYWORDS}]

                st.success(f"""
                ✅ 商品智能匹配完成：
                - 类目敏感词：{', '.join(matched_restricted) or "无"}
                - 普通关键词：{', '.join(matched_normal[:3])}{'...' if len(matched_normal) > 3 else ''}
                - 筛选结果：{len(df)} 条（减少 {original_count - len(df)} 条）
                """)

                if len(df) == 0:
                    st.error("⚠️ 没有匹配到任何商品，请检查匹配条件")
                    return

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
            result_columns = ['客户名称', '商品名称', '类目', 'sku_id', 'order_date']
            if 'BD' in df.columns:
                result_columns.insert(4, 'BD')
            if 'm_id' in df.columns:
                result_columns.append('m_id')

            inactive_df = inactive_df[result_columns].rename(
                columns={'order_date': '最后购买日期'}
            )

            # 显示结果
            st.subheader(f"📑 分析结果（共 {len(inactive_df)} 条不活跃商品）")
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
                help="点击下载Excel格式的分析报告"
            )

        except Exception as e:
            st.error(f"❌ 处理过程中发生错误：{str(e)}")
            st.stop()


if __name__ == "__main__":
    main()
