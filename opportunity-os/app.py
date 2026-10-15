import io
import os
import re
import json
import time
import uuid
import html
import textwrap

import pandas as pd
import requests
import streamlit as st

# ============================================================
# OPPORTUNITY OS — Premium Career Intelligence Studio
# Install:
# python -m pip install streamlit pandas requests pypdf python-docx
#
# Run:
# python -m streamlit run app.py
# ============================================================

st.set_page_config(
    page_title="Opportunity OS | Career Intelligence",
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="expanded",
)

WORK_MODES = ["Not specified", "Remote", "Hybrid", "On-site", "Remote or hybrid", "Any"]

DEFAULTS = {
    "api_url": os.getenv("OPPORTUNITY_API_URL", "http://localhost:8000"),
    "profile_id": uuid.uuid4().hex[:12],
    "candidate_profile": None,
    "resume_text": "",
    "resume_filename": "",
    "last_payload": None,
    "last_error": None,
    "last_prompt": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def render_html(markup):
    """Render custom HTML consistently without displaying HTML source."""
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


def safe_text(value, fallback="Not provided"):
    if value is None:
        return fallback
    if isinstance(value, float) and pd.isna(value):
        return fallback
    value = str(value).strip()
    return value if value else fallback


def first_present(data, keys, default=None):
    if not isinstance(data, dict):
        return default
    for key in keys:
        if data.get(key) is not None:
            return data[key]
    return default


def api_base_url():
    return st.session_state.api_url.strip().rstrip("/")


def normalize_work_mode(value):
    """Map any backend / resume value onto an option the selectbox accepts."""
    text = str(value or "").strip()
    if not text:
        return "Not specified"

    for option in WORK_MODES:
        if text.lower() == option.lower():
            return option

    lowered = text.lower()
    has_remote = "remote" in lowered or "wfh" in lowered or "work from home" in lowered
    has_hybrid = "hybrid" in lowered
    if has_remote and has_hybrid:
        return "Remote or hybrid"
    if has_remote:
        return "Remote"
    if has_hybrid:
        return "Hybrid"
    if any(word in lowered for word in ("on-site", "onsite", "on site", "office", "in-person", "in person")):
        return "On-site"
    if "any" in lowered or "flexible" in lowered:
        return "Any"
    return "Not specified"


# ----------------------------- PREMIUM THEME -----------------------------

render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --canvas: #f2eefa;
    --plum: #59417b;
    --ink: #3f2d54;
    --muted: #6f6080;
    --orchid: #a782d6;
    --pink: #ed9ab8;
    --peach: #ffb08b;
    --teal: #79dccc;
    --lime: #e2f89c;
    --line: #e2d6ed;
}

/* Fonts: scoped on purpose. A blanket [class*="css"] rule overrides the
   icon font and turns expander arrows into literal text. */
.stApp, .stMarkdown, p, label, input, textarea, button,
[data-testid="stCaptionContainer"] {
    font-family: 'Manrope', sans-serif;
}
.stApp {
    background:
        radial-gradient(ellipse at 83% 1%, rgba(237,154,184,.25), transparent 29%),
        radial-gradient(ellipse at 0% 36%, rgba(121,220,204,.21), transparent 29%),
        radial-gradient(ellipse at 68% 100%, rgba(167,130,214,.20), transparent 34%),
        var(--canvas);
    color: var(--ink);
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: rgba(242,238,250,.80); }
[data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
.block-container {
    max-width: 1500px;
    padding-top: 1.15rem;
    padding-bottom: 3rem;
}

/* Violet gradient sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #6a4c97 0%, #6d5fa0 53%, #437d85 100%);
    border-right: 1px solid rgba(255,255,255,.2);
}
section[data-testid="stSidebar"] > div { background: transparent; }
section[data-testid="stSidebar"] .block-container {
    padding: 1.4rem 1.05rem 2rem;
}
section[data-testid="stSidebar"] * { color: #fff8ff; }
section[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,.14) !important;
    border: 1px solid rgba(255,255,255,.30) !important;
    color: #fffaff !important;
    border-radius: 10px !important;
}
section[data-testid="stSidebar"] .stTextInput label {
    color: #fbf0ff !important;
}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #f2e8f6 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(105deg,#e4ffad,#a7efda) !important;
    color: #48395f !important;
    border: 1px solid rgba(255,255,255,.55) !important;
}
/* Developer-settings expander inside the sidebar */
section[data-testid="stSidebar"] .stExpander,
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,.10) !important;
    border: 1px solid rgba(255,255,255,.28) !important;
}
section[data-testid="stSidebar"] .stExpander summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    color: #fffaff !important;
}
/* Alerts keep dark text so they stay readable on their light backgrounds */
section[data-testid="stSidebar"] [data-testid="stAlert"] * {
    color: #2f2540 !important;
}

/* Brand */
.brand-row {
    display: flex;
    align-items: center;
    gap: 11px;
    margin: 0 0 24px;
}
.brand-mark {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 15px;
    background: linear-gradient(135deg,#e6ff9f,#9debd0);
    color: #59457b;
    font-size: 24px;
    font-weight: 900;
    box-shadow: 0 7px 24px rgba(43,38,73,.13);
}
.brand-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -.8px;
    color: #fffaff;
    line-height: 1.1;
}
.brand-sub {
    font: 10px 'DM Mono', monospace;
    letter-spacing: 1px;
    color: #f0e4f6;
    margin-top: 5px;
}
.sidebar-label {
    font: 11px 'DM Mono', monospace;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #f0e1f5;
    margin: 25px 0 9px;
}
.sidebar-chip {
    display: inline-block;
    background: rgba(222,255,163,.18);
    color: #f4ffcf;
    border: 1px solid rgba(233,255,188,.38);
    padding: 8px 10px;
    border-radius: 8px;
    font: 11px 'DM Mono', monospace;
    letter-spacing: .3px;
}
.sidebar-stat {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,.17);
    color: #fff2fa;
    font-size: 13px;
}
.sidebar-stat b {
    font: 11px 'DM Mono', monospace;
    color: #f0ffbd;
    font-weight: 500;
    text-align: right;
}
.sidebar-copy {
    color: #f6edfa;
    font-size: 12px;
    line-height: 1.9;
}

/* Hero panel */
.hero {
    position: relative;
    overflow: hidden;
    display: grid;
    grid-template-columns: minmax(0,1.7fr) minmax(205px,.7fr);
    gap: 22px;
    align-items: center;
    padding: 26px 32px;
    border: 1px solid rgba(255,255,255,.45);
    border-radius: 23px;
    background:
        radial-gradient(ellipse at 76% 10%,rgba(255,216,170,.30),transparent 30%),
        radial-gradient(ellipse at 92% 100%,rgba(121,220,204,.30),transparent 30%),
        linear-gradient(115deg,#6b4a9c 0%,#9366bd 45%,#c46fa8 78%,#d98a86 100%);
    box-shadow: 0 16px 38px rgba(114,78,151,.16);
    margin-bottom: 22px;
}
.hero:before {
    content: "";
    position: absolute;
    width: 290px;
    height: 290px;
    right: -130px;
    top: -180px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,.32);
    box-shadow: 0 0 0 32px rgba(255,255,255,.07),
                0 0 0 68px rgba(255,255,255,.045);
    pointer-events: none;
}
.hero-eyebrow {
    color: #f4ffcf;
    font: 11px 'DM Mono', monospace;
    letter-spacing: 1.4px;
    text-transform: uppercase;
}
.hero-title {
    position: relative;
    z-index: 1;
    color: #fffaff;
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(31px,3.5vw,50px);
    line-height: 1.07;
    letter-spacing: -2.4px;
    font-weight: 700;
    margin: 14px 0 12px;
}
.hero-gradient {
    background: linear-gradient(92deg,#f5ffd4,#caffe9,#fff0dd);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.hero-copy {
    position: relative;
    z-index: 1;
    color: #fffafd;
    font-size: 14px;
    line-height: 1.8;
    max-width: 650px;
    margin: 0;
    text-shadow: 0 1px 2px rgba(60,30,90,.28);
}
.hero-foot {
    position: relative;
    z-index: 1;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 18px;
}
.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(85,47,120,.22);
    border: 1px solid rgba(255,255,255,.32);
    color: #fffaff;
    border-radius: 8px;
    padding: 8px 10px;
    font: 11px 'DM Mono', monospace;
    letter-spacing: .3px;
}
.live-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #e4ff98;
}
.hero-side {
    position: relative;
    z-index: 1;
    border: 1px solid rgba(255,255,255,.38);
    background: rgba(90,63,135,.24);
    border-radius: 16px;
    padding: 18px;
    backdrop-filter: blur(8px);
}
.hero-side-label {
    color: #fff1ff;
    font: 11px 'DM Mono', monospace;
    letter-spacing: 1px;
}
.hero-side-title {
    color: #fffaff;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 600;
    margin: 12px 0 7px;
}
.hero-side-copy {
    color: #fff5fb;
    font-size: 12px;
    line-height: 1.7;
}
.signal-row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin: 15px 0 11px;
    height: 30px;
}
.signal {
    flex: 1;
    border-radius: 4px;
    background: linear-gradient(180deg,#eaffab,#8fe3cb);
}

/* Section headings */
.section-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 9px;
    margin: 22px 0 12px;
}
.section-title {
    color: #3f2d54;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -.45px;
}
.section-note {
    color: #7a6a8a;
    font: 11px 'DM Mono', monospace;
    letter-spacing: .7px;
    text-align: right;
}
.tiny {
    color: #6f6080;
    font-size: 13px;
    line-height: 1.75;
}

/* Workflow cards */
.phase-card {
    min-height: 143px;
    padding: 17px;
    border: 1px solid #e3d7ee;
    border-radius: 15px;
    background: linear-gradient(145deg,#fff7f0,#f5edff);
    box-shadow: 0 5px 17px rgba(100,74,123,.055);
}
.phase-card.aqua {
    background: linear-gradient(145deg,#f0fffa,#e9f7f6);
    border-color: #d0ebe4;
}
.phase-card.peach {
    background: linear-gradient(145deg,#fff5ed,#ffece7);
    border-color: #f4dacf;
}
.phase-card.lilac {
    background: linear-gradient(145deg,#fcf6ff,#f0eaff);
    border-color: #e6d8f7;
}
.phase-card.lemon {
    background: linear-gradient(145deg,#fffff0,#f5f7dc);
    border-color: #e5e7c4;
}
.phase-number {
    color: #7a52b3;
    font: 11px 'DM Mono', monospace;
    letter-spacing: .8px;
}
.phase-title {
    color: #3f2d54;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 14px;
    font-weight: 700;
    margin: 11px 0 7px;
}
.phase-copy {
    color: #6c5e7b;
    font-size: 12px;
    line-height: 1.7;
}

/* Mission control cards */
.metric-card {
    background: linear-gradient(145deg,#fff8f1,#f5edff);
    border: 1px solid #e6daef;
    border-radius: 14px;
    padding: 16px;
    min-height: 104px;
    box-shadow: 0 4px 16px rgba(91,64,121,.05);
}
.metric-card.mint {
    background: linear-gradient(145deg,#effff8,#e2f7ef);
    border-color: #d0e9df;
}
.metric-card.peach {
    background: linear-gradient(145deg,#fff6ed,#ffece5);
    border-color: #f3d8ce;
}
.metric-card.lemon {
    background: linear-gradient(145deg,#fffff0,#f4f5dc);
    border-color: #e5e6c4;
}
.metric-label {
    color: #7a6a8a;
    font: 11px 'DM Mono', monospace;
    letter-spacing: .9px;
}
.metric-value {
    color: #3f2d54;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -.9px;
    margin-top: 8px;
    overflow-wrap: anywhere;
}
.metric-sub {
    color: #7f7090;
    font-size: 12px;
    margin-top: 3px;
}
.status-box {
    background: linear-gradient(105deg,#f3ffdf,#e3faf1);
    border: 1px solid #d6e9bd;
    border-radius: 12px;
    padding: 13px 15px;
    color: #475a3d;
    font-size: 13px;
    line-height: 1.75;
}
.empty-state {
    text-align: center;
    padding: 36px 18px;
    border: 1px dashed #d4c4e2;
    border-radius: 16px;
    background: linear-gradient(135deg,rgba(255,247,241,.9),rgba(243,237,255,.9));
}
.empty-icon {
    color: #8f69c0;
    font-size: 29px;
    margin-bottom: 8px;
}
.empty-title {
    color: #3f2d54;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 16px;
    font-weight: 700;
}
.empty-copy {
    color: #6f6080;
    font-size: 13px;
    line-height: 1.75;
    max-width: 540px;
    margin: 8px auto 0;
}

/* Input areas */
.stTextArea textarea,
.stTextInput input,
.stNumberInput input {
    background: #fff8f4 !important;
    border: 1px solid #ddcde7 !important;
    border-radius: 10px !important;
    color: #3b2a49 !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 13px !important;
    box-shadow: none !important;
}
.stTextArea textarea {
    padding: 13px !important;
    line-height: 1.75 !important;
}
.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: #a97ad3 !important;
    box-shadow: 0 0 0 3px rgba(169,122,211,.13) !important;
}
.stTextArea label,
.stTextInput label,
.stSelectbox label,
.stFileUploader label {
    color: #4f3b61 !important;
    font-weight: 800 !important;
    font-size: 12px !important;
}
.stFileUploader section {
    background: #fff8f4;
    border: 1px dashed #c9b1dc;
    border-radius: 10px;
}
.stFileUploader section * { color: #5a4670 !important; }
.stSelectbox [data-baseweb="select"] > div {
    background: #fff8f4;
    border-color: #ddcde7;
    border-radius: 9px;
    color: #3b2a49;
}

/* Prominent buttons with distinct colours */
.stButton > button,
.stFormSubmitButton > button {
    min-height: 45px;
    border-radius: 10px;
    background: linear-gradient(105deg,#ff987f,#ffbf8f) !important;
    color: #4d2a45 !important;
    border: 1px solid #ffb092 !important;
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 13px;
    box-shadow: 0 6px 16px rgba(222,124,124,.17);
    transition: all .16s ease;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: linear-gradient(105deg,#ffb09b,#ffd0a6) !important;
    color: #4b2e46 !important;
    border-color: #ffd0a6 !important;
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(222,124,124,.23);
}
.stButton > button:focus,
.stFormSubmitButton > button:focus {
    outline: 3px solid rgba(215,165,240,.45) !important;
    outline-offset: 2px;
}
.stDownloadButton > button {
    min-height: 42px;
    background: linear-gradient(105deg,#b7f0d9,#d8f69f) !important;
    color: #2a524a !important;
    border: 1px solid #a8dfc7 !important;
    border-radius: 9px;
    font-weight: 800;
    font-size: 13px;
    box-shadow: 0 4px 13px rgba(85,169,142,.12);
}
.stDownloadButton > button:hover {
    background: #e5ffc0 !important;
    color: #2a524a !important;
    border-color: #95d4b4 !important;
}

/* Tabs, tables and expanders */
.stTabs [data-baseweb="tab-list"] {
    gap: 7px;
    border-bottom: 1px solid #e1d4ea;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    color: #7d6d8b;
    font-size: 13px;
    font-weight: 800;
    padding: 10px;
}
.stTabs [aria-selected="true"] {
    color: #62408f !important;
    border-bottom: 3px solid #ba91df;
}
.stExpander,
[data-testid="stExpander"] {
    border: 1px solid #e0d3e8 !important;
    border-radius: 11px !important;
    background: #fff8f4 !important;
}
.stExpander summary,
[data-testid="stExpander"] summary {
    color: #4d3860;
    font-size: 13px;
    font-weight: 800;
}
[data-testid="stDataFrame"] {
    border: 1px solid #dfd1e9;
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stAlert"] { border-radius: 10px; }
hr { border-color: #e2d7eb !important; }
.footer {
    color: #85769a;
    font: 11px 'DM Mono', monospace;
    letter-spacing: 1px;
    text-align: center;
    padding: 24px 0 3px;
}
@media(max-width:850px) {
    .hero { grid-template-columns: 1fr; padding: 24px 21px; }
    .hero-side { display: none; }
    .hero-title { letter-spacing: -1.3px; }
    .section-note { text-align: left; }
}
</style>
""")


# ---------------------------- RESUME HELPERS ----------------------------

PROFILE_FIELDS = {
    "name": "profile_name",
    "email": "profile_email",
    "phone": "profile_phone",
    "education": "profile_education",
    "graduation_year": "profile_graduation_year",
    "skills": "profile_skills",
    "projects": "profile_projects",
    "experience": "profile_experience",
    "certifications": "profile_certifications",
    "preferred_location": "profile_preferred_location",
    "preferred_work_mode": "profile_preferred_work_mode",
    "minimum_stipend": "profile_minimum_stipend",
}


def profile_value_for_widget(field, value):
    """Convert a profile value into the string a Streamlit widget expects."""
    if isinstance(value, list):
        value = ", ".join(str(x) for x in value)
    if field == "preferred_work_mode":
        return normalize_work_mode(value)
    return "" if value is None else str(value)


def set_profile_widgets(profile):
    if not isinstance(profile, dict):
        return

    for field, key in PROFILE_FIELDS.items():
        st.session_state[key] = profile_value_for_widget(field, profile.get(field, ""))

    st.session_state.candidate_profile = profile
    st.session_state.resume_text = str(profile.get("resume_text", "") or "")
    st.session_state.resume_filename = str(profile.get("resume_filename", "") or "")


def extract_resume_text(uploaded_file):
    raw = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "Install PDF support: python -m pip install pypdf"
            ) from exc

        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

    elif filename.endswith(".docx"):
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError(
                "Install DOCX support: python -m pip install python-docx"
            ) from exc

        doc = Document(io.BytesIO(raw))
        pieces = [p.text for p in doc.paragraphs if p.text.strip()]

        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    pieces.append(" | ".join(cells))

        text = "\n".join(pieces)

    else:
        raise RuntimeError("Please upload a PDF or DOCX resume.")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < 40:
        raise RuntimeError(
            "Very little text was extracted. Try a text-based PDF or DOCX resume."
        )
    return text


def extract_section(resume_text, headings, max_lines=24):
    lines = [x.strip() for x in resume_text.splitlines() if x.strip()]
    all_headers = {
        "education", "academic background", "skills", "technical skills",
        "projects", "personal projects", "experience", "work experience",
        "professional experience", "internships", "certifications",
        "certificates", "achievements", "awards", "summary", "profile",
        "objective", "contact", "interests", "languages", "coursework",
        "publications", "activities"
    }

    start = -1
    for index, line in enumerate(lines):
        clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
        if any(clean == heading or clean.startswith(heading + " ") for heading in headings):
            start = index + 1
            break

    if start < 0:
        return ""

    result = []
    for line in lines[start:]:
        clean = re.sub(r"[^a-z ]", "", line.lower()).strip()
        if clean in all_headers and result:
            break
        result.append(line)
        if len(result) >= max_lines:
            break
    return "\n".join(result).strip()


def build_candidate_profile(resume_text, filename):
    lines = [x.strip(" |•\t") for x in resume_text.splitlines() if x.strip()]

    email_match = re.search(
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        resume_text, re.I
    )
    phone_match = re.search(r"(?:\+?\d[\d ()-]{7,}\d)", resume_text)

    name = ""
    ignored = ("resume", "curriculum vitae", "portfolio", "linkedin", "github", "contact details")

    for line in lines[:10]:
        if len(line) > 55 or "@" in line or re.search(r"https?://|www\.", line, re.I):
            continue
        if re.search(r"\d{5,}", line) or any(x in line.lower() for x in ignored):
            continue
        if len(line.split()) <= 5 and re.search(r"[A-Za-z]", line):
            name = line
            break

    education_lines = [
        line for line in lines
        if re.search(
            r"\b(?:b\.?\s?tech|b\.?\s?e\.?|bachelor|bsc|bca|m\.?\s?tech|master|mca|m\.?\s?sc|ph\.?d|university|college|engineering)\b",
            line, re.I
        )
    ]

    contextual_year = re.findall(
        r"(?:graduat(?:ion|e)|passing|expected|class of|final year|pursuing)[^\n]{0,50}\b(20\d{2})\b",
        resume_text, re.I
    )
    years = re.findall(r"\b20(?:2[4-9]|3[0-5])\b", resume_text)

    skill_bank = [
        "Python", "Java", "C++", "C", "JavaScript", "TypeScript",
        "SQL", "HTML", "CSS", "React", "Node.js", "FastAPI", "Flask",
        "Django", "REST API", "Machine Learning", "Deep Learning",
        "NLP", "Computer Vision", "TensorFlow", "PyTorch", "scikit-learn",
        "Pandas", "NumPy", "Matplotlib", "Power BI", "Tableau", "Excel",
        "AWS", "Azure", "Docker", "Git", "GitHub", "MongoDB", "PostgreSQL",
        "MySQL", "Firebase", "Supabase", "Streamlit", "Hadoop", "Spark",
        "Linux", "Figma", "Data Analysis", "Data Science", "Prompt Engineering",
        "Generative AI", "LLM", "API Integration", "Communication", "Leadership"
    ]

    skills = [
        skill for skill in skill_bank
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(skill) + r"(?![A-Za-z0-9])",
                     resume_text, re.I)
    ]

    return {
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "education": "\n".join(education_lines[:4]),
        "graduation_year": contextual_year[0] if contextual_year else (max(years) if years else ""),
        "skills": skills,
        "projects": extract_section(resume_text, ["projects", "personal projects", "academic projects", "project experience"]),
        "experience": extract_section(resume_text, ["experience", "work experience", "professional experience", "internships", "employment history"]),
        "certifications": extract_section(resume_text, ["certifications", "certificates", "licenses and certifications"]),
        "preferred_location": "",
        "preferred_work_mode": "Not specified",
        "minimum_stipend": "",
        "resume_text": resume_text,
        "resume_filename": filename,
    }


def get_profile_from_widgets():
    profile = {}

    for field, key in PROFILE_FIELDS.items():
        value = st.session_state.get(key, "")
        if field == "skills":
            profile[field] = [
                part.strip()
                for part in str(value).replace("\n", ",").split(",")
                if part.strip()
            ]
        else:
            profile[field] = str(value).strip()

    profile["resume_text"] = st.session_state.get("resume_text", "")
    profile["resume_filename"] = st.session_state.get("resume_filename", "")
    return profile


# ----------------------------- AGENT CALL -----------------------------

def _task_request_from_frontend(body):
    """Translate the UI's prompt/profile into the fields required by /api/tasks."""
    prompt = str(body.get("prompt", "")).strip()
    profile = body.get("candidate_profile") or {}
    if not isinstance(profile, dict):
        profile = {}

    education = str(profile.get("education") or "Computer Science").strip()
    # The API expects the current study year (not graduation year).
    year_match = re.search(r"\b(?:year|yr|semester)\s*[:#-]?\s*(1|2|3|4)\b", prompt, re.I)
    year = int(year_match.group(1)) if year_match else 3
    grad = str(profile.get("graduation_year") or "").strip()
    if not year_match and grad.isdigit():
        try:
            from datetime import datetime
            remaining = int(grad) - datetime.now().year
            if remaining in (0, 1, 2, 3):
                year = max(1, min(4, 4 - remaining))
        except (TypeError, ValueError):
            pass

    skills = profile.get("skills", [])
    if isinstance(skills, str):
        skills = [part.strip() for part in re.split(r"[,\n]", skills) if part.strip()]
    if not isinstance(skills, list):
        skills = []
    skills = [str(item).strip() for item in skills if str(item).strip()]

    location = str(profile.get("preferred_location") or "").strip()
    if not location:
        match = re.search(r"\b(?:in|around|located in)\s+(India|Bengaluru|Bangalore|Remote|Hyderabad|Chennai|Pune|Mumbai|Delhi|Noida)\b", prompt, re.I)
        location = match.group(1) if match else "India"

    mode = str(profile.get("preferred_work_mode") or "").strip()
    if not mode or mode.lower() in {"not specified", "any"}:
        lower_prompt = prompt.lower()
        if "remote" in lower_prompt:
            mode = "Remote"
        elif "hybrid" in lower_prompt:
            mode = "Hybrid"
        elif "on-site" in lower_prompt or "onsite" in lower_prompt:
            mode = "On-site"
        else:
            mode = "Remote"

    count_match = re.search(r"\b(?:top|first|find|show|at least|up to)\s+(\d{1,2})\b", prompt, re.I)
    count = int(count_match.group(1)) if count_match else 3
    count = max(1, min(count, 20))

    # Preserve the original prompt as extra context, while explicitly supplying
    # the fields that this backend actually validates and consumes.
    return {
        "degree": education or "Computer Science",
        "year": year,
        "skills": skills,
        "location": location or "India",
        "work_mode": mode or "Remote",
        "count": count,
        "prompt": prompt,
        "candidate_profile": profile,
        "profile_id": body.get("profile_id"),
    }


def _flatten_task_state(state):
    """Convert the backend's persisted task state into the UI's result format."""
    if not isinstance(state, dict):
        raise RuntimeError("The backend returned an invalid task status response.")

    steps_obj = state.get("steps", {})
    if not isinstance(steps_obj, dict):
        steps_obj = {}

    ui_steps = []
    for key, step in steps_obj.items():
        if not isinstance(step, dict):
            continue
        ui_steps.append({
            "title": key.replace("_", " ").title(),
            "status": step.get("status", "pending"),
            "detail": step.get("error") or (
                f"{step.get('status', 'pending').replace('_', ' ').title()} · "
                f"attempts: {step.get('attempts', 0)}"
            ),
        })

    opportunities = []
    deliverables = []
    email_draft = None
    verification = None
    for key, step in steps_obj.items():
        if not isinstance(step, dict) or not isinstance(step.get("output"), dict):
            continue
        output = step["output"]
        if key == "verify_listings":
            opportunities = output.get("opportunities", opportunities)
        elif key == "filter_and_rank":
            opportunities = output.get("opportunities", opportunities)
        elif key == "research" and not opportunities:
            opportunities = output.get("opportunities", opportunities)
        elif key == "save_spreadsheet":
            path = output.get("path") or output.get("spreadsheet_path") or output.get("file_path")
            filename = output.get("filename")
            if path:
                filename = str(path).replace("\\", "/").rsplit("/", 1)[-1]
            if filename:
                deliverables.append({
                    "name": "Internship shortlist spreadsheet",
                    "description": "Generated by the backend. Download it to review the ranked opportunities.",
                    "url": api_base_url() + "/api/files/" + requests.utils.quote(str(filename), safe=""),
                })
        elif key == "draft_email":
            email_draft = output
            draft_path = output.get("path") or output.get("email_path") or output.get("file_path")
            draft_filename = output.get("filename")
            if draft_path:
                draft_filename = str(draft_path).replace("\\", "/").rsplit("/", 1)[-1]
            if draft_filename:
                deliverables.append({
                    "name": "Personalized application email draft",
                    "description": "Draft only. No email was sent.",
                    "url": api_base_url() + "/api/files/" + requests.utils.quote(str(draft_filename), safe=""),
                })
        elif key == "verify_results":
            verification = output

    errors = state.get("errors", [])
    status = state.get("status", "running")
    result = {
        "status": status,
        "task_id": state.get("task_id"),
        "message": "Task " + str(status).replace("_", " ") + ".",
        "opportunities": opportunities if isinstance(opportunities, list) else [],
        "steps": ui_steps,
        "errors": errors if isinstance(errors, list) else [],
        "deliverables": deliverables,
        "verification": verification or {},
        "email_draft": email_draft,
        "user_request": state.get("user_request", {}),
    }
    if status == "failed" and errors:
        last_error = errors[-1]
        if isinstance(last_error, dict):
            result["error"] = last_error.get("message", "Task failed.")
    return result


def call_agent(body):
    """Start a backend task, poll its status, and normalize the final result."""
    payload = _task_request_from_frontend(body)
    response = requests.post(
        api_base_url() + "/api/tasks",
        json=payload,
        headers={"Accept": "application/json"},
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(
            f"Backend returned HTTP {response.status_code}: {response.text[:800]}"
        )
    try:
        started = response.json()
    except ValueError as exc:
        raise RuntimeError("The backend start response was not valid JSON.") from exc
    task_id = started.get("task_id") if isinstance(started, dict) else None
    if not task_id:
        raise RuntimeError("The backend accepted no task ID; cannot check task progress.")

    status_url = api_base_url() + "/api/tasks/" + requests.utils.quote(str(task_id), safe="")
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        time.sleep(1.5)
        status_response = requests.get(status_url, headers={"Accept": "application/json"}, timeout=15)
        if not status_response.ok:
            raise RuntimeError(
                f"Could not read task status (HTTP {status_response.status_code}): {status_response.text[:500]}"
            )
        try:
            state = status_response.json()
        except ValueError as exc:
            raise RuntimeError("The backend task-status response was not valid JSON.") from exc
        status = str(state.get("status", "running")).lower() if isinstance(state, dict) else "unknown"
        if status in {"completed", "failed", "error"}:
            # Preserve partial results even when a later backend step fails.
            # The UI can show completed outputs and the failed step honestly.
            result = _flatten_task_state(state)
            result["task_id"] = task_id
            if status != "completed":
                result["message"] = (
                    f"Task {task_id} ended with status '{status}'. "
                    "Any outputs from completed steps are shown below."
                )
            return result

    raise requests.Timeout(
        f"Task {task_id} is still running after 600 seconds. "
        "Check the backend logs and task state before launching another task."
    )


def fail_run(run_status, message):
    st.session_state.last_error = message
    run_status.update(label="Agent could not complete", state="error", expanded=False)


# ----------------------------- RESULT HELPERS -----------------------------

def normalize_opportunities(payload):
    rows = first_present(payload, ["internships", "opportunities", "results", "shortlist"], [])

    if isinstance(rows, dict):
        rows = rows.get("items", rows.get("results", []))
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    aliases = {
        "company_name": "Company", "employer": "Company",
        "organization": "Company", "organisation": "Company",
        "title": "Role", "role": "Role", "position": "Role",
        "job_title": "Role", "internship_title": "Role",
        "location": "Location", "work_location": "Location",
        "stipend": "Stipend", "salary": "Stipend", "compensation": "Stipend",
        "match_score": "Match score", "relevance_score": "Match score",
        "score": "Match score", "deadline": "Deadline",
        "application_deadline": "Deadline", "url": "URL",
        "link": "URL", "source_url": "URL", "application_url": "URL",
        "apply_url": "URL",
    }

    df = df.rename(columns={
        col: aliases[col.lower()]
        for col in df.columns if col.lower() in aliases
    })

    # Nested listing inspection can contain another `url` field. Pandas allows
    # duplicate names, but Streamlit/PyArrow does not; make every display name unique.
    unique_columns = []
    seen_columns = {}
    for column in df.columns:
        name = str(column)
        seen_columns[name] = seen_columns.get(name, 0) + 1
        if seen_columns[name] > 1:
            name = f"{name} ({seen_columns[name]})"
        unique_columns.append(name)
    df.columns = unique_columns

    preferred = ["Company", "Role", "Location", "Stipend", "Match score", "Deadline", "URL"]
    ordered = [c for c in preferred if c in df.columns]
    ordered += [c for c in df.columns if c not in ordered]
    return df[ordered]


def prepare_results(df):
    """Make the match score numeric (0-100) so it can be sorted and drawn as a bar."""
    df = df.copy()

    if "Match score" in df.columns:
        numeric = pd.to_numeric(
            df["Match score"].astype(str).str.replace("%", "", regex=False).str.strip(),
            errors="coerce",
        )
        if numeric.notna().any():
            # Scores returned as 0-1 fractions are scaled to a percentage.
            if numeric.max() <= 1:
                numeric = numeric * 100
            df["Match score"] = numeric.round(0)

    return df


def display_execution_steps(payload):
    steps = first_present(payload, ["steps", "execution_steps", "trace", "events"], [])

    if isinstance(steps, str):
        steps = [steps]
    if not isinstance(steps, list) or not steps:
        st.info("No execution trail was returned. Your backend can return a 'steps' array here.")
        return

    for index, item in enumerate(steps, start=1):
        if isinstance(item, dict):
            title = safe_text(first_present(item, ["title", "name", "step", "action"], f"Step {index}"))
            detail = safe_text(first_present(item, ["detail", "message", "description", "output"], "Completed"))
            state = str(item.get("status", "completed")).lower()
        else:
            title, detail, state = f"Execution event {index}", str(item), "completed"

        symbol = "✅" if state in ("done", "complete", "completed", "success", "successful") else "🔄" if state in ("running", "in_progress", "pending") else "•"
        with st.container(border=True):
            left, right = st.columns([0.08, 0.92])
            left.markdown(f"### {symbol}")
            right.markdown(f"**{title}**")
            right.caption(detail)


def show_deliverables(payload):
    items = payload.get("deliverables", [])

    if isinstance(items, dict):
        items = [{"name": k, "content": v} for k, v in items.items()]

    if not isinstance(items, list) or not items:
        render_html("""
        <div class="empty-state">
          <div class="empty-icon">📦</div>
          <div class="empty-title">No deliverables returned yet</div>
          <div class="empty-copy">Application drafts and files will appear here when the backend returns them.</div>
        </div>
        """)
    else:
        for index, item in enumerate(items):
            if isinstance(item, str):
                st.write("• " + item)
                continue
            if not isinstance(item, dict):
                st.write(str(item))
                continue

            name = safe_text(first_present(item, ["name", "title", "type"], f"Deliverable {index + 1}"))
            description = safe_text(first_present(item, ["description", "message"], ""), "")
            url = first_present(item, ["url", "download_url", "href"])
            content = first_present(item, ["content", "text", "body"])

            with st.container(border=True):
                st.markdown(f"**📄 {name}**")
                if description:
                    st.caption(description)
                if url:
                    st.link_button("🔗 Open deliverable", str(url))
                elif content is not None:
                    st.download_button(
                        "⬇️ Download deliverable", str(content),
                        file_name=f"{name.lower().replace(' ', '_')}.txt",
                        mime="text/plain", key=f"deliverable_{index}"
                    )

    drafts = first_present(payload, ["email_drafts", "application_emails", "cover_letters"], [])
    if isinstance(drafts, dict):
        drafts = [{"title": k, "content": v} for k, v in drafts.items()]

    if isinstance(drafts, list) and drafts:
        st.markdown("#### ✉️ Personalized application drafts")
        for index, draft in enumerate(drafts):
            if isinstance(draft, dict):
                title = safe_text(first_present(draft, ["title", "role", "company", "name"], f"Draft {index + 1}"))
                content = safe_text(first_present(draft, ["content", "body", "text"], ""), "")
            else:
                title, content = f"Draft {index + 1}", str(draft)

            with st.expander(title):
                st.text_area("Draft content", content, height=210, key=f"draft_text_{index}")
                st.download_button(
                    "⬇️ Download draft", content,
                    file_name=f"application_draft_{index + 1}.txt",
                    mime="text/plain", key=f"draft_download_{index}"
                )


# -------------------------------- SIDEBAR --------------------------------
with st.sidebar:
    render_html("""
    <div class="brand-row">
      <div class="brand-mark">✳</div>
      <div>
        <div class="brand-name">opportunity<span style="color:#efffc1">OS</span></div>
        <div class="brand-sub">CAREER INTELLIGENCE STUDIO</div>
      </div>
    </div>
    <div class="sidebar-chip">✨ WORKSPACE READY</div>
    <div class="sidebar-label">Workspace overview</div>
    <div class="sidebar-stat"><span>🤖 Agent mode</span><b>AUTONOMOUS</b></div>
    <div class="sidebar-stat"><span>✍️ Main input</span><b>PROMPT</b></div>
    <div class="sidebar-stat"><span>📄 Extra feature</span><b>RESUME</b></div>
    <div class="sidebar-stat"><span>🎯 Output</span><b>SHORTLIST</b></div>
    <div class="sidebar-label">Developer</div>
    """)

    with st.expander("⚙️ Developer settings"):
        st.text_input("API base URL", key="api_url")
        st.text_input(
            "Profile ID",
            key="profile_id",
            help="Reuse this ID to retrieve a saved profile later.",
        )

        if st.button("🔌 Test connection", use_container_width=True):
            try:
                response = requests.get(api_base_url() + "/api/health", timeout=5)
                if response.ok:
                    st.success(f"Connected · HTTP {response.status_code}")
                else:
                    st.warning(f"Backend responded with HTTP {response.status_code}.")
            except requests.RequestException:
                st.error("Cannot reach the backend. Check the URL and start the API.")

    st.markdown("---")
    st.caption("OPPORTUNITY OS · HACKATHON BUILD")
    st.caption("Research depends on connected backend services.")


# -------------------------------- HERO --------------------------------
render_html("""
<div class="hero">
  <div class="hero-main">
    <div class="hero-eyebrow">✦ CAREER INTELLIGENCE / AUTONOMOUS AGENT</div>
    <div class="hero-title">Your next move,<br><span class="hero-gradient">minus the busywork.</span></div>
    <p class="hero-copy">Give your agent a task in your own words. It can research relevant opportunities, compare requirements, and turn results into clear next steps. Resume upload is optional and helps personalize matching.</p>
    <div class="hero-foot">
      <span class="hero-pill"><span class="live-dot"></span> PROMPT-FIRST WORKFLOW</span>
      <span class="hero-pill">🔎 RESEARCH + VALIDATION</span>
      <span class="hero-pill">🌱 OPTIONAL RESUME PROFILE</span>
    </div>
  </div>
  <div class="hero-side">
    <div class="hero-side-label">YOUR CAREER COPILOT</div>
    <div class="hero-side-title">From brief to shortlist ✨</div>
    <div class="hero-side-copy">Turn a single task into a structured search, qualification checks, and an organized set of next steps.</div>
    <div class="signal-row">
      <span class="signal" style="height:11px"></span>
      <span class="signal" style="height:19px"></span>
      <span class="signal" style="height:13px"></span>
      <span class="signal" style="height:28px"></span>
      <span class="signal" style="height:18px"></span>
      <span class="signal" style="height:24px"></span>
      <span class="signal" style="height:15px"></span>
      <span class="signal" style="height:30px"></span>
      <span class="signal" style="height:20px"></span>
    </div>
    <div class="hero-side-copy">ONE PROMPT · MULTIPLE RESEARCH STEPS</div>
  </div>
</div>
""")


# ----------------------------- PRIMARY PROMPT -----------------------------
render_html("""
<div class="section-head">
  <div class="section-title">✍️ Create a task</div>
  <div class="section-note">PRIMARY INPUT · NATURAL LANGUAGE</div>
</div>
<div class="tiny" style="margin-bottom:10px">Tell the agent what you want in your own words—role type, location, work mode, stipend, timing, or other constraints. There are no preset prompt choices.</div>
""")

user_prompt = st.text_area(
    "Task instructions",
    height=155,
    key="user_prompt",
    placeholder="Describe the opportunities you want the agent to find and any preferences or constraints it should follow...",
)


# ------------------------------ WORKFLOW (collapsed) ------------------------------
phases = [
    ("01 / UNDERSTAND", "Understand the task", "Interpret your task, preferences, and constraints.", "lilac"),
    ("02 / DISCOVER", "Explore opportunities", "Search connected sources for relevant roles.", "aqua"),
    ("03 / VALIDATE", "Check the fit", "Compare role requirements with your criteria.", "peach"),
    ("04 / DELIVER", "Make it actionable", "Rank matches and prepare practical application assets.", "lemon"),
]

with st.expander("🧭 How the agent works"):
    phase_cols = st.columns(4)
    for col, (number, title, description, theme_class) in zip(phase_cols, phases):
        with col:
            render_html(f"""
            <div class="phase-card {theme_class}">
              <div class="phase-number">{number}</div>
              <div class="phase-title">{title}</div>
              <div class="phase-copy">{description}</div>
            </div>
            """)


# --------------------------- OPTIONAL RESUME ---------------------------
render_html("""
<div class="section-head">
  <div class="section-title">📄 Optional profile enhancement</div>
  <div class="section-note">RESUME UPLOAD · NOT REQUIRED</div>
</div>
<div class="tiny" style="margin-bottom:10px">Want more personalized matching? Add a resume so the agent can consider your skills, education, projects, and experience. You can skip this section entirely.</div>
""")

with st.expander("➕ Upload a resume or load an existing profile"):
    uploaded_resume = st.file_uploader(
        "Resume file (PDF or DOCX)",
        type=["pdf", "docx"],
        key="resume_upload",
    )

    resume_a, resume_b = st.columns(2)
    with resume_a:
        extract_clicked = st.button("✨ Extract profile", use_container_width=True)
    with resume_b:
        load_profile_clicked = st.button("📥 Load saved profile", use_container_width=True)

    if extract_clicked:
        if uploaded_resume is None:
            st.warning("Choose a resume first. This feature is optional.")
        else:
            try:
                text = extract_resume_text(uploaded_resume)
                profile = build_candidate_profile(text, uploaded_resume.name)
                set_profile_widgets(profile)
                st.success("Resume extracted. Review and correct the details below.")
            except Exception as exc:
                st.error(str(exc))

    if load_profile_clicked:
        if isinstance(st.session_state.candidate_profile, dict):
            set_profile_widgets(st.session_state.candidate_profile)
            st.success("Profile restored from this active session.")
        else:
            st.info("This backend does not provide profile storage endpoints. Upload your resume and choose Extract profile, or restore a previously downloaded JSON profile in a future update.")


profile_exists = (
    isinstance(st.session_state.candidate_profile, dict)
    or bool(st.session_state.resume_text)
)

if profile_exists:
    saved_profile = st.session_state.candidate_profile or {}

    for field, widget_key in PROFILE_FIELDS.items():
        if widget_key not in st.session_state:
            st.session_state[widget_key] = profile_value_for_widget(field, saved_profile.get(field, ""))

    # Safety net: never hand the selectbox a value that is not in its options.
    st.session_state["profile_preferred_work_mode"] = normalize_work_mode(
        st.session_state.get("profile_preferred_work_mode")
    )

    filename = html.escape(safe_text(st.session_state.resume_filename, "Saved profile"))

    render_html(f"""
    <div class="status-box"><strong>🌷 Candidate profile available</strong><br>
    {filename} · Review the extracted details before using them.</div>
    """)

    with st.expander("🪄 Review and edit candidate profile", expanded=True):
        left, right = st.columns(2)

        with left:
            st.text_input("Full name", key="profile_name")
            st.text_input("Email", key="profile_email")
            st.text_input("Phone", key="profile_phone")
            st.text_area("Education / degree", key="profile_education", height=78)
            st.text_input("Graduation year", key="profile_graduation_year")
            st.text_input("Preferred location", key="profile_preferred_location", placeholder="Optional")

        with right:
            st.text_area("Skills (comma-separated)", key="profile_skills", height=78)
            st.text_area("Projects", key="profile_projects", height=95)
            st.text_area("Experience / internships", key="profile_experience", height=95)
            st.text_area("Certifications", key="profile_certifications", height=70)
            st.selectbox(
                "Preferred work mode",
                WORK_MODES,
                key="profile_preferred_work_mode",
            )
            st.text_input("Minimum stipend", key="profile_minimum_stipend", placeholder="Optional")

        save_col, backup_col = st.columns(2)
        with save_col:
            save_profile_clicked = st.button("💾 Save profile to backend", use_container_width=True)
        with backup_col:
            st.download_button(
                "⬇️ Download profile backup",
                data=json.dumps(get_profile_from_widgets(), indent=2, ensure_ascii=False),
                file_name="opportunity_os_profile.json",
                mime="application/json",
                use_container_width=True,
            )

        if save_profile_clicked:
            profile = get_profile_from_widgets()
            st.session_state.candidate_profile = profile

            st.success("Profile saved for this active session. Use Download profile backup to keep a copy; backend profile persistence is not available in the current API.")

    if st.session_state.resume_text:
        with st.expander("📖 View extracted resume text"):
            st.text_area(
                "Extracted content",
                value=st.session_state.resume_text,
                height=190,
                disabled=True,
                key="resume_text_preview",
            )


# ------------------------------ LAUNCH AGENT ------------------------------
st.markdown("")
launch = st.button("🚀  Launch opportunity search", use_container_width=True)

if launch:
    if not user_prompt.strip():
        st.warning("Enter your task prompt before launching. Resume upload is optional and does not replace the prompt.")

    else:
        st.session_state.last_payload = None
        st.session_state.last_error = None
        st.session_state.last_prompt = user_prompt.strip()

        profile = get_profile_from_widgets() if profile_exists else {}

        render_html("""
        <div class="section-head">
          <div class="section-title">⚡ Agent execution</div>
          <div class="section-note">TASK SUBMITTED</div>
        </div>
        """)

        started_at = time.time()

        with st.status("Agent is working…", expanded=True) as run_status:
            try:
                st.write("🧭 Understanding your task…")
                if profile:
                    st.write("📄 Attaching your reviewed candidate profile…")
                st.write("🔎 Researching and validating opportunities. This can take a minute or two…")

                body = {"prompt": user_prompt.strip()}
                if profile:
                    body["candidate_profile"] = profile
                    body["profile_id"] = st.session_state.profile_id

                result = call_agent(body)

                st.session_state.last_payload = result
                elapsed = time.time() - started_at
                run_status.update(
                    label=f"Response received in {elapsed:.0f}s",
                    state="complete",
                    expanded=False,
                )

            except requests.Timeout:
                fail_run(
                    run_status,
                    "The task did not finish before the frontend timeout. Check the backend logs and task state before retrying.",
                )

            except requests.ConnectionError:
                fail_run(
                    run_status,
                    f"Could not connect to {api_base_url()}. Start the backend and verify the API URL.",
                )

            except requests.RequestException as exc:
                fail_run(run_status, str(exc))

            except RuntimeError as exc:
                fail_run(run_status, str(exc))

            except Exception as exc:
                fail_run(run_status, f"Unexpected error: {exc}")


# -------------------------------- ERRORS --------------------------------
if st.session_state.last_error:
    render_html("""
    <div class="section-head">
      <div class="section-title">⚠️ Agent could not complete</div>
      <div class="section-note">CONNECTION / RESPONSE ISSUE</div>
    </div>
    """)

    st.error(st.session_state.last_error)
    st.caption(
        "The frontend starts work through POST /api/tasks and polls GET /api/tasks/{task_id}. "
        "The current backend accepts degree, year, skills, location, work_mode, and count; "
        "some free-text constraints may need to be reflected in those fields."
    )


# ------------------------------ MISSION CONTROL ------------------------------
payload = st.session_state.last_payload

if isinstance(payload, dict):
    render_html("""
    <div class="section-head">
      <div class="section-title">🎯 Mission control</div>
      <div class="section-note">LATEST AGENT RESPONSE</div>
    </div>
    """)

    status = str(first_present(payload, ["status", "state"], "Response received"))
    summary = str(first_present(payload, ["message", "summary", "overview"], "The backend returned a response. Review the findings below."))
    df = normalize_opportunities(payload)
    errors = payload.get("errors", [])

    error_count = len(errors) if isinstance(errors, list) else (1 if errors else 0)
    outputs = payload.get("deliverables", [])
    output_count = len(outputs) if isinstance(outputs, (list, dict)) else 0

    metrics = [
        ("🔎 OPPORTUNITIES", str(len(df)), "Returned by backend", ""),
        ("🧭 RUN STATUS", status.upper(), "Backend-reported status", "mint"),
        ("🧩 ISSUES", str(error_count), "Reported by backend", "peach"),
        ("📦 DELIVERABLES", str(output_count), "Returned by backend", "lemon"),
    ]

    metric_cols = st.columns(4)
    for col, (label, value, subtitle, variant) in zip(metric_cols, metrics):
        with col:
            size = 20 if len(value) > 12 else 26
            render_html(f"""
            <div class="metric-card {variant}">
              <div class="metric-label">{html.escape(label)}</div>
              <div class="metric-value" style="font-size:{size}px">{html.escape(value)}</div>
              <div class="metric-sub">{html.escape(subtitle)}</div>
            </div>
            """)

    st.markdown("")
    render_html('<div class="status-box"><strong>✨ Agent summary</strong></div>')
    if status.lower() in {"failed", "error"}:
        st.warning(
            "The backend reported a failure. The sections below may still contain "
            "useful outputs from steps that completed before the failure. "
            "Do not treat the whole workflow as successful."
        )
        if payload.get("error"):
            st.error(str(payload["error"]))
    st.write(summary)

    if payload.get("task_id"):
        st.caption(f"Task ID: {payload['task_id']}")

    results_tab, trace_tab, files_tab, raw_tab = st.tabs([
        "🔎 Opportunity shortlist",
        "🧭 Execution trail",
        "📦 Deliverables",
        "🛠️ Raw response",
    ])

    with results_tab:
        if df.empty:
            render_html("""
            <div class="empty-state">
              <div class="empty-icon">🌱</div>
              <div class="empty-title">No opportunity records returned</div>
              <div class="empty-copy">
                The backend did not return an opportunities list. Once research is
                connected, actual matching roles will appear here. This interface
                does not create fake listings.
              </div>
            </div>
            """)

        else:
            df = prepare_results(df)
            filter_col, sort_col = st.columns([1.2, 1])

            with filter_col:
                query = st.text_input(
                    "Search shortlist",
                    placeholder="Company, role or location",
                    key="results_query",
                )

            with sort_col:
                choices = [
                    c for c in ["Match score", "Deadline", "Company", "Role"]
                    if c in df.columns
                ]
                order_by = st.selectbox("Sort by", choices, key="results_sort") if choices else None

            shown = df.copy()

            if query:
                # regex=False so typing something like "C++" can't crash the filter.
                mask = shown.astype(str).apply(
                    lambda col: col.str.contains(query, case=False, na=False, regex=False)
                ).any(axis=1)
                shown = shown[mask]

            if order_by == "Match score":
                shown = shown.sort_values("Match score", ascending=False, na_position="last")
            elif order_by == "Deadline":
                deadline_key = pd.to_datetime(shown["Deadline"], errors="coerce")
                shown = (
                    shown.assign(_key=deadline_key)
                    .sort_values("_key", ascending=True, na_position="last")
                    .drop(columns="_key")
                )
            elif order_by:
                shown = shown.sort_values(
                    order_by,
                    ascending=True,
                    na_position="last",
                    key=lambda s: s.astype(str).str.lower(),
                )

            column_config = {}
            if "Match score" in shown.columns and pd.api.types.is_numeric_dtype(shown["Match score"]):
                column_config["Match score"] = st.column_config.ProgressColumn(
                    "Match",
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                )
            if "URL" in shown.columns:
                column_config["URL"] = st.column_config.LinkColumn(
                    "Apply",
                    display_text="Open ↗",
                )

            st.caption(f"Showing {len(shown)} of {len(df)} backend-returned opportunities.")
            st.dataframe(
                shown,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                height=min(520, 100 + 42 * min(len(shown), 10)),
            )

            st.download_button(
                "📥  Download shortlist as CSV",
                shown.to_csv(index=False).encode("utf-8-sig"),
                file_name="opportunity_os_shortlist.csv",
                mime="text/csv",
            )

            if "URL" in shown.columns:
                st.markdown("#### 🔗 Opportunity links")
                for _, row in shown.iterrows():
                    url = safe_text(row.get("URL"), "")
                    if url.startswith(("https://", "http://")):
                        company = safe_text(row.get("Company"), "Opportunity")
                        role = safe_text(row.get("Role"), "Open listing")
                        st.markdown(f"- [{company} — {role}]({url})")

    with trace_tab:
        display_execution_steps(payload)
        if errors:
            st.markdown("#### Issues reported by the agent")
            if isinstance(errors, list):
                for error in errors:
                    st.warning(str(error))
            else:
                st.warning(str(errors))

    with files_tab:
        show_deliverables(payload)

    with raw_tab:
        st.caption("Debug view for backend integration.")
        st.json(payload)

    render_html('<div class="footer">OPPORTUNITY OS · CAREER INTELLIGENCE STUDIO</div>')

else:
    render_html("""
    <div class="section-head">
      <div class="section-title">🌈 Ready when you are</div>
      <div class="section-note">YOUR WORKSPACE IS READY</div>
    </div>
    <div class="empty-state">
      <div class="empty-icon">✳</div>
      <div class="empty-title">One prompt. A whole research workflow.</div>
      <div class="empty-copy">
        Tell the agent what you want to find. Resume upload is optional.
        When the backend is connected, actual research results, source links,
        execution details, and deliverables will appear here.
      </div>
    </div>
    <div class="footer">OPPORTUNITY OS · CAREER INTELLIGENCE STUDIO</div>
    """)