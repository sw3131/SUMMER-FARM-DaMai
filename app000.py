import streamlit as st

# 初始化 session state
if 'recipe_name' not in st.session_state:
    st.session_state.recipe_name = ""  # 配方名称
if 'ingredients' not in st.session_state:
    st.session_state.ingredients = []  # 存储原材料列表
if 'ingredient_counter' not in st.session_state:
    st.session_state.ingredient_counter = 1  # 追踪添加的原材料数量
if 'recipe_set' not in st.session_state:
    st.session_state.recipe_set = False  # 是否设置配方名称


# 单位换算函数：将其他单位转换为克
def convert_to_grams(value, unit):
    if unit == "克":
        return value
    elif unit == "斤":
        return value * 500
    elif unit == "公斤":
        return value * 1000
    elif unit == "毫升":
        return value  # 假设液体的密度为1 g/ml
    elif unit == "升":
        return value * 1000  # 假设液体的密度为1 g/ml
    elif unit == "个":
        return value  # 保留原值，不进行换算
    else:
        return value  # 默认返回原始值


# 添加配方名称
def add_recipe_name():
    recipe_name = st.text_input('请输入配方名称：', value=st.session_state.recipe_name)

    # 当配方名称非空时，保存到 session_state 中
    if recipe_name:
        st.session_state.recipe_name = recipe_name
        st.session_state.recipe_set = True  # 标记配方名称已设置
        st.success(f"配方名称已设置：{recipe_name}")
        st.rerun()  # 重新运行，确保页面刷新
    else:
        st.warning("请输入配方名称")


# 添加原材料
def add_ingredient():
    # 检查配方名称是否已设置
    if not st.session_state.recipe_set:
        add_recipe_name()  # 如果配方名称没有设置，先设置配方名称
        return  # 如果配方名称没设置，就不继续原材料输入

    # 输入原材料信息
    ingredient_name = st.text_input(f'请输入原材料{st.session_state.ingredient_counter}的名称',
                                    key=f'name{st.session_state.ingredient_counter}')
    ingredient_weight = st.number_input(f'请输入原材料{st.session_state.ingredient_counter}的用量', min_value=0.0,
                                        value=0.0, key=f'weight{st.session_state.ingredient_counter}')
    unit = st.selectbox(f"选择原材料{st.session_state.ingredient_counter}的单位",
                        ["克", "斤", "公斤", "毫升", "升", "个"], key=f'unit{st.session_state.ingredient_counter}')

    # 新增“原材料品牌”输入框
    ingredient_brand = st.text_input(f"请输入原材料{st.session_state.ingredient_counter}的品牌",
                                     key=f'brand{st.session_state.ingredient_counter}')

    # 将标签文本加粗并变红
    st.markdown('<p style="color:red; font-weight:bold;">请输入原材料的到货规格：</p>', unsafe_allow_html=True)
    package_weight = st.number_input(f'请输入原材料的到货规格', min_value=0.0, value=0.0,
                                     key=f'package_weight{st.session_state.ingredient_counter}',
                                     label_visibility="collapsed")

    # 再次加粗并变红
    st.markdown('<p style="color:red; font-weight:bold;">选择到货原材料的原始单位：</p>', unsafe_allow_html=True)
    package_unit = st.selectbox(f"选择到货原材料的原始单位", ["克", "斤", "公斤", "毫升", "升", "个"],
                                key=f'package_unit{st.session_state.ingredient_counter}', label_visibility="collapsed")

    # 同样对价格字段进行修改
    st.markdown('<p style="color:red; font-weight:bold;">请输入原材料的到货价格（元）：</p>', unsafe_allow_html=True)
    ingredient_price = st.number_input(f'请输入原材料的到货价格（元）', min_value=0.0, value=0.0,
                                       key=f'price{st.session_state.ingredient_counter}', label_visibility="collapsed")

    # 继续添加按钮
    if st.button('继续添加'):
        if ingredient_name and ingredient_weight > 0 and package_weight > 0:
            # 将原材料数据转换为克
            converted_weight = convert_to_grams(ingredient_weight, unit)
            converted_package_weight = convert_to_grams(package_weight, package_unit)

            # 将原材料信息保存到 session_state 中
            st.session_state.ingredients.append({
                'name': ingredient_name,
                'weight': converted_weight,
                'price': ingredient_price,
                'package_weight': converted_package_weight,
                'unit': unit,
                'package_unit': package_unit,
                'brand': ingredient_brand  # 保存原材料品牌
            })
            # 清空当前输入框
            st.session_state.ingredient_counter += 1  # 增加原材料计数器
            st.session_state.name = ""
            st.session_state.weight = 0.0
            st.session_state.price = 0.0
            st.session_state.package_weight = 0.0
            st.session_state.unit = "克"
            st.session_state.package_unit = "克"
            st.session_state.brand = ""  # 清空品牌输入框
            st.success(f"原材料{ingredient_name}已添加！")
            st.rerun()  # 重新运行，确保页面刷新
        else:
            st.error("请确保所有字段都已填写，并且重量和价格大于0")

    # 完成计算按钮
    if st.button('完成并计算'):
        if not st.session_state.ingredients:
            st.error("没有添加任何原材料！")
        else:
            calculate_cost()


# 计算成本
def calculate_cost():
    total_cost = 0
    st.write(f"配方名称：{st.session_state.recipe_name}")
    st.write("已添加的原材料：")

    for ingredient in st.session_state.ingredients:
        # 计算单克价格和原材料成本
        if ingredient['unit'] == "个":
            st.write(f"原材料名称：{ingredient['name']} ({ingredient['brand']})")
            st.write(f"用量：{ingredient['weight']} {ingredient['unit']}")
            st.write(f"包装重量：{ingredient['package_weight']} {ingredient['package_unit']}")
            st.write(
                f"单个价格：{ingredient['price'] / ingredient['package_weight']:.4f} 元/{ingredient['package_unit']}")
        else:
            st.write(f"原材料名称：{ingredient['name']} ({ingredient['brand']})")
            st.write(f"用量：{ingredient['weight']} 克")
            st.write(f"包装重量：{ingredient['package_weight']} 克")
            st.write(f"单克价格：{ingredient['price'] / ingredient['package_weight']:.4f} 元/克")

        # 计算单个原材料的成本
        cost_per_gram = ingredient['price'] / ingredient['package_weight']
        ingredient_cost = ingredient['weight'] * cost_per_gram
        total_cost += ingredient_cost

    # 输出总成本
    st.write(f"总成本：{total_cost:.2f} 元")


# 显示输入界面
st.title('烘焙产品成本计算')

# 运行原材料添加界面
add_ingredient()
