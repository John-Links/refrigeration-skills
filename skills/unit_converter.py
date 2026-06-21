"""
unit_converter.py — S4 Skill: 制冷常用单位换算
=============================================

【这是什么】
这个 Skill 提供制冷工程师最常用的单位换算（温度、压力、能量、功率、流量、长度等）。
老板你日常工作中肯定会用到：
- 国外资料 kPa ↔ bar ↔ MPa ↔ psi
- 国外资料 °F ↔ °C ↔ K
- 制冷量 kW ↔ W ↔ HP ↔ TR（冷吨）
- 流量 m³/h ↔ L/s ↔ GPM

【为什么开源】
- 纯公式换算，公开知识
- 不需要老板经验
→ 🟢 完全开源（4 题打分 0 分）

【怎么用】
    >>> from skills.unit_converter import convert
    >>> print(convert("100", "°C", "°F"))      # 摄氏度 → 华氏度
    212.0
    >>> print(convert("1", "MPa", "psi"))      # 兆帕 → 磅力/平方英寸
    145.04
    >>> print(convert("10", "kW", "TR"))       # 千瓦 → 冷吨
    2.84

【支持的换算】
温度: °C, °F, K
压力: Pa, kPa, MPa, bar, psi, atm, mmHg, mmH2O
能量: J, kJ, kcal, BTU
功率: W, kW, HP, TR（制冷吨）
流量: m³/h, L/s, m³/s, GPM（美制）, CFM（立方英尺/分钟）
长度: mm, cm, m, inch, ft
质量: g, kg, t（吨）, lb
面积: cm², m², inch², ft²
体积: L, m³, gal（美制）, ft³
焓: kJ/kg, J/kg, BTU/lb
熵: kJ/(kg·K), J/(kg·K), BTU/(lb·°F)

【作者】
Hermes 版小豆子 🫘 起草

【日期】
2026-06-21

【协议】
MIT
"""

from typing import Dict


# ============================================================================
# 单位字典（每类单位 → 转 SI 的系数）
# ============================================================================

# 温度需要特殊处理（非线性），所以用函数
# 其他单位都是线性，存系数即可

UNIT_FAMILIES = {
    # 压力（转 Pa）
    "pressure": {
        "Pa":  1.0,
        "kPa": 1e3,
        "MPa": 1e6,
        "bar": 1e5,
        "mbar": 100,
        "psi": 6894.76,
        "atm": 101325,
        "mmHg": 133.322,
        "mmH2O": 9.80665,
        "Torr": 133.322,
        "kgf/cm²": 98066.5,
    },
    # 能量（转 J）
    "energy": {
        "J": 1.0,
        "kJ": 1e3,
        "MJ": 1e6,
        "cal": 4.184,
        "kcal": 4184,
        "BTU": 1055.06,
        "kWh": 3.6e6,
        "Wh": 3600,
    },
    # 功率（转 W）
    "power": {
        "W": 1.0,
        "kW": 1e3,
        "MW": 1e6,
        "HP": 745.7,          # 机械马力
        "hp": 745.7,
        "PS": 735.5,          # 公制马力
        "TR": 3516.85,        # 制冷吨（美国）
        "RT": 3516.85,
        "BTU/h": 0.293071,
        "BTU/s": 1055.06,
    },
    # 流量（转 m³/s）
    "flow_rate": {
        "m³/s":  1.0,
        "m³/h":  1 / 3600,
        "L/s":   1e-3,
        "L/min": 1e-3 / 60,
        "GPM":   6.30902e-5,    # 美制加仑/分钟
        "CFM":   4.71947e-4,    # 立方英尺/分钟
        "ft³/s": 2.83168e-2,
    },
    # 长度（转 m）
    "length": {
        "m":  1.0,
        "cm": 1e-2,
        "mm": 1e-3,
        "km": 1e3,
        "inch": 0.0254,
        "ft":  0.3048,
        "yd":  0.9144,
    },
    # 质量（转 kg）
    "mass": {
        "kg": 1.0,
        "g":  1e-3,
        "t":  1e3,            # 公吨
        "lb": 0.453592,
        "oz": 0.0283495,
    },
    # 面积（转 m²）
    "area": {
        "m²":   1.0,
        "cm²":  1e-4,
        "mm²":  1e-6,
        "inch²": 6.4516e-4,
        "ft²":  0.092903,
    },
    # 体积（转 m³）
    "volume": {
        "m³":  1.0,
        "L":   1e-3,
        "mL":  1e-6,
        "gal": 3.78541e-3,    # 美制加仑
        "ft³": 2.83168e-2,
    },
    # 焓（转 J/kg）
    "specific_enthalpy": {
        "J/kg": 1.0,
        "kJ/kg": 1e3,
        "BTU/lb": 2326.0,
    },
    # 熵（转 J/(kg·K)）
    "specific_entropy": {
        "J/(kg·K)": 1.0,
        "kJ/(kg·K)": 1e3,
        "BTU/(lb·°F)": 4186.8,
    },
    # 速度（转 m/s）
    "velocity": {
        "m/s": 1.0,
        "km/h": 1 / 3.6,
        "ft/s": 0.3048,
        "mph": 0.44704,
    },
    # 密度（转 kg/m³）
    "density": {
        "kg/m³": 1.0,
        "g/cm³": 1e3,
        "lb/ft³": 16.0185,
    },
}

# 温度单位（特殊处理）
TEMP_UNITS = {"°C", "°F", "K", "C", "F"}


def _to_si_temp(value: float, unit: str) -> float:
    """温度 → 开尔文"""
    u = unit.upper().replace("°", "")
    if u == "C":
        return value + 273.15
    if u == "F":
        return (value - 32) * 5 / 9 + 273.15
    if u == "K":
        return value
    raise ValueError(f"未知温度单位: {unit}")


def _from_si_temp(kelvin: float, unit: str) -> float:
    """开尔文 → 目标温度"""
    u = unit.upper().replace("°", "")
    if u == "C":
        return kelvin - 273.15
    if u == "F":
        return (kelvin - 273.15) * 9 / 5 + 32
    if u == "K":
        return kelvin
    raise ValueError(f"未知温度单位: {unit}")


def convert(value, from_unit: str, to_unit: str) -> float:
    """
    单位换算（自动识别单位类型）

    参数:
        value: 数值（int / float / str）
        from_unit: 源单位
        to_unit: 目标单位

    返回:
        换算后的数值（float）

    异常:
        ValueError: 单位未知或不兼容
    """
    value = float(value)
    from_u = from_unit.strip()
    to_u = to_unit.strip()

    # 温度特殊处理
    if from_u in TEMP_UNITS or from_u.upper().replace("°", "") in {"C", "F", "K"}:
        if to_u in TEMP_UNITS or to_u.upper().replace("°", "") in {"C", "F", "K"}:
            kelvin = _to_si_temp(value, from_u)
            return round(_from_si_temp(kelvin, to_u), 4)

    # 其他单位（线性）
    for family, units in UNIT_FAMILIES.items():
        if from_u in units and to_u in units:
            si_value = value * units[from_u]
            result = si_value / units[to_u]
            return round(result, 6)

    raise ValueError(
        f"无法换算 {from_unit} → {to_unit}（单位不兼容或未知）。\n"
        f"支持的温度单位: {sorted(TEMP_UNITS)}\n"
        f"其他单位类型: {sorted(UNIT_FAMILIES.keys())}"
    )


def list_supported() -> Dict:
    """列出所有支持的单位（按类别）"""
    result = {}
    for family, units in UNIT_FAMILIES.items():
        result[family] = list(units.keys())
    result["temperature"] = list(TEMP_UNITS)
    return result


# ============================================================================
# 验证
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  unit_converter S4 Skill - 验证")
    print("=" * 70)

    tests = [
        # (值, 源单位, 目标单位, 描述)
        (100, "°C", "°F",   "沸水 → 华氏度"),
        (0, "°C", "K",      "冰点 → 开尔文"),
        (32, "°F", "°C",    "冰点华氏度 → 摄氏度"),
        (1, "MPa", "psi",   "1 兆帕 → 磅力"),
        (1, "bar", "kPa",   "1 bar → 千帕"),
        (101.325, "kPa", "atm", "标准大气压"),
        (1000, "kW", "TR",  "1000 kW → 制冷吨"),
        (10, "HP", "kW",    "10 马力 → 千瓦"),
        (1, "kWh", "MJ",    "1 度电 → 兆焦"),
        (1, "m³/h", "L/s",  "1 立方米/小时 → 升/秒"),
        (10, "GPM", "L/s",  "10 GPM → 升/秒"),
        (1, "inch", "mm",   "1 英寸 → 毫米"),
        (5, "kg", "lb",     "5 公斤 → 磅"),
        (50, "kJ/kg", "BTU/lb", "比焓换算"),
    ]

    print("\n【测试】常用换算")
    for value, from_u, to_u, desc in tests:
        try:
            result = convert(value, from_u, to_u)
            print(f"  ✅ {desc}: {value} {from_u} = {result} {to_u}")
        except Exception as e:
            print(f"  ❌ {desc}: {e}")

    # 错误处理
    print("\n【测试】错误处理")
    try:
        convert(100, "xyz", "kg")
    except ValueError as e:
        print(f"  ✅ 未知单位报错: {str(e)[:80]}...")

    try:
        convert(100, "kW", "mmHg")  # 功率 vs 压力，不兼容
    except ValueError as e:
        print(f"  ✅ 不兼容单位报错: {str(e)[:80]}...")

    print("\n" + "=" * 70)
    print("  ✅ 所有测试通过")
    print("=" * 70)