"""refrigeration-skills: 制冷垂直 AI Agent Skills 集"""

__version__ = "1.2.0"
__author__ = "强领制冷技术（上海）有限公司"

# 第一个 Skill（已上线）
from .coolprop_query import (
    query_saturation_by_temperature,
    query_saturation_by_pressure,
    query_single_point,
    REFRIGERANT_LIST,
)

# 第二个 Skill（v1.1.0 新增）
from .coolprop_ph import generate_ph_curve

# 第三个 Skill（v1.1.0 新增）
from .coolprop_sat_table import generate_saturation_table, format_table_ascii

# 第四个 Skill（v1.1.0 新增）
from .unit_converter import convert, list_supported

# 第五个 Skill（v1.1.0 新增）
from .psychrometric import query_state

# 第六个 Skill（v1.1.0 新增）
from .pipe_pressure_drop import calc_pressure_drop

# 第七个 Skill（v1.2.0 新增）
from .coolprop_t_s import (
    generate_saturation_curve,
    generate_isotherm,
    generate_isobar,
    generate_full_ts_chart,
)

__all__ = [
    # S1
    "query_saturation_by_temperature",
    "query_saturation_by_pressure",
    "query_single_point",
    "REFRIGERANT_LIST",
    # S2
    "generate_ph_curve",
    # S3
    "generate_saturation_table",
    "format_table_ascii",
    # S4
    "convert",
    "list_supported",
    # S5
    "query_state",
    # S6
    "calc_pressure_drop",
    # S7
    "generate_saturation_curve",
    "generate_isotherm",
    "generate_isobar",
    "generate_full_ts_chart",
]