import re
import pandas as pd

TOP_LEVEL_RULES = {
    "EV / Charging": {
        "cpc_prefixes": ["B60L", "B60M", "H02J", "H01M10/44", "H01M10/42", "Y02T", "Y02E60/50", "B60L53", "B60L50"],
        "keywords": ["charging", "charger", "plug-in", "electric vehicle", "ev charging", "charge control", "on-board charger", "charging inlet", "charging cable", "charging connector", "charging socket", "dc charging", "ac charging"],
    },
    "Battery": {
        "cpc_prefixes": ["H01M", "B60L58", "Y02E60", "B60L58/10", "B60L58/12"],
        "keywords": ["battery", "cell", "state of charge", "soc", "pack", "electrolyte", "anode", "cathode", "battery module", "battery pack", "battery management", "bms", "state of health", "soh"],
    },
    "ADAS / Autonomous Driving": {
        "cpc_prefixes": ["B60W", "G05D1", "G08G", "G01C", "G06V", "B60T7", "B60Q9"],
        "keywords": ["autonomous", "adas", "driver assistance", "lane keeping", "adaptive cruise", "object detection", "perception", "parking assist", "surround view", "collision avoidance", "blind spot", "path planning", "trajectory"],
    },
    "Infotainment / HMI": {
        "cpc_prefixes": ["G06F3", "G09G", "B60K35", "G10L", "H04R"],
        "keywords": ["infotainment", "display", "hmi", "touchscreen", "user interface", "cockpit", "cluster", "voice assistant", "gesture control", "display panel", "head unit", "head-up display", "hud"],
    },
    "Connectivity": {
        "cpc_prefixes": ["H04W", "H04L", "G08C", "H04B", "H04Q"],
        "keywords": ["connectivity", "wireless", "telematics", "network", "v2x", "remote communication", "connected vehicle", "vehicle-to-vehicle", "vehicle-to-infrastructure", "antenna", "modem", "over-the-air", "ota"],
    },
    "Vehicle Control": {
        "cpc_prefixes": ["B60W", "F02D", "G05B", "B62D", "B60T", "F16H"],
        "keywords": ["vehicle control", "torque control", "brake control", "traction control", "steering control", "controller", "powertrain control", "drive mode", "suspension control", "stability control", "yaw control"],
    },
    "Off-road / Terrain": {
        "cpc_prefixes": ["B60R", "B62D", "B60K", "B60G", "E02F"],
        "keywords": ["terrain response", "off-road", "all terrain", "4x4", "traction terrain", "wading", "slope", "rock crawl", "descent control", "terrain mode", "off road", "terrain management"],
    },
    "Safety": {
        "cpc_prefixes": ["B60R21", "G08B", "A62B", "B60R22", "B60Q"],
        "keywords": ["safety", "airbag", "occupant protection", "crash", "collision mitigation", "seat belt", "child lock", "restraint", "pedestrian protection", "hazard warning", "emergency braking"],
    },
    "Thermal Management": {
        "cpc_prefixes": ["B60H", "F28D", "F25B", "F24F", "H01M10/48"],
        "keywords": ["thermal", "cooling", "heating", "heat exchanger", "temperature control", "hvac", "coolant", "radiator", "heat pump", "thermal management", "air conditioning"],
    },
    "Manufacturing / Materials": {
        "cpc_prefixes": ["B29", "C22", "C23", "B21", "B22", "B23", "C08"],
        "keywords": ["manufacturing", "material", "composite", "forming", "casting", "welding", "assembly", "molding", "pressing", "laminate", "alloy", "surface treatment", "adhesive"],
    },
}

SUBTECH_KEYWORDS = {
    "fast charging": "Fast Charging",
    "wireless charging": "Wireless Charging",
    "thermal runaway": "Thermal Safety",
    "battery pack": "Battery Pack",
    "battery management": "Battery Management",
    "navigation": "Navigation",
    "user interface": "User Interface",
    "gesture control": "Gesture Control",
    "telematics": "Telematics",
    "v2x": "V2X",
    "lane": "Lane Assistance",
    "parking assist": "Parking Assistance",
    "autonomous": "Autonomy",
    "terrain": "Terrain Management",
    "airbag": "Occupant Safety",
    "cooling": "Cooling",
    "heating": "Heating",
    "heat pump": "Heat Pump",
    "composite": "Composites",
}

SECTION_FALLBACK = {
    "H": "Connectivity",
    "G": "ADAS / Autonomous Driving",
    "B": "Vehicle Control",
    "F": "Thermal Management",
    "C": "Manufacturing / Materials",
}


def _safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _iter_cpc_codes(cpc_codes):
    text = _safe_text(cpc_codes)
    if not text:
        return []
    text = text.strip("[]")
    parts = [x.strip(" '\"") for x in re.split(r",|;", text)]
    return [p for p in parts if p]


def infer_top_level_tech(row: pd.Series) -> str:
    text = " ".join([
        _safe_text(row.get("title")),
        _safe_text(row.get("abstract")),
        _safe_text(row.get("cpc_codes")),
        _safe_text(row.get("cpc_sections")),
        _safe_text(row.get("patent_type")),
    ]).lower()

    codes = [c.upper() for c in _iter_cpc_codes(row.get("cpc_codes"))]
    sections = [s.strip().upper() for s in _safe_text(row.get("cpc_sections")).replace(";", ",").split(",") if s.strip()]

    for label, rule in TOP_LEVEL_RULES.items():
        for prefix in rule["cpc_prefixes"]:
            prefix_u = prefix.upper()
            if any(code.startswith(prefix_u) for code in codes):
                return label

    for label, rule in TOP_LEVEL_RULES.items():
        if any(keyword.lower() in text for keyword in rule["keywords"]):
            return label

    for section in sections:
        if section in SECTION_FALLBACK:
            return SECTION_FALLBACK[section]

    return "Other / Unmapped"


def infer_sub_tech(row: pd.Series) -> str:
    text = " ".join([
        _safe_text(row.get("title")),
        _safe_text(row.get("abstract")),
        _safe_text(row.get("cpc_codes")),
    ]).lower()

    for keyword, label in SUBTECH_KEYWORDS.items():
        if keyword in text:
            return label
    return ""


def add_technology_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "top_level_tech" not in out.columns:
        out["top_level_tech"] = out.apply(infer_top_level_tech, axis=1)
    else:
        out["top_level_tech"] = out["top_level_tech"].fillna("").astype(str)
        mask = out["top_level_tech"].str.strip() == ""
        if mask.any():
            out.loc[mask, "top_level_tech"] = out.loc[mask].apply(infer_top_level_tech, axis=1)

    if "sub_tech" not in out.columns:
        out["sub_tech"] = out.apply(infer_sub_tech, axis=1)
    else:
        out["sub_tech"] = out["sub_tech"].fillna("").astype(str)
        mask = out["sub_tech"].str.strip() == ""
        if mask.any():
            out.loc[mask, "sub_tech"] = out.loc[mask].apply(infer_sub_tech, axis=1)

    return out
