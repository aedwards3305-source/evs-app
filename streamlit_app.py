import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Tuple
import base64
import time

# ---------------------- App meta ----------------------
st.set_page_config(page_title="EVS Ops Assessment", layout="wide")
st.title("EVS Inspection & Operational Assessment — Multi-Hospital")
APP_VERSION = "v4.3.0"
st.caption("Create Systems → Hospitals → Campuses, collect inspections by month, and roll up metrics by campus, hospital, or system.")
PERIOD_PLACEHOLDER = "(create new)"

# =============================================================
# Constants and Templates
# =============================================================
DEFAULT_WEIGHTS: Dict[str, float] = {
    "financial_pip": 0.30,
    "system_standards": 0.10,
    "bci": 0.60,
}

# NOTE: None means "exclude from denominator"
DEFAULT_RESPONSE_MAPS: Dict[str, Dict[str, float | None]] = {
    "contractual_pip": {"Yes": 1.0, "Partial": 0.25, "No": 0.0, "N/A": None},
    "system_standards": {"Yes": 1.0, "Partial": 0.5, "No": 0.0, "N/A": None},
    "bci": {"Pass": 1.0, "Partial": 0.5, "Fail": 0.0, "N/A": None},
}

# =============================================================
# Photo helpers (for camera/upload features)
# =============================================================
def _bytes_to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")

def _ensure_photos_container(campus: Dict, period: str) -> None:
    ph = campus.setdefault("photos", {})
    ph.setdefault(period, [])

def build_evs_template() -> Dict:
    """Campus template with your sections, checklists, and photos storage."""
    bci_areas = {
        "Entrance and Lobby": [
            "Are entrance areas free of cigarette butts and litter?",
            "Are mats clean and in proper position?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are cigarette urns, exterior urns and trash containers clean and properly lined?",
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
        ],
        "Restrooms": [
            "Are floors clean and free of dirt, spills, litter and are grout lines clean?",
            "Are all fixtures (sinks, toilets, tubs, water fountain, etc.) clean and mineral free?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are waste containers clean, properly lined and in proper condition?",
            "Are supply dispensers clean and adequately filled?",
            "Is room odor free?",
        ],
        "Corridors": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are walls windows, glass, mirrors and doors free of marks and finger smears?",
            "Are waste containers clean, properly lined and in proper condition?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
            "Are fixtures (sinks, water fountain, etc.) soap and mineral free?",
        ],
        "Elevators": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are walls are clean and free of smudges and marks?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are elevator tracks clean?",
        ],
        "Stairs": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are walls, hand rails and doors clean and free of smudges and marks?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are fire extinguisher cabinets/closets clean?",
        ],
        "Support Rooms (Conference and Training)": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are waste containers clean, properly lined and in proper condition?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
            "Are fixtures (sinks, water fountain, etc.) soap and mineral free?",
        ],
        "Patient/Resident Room (4 rooms)": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are waste containers clean and properly lined and in proper condition?",
            "Is the patient bed clean including side rails, headboard, footboard, frame and wheels?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
            "Are tent cards in patient room?",
            "Are curtains, drapes and linens free of spots and dust?",
            "Are all fixtures (sinks, toilets, tubs, water fountain, etc.) soap and mineral free?",
            "Are supply dispensers clean and adequately filled?",
            "Are the Que's of Clean completed in the Bathroom?",
            "Is the room odor free?",
        ],
        "Operating Rooms, Corridor and Core": [
            "Are the floors clean and free of visible debris and have the proper finish?",
            "Are the vents and exhaust fans dust free?",
            "Are the walls, doors and windows clean and with no spot or stains?",
            "Are trash cans clean, emptied and lined?",
            "Is the Equipment in EVS scope of services clean and sanitized to include behind and under equipment?",
            "Are ledges and other horizontal surfaces clean and dust free?",
            "Are all fixtures (scrub sinks, water fountain, etc.) soap and mineral free?",
            "Are supply dispensers clean and adequately filled?",
            "Is the room terminally cleaned within 24 hours after procedures?",
        ],
        "Sterile Processing Department": [
            "Are the floors clean and free of visible debris and have the proper finish?",
            "Are the vents and exhaust fans dust free?",
            "Are the walls, doors and windows clean and with no spot or stains?",
            "Are trash cans clean, emptied and lined?",
            "Is the Equipment in EVS scope of services clean and sanitized to include behind and under equipment?",
            "Are ledges and other horizontal surfaces clean and dust free?",
            "Are all fixtures (scrub sinks, water fountain, etc.) soap and mineral free?",
            "Are supply dispensers clean and adequately filled?",
        ],
        "Emergency Department": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are trash cans clean, emptied and lined?",
            "Are patient beds clean including side rails, headboard, footboard, frame and wheels?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
            "Are curtains, drapes and linens free of spots and dust?",
            "Are all fixtures (sinks, toilets, tubs, water fountain, etc.) soap and mineral free?",
            "Are supply dispensers clean and adequately filled?",
            "Is the room odor free?",
        ],
        "Offices (4 rooms)": [
            "Are floors finished with depth shine and/or carpets are clean and fresh?",
            "Are ledges, lights, vents and registers clean and free of dust?",
            "Are walls, windows, glass, mirrors and doors free of marks and finger smears?",
            "Are trash cans clean, emptied and lined?",
            "Are furniture, cabinets and locker exteriors dust free and clean?",
            "Are restrooms clean and free of trash?",
            "Are telephones clean and free of dust?",
            "Are all fixtures (sinks, toilets, tubs, water fountain, etc.) soap and mineral free?",
            "Are supply dispensers clean and adequately filled?",
        ],
    }

    contractual_pip_items = [
        "Qualtrics Patient Satisfaction Scores Cleanliness",
        "Qualtrics Patient Satisfaction Scores Courtesy",
        "Overall Discharge Clean Compliance Percent of Stat Rooms cleaned within 60 minutes and Routine rooms within 120 minutes equal to or above MHHS PIP Target?",
        "Virtual Manager Utilization Percentage",
        "ATP Compliance YTD equal to or above the PIP Targets?",
        "Linen Clean Reject Rate",
        "Linen Overall Fill Rate",
        "Linen Overall On time Delivery",
        "Is the Linen Utilization Pounds Per Adjusted Patient Day equal to or below the PIP Target?",
        "Is Contract Service - Housekeeping Fees and Expenses below YTD budget",
        "Is Chemicals Expenses below YTD budget",
        "Is Housekeeping Supplies expenses below YTD budget",
    ]

    system_standard_items = [
        "Is My Rounding program in place and maintained per Compass requirements (incl. feedback, service recovery communication)?",
        "Has EVS implemented Right Person/Right Place to evaluate unit scores and dedicate staff accordingly?",
        "Is patient scripting conducted daily (verified)?",
        "Does EVS management conduct observations for 10 Step Cleaning & QA of rooms daily (≥2 per employee per month) and meet Compass targets?",
        "Are Nurse Roundings conducted by EVS leadership and at/above Compass YTD targets?",
        "Is EVS equipment in good working order with no dirt buildup?",
    ]

    operational_info = [
        "YTD Adjusted Patient Days variance to budget",
        "YTD Discharge Cleans",
        "ATP swabs completed YTD?",
        "Stat Rooms percent of total discharge cleans?",
        "Bed Turnaround time for Stat Rooms cleans % compliant in 60 min",
        "Bed Turnaround time for Regular Room cleans % compliant in 120 min.",
        "Stat rooms % rooms occupied w/in 90 min",
        "Stat rooms % rooms occupied w/in 60 min",
        "Does Facility use Auto Stat function for bed to designate bed clean status in Bed Management?",
        "Open Positions",
    ]

    campus = {
        "meta": {
            "system": "",
            "hospital": "",
            "campus": "",
            "date": "",
            "assessed_by": "",
            "evs_manager": "",
        },
        "periods": [],
        "sections": {
            "operational_info": [
                {"name": k, "values": {}, "comments": {}} for k in operational_info
            ],
            "contractual_pip": [
                {"name": k, "responses": {}, "comments": {}} for k in contractual_pip_items
            ],
            "system_standards": [
                {"name": k, "responses": {}, "comments": {}} for k in system_standard_items
            ],
            "bci": {
                "areas": {
                    area: [
                        {"name": q, "points": 1.0, "responses": {}, "comments": {}}
                        for q in qs
                    ]
                    for area, qs in bci_areas.items()
                }
            },
        },
        "photos": {},  # NEW: maps period -> list of {b64, caption, ts}
    }
    return campus

# =============================================================
# Initialization & Migration
# =============================================================

def _new_empty_doc() -> Dict:
    return {
        "systems": {},
        "weights": DEFAULT_WEIGHTS.copy(),
        "response_maps": json.loads(json.dumps(DEFAULT_RESPONSE_MAPS)),
        "version": 4,
    }

def ensure_system(name: str) -> None:
    if name and name not in st.session_state.doc["systems"]:
        st.session_state.doc["systems"][name] = {"hospitals": {}}

def ensure_hospital(sys: str, hosp: str) -> None:
    ensure_system(sys)
    sysobj = st.session_state.doc["systems"][sys]
    if hosp and hosp not in sysobj["hospitals"]:
        sysobj["hospitals"][hosp] = {"campuses": {}}

def ensure_campus(sys: str, hosp: str, camp: str) -> None:
    ensure_hospital(sys, hosp)
    hospobj = st.session_state.doc["systems"][sys]["hospitals"][hosp]
    if camp and camp not in hospobj["campuses"]:
        hospobj["campuses"][camp] = build_evs_template()
        hospobj["campuses"][camp]["meta"].update({"system": sys, "hospital": hosp, "campus": camp})

def _migrate_old_doc(old_doc: Dict | None) -> Dict:
    """Migrate v2/v3 single-facility docs to v4 multi-hospital."""
    new_doc = _new_empty_doc()
    if not isinstance(old_doc, dict):
        return new_doc
    if "facilities" in old_doc and isinstance(old_doc["facilities"], dict) and old_doc["facilities"]:
        sys_name = old_doc.get("system_name", "Migrated System")
        new_doc["systems"][sys_name] = {"hospitals": {}}
        for fac_name, fac_data in old_doc["facilities"].items():
            campus = build_evs_template()
            if isinstance(fac_data, dict):
                if isinstance(fac_data.get("sections"), dict):
                    campus["sections"] = fac_data["sections"]
                if isinstance(fac_data.get("periods"), list):
                    campus["periods"] = fac_data["periods"]
                if isinstance(fac_data.get("meta"), dict):
                    campus["meta"].update({
                        "date": fac_data["meta"].get("date", ""),
                        "assessed_by": fac_data["meta"].get("assessed_by", ""),
                        "evs_manager": fac_data["meta"].get("evs_manager", ""),
                    })
            campus["meta"].update({"system": sys_name, "hospital": fac_name, "campus": "Main Campus"})
            new_doc["systems"][sys_name]["hospitals"][fac_name] = {"campuses": {"Main Campus": campus}}
        if "weights" in old_doc:
            new_doc["weights"] = old_doc["weights"]
        if "response_maps" in old_doc:
            new_doc["response_maps"] = old_doc["response_maps"]
        return new_doc
    return new_doc

# Put a valid doc in session
_doc = st.session_state.get("doc")
if not isinstance(_doc, dict) or "systems" not in _doc:
    st.session_state.doc = _migrate_old_doc(_doc)
else:
    st.session_state.doc.setdefault("systems", {})
    st.session_state.doc.setdefault("weights", DEFAULT_WEIGHTS.copy())
    st.session_state.doc.setdefault("response_maps", json.loads(json.dumps(DEFAULT_RESPONSE_MAPS)))
    st.session_state.doc.setdefault("version", 4)

# =============================================================
# Scoring helpers
# =============================================================

def score_section_responses(rows: List[Dict], period: str, resp_map: Dict[str, float | None]) -> Tuple[float, float]:
    score = 0.0
    denom = 0.0
    for r in rows:
        resp = r.get("responses", {}).get(period, None)
        mult = resp_map.get(resp, None) if resp is not None else None
        if mult is None:
            continue
        score += 1.0 * float(mult)
        denom += 1.0
    return score, denom

def score_bci_area(items: List[Dict], period: str, resp_map: Dict[str, float | None]) -> Tuple[float, float]:
    score = 0.0
    denom = 0.0
    for it in items:
        pts = float(it.get("points", 1) or 1)
        resp = it.get("responses", {}).get(period, None)
        mult = resp_map.get(resp, None) if resp is not None else None
        if mult is None:
            continue
        score += pts * float(mult)
        denom += pts
    return score, denom

def compute_period_components(campus: Dict, period: str, maps: Dict[str, Dict]) -> Dict:
    areas = campus["sections"]["bci"]["areas"]
    bci_by_dim: Dict[str, Tuple[float, float]] = {}
    bci_total_s = 0.0
    bci_total_d = 0.0
    for area, items in areas.items():
        s, d = score_bci_area(items, period, maps["bci"])
        bci_by_dim[area] = (s, d)
        bci_total_s += s
        bci_total_d += d
    pip_s, pip_d = score_section_responses(campus["sections"]["contractual_pip"], period, maps["contractual_pip"])
    sys_s, sys_d = score_section_responses(campus["sections"]["system_standards"], period, maps["system_standards"])
    return {"bci_by_dimension": bci_by_dim, "bci_total": (bci_total_s, bci_total_d), "pip": (pip_s, pip_d), "sys": (sys_s, sys_d)}

def summarise_from_components(comp: Dict, weights: Dict[str, float]) -> Dict:
    bci_pct_by_dim = {a: (s / d * 100 if d else 0.0) for a, (s, d) in comp["bci_by_dimension"].items()}
    bs, bd = comp["bci_total"]
    bci_overall = (bs / bd * 100) if bd else 0.0
    ps, pd = comp["pip"]
    pip_pct = (ps / pd * 100) if pd else 0.0
    ss, sd = comp["sys"]
    sys_pct = (ss / sd * 100) if sd else 0.0
    weighted = pip_pct * weights["financial_pip"] + sys_pct * weights["system_standards"] + bci_overall * weights["bci"]
    return {
        "bci_by_dimension": {k: round(v, 1) for k, v in bci_pct_by_dim.items()},
        "bci_overall": round(bci_overall, 1),
        "operational": {
            "financial_pip": round(pip_pct, 1),
            "system_standards": round(sys_pct, 1),
            "bci": round(bci_overall, 1),
            "weighted": round(weighted, 1),
        },
    }

def aggregate_components(components: List[Dict]) -> Dict:
    agg = {"bci_by_dimension": {}, "bci_total": (0.0, 0.0), "pip": (0.0, 0.0), "sys": (0.0, 0.0)}
    for comp in components:
        for area, (s, d) in comp["bci_by_dimension"].items():
            ss, dd = agg["bci_by_dimension"].get(area, (0.0, 0.0))
            agg["bci_by_dimension"][area] = (ss + s, dd + d)
        bs, bd = agg["bci_total"]
        cs, cd = comp["bci_total"]
        agg["bci_total"] = (bs + cs, bd + cd)
        ps, pd = agg["pip"]
        ps2, pd2 = comp["pip"]
        agg["pip"] = (ps + ps2, pd + pd2)
        ss, sd = agg["sys"]
        ss2, sd2 = comp["sys"]
        agg["sys"] = (ss + ss2, sd + sd2)
    return agg

def migrate_period_label(campus: Dict, old_label: str, new_label: str) -> None:
    """Move any data saved under a placeholder period label to the new label."""
    if not old_label or not new_label or old_label == new_label:
        return
    # Operational Info
    for r in campus["sections"]["operational_info"]:
        if old_label in r["values"]:
            r["values"].setdefault(new_label, r["values"][old_label])
            r["values"].pop(old_label, None)
        if old_label in r["comments"]:
            r["comments"].setdefault(new_label, r["comments"][old_label])
            r["comments"].pop(old_label, None)
    # Contractual & System Standards
    for section in ["contractual_pip", "system_standards"]:
        for r in campus["sections"][section]:
            if old_label in r["responses"]:
                r["responses"].setdefault(new_label, r["responses"][old_label])
                r["responses"].pop(old_label, None)
            if old_label in r["comments"]:
                r["comments"].setdefault(new_label, r["comments"][old_label])
                r["comments"].pop(old_label, None)
    # BCI
    for items in campus["sections"]["bci"]["areas"].values():
        for it in items:
            if old_label in it["responses"]:
                it["responses"].setdefault(new_label, it["responses"][old_label])
                it["responses"].pop(old_label, None)
            if old_label in it["comments"]:
                it["comments"].setdefault(new_label, it["comments"][old_label])
                it["comments"].pop(old_label, None)

# =============================================================
# Sidebar — Hierarchy, Periods, Scoring Maps, Save/Load
# =============================================================
with st.sidebar:
    st.header("Hierarchy")

    # One-run flags (must be handled BEFORE creating widgets)
    if st.session_state.get("clear_new_period_flag"):
        st.session_state["new_period_input"] = ""
        st.session_state["clear_new_period_flag"] = False

    # Commit handlers for Add-or-Select flows (must run BEFORE widgets)
    if st.session_state.get("sys_add_commit"):
        name = (st.session_state.get("sys_new_name") or "").strip()
        if name:
            ensure_system(name)
            st.session_state["sys_select"] = name
        st.session_state["sys_add_commit"] = False
        st.session_state["clear_sys_new_flag"] = True
        st.rerun()

    if st.session_state.get("hosp_add_commit"):
        name = (st.session_state.get("hosp_new_name") or "").strip()
        parent = st.session_state.get("hosp_new_parent_sys")
        if name and parent:
            ensure_hospital(parent, name)
            st.session_state["sys_select"] = parent
            st.session_state["hosp_select"] = name
        st.session_state["hosp_add_commit"] = False
        st.session_state["clear_hosp_new_flag"] = True
        st.rerun()

    if st.button("🔄 Reset App (clear session)"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    # -------- System (Hospital Set): Add-or-Select --------
    sys_names = sorted(list(st.session_state.doc["systems"].keys()))
    SYS_ADD_LABEL = "➕ Add new system…"
    sys_options = sys_names + [SYS_ADD_LABEL] if sys_names else [SYS_ADD_LABEL]

    # validate stored selection before widget is created
    if "sys_select" not in st.session_state or st.session_state["sys_select"] not in sys_options:
        st.session_state["sys_select"] = sys_options[0]

    selected_sys = st.selectbox("System (Hospital Set)", sys_options, key="sys_select")

    if selected_sys == SYS_ADD_LABEL:
        if st.session_state.get("clear_sys_new_flag"):
            st.session_state["sys_new_input"] = ""
            st.session_state["clear_sys_new_flag"] = False
        new_sys_name = st.text_input("New system name", placeholder="e.g., Memorial Hermann", key="sys_new_input")
        if st.button("Add system", key="sys_add_button") and new_sys_name.strip():
            st.session_state["sys_new_name"] = new_sys_name.strip()
            st.session_state["sys_add_commit"] = True
            st.rerun()
        # Halt until a real system is selected
        st.stop()
    else:
        current_sys = selected_sys

    # -------- Hospital: Add-or-Select (scoped to current system) --------
    hosp_names = sorted(list(st.session_state.doc["systems"][current_sys]["hospitals"].keys()))
    HOSP_ADD_LABEL = "➕ Add new hospital…"
    hosp_options = hosp_names + [HOSP_ADD_LABEL] if hosp_names else [HOSP_ADD_LABEL]

    if "hosp_select" not in st.session_state or st.session_state["hosp_select"] not in hosp_options:
        st.session_state["hosp_select"] = hosp_options[0]

    selected_hosp = st.selectbox("Hospital", hosp_options, key="hosp_select")

    if selected_hosp == HOSP_ADD_LABEL:
        if st.session_state.get("clear_hosp_new_flag"):
            st.session_state["hosp_new_input"] = ""
            st.session_state["clear_hosp_new_flag"] = False
        new_hosp_name = st.text_input("New hospital name", placeholder="e.g., Cypress Hospital", key="hosp_new_input")
        if st.button("Add hospital", key="hosp_add_button") and new_hosp_name.strip():
            st.session_state["hosp_new_name"] = new_hosp_name.strip()
            st.session_state["hosp_new_parent_sys"] = current_sys
            st.session_state["hosp_add_commit"] = True
            st.rerun()
        # Halt until a real hospital is selected
        st.stop()
    else:
        current_hosp = selected_hosp

    # -------- Campus (kept simple) --------
    camp_names = list(st.session_state.doc["systems"][current_sys]["hospitals"][current_hosp]["campuses"].keys())
    new_camp = st.text_input("Create/Select Campus", placeholder="e.g., Main, East, West", key="camp_input")
    if new_camp:
        ensure_campus(current_sys, current_hosp, new_camp)
        current_camp = new_camp
    elif camp_names:
        current_camp = st.selectbox("Campus", camp_names, index=0, key="camp_select")
    else:
        ensure_campus(current_sys, current_hosp, "Main Campus")
        current_camp = "Main Campus"

    CAMP = st.session_state.doc["systems"][current_sys]["hospitals"][current_hosp]["campuses"][current_camp]

    with st.expander("Campus Profile", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            CAMP["meta"]["assessed_by"] = st.text_input("Assessed By", CAMP["meta"].get("assessed_by", ""), key="assessed_by_input")
            CAMP["meta"]["evs_manager"] = st.text_input("EVS Manager", CAMP["meta"].get("evs_manager", ""), key="evs_manager_input")
        with c2:
            CAMP["meta"]["date"] = st.text_input("Date", CAMP["meta"].get("date", ""), placeholder="e.g., 6/19/2025", key="date_input")

    periods = CAMP["periods"]

    # Period creation (handle button BEFORE selectbox to avoid state mutation errors)
    if "current_period_select" not in st.session_state:
        st.session_state["current_period_select"] = PERIOD_PLACEHOLDER

    colp1, colp2 = st.columns([2, 1])
    with colp2:
        new_period = st.text_input("New period label", placeholder="e.g., Jun-25", key="new_period_input")
        add_clicked = st.button("Add/Select Period", key="add_select_period_btn")
        if add_clicked and new_period:
            migrate_period_label(CAMP, PERIOD_PLACEHOLDER, new_period)
            if new_period not in CAMP["periods"]:
                CAMP["periods"].append(new_period)
            st.session_state["current_period_select"] = new_period
            st.session_state["clear_new_period_flag"] = True
            st.rerun()

    with colp1:
        # Validate selection
        if st.session_state["current_period_select"] not in (periods + [PERIOD_PLACEHOLDER]):
            st.session_state["current_period_select"] = PERIOD_PLACEHOLDER
        current_period = st.selectbox(
            "Current period",
            options=periods + [PERIOD_PLACEHOLDER],
            key="current_period_select",
        )

    st.divider()
    st.header("Scoring & Weights")
    maps = st.session_state.doc["response_maps"]

    for section_key, title in [
        ("contractual_pip", "Contractual & PIP"),
        ("system_standards", "System Standards"),
        ("bci", "BCI Checklist"),
    ]:
        with st.expander(f"{title} responses"):
            for k in list(maps[section_key].keys()):
                if maps[section_key][k] is None:
                    st.write(f"{k}: excluded from denominator")
                else:
                    maps[section_key][k] = st.slider(
                        f"{k}",
                        0.0, 1.0,
                        float(maps[section_key][k] or 0.0),
                        0.05,
                        key=f"respmap_{section_key}_{k}_v430",
                    )

    for key_name, label in [
        ("financial_pip", "Weight: Contractual & PIP"),
        ("system_standards", "Weight: System Standards"),
        ("bci", "Weight: BCI"),
    ]:
        st.session_state.doc["weights"][key_name] = st.slider(
            label, 0.0, 1.0, float(st.session_state.doc["weights"][key_name]), 0.05,
            key=f"weight_{key_name}_v430",
        )

    st.divider()
    doc_json = json.dumps(st.session_state.doc, indent=2).encode("utf-8")
    st.download_button("💾 Download Document (JSON)", doc_json, file_name="EVS_MultiHospital.json")
    up = st.file_uploader("Import Document (JSON)", type=["json"])
    if up:
        try:
            incoming = json.load(up)
            if not isinstance(incoming, dict) or "systems" not in incoming:
                incoming = _migrate_old_doc(incoming)
            st.session_state.doc = incoming
            st.success("Document loaded.")
            st.rerun()
        except Exception as e:
            st.error(f"Load failed: {e}")

# Stop early if no real period selected (prevents 'phantom' edits)
if current_period == PERIOD_PLACEHOLDER:
    st.warning("Create/select a period first: enter a label then click **Add/Select Period**. Once a real period is selected, the data entry tabs will appear.")
    st.stop()

# =============================================================
# Tabs: data entry and dashboards
# =============================================================
tabs = st.tabs([
    "📈 Operational Info",
    "📊 Contractual & PIP",
    "🧭 System Standards",
    "🧹 BCI",
    "📷 Photos & Evidence",   # NEW
    "📋 Campus Summary",
    "📊 Roll-Up Dashboard",
])
TAB_OPINFO, TAB_PIP, TAB_SYS, TAB_BCI, TAB_PHOTOS, TAB_SUMMARY, TAB_ROLLUP = tabs

# ---------------------- Operational Info ----------------------
with TAB_OPINFO:
    st.subheader(f"Operational Information — {current_sys} / {current_hosp} / {current_camp} / {current_period}")
    rows = CAMP["sections"]["operational_info"]
    df = pd.DataFrame([
        {"KPI": r["name"], "Value": r.get("values", {}).get(current_period, ""), "Comments": r.get("comments", {}).get(current_period, "")}
        for r in rows
    ])
    with st.form(key=f"form_opinfo_{current_sys}_{current_hosp}_{current_camp}_{current_period}"):
        edited = st.data_editor(
            df, use_container_width=True, num_rows="dynamic",
            key=f"opinfo_editor_{current_sys}_{current_hosp}_{current_camp}_{current_period}",
        )
        saved = st.form_submit_button("Save operational info")
    if saved:
        for i, r in enumerate(rows):
            r["values"][current_period] = edited.iloc[i]["Value"]
            r["comments"][current_period] = edited.iloc[i]["Comments"]
        st.success("Saved.")

# ---------------------- Contractual & PIP ----------------------
with TAB_PIP:
    st.subheader("Contractual Financial & PIP Results")
    rows = CAMP["sections"]["contractual_pip"]
    options = list(st.session_state.doc["response_maps"]["contractual_pip"].keys())
    df = pd.DataFrame([
        {"Question": r["name"], "Response": r.get("responses", {}).get(current_period, ""), "Comments": r.get("comments", {}).get(current_period, "")}
        for r in rows
    ])
    with st.form(key=f"form_pip_{current_sys}_{current_hosp}_{current_camp}_{current_period}"):
        edited = st.data_editor(
            df, use_container_width=True, num_rows="dynamic",
            column_config={"Response": st.column_config.SelectboxColumn(options=options)},
            key=f"pip_editor_{current_sys}_{current_hosp}_{current_camp}_{current_period}",
        )
        saved = st.form_submit_button("Save PIP responses")
    if saved:
        for i, r in enumerate(rows):
            r["responses"][current_period] = edited.iloc[i]["Response"]
            r["comments"][current_period] = edited.iloc[i]["Comments"]
        st.success("Saved.")
    s, d = score_section_responses(rows, current_period, st.session_state.doc["response_maps"]["contractual_pip"])
    st.metric("Section Total", f"{s:.1f}")
    st.metric("% Compliant", f"{(s / d * 100 if d else 0):.1f}%")

# ---------------------- System Standards ----------------------
with TAB_SYS:
    st.subheader("System Standards")
    rows = CAMP["sections"]["system_standards"]
    options = list(st.session_state.doc["response_maps"]["system_standards"].keys())
    df = pd.DataFrame([
        {"Question": r["name"], "Response": r.get("responses", {}).get(current_period, ""), "Comments": r.get("comments", {}).get(current_period, "")}
        for r in rows
    ])
    with st.form(key=f"form_sys_{current_sys}_{current_hosp}_{current_camp}_{current_period}"):
        edited = st.data_editor(
            df, use_container_width=True, num_rows="dynamic",
            column_config={"Response": st.column_config.SelectboxColumn(options=options)},
            key=f"sys_editor_{current_sys}_{current_hosp}_{current_camp}_{current_period}",
        )
        saved = st.form_submit_button("Save System Standards")
    if saved:
        for i, r in enumerate(rows):
            r["responses"][current_period] = edited.iloc[i]["Response"]
            r["comments"][current_period] = edited.iloc[i]["Comments"]
        st.success("Saved.")
    s, d = score_section_responses(rows, current_period, st.session_state.doc["response_maps"]["system_standards"])
    st.metric("Section Total", f"{s:.1f}")
    st.metric("% Compliant", f"{(s / d * 100 if d else 0):.1f}%")

# ---------------------- BCI ----------------------
with TAB_BCI:
    st.subheader("Building Cleanliness Inspection")
    areas = CAMP["sections"]["bci"]["areas"]
    options = list(st.session_state.doc["response_maps"]["bci"].keys())
    with st.form(key=f"form_bci_{current_sys}_{current_hosp}_{current_camp}_{current_period}"):
        edited_by_area = {}
        for area, items in areas.items():
            st.markdown(f"### {area}")
            df = pd.DataFrame([
                {
                    "Item": it["name"],
                    "Points": it.get("points", 1.0),
                    "Response": it.get("responses", {}).get(current_period, ""),
                    "Comments": it.get("comments", {}).get(current_period, ""),
                }
                for it in items
            ])
            edited = st.data_editor(
                df, use_container_width=True, num_rows="dynamic",
                column_config={
                    "Points": st.column_config.NumberColumn(min_value=0.0, step=0.5),
                    "Response": st.column_config.SelectboxColumn(options=options),
                },
                key=f"bci_{area}_{current_sys}_{current_hosp}_{current_camp}_{current_period}",
            )
            edited_by_area[area] = edited
            st.divider()
        saved = st.form_submit_button("Save BCI responses")
    if saved:
        for area, items in areas.items():
            edited = edited_by_area[area]
            for i, it in enumerate(items):
                it["points"] = float(edited.iloc[i]["Points"] or 1)
                it["responses"][current_period] = edited.iloc[i]["Response"]
                it["comments"][current_period] = edited.iloc[i]["Comments"]
        st.success("Saved.")
    # Totals snapshot
    for area, items in areas.items():
        s, d = score_bci_area(items, current_period, st.session_state.doc["response_maps"]["bci"])
        st.caption(f"**{area}** — Section Total: {s:.1f}  |  % Compliant: {(s / d * 100 if d else 0):.1f}%")

# ---------------------- Photos & Evidence ----------------------
with TAB_PHOTOS:
    st.subheader(f"Photos & Evidence — {current_sys} / {current_hosp} / {current_camp} / {current_period}")
    _ensure_photos_container(CAMP, current_period)

    with st.expander("Add photos", expanded=True):
        c1, c2 = st.columns(2)

        # Camera capture
        with c1:
            snap = st.camera_input("Take a photo")
            snap_caption = st.text_input("Caption (for camera photo)", key=f"cap_cam_{current_sys}_{current_hosp}_{current_camp}_{current_period}")
            if st.button("Save camera photo", key=f"save_cam_{current_sys}_{current_hosp}_{current_camp}_{current_period}") and snap is not None:
                try:
                    data = snap.getvalue()
                    CAMP["photos"][current_period].append({
                        "b64": _bytes_to_b64(data),
                        "caption": snap_caption.strip(),
                        "ts": time.time(),
                    })
                    st.success("Saved camera photo.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

        # File upload
        with c2:
            uploads = st.file_uploader(
                "Upload images (JPEG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True,
                key=f"upl_{current_sys}_{current_hosp}_{current_camp}_{current_period}"
            )
            upload_caption = st.text_input("Caption (applies to all uploads)", key=f"cap_upl_{current_sys}_{current_hosp}_{current_camp}_{current_period}")
            if st.button("Save uploaded image(s)", key=f"save_upl_{current_sys}_{current_hosp}_{current_camp}_{current_period}") and uploads:
                saved = 0
                for up in uploads:
                    try:
                        data = up.getvalue()
                        CAMP["photos"][current_period].append({
                            "b64": _bytes_to_b64(data),
                            "caption": upload_caption.strip(),
                            "ts": time.time(),
                        })
                        saved += 1
                    except Exception as e:
                        st.error(f"Save failed for {getattr(up, 'name', 'file')}: {e}")
                if saved:
                    st.success(f"Saved {saved} image(s).")

    st.divider()
    st.markdown("### Gallery")
    gallery = CAMP["photos"].get(current_period, [])

    if not gallery:
        st.info("No photos saved for this period yet.")
    else:
        # Sort newest first
        gallery_sorted = sorted(gallery, key=lambda x: x.get("ts", 0), reverse=True)
        per_row = 3
        rows = (len(gallery_sorted) + per_row - 1) // per_row
        for r in range(rows):
            cols = st.columns(per_row)
            for i in range(per_row):
                idx = r * per_row + i
                if idx >= len(gallery_sorted):
                    break
                item = gallery_sorted[idx]
                with cols[i]:
                    # display image
                    try:
                        st.image(base64.b64decode(item["b64"]), use_container_width=True)
                    except Exception:
                        st.warning("Unable to display image.")
                    # caption editor
                    cap_key = f"cap_edit_{current_sys}_{current_hosp}_{current_camp}_{current_period}_{idx}"
                    new_cap = st.text_input("Caption", value=item.get("caption", ""), key=cap_key)
                    # action buttons
                    cdel, csave = st.columns(2)
                    with csave:
                        if st.button("💾 Save", key=f"save_cap_{cap_key}"):
                            # find the real object in CAMP["photos"][current_period] and update its caption by timestamp match
                            for j, orig in enumerate(CAMP["photos"][current_period]):
                                if orig.get("ts") == item.get("ts"):
                                    CAMP["photos"][current_period][j]["caption"] = new_cap
                                    st.success("Updated caption.")
                                    break
                    with cdel:
                        if st.button("🗑️ Delete", key=f"del_{cap_key}"):
                            # delete by timestamp match
                            CAMP["photos"][current_period] = [
                                ph for ph in CAMP["photos"][current_period] if ph.get("ts") != item.get("ts")
                            ]
                            st.success("Deleted photo.")
                            st.rerun()

# ---------------------- Campus Summary ----------------------
with TAB_SUMMARY:
    st.subheader("Campus Summary Dashboard")
    weights = st.session_state.doc["weights"]
    maps = st.session_state.doc["response_maps"]
    ms_key = f"campus_summary_periods_{current_sys}_{current_hosp}_{current_camp}"
    chosen = st.multiselect(
        "Choose periods (up to 4)",
        options=CAMP["periods"],
        default=CAMP["periods"][-4:] if CAMP["periods"] else [],
        max_selections=4,
        key=ms_key,
    )
    if chosen:
        comps = {p: compute_period_components(CAMP, p, maps) for p in chosen}
        summaries = {p: summarise_from_components(c, weights) for p, c in comps.items()}
        dims = list(CAMP["sections"]["bci"]["areas"].keys())
        rows = []
        for d in dims:
            row = {"Area": d}
            for p in chosen:
                row[p] = summaries[p]["bci_by_dimension"].get(d, 0.0)
            rows.append(row)
        df_bci = pd.DataFrame(rows)
        overall_row = {"Area": "% Compliant"}
        for p in chosen:
            overall_row[p] = summaries[p]["bci_overall"]
        df_bci = pd.concat([df_bci, pd.DataFrame([overall_row])], ignore_index=True)
        if len(chosen) >= 2:
            df_bci["Δ"] = (df_bci[chosen[-1]] - df_bci[chosen[-2]]).round(1)
        cfg = {p: st.column_config.NumberColumn(format="%.1f%%") for p in chosen}
        if "Δ" in df_bci.columns:
            cfg["Δ"] = st.column_config.NumberColumn(format="%+.1f%%")
        st.dataframe(df_bci, use_container_width=True, column_config=cfg)

        st.markdown("#### OPERATIONAL MONTHLY ASSESSMENT")
        labels = [
            ("Contractual Financial and PIP Results (30% of Total)", "financial_pip"),
            ("System Standards (10% of Total)", "system_standards"),
            ("Building Cleanliness Inspection (60% of Total)", "bci"),
            ("Weighted % Compliant", "weighted"),
        ]
        op_rows = []
        for text, key in labels:
            r = {"Category": text}
            for p in chosen:
                r[p] = summaries[p]["operational"][key]
            op_rows.append(r)
        df_op = pd.DataFrame(op_rows)
        if len(chosen) >= 2:
            df_op["Δ"] = (df_op[chosen[-1]] - df_op[chosen[-2]]).round(1)
        cfg2 = {p: st.column_config.NumberColumn(format="%.1f%%") for p in chosen}
        if "Δ" in df_op.columns:
            cfg2["Δ"] = st.column_config.NumberColumn(format="%+.1f%%")
        st.dataframe(df_op, use_container_width=True, column_config=cfg2)
    else:
        st.info("Add/select periods to render the dashboard.")

# ---------------------- Roll-Up Dashboard ----------------------
with TAB_ROLLUP:
    st.subheader("Roll-Up Dashboard (Hospital or System)")
    weights = st.session_state.doc["weights"]
    maps = st.session_state.doc["response_maps"]
    scope_key = f"scope_radio_{current_sys}_{current_hosp}"
    scope = st.radio("Scope", ["Hospital (all campuses)", "System (all hospitals & campuses)"], horizontal=True, key=scope_key)

    sysobj = st.session_state.doc["systems"][current_sys]
    hospobj = sysobj["hospitals"][current_hosp]

    def all_campus_periods(campuses: Dict[str, Dict]) -> List[str]:
        s = set()
        for c in campuses.values():
            s.update(c["periods"])
        return sorted(list(s))

    if scope.startswith("Hospital"):
        campuses = hospobj["campuses"]
        available_periods = all_campus_periods(campuses)
        ms_key = f"rollup_periods_hospital_{current_sys}_{current_hosp}"
    else:
        all_camps = {}
        for h in sysobj["hospitals"].values():
            all_camps.update(h["campuses"])  # flatten
        campuses = all_camps
        available_periods = all_campus_periods(campuses)
        ms_key = f"rollup_periods_system_{current_sys}"

    chosen = st.multiselect(
        "Choose periods (up to 4)",
        options=available_periods,
        default=available_periods[-4:] if available_periods else [],
        max_selections=4,
        key=ms_key,
    )

    if chosen:
        comps_by_period = {}
        for p in chosen:
            comp_list = []
            for camp in campuses.values():
                if p in camp["periods"]:
                    comp_list.append(compute_period_components(camp, p, maps))
            if comp_list:
                comps_by_period[p] = aggregate_components(comp_list)
        summaries = {p: summarise_from_components(c, weights) for p, c in comps_by_period.items()}
        if not summaries:
            st.info("No data for selected periods.")
        else:
            dims = list(build_evs_template()["sections"]["bci"]["areas"].keys())
            rows = []
            for d in dims:
                row = {"Area": d}
                for p in chosen:
                    row[p] = summaries.get(p, {}).get("bci_by_dimension", {}).get(d, 0.0)
                rows.append(row)
            df_bci = pd.DataFrame(rows)
            overall_row = {"Area": "% Compliant"}
            for p in chosen:
                overall_row[p] = summaries.get(p, {}).get("bci_overall", 0.0)
            df_bci = pd.concat([df_bci, pd.DataFrame([overall_row])], ignore_index=True)
            if len(chosen) >= 2:
                df_bci["Δ"] = (df_bci[chosen[-1]] - df_bci[chosen[-2]]).round(1)
            cfg = {p: st.column_config.NumberColumn(format="%.1f%%") for p in chosen}
            if "Δ" in df_bci.columns:
                cfg["Δ"] = st.column_config.NumberColumn(format="%+.1f%%")
            st.dataframe(df_bci, use_container_width=True, column_config=cfg)

            st.markdown("#### OPERATIONAL MONTHLY ASSESSMENT")
            labels = [
                ("Contractual Financial and PIP Results (30% of Total)", "financial_pip"),
                ("System Standards (10% of Total)", "system_standards"),
                ("Building Cleanliness Inspection (60% of Total)", "bci"),
                ("Weighted % Compliant", "weighted"),
            ]
            op_rows = []
            for text, key in labels:
                r = {"Category": text}
                for p in chosen:
                    r[p] = summaries.get(p, {}).get("operational", {}).get(key, 0.0)
                op_rows.append(r)
            df_op = pd.DataFrame(op_rows)
            if len(chosen) >= 2:
                df_op["Δ"] = (df_op[chosen[-1]] - df_op[chosen[-2]]).round(1)
            cfg2 = {p: st.column_config.NumberColumn(format="%.1f%%") for p in chosen}
            if "Δ" in df_op.columns:
                cfg2["Δ"] = st.column_config.NumberColumn(format="%+.1f%%")
            st.dataframe(df_op, use_container_width=True, column_config=cfg2)

            # ---- Per-campus snapshot (selected period) ----
            st.markdown("#### Per-campus snapshot (selected period)")
            detail_period = st.selectbox(
                "Campus snapshot period",
                chosen,
                index=len(chosen) - 1,
                key=f"campus_snapshot_{ms_key}",
            )
            rows = []
            for campus_name, camp in campuses.items():
                if detail_period in camp["periods"]:
                    comp = compute_period_components(camp, detail_period, maps)
                    s = summarise_from_components(comp, weights)
                    rows.append({
                        "Campus": campus_name,
                        "BCI Overall %": s["bci_overall"],
                        "Contractual & PIP %": s["operational"]["financial_pip"],
                        "System Standards %": s["operational"]["system_standards"],
                        "Weighted %": s["operational"]["weighted"],
                    })
            if rows:
                snap_df = pd.DataFrame(rows).sort_values("Weighted %", ascending=False)
                st.dataframe(
                    snap_df,
                    use_container_width=True,
                    column_config={
                        "BCI Overall %": st.column_config.NumberColumn(format="%.1f%%"),
                        "Contractual & PIP %": st.column_config.NumberColumn(format="%.1f%%"),
                        "System Standards %": st.column_config.NumberColumn(format="%.1f%%"),
                        "Weighted %": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )
            else:
                st.info("No campuses have data for that period.")
    else:
        st.info("Pick at least one period to render roll-ups.")

st.caption("Add Systems → Hospitals → Campuses and months. Enter data per campus & month; then view Campus or aggregated Hospital/System dashboards. Export/import the whole file as JSON. | App " + APP_VERSION)
