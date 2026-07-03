import streamlit as st
import pandas as pd
import math

st.set_page_config(
    page_title="マイテックスイット 操作チェーン長さ判定",
    layout="wide",
)

st.markdown("""
<style>

/* 上のヘッダーを消す */
header{
    visibility:hidden;
}

/* ハンバーガーメニューを消す */
#MainMenu{
    visibility:hidden;
}

/* フッターを消す */
footer{
    visibility:hidden;
}

/* ページ余白 */
.block-container{
    padding-top:0.5rem;
    padding-bottom:0.5rem;
}

/* 判定ボタンを少し上に移動 */
div[data-testid="stButton"]{
    margin-top:-8px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.block-container{
    padding-top:0rem;
    padding-bottom:0.5rem;
}

.app-title{
    text-align:center;
    font-size:2.2rem;
    font-weight:700;
    margin-top:20px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="app-title">マイテックスイット 操作チェーン長さ判定</div>',
    unsafe_allow_html=True,
)

st.divider()

# 画面レイアウト
left_margin, input_col, space1, result_col, space2, image_col, right_margin = st.columns(
    [0.4, 3, 0.4, 3, 0.4, 4, 0.4]
)


# =========================
# Excel情報の取得
# =========================

@st.cache_data
def load_screen_data():
    df = pd.read_excel(
        "スクリーン情報_サイドホルダー選定表.xlsx",
        sheet_name="スクリーン情報",
        header=3
    )

    # 必要列だけ使用
    df = df[
        [
            "シリーズ名",
            "最小製品幅W(mm)",
            "最大製品幅W(mm)",
            "最小製品高さH(mm)",
            "最大製品高さH(mm)",
            "最大取付高さTH(mm)",
            "幅丈比",
            "厚み(mm)",
            "巻き径GP"
        ]
    ]

    # 空行除外
    df = df.dropna(subset=["シリーズ名"])

    # 文字列の余計な空白除去
    df["シリーズ名"] = df["シリーズ名"].astype(str).str.strip()
    df["幅丈比"] = df["幅丈比"].astype(str).str.strip()

    return df


def load_screen_names():
    df = load_screen_data()
    return [""] + df["シリーズ名"].tolist()


def get_screen_limits(screen_name):
    df = load_screen_data()

    matched = df[df["シリーズ名"] == screen_name]

    if matched.empty:
        return None

    return matched.iloc[0]


def parse_width_height_ratio(ratio_text):
    """
    幅丈比 '1:8' を 8 に変換する
    例：1:8 → 高さは幅の8倍まで
    """
    try:
        left, right = ratio_text.split(":")
        left = float(left)
        right = float(right)

        if left <= 0:
            return None

        return right / left

    except Exception:
        return None
    
@st.cache_data
def load_side_holder_table():
    df = pd.read_excel(
        "スクリーン情報_サイドホルダー選定表.xlsx",
        sheet_name="サイドホルダー選定表",
        header=3,
    )

    return df.dropna(subset=["巻径GP"])


# =========================
# 計算定数
# =========================

A_MAX = 1500  # 操作起点最大高さ mm
K_BASE_DISTANCE = 200  # 基準距離 mm


# =========================
# 計算関数
# =========================

def get_pipe_type(product_width):
    """
    製品幅からパイプ種類を判定する

    """
    if product_width is None:
        return None

    if product_width <= 2000:
        return "Eパイプ"
    else:
        return "Gパイプ"


def get_pipe_diameter(pipe_type):
    """
    パイプ種類からパイプ直径を返す

    """
    if pipe_type == "Eパイプ":
        return 41
    elif pipe_type == "Gパイプ":
        return 45
    else:
        return None


def get_pipe_radius(pipe_diameter):
    """
    パイプ直径からパイプ半径を返す

    """
    if pipe_diameter is None:
        return None

    return pipe_diameter / 2


def calculate_basic_values(product_width, screen_limits):
    """
    まずは定数とパイプ情報までをまとめて計算する
    """
    pipe_type = get_pipe_type(product_width)
    pipe_diameter = get_pipe_diameter(pipe_type)
    pipe_radius = get_pipe_radius(pipe_diameter)
    fabric_thickness = float(screen_limits["厚み(mm)"])

    return {
        "操作起点最大高さ Amax": A_MAX,
        "基準距離 K": K_BASE_DISTANCE,
        "パイプ種類": pipe_type,
        "パイプ直径": pipe_diameter,
        "パイプ半径": pipe_radius,
        "生地厚さ": fabric_thickness,
    }

def calculate_roll_diameter(
    fabric_thickness,
    product_height,
    pipe_radius,
):
    """
    巻き径を計算する
    """

    return (
        math.sqrt(
            fabric_thickness * (product_height + 205) / math.pi
            + pipe_radius ** 2
        )
        * 2
    )

def calculate_roll_numbers(
    pipe_diameter,
    fabric_thickness,
    roll_diameter
):
    """
    巻き数を計算する
    """

    return (
        (roll_diameter - pipe_diameter)
        / 2
        / fabric_thickness
    )

def calculate_angle_lead (
    roll_numbers
):
    """
    進み角度を計算する
    """
    
    return (roll_numbers * 360)

def calculate_ball_chain_lead_count(
    angle_lead,
):
    """
    ボールチェーン進み玉数を計算する
    """

    return angle_lead / 90

def get_side_holder(
    roll_diameter_group,
    product_width,
    product_height,
):
    """
    サイドホルダー種類を取得する
    """

    df = load_side_holder_table()

    for _, row in df.iterrows():

        # 巻径GP一致
        if row["巻径GP"] != roll_diameter_group:
            continue

        # 幅判定
        if row["$W"] == "<=":
            width_ok = product_width <= row["製品幅"]
        else:
            width_ok = product_width > row["製品幅"]

        # 高さ判定
        if row["$H"] == "<=":
            height_ok = product_height <= row["製品丈"]
        else:
            height_ok = product_height > row["製品丈"]

        if width_ok and height_ok:
            return row["ｻｲﾄﾞﾎﾙﾀﾞｰ種類"]

    return None

def calculate_side_holder_center_distance(
    side_holder,
):
    """
    サイドホルダー中心距離を計算する
    """

    if side_holder == "S":
        return 45.2
    else:
        return 55.5
    
def calculate_pipe_center_height(
    mount_type,
    product_height,
    mount_height,
    side_holder_center_distance,
    pipe_radius,
):
    """
    床からパイプ中心までの距離を計算する
    """

    if mount_type == "天井付け":

        if mount_height is None:
            return product_height - side_holder_center_distance
        else:
            return mount_height - side_holder_center_distance

    else:

        if mount_height is None:
            return product_height - pipe_radius
        else:
            return mount_height - pipe_radius
        
def calculate_base_distance_difference(
    base_distance,
    side_holder_center_distance,
):
    """
    基準距離 - サイドホルダー軸心距離を計算する
    """

    return base_distance - side_holder_center_distance

def calculate_one_stroke_distance(
    ball_chain_lead_count,
):
    """
    1ストローク距離を計算する
    """

    return ball_chain_lead_count * 12

def calculate_ball_chain_total_length(
    use_dimension_a,
    dimension_a_input,
    pipe_radius,
    one_stroke_distance,
    pipe_center_height,
    operation_start_max_height,
    base_distance_difference,
    base_distance,
):
    """
    ボールチェーン全長を計算する
    """

    # A寸法指定時
    if use_dimension_a:
        return (
            (dimension_a_input - pipe_radius) * 2
            + one_stroke_distance
        )

    # 通常計算
    if (
        pipe_center_height
        <= operation_start_max_height + base_distance_difference
    ):
        return (
            2 * (base_distance + 6)
            + one_stroke_distance
        )

    return (
        2 * (
            pipe_center_height
            - operation_start_max_height
            + 6
        )
        + one_stroke_distance
    )

def calculate_dimension_a(
    ball_chain_total_length,
    one_stroke_distance,
    pipe_radius,
):
    """
    A寸法を計算する
    """

    value = (
        (ball_chain_total_length - one_stroke_distance)
        / 2
        + pipe_radius
    )

    return math.ceil(value / 10) * 10

def calculate_dimension_b(
    dimension_a,
    one_stroke_distance,
):
    """
    B寸法を計算する
    """

    return dimension_a + one_stroke_distance

def calculate_dimension_c(
    dimension_a,
    dimension_b,
):
    """
    C寸法を計算する
    """

    return (dimension_a + dimension_b) / 2

def calculate_high_side_height(
    mount_type,
    product_height,
    mount_height,
    side_holder_center_distance,
    dimension_a,
    pipe_radius,
):
    """
    床から高い側の高さを計算する
    """

    # 取付高さを使用する値
    if mount_height is None:
        height = product_height
    else:
        height = mount_height

    # 天井付け
    if mount_type == "天井付け":
        return (
            height
            - side_holder_center_distance
            + pipe_radius
            - dimension_a
        )

    # 正面付け
    return (
        height
        - dimension_a
    )
    
def calculate_low_side_height(
    mount_type,
    pipe_center_height,
    side_holder_center_distance,
    dimension_b,
    pipe_radius,
):
    """
    床から低い側の高さを計算する
    """

    if mount_type == "天井付け":
        return (
            pipe_center_height
            + side_holder_center_distance
            - (side_holder_center_distance - pipe_radius)
            - dimension_b
        )

    else:
        return (
            pipe_center_height
            - dimension_b
            + pipe_radius
        )
    
def reset_result():
    st.session_state.result = {
        "judge": "****",
        "a": "****",
        "b": "****",
        "c": "****",
        "high": "****",
        "low": "****",
        "minimum_dimension_a": None,
        "maximum_dimension_a": None,
    }

def reset_inputs():

    for key in [
        "screen_name",
        "mount_type",
        "product_width",
        "product_height",
        "use_mount_height",
        "mount_height",
        "use_dimension_a",
        "dimension_a_input",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    reset_result()

    st.rerun()

def judge_chain_length(
    use_dimension_a,
    dimension_a,
    standard_chain_length,
    low_side_height,
):
    """
    コード長さ判定
    """

    if not use_dimension_a:
        return True, "製作可能"

    if dimension_a < standard_chain_length:
        return False, "希望チェーン長さ(A)が短すぎます"

    if low_side_height < 10:
        return False, "希望チェーン長さ(A)が長すぎます"

    return True, "製作可能"

def draw_svg():

    svg = """
    <svg width="420" height="320"
         xmlns="http://www.w3.org/2000/svg">

        <!-- 天井 -->
        <rect
            x="50"
            y="20"
            width="260"
            height="8"
            fill="#8d8452"
            stroke="#5b5430"
            stroke-width="2"/>

        <!-- パイプ -->
        <rect
            x="70"
            y="28"
            width="220"
            height="22"
            fill="#8b8b8b"
            stroke="#555"
            stroke-width="2"/>

        <!-- 左エンドキャップ -->
        <rect
            x="66"
            y="26"
            width="8"
            height="26"
            fill="#214f93"/>

        <!-- 右エンドキャップ -->
        <rect
            x="286"
            y="26"
            width="8"
            height="26"
            fill="#214f93"/>

        <!-- Aチェーン（手前） -->
        <line
            x1="286"
            y1="50"
            x2="286"
            y2="155"
            stroke="#163d87"
            stroke-width="2"/>

        <!-- Bチェーン（奥） -->
        <line
            x1="294"
            y1="50"
            x2="294"
            y2="220"
            stroke="#163d87"
            stroke-width="2"/>

        <!-- Aグリップ -->
        <path
            d="
                M282 135
                Q282 133 284 133
                L286 133
                Q288 133 288 135
                L290 170
                Q290 172 288 172
                L282 172
                Q280 172 280 170
                Z"
            fill="#0d67c2"
            stroke="#18407a"
            stroke-width="2"/>

        <!-- Bグリップ -->
        <path
            d="
                M290 200
                Q290 198 292 198
                L294 198
                Q296 198 296 200
                L298 235
                Q298 237 296 237
                L290 237
                Q288 237 288 235
                Z"
            fill="#0d67c2"
            stroke="#18407a"
            stroke-width="2"/>

    </svg>
    """

    st.components.v1.html(svg, height=280)

# =========================
# バリデーション関数
# =========================

def validate_inputs(
    mount_type,
    product_width,
    product_height,
    use_mount_height,
    mount_height,
    use_dimension_a,
    dimension_a_input,
    screen,
    screen_limits,
):
    
    errors = []

    if not mount_type:
        errors.append("取付方法を選択してください。")

    if not screen:
        errors.append("スクリーンを選択してください。")
        return errors

    if screen_limits is None:
        errors.append("選択されたスクリーンの制限情報が見つかりません。")
        return errors

    min_width = int(screen_limits["最小製品幅W(mm)"])
    max_width = int(screen_limits["最大製品幅W(mm)"])
    min_height = int(screen_limits["最小製品高さH(mm)"])
    max_height = int(screen_limits["最大製品高さH(mm)"])
    max_mount_height = int(screen_limits["最大取付高さTH(mm)"])
    width_height_ratio_text = str(screen_limits["幅丈比"]).strip()
    width_height_ratio = parse_width_height_ratio(width_height_ratio_text)

    if product_width is None or product_width <= 0:
        errors.append("製品幅 W を入力してください。")
    else:
        if product_width < min_width:
            errors.append(
                f"製品幅 W が小さすぎます。{screen}は{min_width}mm以上で入力してください。"
            )
        if product_width > max_width:
            errors.append(
                f"製品幅 W が大きすぎます。{screen}は{max_width}mm以下で入力してください。"
            )
        if product_width % 5 != 0:
            errors.append("製品幅 W は5mm単位で入力してください。")

    if product_height is None or product_height <= 0:
        errors.append("製品高さ H を入力してください。")
    else:
        if product_height < min_height:
            errors.append(
                f"製品高さ H が小さすぎます。{screen}は{min_height}mm以上で入力してください。"
            )
        if product_height > max_height:
            errors.append(
                f"製品高さ H が大きすぎます。{screen}は{max_height}mm以下で入力してください。"
            )
        if product_height % 10 != 0:
            errors.append("製品高さ H は10mm単位で入力してください。")

    # 幅丈比チェック
    if (
        product_width is not None
        and product_width > 0
        and product_height is not None
        and product_height > 0
    ):
        if width_height_ratio is None:
            errors.append(f"{screen}の幅丈比設定が不正です。")
        else:
            max_height_by_ratio = product_width * width_height_ratio

            if product_height > max_height_by_ratio:
                errors.append(f"幅丈比制限を超えています。{screen}の幅丈比は{width_height_ratio_text}です。")
                errors.append(f"製品幅 W={product_width}mm の場合、製品高さ H は最大{int(max_height_by_ratio)}mmまでです。")

    if use_mount_height:
        if mount_height is None or mount_height <= 0:
            errors.append("取付高さを入力してください。")
            errors.append("指定しない場合はチェックボックスを外してください。")
        else:
            if product_height is not None and product_height > 0 and mount_height < product_height:
                errors.append("取付高さは製品高さ H 以上で入力してください。")

            if mount_height > max_mount_height:
                errors.append(
                    f"取付高さが大きすぎます。{screen}は{max_mount_height}mm以下で入力してください。"
                )

            if mount_height % 10 != 0:
                errors.append("取付高さは10mm単位で入力してください。")
    
    if use_dimension_a:
        if dimension_a_input is None or dimension_a_input <= 0:
            errors.append("A側希望チェーン長さ(A)を入力してください。")
            errors.append("指定しない場合はチェックボックスを外してください。")
        else:
            if dimension_a_input % 10 != 0:
                errors.append("A側希望チェーン長さ(A)は10mm単位で入力してください。")

    return errors


# =========================
# 入力フォーム
# =========================

with input_col:

    st.subheader("条件入力")

    screen_name = st.selectbox(
        "スクリーン名",
        options=load_screen_names(),
        key="screen_name",
        on_change=reset_result,
    )

    screen_limits = get_screen_limits(screen_name) if screen_name else None

    mount_type = st.selectbox(
        "取付方法",
        options=[
            "",
            "天井付け",
            "正面付け",
        ],
        key="mount_type",
        on_change=reset_result,
    )

    product_width = st.number_input(
        "製品幅 W",
        min_value=1,
        max_value=9999,
        value=None,
        step=5,
        help="単位：mm。5mm単位で入力してください。",
        key="product_width",
        on_change=reset_result,
    )

    product_height = st.number_input(
        "製品高さ H",
        min_value=1,
        max_value=9999,
        value=None,
        step=10,
        help="単位：mm。10mm単位で入力してください。",
        key="product_height",
        on_change=reset_result,
    )

    use_mount_height = st.checkbox(
        "取付高さを指定する",
        key="use_mount_height",
        on_change=reset_result,
        )

    mount_height = None

    if use_mount_height:
        mount_height = st.number_input(
            "取付高さ",
            min_value=1,
            max_value=9999,
            value=None,
            step=10,
            help="単位：mm。10mm単位で入力してください。",
            key="mount_height",
            on_change=reset_result,
        )

    use_dimension_a = st.checkbox(
        "A側希望チェーン長さ(A)を指定する",
        key="use_dimension_a",
        on_change=reset_result,
    )

    dimension_a_input = None

    if use_dimension_a:
        dimension_a_input = st.number_input(
            "A側希望チェーン長さ(A)",
            min_value=1,
            max_value=9999,
            value=None,
            step=10,
            help="単位:mm。10mm単位で入力してください。",
            key="dimension_a_input",
            on_change=reset_result,
        )

    _, button_col = st.columns([2.5, 1.5])

    with button_col:
        judge_button = st.button(
            "判定する",
            use_container_width=True,
        )

    st.divider()

    # =========================
    # 選択スクリーンの制限表示
    # =========================

    if screen_limits is not None:
        st.info(
            f"""
            選択中スクリーン：{screen_name}

            - 製品幅 W：{int(screen_limits["最小製品幅W(mm)"])} ～ {int(screen_limits["最大製品幅W(mm)"])} mm
            - 製品高さ H：{int(screen_limits["最小製品高さH(mm)"])} ～ {int(screen_limits["最大製品高さH(mm)"])} mm
            - 最大取付高さ TH：{int(screen_limits["最大取付高さTH(mm)"])} mm
            - 幅丈比：{screen_limits["幅丈比"]}
            """
        )

# =========================
# 計算結果初期値
# =========================

if "result" not in st.session_state:
    st.session_state.result = {
        "judge": "****",
        "a": "****",
        "b": "****",
        "c": "****",
        "high": "****",
        "low": "****",
        "minimum_dimension_a": None,
        "maximum_dimension_a": None,
    }

# =========================
# 判定ボタン
# =========================

with input_col:

    if judge_button:
        errors = validate_inputs(
            mount_type=mount_type,
            product_width=product_width,
            product_height=product_height,
            use_mount_height=use_mount_height,
            mount_height=mount_height,
            use_dimension_a=use_dimension_a,
            dimension_a_input=dimension_a_input,
            screen=screen_name,
            screen_limits=screen_limits,
            )

        if errors:
            st.error("入力内容にエラーがあります。")
            for error in errors:
                st.write(f"- {error}")
        else:
            basic_values = calculate_basic_values(
                product_width, 
                screen_limits,
            )

            # 基本情報取り出し
            pipe_diameter = basic_values["パイプ直径"]
            pipe_radius = basic_values["パイプ半径"]
            fabric_thickness = basic_values["生地厚さ"]
            roll_diameter_group = screen_limits["巻き径GP"]

            # 巻き径
            roll_diameter = calculate_roll_diameter(
            fabric_thickness,
            product_height,
            pipe_radius,
        )

            # 巻き数
            roll_numbers = calculate_roll_numbers(
            pipe_diameter,
            fabric_thickness,
            roll_diameter,
        )
            
            #進み角度
            angle_lead = calculate_angle_lead(
            roll_numbers,
        )

            # ボールチェーン進み玉数
            ball_chain_lead_count = calculate_ball_chain_lead_count(
            angle_lead,
        )
            
            #サイドホルダー取得
            side_holder = get_side_holder(
            roll_diameter_group,
            product_width,
            product_height,
        )
            
            #サイドホルダー中心距離
            side_holder_center_distance = calculate_side_holder_center_distance(
            side_holder,
        )
            
            #床からパイプ中心間距離
            pipe_center_height = calculate_pipe_center_height(
            mount_type,
            product_height,
            mount_height,
            side_holder_center_distance,
            pipe_radius,
        )
            
            #基準距離-サイドホルダー中心間距離
            base_distance_difference = calculate_base_distance_difference(
            basic_values["基準距離 K"],
            side_holder_center_distance,
        )
            
            #1ストローク距離
            one_stroke_distance = calculate_one_stroke_distance(
            ball_chain_lead_count,
        )
            
            # 標準チェーン長さ用ボールチェーン全長
            standard_ball_chain_total_length = calculate_ball_chain_total_length(
            False,
            None,
            pipe_radius,
            one_stroke_distance,
            pipe_center_height,
            basic_values["操作起点最大高さ Amax"],
            base_distance_difference,
            basic_values["基準距離 K"],
        )

            #ボールチェーン全長
            ball_chain_total_length = calculate_ball_chain_total_length(
            use_dimension_a,
            dimension_a_input,
            pipe_radius,
            one_stroke_distance,
            pipe_center_height,
            basic_values["操作起点最大高さ Amax"],
            base_distance_difference,
            basic_values["基準距離 K"],
        )
            
            # 標準チェーン長さ(A寸法)
            standard_chain_length = calculate_dimension_a(
            standard_ball_chain_total_length,
            one_stroke_distance,
            pipe_radius,
            )

            # 実際に使用するA寸法
            dimension_a = standard_chain_length

            if use_dimension_a:
                dimension_a = dimension_a_input

            # B寸法
            dimension_b = calculate_dimension_b(
            dimension_a,
            one_stroke_distance,
        )
            
            # 標準B寸法
            standard_dimension_b = calculate_dimension_b(
            standard_chain_length,
            one_stroke_distance,
        )
            
            # C寸法
            dimension_c = calculate_dimension_c(
            dimension_a,
            dimension_b,
        )
            
            # 床から高い側の高さ
            high_side_height = calculate_high_side_height(
            mount_type,
            product_height,
            mount_height,
            side_holder_center_distance,
            dimension_a,
            pipe_radius,
        )
            
            # 床から低い側の高さ
            low_side_height = calculate_low_side_height(
            mount_type,
            pipe_center_height,
            side_holder_center_distance,
            dimension_b,
            pipe_radius,
        )
            
            # 標準B側床から高さ
            standard_low_side_height = calculate_low_side_height(
            mount_type,
            pipe_center_height,
            side_holder_center_distance,
            standard_dimension_b,
            pipe_radius,
        )
            
            # 指定可能A寸法範囲
            minimum_dimension_a = math.ceil(standard_chain_length / 10) * 10

            maximum_dimension_a = math.floor(
                (
                    standard_chain_length
                    + (standard_low_side_height - 10)
                ) / 10
            ) * 10

            judge_ok, judge_message = judge_chain_length(
            use_dimension_a=use_dimension_a,
            dimension_a=dimension_a,
            standard_chain_length=standard_chain_length,
            low_side_height=low_side_height,
        )
            
            st.session_state.result = {
                "judge": judge_message,
                "a": f"{dimension_a:.0f}",
                "b": f"{dimension_b:.0f}",
                "c": f"{dimension_c:.0f}",
                "high": f"{high_side_height:.0f}",
                "low": f"{low_side_height:.0f}",
                "minimum_dimension_a": minimum_dimension_a,
                "maximum_dimension_a": maximum_dimension_a,
            }

            st.success("入力チェックOKです。")

with result_col:

    st.subheader("計算結果")

    st.divider()

    st.write(f"対応可否判定：{st.session_state.result['judge']}")

    if st.session_state.result["judge"] in (
        "希望チェーン長さ(A)が短すぎます",
        "希望チェーン長さ(A)が長すぎます",
    ):

        if mount_height is None:

            st.error(
                f"""
    {screen_name}製品幅 W{product_width} × 製品高さ H{product_height} の場合

    指定できるA側希望チェーン長さ(A)は、{st.session_state.result["minimum_dimension_a"]} mm ～ {st.session_state.result["maximum_dimension_a"]} mmです。
    """
            )

        else:

            st.error(
                f"""
    {screen_name}製品幅 W{product_width} × 製品高さ H{product_height}×取付高さ TH{mount_height} の場合

    指定できるA側希望チェーン長さ(A)は、{st.session_state.result["minimum_dimension_a"]} mm ～ {st.session_state.result["maximum_dimension_a"]} mmです。
    """
            )

    st.divider()

    st.write(f"A寸法：{st.session_state.result['a']} mm")

    st.write(f"B寸法：{st.session_state.result['b']} mm")

    st.write(f"C寸法：{st.session_state.result['c']} mm")

    st.write(f"A側床から高さ(YH)：{st.session_state.result['high']} mm")

    st.write(f"B側床から高さ(YH)：{st.session_state.result['low']} mm")

with image_col:

    st.subheader("イメージ")

    st.divider()

    draw_svg()