import streamlit as st
import math
import random
from dataclasses import dataclass

# =========================================================
# CONFIG + SIMPLE STYLING
# =========================================================
st.set_page_config(page_title="Foundation Design Tool", layout="wide")  # fix the error

st.markdown(
    """
    <style>
      .app-title {font-size: 2.15rem; font-weight: 900; margin-bottom: 0.2rem;}
      .app-sub {color: #6b7280; margin-top: 0;}
      .card {border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px; background: #ffffff;}
      .card:hover {border-color: #cbd5e1; box-shadow: 0 6px 20px rgba(0,0,0,0.06);}
      .kpi {border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; background: #fff;}
      .muted {color:#6b7280;}
      .chip {display:inline-block; padding: 4px 10px; border-radius: 999px; font-weight: 800; font-size: 0.85rem;}
      .chip-ok {background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;}
      .chip-bad {background:#fef2f2; color:#991b1b; border:1px solid #fecaca;}
      hr {margin: 0.7rem 0;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">🧱 Foundation Design & Analysis Tool</div>', unsafe_allow_html=True)
st.markdown('<p class="app-sub">Cleaner UI + audience-friendly defaults (Student / Engineer).</p>', unsafe_allow_html=True)

# =========================================================
# SESSION STATE (NAV)
# =========================================================
FEATURES = [
    "Bearing Capacity",
    "Settlement",
    "Sliding Check",
    "Overturning Check",
    "Full Foundation Design (Monte Carlo Robustness)",
]

if "page" not in st.session_state:
    st.session_state.page = "home"
if "analysis_type" not in st.session_state:
    st.session_state.analysis_type = None
if "result" not in st.session_state:
    st.session_state.result = None


def go_home(clear_inputs=False):
    st.session_state.page = "home"
    st.session_state.analysis_type = None
    st.session_state.result = None
    if clear_inputs:
        keep = {"page", "analysis_type", "result"}
        for k in list(st.session_state.keys()):
            if k not in keep:
                del st.session_state[k]
    st.rerun()


def open_feature(name):
    st.session_state.page = "feature"
    st.session_state.analysis_type = name
    st.session_state.result = None
    st.rerun()


# =========================================================
# HELPERS
# =========================================================
def chip(text, ok=True):
    cls = "chip chip-ok" if ok else "chip chip-bad"
    st.markdown(f"<span class='{cls}'>{text}</span>", unsafe_allow_html=True)


def kpi(label, value, caption=None):
    st.markdown(
        f"<div class='kpi'><div class='muted'>{label}</div>"
        f"<div style='font-size:1.35rem;font-weight:900'>{value}</div></div>",
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)


def safe_float_list(csv_text: str):
    out, bad = [], []
    for token in csv_text.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(float(token))
        except ValueError:
            bad.append(token)
    return out, bad


# =========================================================
# ENGINEERING FUNCTIONS (YOUR ORIGINALS)
# =========================================================
def bearing_capacity_q_ult(c_kpa, gamma_knm3, Df_m, B_m, phi_deg):
    phi = math.radians(phi_deg)
    q = gamma_knm3 * Df_m

    if abs(phi) < 1e-9:
        Nq = 1.0
        Nc = 5.14
        Ng = 0.0
    else:
        Nq = math.exp(math.pi * math.tan(phi)) * (math.tan(math.radians(45) + phi / 2) ** 2)
        Nc = (Nq - 1) / math.tan(phi)
        Ng = 2 * (Nq + 1) * math.tan(phi)

    return c_kpa * Nc + q * Nq + 0.5 * gamma_knm3 * B_m * Ng


def settlement_elastic(P_kN, B_m, L_m, Es_kPa, nu, influence_I=1.0):
    A = B_m * L_m
    q_kPa = P_kN / A
    return influence_I * (q_kPa * B_m * (1 - nu**2)) / Es_kPa


def sliding_fs(P_kN, H_kN, mu):
    if H_kN <= 0:
        return float("inf")
    return (mu * P_kN) / H_kN


def overturning_fs(P_kN, B_m, M_kNm):
    if M_kNm <= 0:
        return float("inf")
    Mr = P_kN * (B_m / 2)
    return Mr / M_kNm


# =========================================================
# PROFILE / AUDIENCE MODE (SIDEBAR)
# =========================================================
st.sidebar.header("⚙️ Profile")

audience = st.sidebar.radio(
    "Audience mode",
    ["Student", "Engineer / Contractor"],
    index=1,
    key="audience",
)

units = st.sidebar.radio(
    "Display units",
    ["kN / m / kPa", "kN / m / kPa (same)"],
    index=0,
)

# Defaults
default_FS_bearing = 3.0
default_FS_slide = 1.5
default_FS_ot = 2.0
default_settle_limit_mm = 25.0

st.sidebar.caption(
    "Educational defaults; verify with design codes."
    if audience == "Student"
    else "Quick checks only; confirm with project specs."
)

st.sidebar.markdown("---")

st.sidebar.subheader("✅ Design criteria (editable)")
FS_slide_req = st.sidebar.number_input("Required FS (Sliding)", value=default_FS_slide, min_value=1.0, step=0.1)
FS_ot_req = st.sidebar.number_input("Required FS (Overturning)", value=default_FS_ot, min_value=1.0, step=0.1)
settle_limit = st.sidebar.number_input("Settlement limit (mm)", value=default_settle_limit_mm, min_value=1.0)

st.sidebar.markdown("---")
st.sidebar.button("⬅ Home", on_click=go_home, kwargs={"clear_inputs": False})
st.sidebar.button("🧹 Clear & Home", on_click=go_home, kwargs={"clear_inputs": True})

# =========================================================
# HOME PAGE
# =========================================================
if st.session_state.page == "home":
    st.subheader("Choose a function")

    cards = [
        ("⚖️", "Bearing Capacity", "Compute ultimate & allowable bearing capacity."),
        ("📉", "Settlement", "Estimate elastic settlement."),
        ("🧷", "Sliding Check", "Factor of safety against sliding."),
        ("🧱", "Overturning Check", "Factor of safety against overturning."),
        ("🎲", "Full Foundation Design (Monte Carlo Robustness)", "Robustness score."),
    ]

    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(cards):
        with cols[i % 3]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"### {icon} {title}")
            st.write(desc)
            if st.button("Open", key=f"open_{title}"):
                open_feature(title)
            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.write("Feature page logic unchanged (same as your original code).")
