"""Application Diagnostic screen."""
import hashlib
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import app_engine as AE
from ai_summary import provider_config

SAMPLES = Path(__file__).parent / "samples"
APP_TYPES = ["Field sales or dealer app", "CRM (Customer Relationship Management)", "Loyalty app",
             "SCM (Supply Chain Management)", "ERP (Enterprise Resource Planning) screens", "Customer facing app", "Other"]


def _read_any(up):
    name = up.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(up, dtype=str)
    return pd.read_csv(up, dtype=str, keep_default_na=False)


def render(client, secret):
    st.subheader("Application Diagnostic")
    st.write("Upload screenshots of one user journey, in order. The agent reviews screens, fields and steps, "
             "suggests a simpler journey, and proposes A/B experiments to validate it. "
             "Add analytics exports to turn observations into measured evidence.")

    with st.expander("Before you upload: privacy", expanded=False):
        st.write("Screenshots are sent to the AI (Artificial Intelligence) service for review. Hide or blur customer names, "
                 "phone numbers, account numbers and other personal data first. Use real client screenshots only with "
                 "the client's written permission.")

    c1, c2 = st.columns(2)
    with c1:
        app_name = st.text_input("Application name", placeholder="For example: Dealer Partner App")
        app_type = st.selectbox("Application type", APP_TYPES)
    with c2:
        journey = st.text_input("Journey shown", placeholder="For example: Register a new retailer")
        users = st.text_input("Main users", placeholder="For example: Field sales officers on mobile")
    extra = st.text_area("Anything Canyon already knows (optional)", height=70,
                         placeholder="For example: Sales head says onboarding takes too long; approval team rejects many forms.")

    shots = st.file_uploader("Screenshots in journey order (name them 01, 02, 03 ... to keep the order). Up to 12.",
                             type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    a1, a2 = st.columns(2)
    with a1:
        funnel_up = st.file_uploader("Optional: funnel export. Columns: step, users. First row = users who started; then one row per screen = users who completed it",
                                     type=["csv", "xlsx"], key="funnel")
    with a2:
        usage_up = st.file_uploader("Optional: page usage export (page, views)", type=["csv", "xlsx"], key="usage")

    b1, b2 = st.columns([1, 1])
    run = b1.button("Run application diagnostic", type="primary", width="stretch")
    sample = b2.button("Use illustrative sample", width="stretch")

    if sample:
        files = [(p.name, p.read_bytes()) for p in sorted((SAMPLES / "app_screens").glob("*.png"))]
        st.session_state.app_diag = {
            "source": "Illustrative sample: a fictional field sales app, not client data",
            "files": files,
            "result": AE.normalize(json.loads((SAMPLES / "app_sample_result.json").read_text()), len(files)),
            "funnel": pd.read_csv(SAMPLES / "funnel_retailer_onboarding.csv", dtype=str),
            "usage": pd.read_csv(SAMPLES / "page_usage_90_days.csv", dtype=str),
            "app_name": "Demo Partner App (fictional)",
        }

    if run:
        if not shots:
            st.error("Add at least one screenshot, then run again.")
        else:
            cfg = provider_config(secret)
            if not cfg:
                st.error("The AI settings are missing. Add the Azure OpenAI settings in the app Secrets, "
                         "or try the illustrative sample.")
            else:
                files = sorted([(f.name, f.getvalue()) for f in shots], key=lambda x: x[0].lower())[:AE.MAX_SCREENS]
                key = hashlib.sha256(b"".join(d for _, d in files) + (app_name + journey + extra).encode()).hexdigest()
                cache = st.session_state.setdefault("app_cache", {})
                if key not in cache:
                    with st.spinner(f"Reviewing {len(files)} screens. This can take up to a minute..."):
                        try:
                            cache[key] = AE.analyse_screens(cfg, files, app_name, app_type, journey, users, extra)
                        except Exception as e:
                            st.error("The AI review did not complete. Check that your Azure deployment accepts images "
                                     f"(for example a GPT 4o, GPT 4.1 or GPT 5 deployment). Details: {e}")
                            return
                try:
                    funnel_df = _read_any(funnel_up) if funnel_up else None
                    usage_df = _read_any(usage_up) if usage_up else None
                except Exception as e:
                    st.error(f"Could not read the analytics file. Save it as .csv or .xlsx. Details: {e}")
                    return
                st.session_state.app_diag = {"source": f"{len(files)} uploaded screenshots", "files": files,
                                             "result": cache[key], "funnel": funnel_df, "usage": usage_df,
                                             "app_name": app_name}

    data = st.session_state.get("app_diag")
    if not data:
        st.info("Upload screenshots and run the diagnostic, or try the illustrative sample.")
        return
    _show(data, client)


def _show(data, client):
    files = data["files"]
    funnel = AE.funnel_analysis(data["funnel"])
    usage = AE.page_usage_analysis(data["usage"])
    result = AE.attach_measured(json.loads(json.dumps(data["result"])), funnel)
    c = AE.counts(result)
    j = result["journey"]

    st.divider()
    st.caption("Source: " + data["source"])
    k = st.columns(4)
    k[0].metric("Screens reviewed", len(files))
    k[1].metric("Findings", sum(c.values()))
    k[1].caption(f"{c['High']} High · {c['Medium']} Medium · {c['Low']} Low")
    k[2].metric("Journey steps", f"{j.get('current_steps')} → {j.get('proposed_steps')}")
    if funnel:
        k[3].metric("Measured completion", f"{funnel['completion']}%")
    else:
        k[3].metric("Evidence level", "1 Observed")
    if result.get("app_summary"):
        st.write(result["app_summary"])

    tabs = st.tabs(["Findings", "Screens", "Proposed journey", "Experiments", "Measured evidence"])
    with tabs[0]:
        for f in result["findings"]:
            badge = "Level 2 Measured" if f["evidence_level"].startswith("2") else "Level 1 Observed"
            with st.expander(f"Screen {f['screen']} · {f['title']}", expanded=f["severity"] == "High"):
                st.markdown(f'<span class="sev {f["severity"]}">{f["severity"].upper()}</span> &nbsp; '
                            f'{f["category"]} · Effort {f["effort"]} · {badge}', unsafe_allow_html=True)
                cols = st.columns([1, 3])
                if 0 < f["screen"] <= len(files):
                    cols[0].image(files[f["screen"] - 1][1], width=170)
                cols[1].write("**What we see:** " + f["evidence"])
                if f["measured"]:
                    cols[1].write("**Measured:** " + f["measured"])
                cols[1].write("**Recommendation:** " + f["recommendation"])
    with tabs[1]:
        info = {s.get("index"): s for s in result["screens"]}
        for i, (name, img) in enumerate(files, 1):
            s = info.get(i, {})
            cols = st.columns([1, 3])
            cols[0].image(img, width=200)
            cols[1].markdown(f"**Screen {i}: {s.get('name') or name}**")
            if s:
                cols[1].write(f"{s.get('purpose', '')}")
                cols[1].write(f"Fields: {s.get('fields', 0)} · Required: {s.get('required_fields', 0)} · "
                              f"Uploads: {s.get('uploads', 0)}")
                if s.get("notes"):
                    cols[1].caption(s["notes"])
            n = sum(1 for f in result["findings"] if f["screen"] == i)
            cols[1].write(f"Findings on this screen: {n}")
            st.write("")
    with tabs[2]:
        st.markdown(f"**From {j.get('current_steps')} steps to {j.get('proposed_steps')} steps**")
        for p in j.get("proposed_flow", []):
            st.markdown(f"**Step {p.get('step')}: {p.get('name')}**  \n{p.get('what_happens')}")
        if j.get("changes"):
            st.markdown("**What changes**")
            for ch in j["changes"]:
                st.markdown(f"* {ch}")
        st.caption("This is a suggestion from screenshots. Validate it with a prototype or an A/B experiment before rollout.")
    with tabs[3]:
        for i, e in enumerate(result["experiments"], 1):
            st.markdown(f"**Experiment {i}:** {e.get('hypothesis', '')}")
            st.write(f"Variant: {e.get('variant', '')}")
            st.write(f"Primary metric: {e.get('primary_metric', '')} · Guardrail: {e.get('guardrail_metric', '')}")
            st.caption(f"Can run on: {e.get('platforms', '')}")
        if result["needs_more_evidence"]:
            st.markdown("**Evidence that would confirm these findings**")
            for x in result["needs_more_evidence"]:
                st.markdown(f"* {x}")
    with tabs[4]:
        if not funnel and not usage:
            st.info("Add a funnel export or a page usage export to measure drop off and find pages nobody uses. "
                    "These usually come from Google Analytics 4, Mixpanel, Amplitude, Firebase or the app's own logs.")
        if funnel:
            st.markdown(f"**Funnel:** {funnel['end']} of {funnel['start']} users completed "
                        f"({funnel['completion']}%). Largest drop off: **{funnel['worst']['Step']}** "
                        f"({funnel['worst']['Drop off %']}%).")
            fdf = pd.DataFrame(funnel["rows"])
            chart = fdf.assign(Step=[f"{r['Screen']:02d}. {r['Step']}" for r in funnel["rows"]])
            st.bar_chart(chart, x="Step", y="Drop off %", color="#0B6E69")
            st.dataframe(fdf, hide_index=True, width="stretch")
        if usage:
            st.markdown(f"**Page usage:** {len(usage['low'])} pages have under {usage['threshold']}% of all views.")
            st.dataframe(pd.DataFrame(usage["rows"]), hide_index=True, width="stretch")

    buf = io.BytesIO()
    AE.to_excel(result, funnel, usage, buf, client, data.get("app_name", ""))
    st.download_button("Download Excel report", buf.getvalue(),
                       file_name=f"Canyon_Application_Diagnostic_{(client or 'Client').replace(' ', '_')}_{date.today():%Y%m%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
