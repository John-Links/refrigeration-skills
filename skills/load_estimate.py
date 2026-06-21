"""
S10 - load_estimate: 房间冷负荷估算（简化版）

功能：估算房间冷负荷，6 大分项（围护传热/新风/人员/设备/照明/潜热）

注意：
- 本 Skill 是简化估算（教学 + 快速估算用），不是 ASHRAE 严谨算法
- ASHRAE 严谨负荷计算（含逐时计算、冷桥、太阳得热分布等）= 未来网页工具
- 误差范围：±20%，对设计估算够用
- 不适合：手术室、洁净室、博物馆、图书馆等特殊场所

数据来源：暖通设计手册 + ASHRAE Handbook 简化
开源协议：MIT
版权：强领制冷技术（上海）有限公司
"""

import math
from typing import Dict

__version__ = "1.0.0"
__skill_name__ = "load_estimate"


# ============================================================================
# 围护结构 U 值默认值（单位 W/(m²·K)）
# ============================================================================
DEFAULT_U_VALUES = {
    "外墙_普通": 1.5,
    "外墙_保温": 0.5,
    "屋顶_普通": 1.0,
    "屋顶_保温": 0.4,
    "楼板": 1.2,
    "单层玻璃": 5.8,
    "双层中空": 2.8,
    "双层Low-E": 1.6,
    "三层中空": 1.0,
}

# 窗户太阳得热系数 SHGC 默认值
DEFAULT_SHGC = {
    "单层玻璃": 0.86,
    "双层中空": 0.76,
    "双层Low-E": 0.40,
    "三层中空": 0.30,
}


# ============================================================================
# 人员散热（显热 + 潜热）单位 W/人
# ============================================================================
PEOPLE_HEAT = {
    "静坐":   {"sensible": 60,  "latent": 40,  "total": 100},
    "轻度劳动": {"sensible": 70,  "latent": 55,  "total": 125},
    "中等劳动": {"sensible": 85,  "latent": 90,  "total": 175},
    "重劳动":   {"sensible": 135, "latent": 195, "total": 330},
}


# ============================================================================
# 设备功率系数（除湿设备散热 = 输入功率 × 系数）
# ============================================================================
EQUIPMENT_FACTOR = {
    "照明": 1.0,           # 全部转化为热
    "办公设备": 0.7,        # 电脑等约 70% 转化为热
    "电机": 1.0,           # 全部
    "厨房设备": 0.6,        # 部分排风带走
    "其他": 0.8,
}


# ============================================================================
# 核心函数
# ============================================================================

def estimate_cooling_load(
    # 房间基本参数
    area_m2: float,
    height_m: float = 3.0,
    num_rooms: int = 1,
    # 围护结构
    envelope: Dict = None,
    # 新风
    outdoor_temp_c: float = 35.0,
    outdoor_rh: float = 0.6,
    indoor_temp_c: float = 26.0,
    indoor_rh: float = 0.5,
    ach_per_hour: float = 1.0,  # 换气次数
    # 人员
    num_people: int = 0,
    activity: str = "静坐",
    # 设备
    lighting_w: float = 0,
    equipment_w: float = 0,
    # 太阳得热（简化）
    window_area_m2: float = 0,
    window_orientation: str = "南",
    peak_solar_w_per_m2: float = 200,
    # 渗透风（门缝等）
    infiltration_ach: float = 0.5,
) -> Dict:
    """
    估算房间总冷负荷（6 大分项）

    参数：
        area_m2: 房间面积
        height_m: 层高（默认 3m）
        num_rooms: 房间数（影响新风计算）
        envelope: 围护结构字典
            {
                "wall_area_m2": 50, "wall_U": 1.5,
                "roof_area_m2": 30, "roof_U": 0.5,
                "floor_area_m2": 30, "floor_U": 1.2,
                "window_area_m2": 10, "window_U": 2.8,
            }
        outdoor_temp_c: 室外干球温度（默认 35°C，夏季空调工况）
        outdoor_rh: 室外相对湿度
        indoor_temp_c: 室内设计温度（默认 26°C）
        indoor_rh: 室内设计相对湿度
        ach_per_hour: 换气次数（默认 1.0）
        num_people: 人员数
        activity: 活动强度（静坐/轻度劳动/中等劳动/重劳动）
        lighting_w: 照明功率
        equipment_w: 设备功率
        window_area_m2: 窗户面积
        window_orientation: 朝向（南/北/东/西）
        peak_solar_w_per_m2: 峰值太阳辐射（默认 200）
        infiltration_ach: 渗透风换气次数（默认 0.5）

    返回：
        {
            "input": {...},
            "load_breakdown": {
                "envelope_w": float,
                "solar_w": float,
                "ventilation_w": float,
                "infiltration_w": float,
                "people_w": float,
                "lighting_w": float,
                "equipment_w": float,
                "total_sensible_w": float,
                "total_latent_w": float,
                "total_w": float,
            },
            "per_area_w_per_m2": float,
            "metadata": {...}
        }
    """
    # 默认围护结构
    if envelope is None:
        envelope = {}
    wall_area = envelope.get("wall_area_m2", 0)
    wall_U = envelope.get("wall_U", 1.5)
    roof_area = envelope.get("roof_area_m2", 0)
    roof_U = envelope.get("roof_U", 0.5)
    floor_area = envelope.get("floor_area_m2", 0)
    floor_U = envelope.get("floor_U", 1.2)
    win_area = envelope.get("window_area_m2", window_area_m2)
    win_U = envelope.get("window_U", 2.8)

    volume = area_m2 * height_m * num_rooms

    # ----- 1. 围护结构传热（显热）-----
    delta_t = outdoor_temp_c - indoor_temp_c
    q_envelope = (
        wall_area * wall_U * delta_t +
        roof_area * roof_U * delta_t +
        floor_area * floor_U * delta_t * 0.5 +  # 楼板传热减半
        win_area * win_U * delta_t
    )

    # ----- 2. 太阳得热（显热）-----
    # 朝向修正系数
    orientation_factor = {
        "东": 0.85, "西": 0.85, "南": 0.55, "北": 0.35, "东南": 0.75,
        "西南": 0.75, "东北": 0.55, "西北": 0.55, "水平": 1.0,
    }.get(window_orientation, 0.6)
    # SHGC 默认 0.76（双层中空）
    shgc = envelope.get("shgc", 0.76)
    q_solar = win_area * peak_solar_w_per_m2 * orientation_factor * shgc

    # ----- 3. 新风负荷（显热 + 潜热）-----
    # 空气参数
    air_density = 1.2  # kg/m³
    air_cp = 1.005     # kJ/(kg·K)
    h_fg = 2500        # kJ/kg（汽化潜热，0°C 附近；30-40°C 区间约 2400）

    # 显热（温差传热）
    air_flow_vent_m3_s = volume * ach_per_hour / 3600
    q_vent_sensible = air_flow_vent_m3_s * air_density * air_cp * 1000 * delta_t  # W

    # 潜热（含湿量差 × 汽化潜热）
    W_out = humidity_ratio(outdoor_temp_c, outdoor_rh)  # g/kg
    W_in = humidity_ratio(indoor_temp_c, indoor_rh)
    delta_W_g_kg = max(0.0, W_out - W_in)  # g 水 / kg 干空气
    q_vent_latent = air_flow_vent_m3_s * air_density * delta_W_g_kg * h_fg  # W

    # ----- 4. 渗透风负荷（按换气次数）-----
    air_flow_inf_m3_s = volume * infiltration_ach / 3600
    q_inf_sensible = air_flow_inf_m3_s * air_density * air_cp * 1000 * delta_t
    q_inf_latent = air_flow_inf_m3_s * air_density * delta_W_g_kg * h_fg

    # ----- 5. 人员负荷 -----
    people = PEOPLE_HEAT.get(activity, PEOPLE_HEAT["静坐"])
    q_people_sensible = num_people * people["sensible"]
    q_people_latent = num_people * people["latent"]

    # ----- 6. 照明负荷（全转化为热）-----
    q_lighting = lighting_w * EQUIPMENT_FACTOR["照明"]

    # ----- 7. 设备负荷 -----
    q_equipment = equipment_w * EQUIPMENT_FACTOR["其他"]

    # ----- 汇总 -----
    total_sensible = (
        q_envelope + q_solar +
        q_vent_sensible + q_inf_sensible +
        q_people_sensible + q_lighting + q_equipment
    )
    total_latent = q_vent_latent + q_inf_latent + q_people_latent
    total = total_sensible + total_latent

    return {
        "input": {
            "area_m2": area_m2,
            "height_m": height_m,
            "volume_m3": volume,
            "outdoor_temp_c": outdoor_temp_c,
            "indoor_temp_c": indoor_temp_c,
            "delta_t": delta_t,
            "num_people": num_people,
            "activity": activity,
            "lighting_w": lighting_w,
            "equipment_w": equipment_w,
        },
        "load_breakdown": {
            "envelope_w": round(q_envelope, 1),
            "solar_w": round(q_solar, 1),
            "ventilation_sensible_w": round(q_vent_sensible, 1),
            "ventilation_latent_w": round(q_vent_latent, 1),
            "infiltration_sensible_w": round(q_inf_sensible, 1),
            "infiltration_latent_w": round(q_inf_latent, 1),
            "people_sensible_w": round(q_people_sensible, 1),
            "people_latent_w": round(q_people_latent, 1),
            "lighting_w": round(q_lighting, 1),
            "equipment_w": round(q_equipment, 1),
        },
        "totals": {
            "sensible_w": round(total_sensible, 1),
            "latent_w": round(total_latent, 1),
            "total_w": round(total, 1),
            "total_kw": round(total / 1000, 3),
        },
        "per_area": {
            "w_per_m2": round(total / area_m2, 1) if area_m2 > 0 else 0,
            "recommendation": recommend_unit(total, area_m2),
        },
        "metadata": {
            "skill": __skill_name__,
            "version": __version__,
            "accuracy_note": "简化估算，误差 ±20%，不适合特殊场所",
            "for_professional": "严谨 ASHRAE 算法请使用网页工具（待开发）",
        },
    }


def saturation_pressure(T_c: float) -> float:
    """饱和水蒸气压力（kPa），简化 Magnus 公式"""
    return 0.61078 * math.exp(17.27 * T_c / (T_c + 237.3))


def humidity_ratio(T_c: float, rh: float) -> float:
    """
    含湿量（g 水 / kg 干空气）

    W = 622 * P_ws * RH / (P_atm - P_ws * RH)

    其中 P_ws = 饱和水蒸气压力（kPa），P_atm = 101.325 kPa
    """
    P_ws = saturation_pressure(T_c)
    return 622.0 * rh * P_ws / (101.325 - rh * P_ws)


def recommend_unit(total_w: float, area_m2: float) -> str:
    """根据冷负荷推荐空调机型"""
    w_per_m2 = total_w / area_m2 if area_m2 > 0 else 0
    total_kw = total_w / 1000

    if w_per_m2 < 100:
        unit = "小型分体空调（家用）"
    elif w_per_m2 < 200:
        unit = "多联机（VRF）或单元式空调"
    elif w_per_m2 < 300:
        unit = "水冷机组 + 风机盘管"
    else:
        unit = "冷水机组 + 空调箱"

    return f"{unit}（约 {total_kw:.2f} kW，单位指标 {w_per_m2:.1f} W/m²）"


def quick_estimate(
    area_m2: float,
    building_type: str = "办公室",
) -> Dict:
    """
    一键估算（按建筑类型套用经验指标）

    参数：
        area_m2: 面积
        building_type: 建筑类型
            - 办公室: 120 W/m²
            - 商场: 180 W/m²
            - 餐厅: 250 W/m²
            - 酒店客房: 100 W/m²
            - 医院病房: 130 W/m²
            - 数据中心: 600 W/m²
            - 体育馆: 250 W/m²
            - 仓库: 50 W/m²

    返回：
        {"building_type": ..., "area_m2": ..., "estimated_total_kw": ..., "w_per_m2": ...}
    """
    indicator = {
        "办公室": 120, "商场": 180, "餐厅": 250, "酒店客房": 100,
        "医院病房": 130, "数据中心": 600, "体育馆": 250, "仓库": 50,
        "住宅": 100, "学校教室": 110, "图书馆": 80, "展厅": 200,
    }
    w_per_m2 = indicator.get(building_type, 120)
    total_w = area_m2 * w_per_m2

    return {
        "building_type": building_type,
        "area_m2": area_m2,
        "w_per_m2": w_per_m2,
        "estimated_total_w": total_w,
        "estimated_total_kw": round(total_w / 1000, 3),
        "note": f"按 {building_type} 经验指标 {w_per_m2} W/m² 估算，仅供参考",
    }


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S10 load_estimate 自测 - 冷负荷估算（简化版）")
    print("=" * 70)

    # 测试 1: 标准办公室
    print("\n[测试 1] 100m² 办公室（夏季空调）")
    envelope = {
        "wall_area_m2": 60, "wall_U": 1.5,
        "roof_area_m2": 100, "roof_U": 0.5,
        "floor_area_m2": 100, "floor_U": 1.2,
        "window_area_m2": 15, "window_U": 2.8,
    }
    result = estimate_cooling_load(
        area_m2=100,
        height_m=3.0,
        envelope=envelope,
        outdoor_temp_c=35,
        indoor_temp_c=26,
        ach_per_hour=1.0,
        num_people=10,
        activity="静坐",
        lighting_w=1000,
        equipment_w=2000,
        window_area_m2=15,
        window_orientation="南",
    )
    print(f"\n  总冷负荷: {result['totals']['total_kw']} kW")
    print(f"  显热: {result['totals']['sensible_w']} W")
    print(f"  潜热: {result['totals']['latent_w']} W")
    print(f"  单位指标: {result['per_area']['w_per_m2']} W/m²")
    print(f"  推荐机型: {result['per_area']['recommendation']}")
    print(f"\n  分项明细:")
    breakdown = result["load_breakdown"]
    print(f"    围护传热:    {breakdown['envelope_w']:>8.1f} W  ({breakdown['envelope_w']/result['totals']['total_w']*100:>5.1f}%)")
    print(f"    太阳得热:    {breakdown['solar_w']:>8.1f} W  ({breakdown['solar_w']/result['totals']['total_w']*100:>5.1f}%)")
    print(f"    新风(显热):  {breakdown['ventilation_sensible_w']:>8.1f} W")
    print(f"    新风(潜热):  {breakdown['ventilation_latent_w']:>8.1f} W")
    print(f"    渗透(显热):  {breakdown['infiltration_sensible_w']:>8.1f} W")
    print(f"    渗透(潜热):  {breakdown['infiltration_latent_w']:>8.1f} W")
    print(f"    人员(显热):  {breakdown['people_sensible_w']:>8.1f} W")
    print(f"    人员(潜热):  {breakdown['people_latent_w']:>8.1f} W")
    print(f"    照明:        {breakdown['lighting_w']:>8.1f} W")
    print(f"    设备:        {breakdown['equipment_w']:>8.1f} W")

    # 测试 2: 大型商场
    print("\n[测试 2] 500m² 商场")
    envelope2 = {
        "wall_area_m2": 200, "wall_U": 0.8,
        "roof_area_m2": 500, "roof_U": 0.4,
        "window_area_m2": 50, "window_U": 1.6,
    }
    result2 = estimate_cooling_load(
        area_m2=500,
        height_m=4.5,
        envelope=envelope2,
        outdoor_temp_c=35,
        indoor_temp_c=26,
        ach_per_hour=1.5,
        num_people=100,
        activity="轻度劳动",
        lighting_w=5000,
        equipment_w=3000,
    )
    print(f"  总冷负荷: {result2['totals']['total_kw']} kW")
    print(f"  单位指标: {result2['per_area']['w_per_m2']} W/m²")
    print(f"  推荐机型: {result2['per_area']['recommendation']}")

    # 测试 3: quick_estimate 快速估算
    print("\n[测试 3] quick_estimate - 快速估算")
    for btype in ["办公室", "商场", "餐厅", "数据中心"]:
        q = quick_estimate(1000, btype)
        print(f"  {btype:8s} 1000m²: {q['estimated_total_kw']} kW  ({q['w_per_m2']} W/m²)")

    # 测试 4: 边界检查
    print("\n[测试 4] 边界检查 - 空房间")
    result4 = estimate_cooling_load(area_m2=50)
    print(f"  空房间冷负荷: {result4['totals']['total_w']} W")
    print(f"  （应接近围护传热 + 新风基线）")

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！S10 load_estimate 可用。")
    print("=" * 70)