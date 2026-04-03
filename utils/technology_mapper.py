import re
import pandas as pd

TOP_LEVEL_RULES = {
    "EV / Charging": {
        "cpc_prefixes": ["B60L", "B60M", "H02J", "H01M10/44", "H01M10/42", "Y02T"],
        "keywords": ["charging", "charger", "plug-in", "electric vehicle", "ev charging", "charge control", "on-board charger"],
    },
    "Battery": {
        "cpc_prefixes": ["H01M", "B60L58", "Y02E60"],
        "keywords": ["battery", "cell", "state of charge", "soc", "pack", "electrolyte", "anode", "cathode"],
    },
    "ADAS / Autonomous Driving": {
        "cpc_prefixes": ["B60W", "G05D1", "G08G", "G01C", "G06V"],
        "keywords": ["autonomous", "adas", "driver assistance", "lane keeping", "adaptive cruise", "object detection", "perception"],
    },
    "Infotainment / HMI": {
        "cpc_prefixes": ["G06F3", "G09G", "B60K35"],
        "keywords": ["infotainment", "display", "hmi", "touchscreen", "user interface", "cockpit", "cluster"],
    },
    "Connectivity": {
        "cpc_prefixes": ["H04W", "H04L", "G08C"],
        "keywords": ["connectivity", "wireless", "telematics", "network", "v2x", "remote communication", "connected vehicle"],
    },
    "Vehicle Control": {
        "cpc_prefixes": ["B60W", "F02D", "G05B"],
        "keywords": ["vehicle control", "torque control", "brake control", "traction control", "steering control", "controller"],
    },
    "Off-road / Terrain": {
        "cpc_prefixes": ["B60R", "B62D", "B60K"],
        "keywords": ["terrain response", "off-road", "all terrain", "4x4", "traction terrain", "wading", "slope"],
    },
    "Safety": {
        "cpc_prefixes": ["B60R21", "G08B", "A62B"],
        "keywords": ["safety", "airbag", "occupant protection", "crash", "collision mitigation", "seat belt"],
    },
    "Thermal Management": {
        "cpc_prefixes": ["B60H", "F28D", "F25B"],
        "keywords": ["thermal", "cooling", "heating", "heat exchanger", "temperature control", "hvac"],
    },
    "Manufacturing / Materials": {
        "cpc_prefixes": ["B29", "C22", "C23", "B21", "B22"],
        "keywords": ["manufacturing", "material", "composite", "forming", "casting", "welding", "assembly"],
    },
}

SUBTECH_KEYWORDS = {
    "fast charging": "Fast Charging",
    "wireless charging": "Wireless Charging",
    "thermal runaway": "Thermal Safety",
    "battery pack": "Battery Pack",
    "navigation": "Navigation",
    "user interface": "User Interface",
    "telematics": "Telematics",
    "v2x": "V2X",
    "lane": "Lane Assistance",
    "autonomous": "Autonomy",
    "terrain": "Terrain Management",
    "airbag": "Occupant Safety",
    "cooling": "Cooling",
    "heating": "Heating",
    "composite": "Composites",
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
    parts = [x.strip(" '\"") for x in text.split(",")]
    return [p for p in parts if p]

def infer_top_level_tech(row: pd.Series) -> str:
    text = " ".join([
        _safe_text(row.get("title")),
        _safe_text(row.get("abstract")),
        _safe_text(row.get("cpc_codes")),
        _safe_text(row.get("cpc_sections")),
    ]).lower()

    codes = [c.upper() for c in _iter_cpc_codes(row.get("cpc_codes"))]

    for label, rule in TOP_LEVEL_RULES.items():
        for prefix in rule["cpc_prefixes"]:
            prefix_u = prefix.upper()
            if any(code.startswith(prefix_u) for code in codes):
                return label

    for label, rule in TOP_LEVEL_RULES.items():
        if any(keyword.lower() in text for keyword in rule["keywords"]):
            return label

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
