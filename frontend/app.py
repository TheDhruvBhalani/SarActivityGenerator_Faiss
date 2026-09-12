"""
SAR Generator - Streamlit Frontend
Layer 1 UI for SAR Generation System

Run with:
    streamlit run frontend/app.py
"""
import streamlit as st
import requests
import json
import pandas as pd
import glob
import os
import re
from datetime import datetime
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
GENERATED_SARS_DIR = str(PROJECT_ROOT / "data" / "generated_narratives")

# Page config
st.set_page_config(
    page_title="SAR Generator",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="expanded"
)

# Ensure output directory exists
os.makedirs(GENERATED_SARS_DIR, exist_ok=True)

# Session state initialization
for k, v in {
    "token": None,
    "role": None,
    "username": None,
    "generated_sar": None,
    "current_alert_id": "ALERT001",
    "edit_mode": False,
    "saved_text": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_narrative(data) -> str:
    """Convert narrative dict or string into readable text"""
    if data is None:
        return "_No narrative generated._"
    if isinstance(data, dict):
        text = (
            data.get("fulltext") or
            data.get("full_text") or
            data.get("narrative") or
            data.get("text") or
            "\n\n".join(str(v) for v in data.values() if v)
        )
        return text or "_Empty narrative._"
    return str(data)


def strip_markdown(text: str) -> str:
    """Strip markdown formatting for plain text editing"""
    lines_in = text.split("\n")
    out = []
    for line in lines_in:
        line = re.sub(r"^#{1,6}\s*", "", line)
        if re.match(r"^\s*[-\*_]{2,}\s*$", line):
            continue
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"__(.+?)__", r"\1", line)
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        line = re.sub(r"_(.+?)_", r"\1", line)
        line = re.sub(r"`(.+?)`", r"\1", line)
        line = re.sub(r"^>\s*", "", line)
        if re.match(r"^\s*\|.*\|\s*$", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^[-:\s]+$", c) for c in cells if c):
                continue
            line = "  |  ".join(c for c in cells if c)
        line = re.sub(r"^\s*[-\*\+]\s+", "", line)
        line = re.sub(r"^\s*\d+\.\s+", "", line)
        out.append(line)
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return result.strip()


def sget(d, *keys, default="?"):
    """Safe get from dict with multiple key options"""
    for k in keys:
        if k in d:
            return d[k]
    return default


def api_call(method, endpoint, data=None, auth_required=True):
    """Make API call to backend"""
    if auth_required and not st.session_state.token:
        return None, "Not authenticated."

    url = f"{API_BASE_URL}{endpoint}"
    headers = {}
    if auth_required and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=60)
        else:
            resp = requests.post(url, json=data, headers=headers, timeout=120)

        if resp.status_code == 200:
            return resp.json(), None
        else:
            return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
    except requests.exceptions.ConnectionError:
        return None, "API offline - ensure backend is running on port 8000"
    except Exception as e:
        return None, f"Error: {e}"


def load_all_sars_from_disk():
    """Load SAR files from local storage"""
    if not os.path.exists(GENERATED_SARS_DIR):
        return []

    files = sorted(
        glob.glob(f"{GENERATED_SARS_DIR}/*.json"),
        key=os.path.getctime,
        reverse=True
    )[:50]

    sars = []
    for fp in files:
        try:
            with open(fp) as f:
                data = json.load(f)
            if sget(data, "sarid", "sar_id") != "?":
                sars.append(data)
        except Exception:
            pass
    return sars


def save_sar_to_disk(sar_data, updated_text):
    """Save edited SAR narrative to disk"""
    sar_id = sget(sar_data, "sarid", "sar_id")
    for fp in glob.glob(f"{GENERATED_SARS_DIR}/*.json"):
        try:
            with open(fp) as f:
                d = json.load(f)
            if sget(d, "sarid", "sar_id") == sar_id:
                if isinstance(d.get("narrative"), dict):
                    for key in ("fulltext", "full_text", "narrative", "text", "content"):
                        if key in d["narrative"]:
                            d["narrative"][key] = updated_text
                            break
                else:
                    d["narrative"] = updated_text
                with open(fp, "w") as f:
                    json.dump(d, f, indent=2)
                return True
        except Exception:
            pass
    return False


def get_approval_badge(sar):
    """Get approval status badge"""
    status = sar.get("approvalstatus", None)
    if status == "APPROVED":
        return "APPROVED"
    elif status == "REJECTED":
        return "REJECTED"
    else:
        return "PENDING"


# =============================================================================
# SIDEBAR - AUTHENTICATION
# =============================================================================

st.sidebar.title("Authentication")

if not st.session_state.token:
    username = st.sidebar.text_input("Username", value="analyst1")
    password = st.sidebar.text_input("Password", value="pass123", type="password")

    if st.sidebar.button("Login", type="primary"):
        result, err = api_call(
            "POST", "/api/v1/auth/login",
            {"username": username, "password": password},
            auth_required=False
        )
        if result:
            st.session_state.token = result["access_token"]
            st.session_state.role = result["role"]
            st.session_state.username = result["username"]
            st.sidebar.success(f"Logged in as {result['role']}")
            st.rerun()
        else:
            st.sidebar.error(f"{err}")

    st.sidebar.info("""
**Demo Credentials:**
- `analyst1` / `pass123` → ANALYST
- `compliance1` / `comply123` → COMPLIANCE_OFFICER
- `admin` / `admin123` → ADMIN
    """)

else:
    role = st.session_state.role
    username = st.session_state.username or role.lower()
    st.sidebar.success(f"**{role}**")
    st.sidebar.caption(f"Logged in as: `{username}`")

    if role == "ADMIN":
        st.sidebar.info("Full access - Generate, Approve & Audit")
    elif role == "ANALYST":
        st.sidebar.info("Generate SARs, Approve/Reject, view Audit Trails")
    elif role == "COMPLIANCE_OFFICER":
        st.sidebar.info("Oversight - View all SARs and Audit Trails")
        st.sidebar.warning("Cannot generate or approve SARs")

    if st.sidebar.button("Logout"):
        for k in ["token", "role", "username", "generated_sar", "edit_mode", "saved_text"]:
            st.session_state[k] = None
        st.session_state["edit_mode"] = False
        st.rerun()

# API Health Check
st.sidebar.divider()
health, _ = api_call("GET", "/api/health", auth_required=False)
if health:
    svcs = health.get("services", {})
    st.sidebar.success("API Online")
    st.sidebar.caption(
        f"DB: {svcs.get('database', '?')} | "
        f"RAG: {svcs.get('ragpipeline', '?')} | "
        f"LLM: {svcs.get('llmengine', '?')}"
    )
else:
    st.sidebar.error("API Offline")
    st.sidebar.warning("Run `python main.py` to start backend")


# =============================================================================
# MAIN CONTENT
# =============================================================================

st.title("SAR Narrative Generator")
st.markdown("*Layer 2 FastAPI → RAG → LLM → Audit Trail*")
st.divider()

if not st.session_state.token:
    st.warning("Please login using the sidebar to continue.")
    st.stop()

role = st.session_state.role or "ANALYST"
username = st.session_state.username or role.lower()

tab1, tab2, tab3 = st.tabs(["Generate SAR", "Review & Approve", "Audit Trail"])


# =============================================================================
# TAB 1 - GENERATE SAR
# =============================================================================

with tab1:
    st.header("Generate SAR from Alert")

    if role == "COMPLIANCE_OFFICER":
        st.warning("""
**COMPLIANCE_OFFICER** role cannot generate SARs.

Your access is oversight only:
- **Tab 2** - View all SAR narratives (read-only)
- **Tab 3** - View the full 7-step Audit Trail

To generate a SAR, login as `analyst1` (ANALYST).
        """)

    else:
        col_left, col_right = st.columns([1, 3])

        with col_left:
            st.subheader("Alert Selection")
            alert_options = {
                "ALERT001 - Structuring": "ALERT001",
                "ALERT002 - Layering": "ALERT002",
                "ALERT003 - TBML": "ALERT003",
            }
            selected = st.selectbox("Select Alert:", list(alert_options.keys()))
            st.session_state.current_alert_id = alert_options[selected]
            st.code(f"Alert ID: {st.session_state.current_alert_id}")

            use_hybrid = st.checkbox("Hybrid Search (BM25 + Semantic)", value=True)
            use_reranking = st.checkbox("Cross-Encoder Re-ranking", value=True)
            st.divider()

            if st.button("Generate SAR", type="primary", use_container_width=True):
                with st.spinner("RAG → LLM → Validation → Audit (30-90s)..."):
                    result, err = api_call("POST", "/api/v1/generate-sar", {
                        "alertid": st.session_state.current_alert_id,
                        "analystid": username,
                        "usehybrid": use_hybrid,
                        "usereranking": use_reranking,
                    })
                    if result:
                        st.session_state.generated_sar = result
                        st.session_state.saved_text = None
                        st.session_state.edit_mode = False
                        st.success(f"SAR Generated: `{result['sarid']}`")
                        st.rerun()
                    else:
                        st.error(f"{err}")

        with col_right:
            st.subheader("Generated SAR")
            if st.session_state.generated_sar:
                sar = st.session_state.generated_sar
                c1, c2, c3 = st.columns(3)
                c1.metric("SAR ID", sget(sar, "sarid", "sar_id")[-15:])
                c2.metric(
                    "Time",
                    f"{float(sget(sar, 'generationtimeseconds', 'generation_time_seconds', default=0)):.1f}s"
                )
                c3.metric("Status", sget(sar, "validationstatus", "validation_status"))

                st.markdown("### Full SAR Narrative")
                narrative_text = render_narrative(sar.get("narrative"))
                with st.container(border=True):
                    st.markdown(narrative_text)

                st.download_button(
                    "Download SAR (.txt)",
                    data=narrative_text,
                    file_name=f"{sget(sar, 'sarid', 'sar_id')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

                with st.expander("Raw Metadata"):
                    st.json(sar.get("metadata", {}))
            else:
                st.info("Click **Generate SAR** to create a narrative.")


# =============================================================================
# TAB 2 - REVIEW & APPROVE
# =============================================================================

with tab2:
    st.header("Review & Approve SAR")

    disk_sars = load_all_sars_from_disk()
    sar_options = {}

    if st.session_state.generated_sar:
        s = st.session_state.generated_sar
        key = f"[Session] {sget(s, 'sarid', 'sar_id')} - {sget(s, 'alertid', 'alert_id')}"
        sar_options[key] = s

    for s in disk_sars:
        sar_id_val = sget(s, "sarid", "sar_id")
        alert_id_val = sget(s, "alertid", "alert_id")
        analyst_val = s.get("analystid", "unknown")
        approval_val = s.get("approvalstatus", "PENDING")
        approval_icon = {"APPROVED": "[OK]", "REJECTED": "[X]"}.get(approval_val, "[?]")
        key = f"[Disk] {sar_id_val} | {alert_id_val} | by {analyst_val} | {approval_icon} {approval_val}"
        if key not in sar_options:
            sar_options[key] = s

    if not sar_options:
        st.warning("No SARs found.")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            file_count = len(glob.glob(f'{GENERATED_SARS_DIR}/*.json')) if os.path.exists(GENERATED_SARS_DIR) else 0
            st.info(f"""
**Looking in:**
`{GENERATED_SARS_DIR}`

**Files found:** `{file_count}` JSON files
            """)
        with col_d2:
            st.info("""
**To create a SAR:**
1. Login as `analyst1`
2. Go to **Tab 1 → Generate SAR**
3. Come back here to review
            """)
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    else:
        sel_col, refresh_col = st.columns([5, 1])
        with sel_col:
            chosen_label = st.selectbox(
                f"Select SAR to Review ({len(sar_options)} available):",
                list(sar_options.keys())
            )
        with refresh_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Refresh", use_container_width=True):
                st.rerun()

        sar = sar_options[chosen_label]
        sar_id = sget(sar, "sarid", "sar_id")
        alert_id = sget(sar, "alertid", "alert_id")
        val_status = sget(sar, "validationstatus", "validation_status")
        generated_by = sar.get("analystid", "unknown")
        approval_badge = get_approval_badge(sar)

        st.info(
            f"**SAR ID:** `{sar_id}` | "
            f"**Alert:** `{alert_id}` | "
            f"**Generated by:** `{generated_by}` | "
            f"**Validation:** `{val_status}` | "
            f"**Approval:** {approval_badge}"
        )

        raw_markdown = render_narrative(sar.get("narrative"))

        # ANALYST / ADMIN - full edit + approve
        if role in ["ANALYST", "ADMIN"]:
            top_left, top_right = st.columns([3, 1])
            with top_left:
                st.markdown("### SAR Narrative")
            with top_right:
                if not st.session_state.edit_mode:
                    if st.button("Edit Narrative", use_container_width=True):
                        st.session_state.edit_mode = True
                        st.rerun()
                else:
                    if st.button("View Mode", use_container_width=True):
                        st.session_state.edit_mode = False
                        st.rerun()

            col_nar, col_approve = st.columns([2, 1])
            with col_nar:
                if not st.session_state.edit_mode:
                    with st.container(border=True):
                        st.markdown(raw_markdown)
                    if st.session_state.saved_text is not None:
                        st.success("Your edits are saved and will be submitted.")
                else:
                    working_plain = st.session_state.saved_text or strip_markdown(raw_markdown)
                    st.caption("Edit below - changes feed Track C learning.")
                    edited_input = st.text_area(
                        "narrative_editor",
                        value=working_plain,
                        height=600,
                        label_visibility="collapsed"
                    )
                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        if st.button("Save Changes", type="primary", use_container_width=True):
                            st.session_state.saved_text = edited_input
                            st.session_state.edit_mode = False
                            save_sar_to_disk(sar, edited_input)
                            st.rerun()
                    with cancel_col:
                        if st.button("Discard Changes", use_container_width=True):
                            st.session_state.edit_mode = False
                            st.rerun()

            with col_approve:
                st.subheader("Approval Decision")
                st.success(f"**{role}** - Approval enabled")
                st.divider()
                approval = st.radio("Decision:", ["APPROVED", "REJECTED"], index=0)
                comments = st.text_area(
                    "Reviewer Comments:",
                    height=150,
                    placeholder="Rationale, flags, observations..."
                )
                st.divider()
                if st.button("Submit Decision", type="primary", use_container_width=True):
                    with st.spinner("Submitting..."):
                        final_text = (
                            st.session_state.saved_text
                            if st.session_state.saved_text
                            else raw_markdown
                        )
                        result, err = api_call(
                            "POST",
                            f"/api/v1/sar/{sar_id}/approve",
                            {
                                "sarid": sar_id,
                                "analystid": username,
                                "editednarrative": {"fulltext": final_text},
                                "approvalstatus": approval,
                                "comments": comments,
                            }
                        )
                        if result:
                            if approval == "APPROVED":
                                st.success("SAR Approved and submitted!")
                            else:
                                st.error("SAR Rejected.")
                            if result.get("learningtriggered"):
                                st.info("Track C Adaptive Learning Triggered")
                            with st.expander("API Response"):
                                st.json(result)
                            st.rerun()
                        else:
                            st.error(f"{err}")

        # COMPLIANCE_OFFICER - oversight read-only view
        elif role == "COMPLIANCE_OFFICER":
            st.info("""
**COMPLIANCE_OFFICER - Oversight View**

You can read and download this SAR narrative.
The full 7-step audit trail is in **Tab 3**.

> **Approval / Rejection is performed by ANALYST** - not COMPLIANCE_OFFICER.
> This is an intentional RBAC control (PMLA separation of duties).
            """)

            approval_status = sar.get("approvalstatus", None)
            if approval_status == "APPROVED":
                st.success(f"This SAR has been **APPROVED** by `{sar.get('approved_by', 'analyst')}`")
            elif approval_status == "REJECTED":
                st.error(f"This SAR has been **REJECTED** by `{sar.get('approved_by', 'analyst')}`")
            else:
                st.warning("This SAR is **PENDING APPROVAL** - awaiting ANALYST review")

            st.markdown("### SAR Narrative (Read-only - Oversight)")
            with st.container(border=True):
                st.markdown(raw_markdown)

            dl_col, meta_col = st.columns(2)
            with dl_col:
                st.download_button(
                    "Download SAR (.txt)",
                    data=raw_markdown,
                    file_name=f"{sar_id}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with meta_col:
                with st.expander("SAR Metadata"):
                    st.json({
                        "sar_id": sar_id,
                        "alert_id": alert_id,
                        "generated_by": generated_by,
                        "approval_status": sar.get("approvalstatus", "PENDING"),
                        "approved_by": sar.get("approved_by", "-"),
                        "approved_at": sar.get("approved_at", "-"),
                        "validation": val_status,
                    })


# =============================================================================
# TAB 3 - AUDIT TRAIL
# =============================================================================

with tab3:
    st.header("Audit Trail")

    AUDIT_ROLES = ["ANALYST", "COMPLIANCE_OFFICER", "ADMIN"]

    if role not in AUDIT_ROLES:
        st.error("""
**Access Denied - Audit Trail**

Restricted to: ANALYST, COMPLIANCE_OFFICER, ADMIN

Login with `analyst1` / `pass123` or `compliance1` / `comply123`
        """)

    else:
        role_badge = {
            "ANALYST": "ANALYST",
            "COMPLIANCE_OFFICER": "COMPLIANCE_OFFICER",
            "ADMIN": "ADMIN",
        }.get(role, role)
        st.caption(f"Viewing as: **{role_badge}** - full audit access granted")

        STEP_ICONS = {
            "ALERT_INGESTION": "1",
            "RAG_RETRIEVAL": "2",
            "PATTERN_DETECTION": "3",
            "LLM_GENERATION": "4",
            "VALIDATION": "5",
            "COMPLIANCE_CHECK": "6",
            "ANALYST_ACTIONS": "7",
            "ERROR": "X",
        }

        DETAIL_LABELS = {
            "customer": "Customer",
            "txn_count": "Transactions",
            "total_amount": "Total Amount",
            "pattern_type": "Pattern",
            "tokens": "Tokens Used",
            "method": "Generation Method",
            "analyst": "Analyst",
            "alert_id": "Alert ID",
            "docs_retrieved": "Docs Retrieved",
            "retrieval_method": "Retrieval Method",
            "patterns_found": "Patterns Found",
            "risk_score": "Risk Score",
            "validation_score": "Validation Score",
            "checks_passed": "Checks Passed",
            "checks_failed": "Checks Failed",
            "word_count": "Word Count",
            "narrative_length": "Narrative Length",
            "generation_method": "Generation Method",
            "model_used": "Model Used",
            "compliance_flags": "Compliance Flags",
            "approval_status": "Approval Status",
            "action": "Action",
            "comments": "Comments",
            "knowledge_chunks": "Knowledge Chunks",
        }

        # Alert ID input
        audit_alert_id = st.text_input(
            "Alert ID:",
            value=st.session_state.current_alert_id,
            help="Enter alert ID to load the audit trail"
        )

        col_fetch, col_auto = st.columns([2, 1])
        fetch_clicked = col_fetch.button("Fetch Audit Trail", type="primary", use_container_width=True)
        auto_load = col_auto.checkbox("Auto-load", value=True)

        # Two-panel layout
        col_trail, col_history = st.columns(2)

        # LEFT PANEL - 7-Step Logic Audit Trail
        with col_trail:
            st.subheader("7-Step Logic Audit Trail")

            if fetch_clicked or auto_load:
                result, err = api_call("GET", f"/api/v1/logic-audit-trail/{audit_alert_id}")
                if result:
                    trail = result.get("audit_trail", {})
                    steps = trail.get("steps", {})
                    overall = trail.get("overall_status", "UNKNOWN")
                    color = {"COMPLETED": "green", "IN_PROGRESS": "yellow", "FAILED": "red"}.get(overall, "gray")
                    st.success(f"**{overall}** - {len(steps)} steps logged for `{audit_alert_id}`")

                    if steps:
                        st.markdown("#### Pipeline Steps")
                        for step_name, step_data in steps.items():
                            icon = STEP_ICONS.get(step_name, "?")
                            status = step_data.get("status", "?")
                            badge = "[OK]" if status == "COMPLETED" else ("[X]" if status == "FAILED" else "[?]")
                            ts = step_data.get("timestamp", "")[:19].replace("T", " ")

                            with st.expander(
                                f"Step {icon}: **{step_name}** {badge} - {ts}",
                                expanded=(step_name == "LLM_GENERATION")
                            ):
                                details = step_data.get("details", {})
                                if details:
                                    for raw_k, val in details.items():
                                        if raw_k in ("edit_summary",):
                                            continue
                                        label = DETAIL_LABELS.get(raw_k, raw_k.replace("_", " ").title())
                                        if raw_k == "total_amount" and isinstance(val, (int, float)):
                                            val = f"Rs {val:,.0f}"
                                        if isinstance(val, list):
                                            val = ", ".join(str(x) for x in val) if val else "None"
                                        if isinstance(val, dict):
                                            val = json.dumps(val)
                                        st.markdown(f"- **{label}:** `{val}`")

                                # ANALYST_ACTIONS: edit summary
                                if step_name == "ANALYST_ACTIONS":
                                    es = details.get("edit_summary", {})
                                    if es and es.get("total_changes", 0) > 0:
                                        st.markdown("**Edit Summary:**")
                                        st.markdown(f"- **Lines Added:** `{es.get('lines_added', 0)}`")
                                        st.markdown(f"- **Lines Removed:** `{es.get('lines_removed', 0)}`")
                                    else:
                                        cmt = details.get("analyst_comments", "")
                                        if cmt:
                                            st.info(f"{cmt}")
                                        else:
                                            st.info("No analyst edits yet - approve/reject in Tab 2 to populate.")

                    with st.expander("Full Trail JSON"):
                        st.json(trail)

                else:
                    if err and "404" in str(err):
                        st.info(f"No audit trail yet for `{audit_alert_id}`. Generate a SAR first.")
                    else:
                        st.error(f"{err}")

        # RIGHT PANEL - SAR History + Learning Analytics
        with col_history:
            st.subheader("SAR History")
            disk_sars = load_all_sars_from_disk()
            if disk_sars:
                rows = []
                for s in disk_sars:
                    meta = s.get("metadata", {})
                    approval = s.get("approvalstatus", "PENDING")
                    rows.append({
                        "SAR ID": sget(s, "sarid", "sar_id")[-15:],
                        "Alert": sget(s, "alertid", "alert_id"),
                        "Generated by": s.get("analystid", "?"),
                        "Validation": sget(s, "validationstatus", "validation_status"),
                        "Approval": approval or "PENDING",
                        "Time(s)": f"{float(s.get('generationtimeseconds', 0)):.1f}",
                        "Pattern": meta.get("pattern_type", "?"),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("No SAR files on disk yet.")

            st.divider()
            st.subheader("Learning Analytics")
            if st.button("Fetch Learning Stats", use_container_width=True):
                result, err = api_call("GET", "/api/v1/learning/metrics")
                if result:
                    metrics = result.get("metrics", {})
                    c1, c2 = st.columns(2)
                    c1.metric("Total SARs", metrics.get("total_sars", 0))
                    c2.metric("Patterns Learned", metrics.get("patterns_learned", 0))

                    if metrics.get("pattern_distribution"):
                        st.bar_chart(metrics["pattern_distribution"])
                else:
                    st.error(f"{err}")

            if st.button("View Learned Patterns", use_container_width=True):
                result, err = api_call("GET", "/api/v1/learning/patterns")
                if result:
                    patterns = result.get("patterns", [])
                    if patterns:
                        for p in patterns[:5]:
                            with st.expander(f"{p['name']} (confidence: {p['confidence']:.2f})"):
                                st.markdown(f"**Type:** {p['type']}")
                                st.markdown(f"**Frequency:** {p['frequency']}")
                                st.code(p['rule'])
                    else:
                        st.info("No patterns learned yet.")
                else:
                    st.error(f"{err}")


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown(
    """<div style='text-align:center;color:#888;font-size:0.8em;'>
    SAR Generator v3.0 | Layer 2 FastAPI | RAG + LLM | 7-Step Audit Trail | PMLA / FIU-IND
    </div>""",
    unsafe_allow_html=True
)
