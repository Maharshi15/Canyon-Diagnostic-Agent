"""Diagnostic Report screen: one Word report from every module run in this session."""
from datetime import date

import pandas as pd
import streamlit as st

import report_engine as RE

SOURCES = [("md_diag", "Master Data Diagnostic"), ("app_diag", "Application Diagnostic"), ("proc_diag", "Process Diagnostic")]


def render(client):
    st.subheader("Diagnostic Report")
    st.write("Builds one client ready Word report from the modules you ran in this session: executive summary, "
             "scope, scorecard, findings with evidence levels, quick wins, experiments, roadmap and next step.")

    ready = {k: st.session_state.get(k) for k, _ in SOURCES}
    cols = st.columns(3)
    include = {}
    for (key, name), col in zip(SOURCES, cols):
        if ready[key]:
            include[key] = col.checkbox(name, value=True, key=f"rep_{key}")
            col.caption("Source: " + ready[key].get("source", ""))
        else:
            col.checkbox(name, value=False, disabled=True, key=f"rep_{key}")
            col.caption("Not run yet in this session")
    if not any(ready.values()):
        st.info("Run at least one module first (the illustrative samples work too), then come back here.")
        return
    chosen = {k: ready[k] for k, on in include.items() if on}
    if not chosen:
        st.warning("Tick at least one module to include.")
        return

    c1, c2 = st.columns(2)
    prepared_by = c1.text_input("Prepared by", value="Maharshi Upadhyay, Business Development Head, Canyon Data Labs")
    contact = c2.text_input("Contact", value="maharshi@canyondatalabs.com")
    kind = st.radio("Report type", ["Full report", "One page summary for a prospect"], horizontal=True)
    notes = st.text_area("Note to add under the executive summary (optional)", height=70,
                         placeholder="For example: Reviewed with the IT (Information Technology) head on 12 October.")

    data = RE.collect(md=chosen.get("md_diag"), app=chosen.get("app_diag"), proc=chosen.get("proc_diag"))
    if data["illustrative"]:
        st.warning("This report includes illustrative sample data. It is labelled as such and is for demos only, "
                   "not to be sent as a client's real diagnostic.")
    if not (client or "").strip():
        st.caption("Tip: add the client name in the left panel so it appears on the report.")

    st.markdown("#### Preview")
    st.markdown("**Executive summary**")
    for line in RE.exec_summary(data, client):
        st.markdown(f"* {line}")
    st.markdown("**Scorecard**")
    st.dataframe(pd.DataFrame([{"Module": m["name"], "Headline": m["headline"], "Detail": m["detail"]}
                               for m in data["modules"]]), hide_index=True, width="stretch")
    st.markdown(f"**Findings** ({len(data['findings'])})")
    st.dataframe(pd.DataFrame([{"ID": f["id"], "Severity": f["severity"], "Level": f["level"], "Finding": f["finding"],
                                "Recommendation": f["rec"], "Effort": f["effort"]} for f in data["findings"]]),
                 hide_index=True, width="stretch")

    teaser = kind != "Full report"
    doc = RE.build_docx(data, client, prepared_by, contact, notes, teaser=teaser)
    stem = "Canyon_Diagnostic_Summary" if teaser else "Canyon_Diagnostic_Report"
    st.download_button("Download Word report", doc, type="primary",
                       file_name=f"{stem}_{(client or 'Client').replace(' ', '_')}_{date.today():%Y%m%d}.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    st.caption("Open it in Word to review, then use File, Save As, PDF to send a PDF. "
               "Read every finding before sending: the report is a draft for Canyon to check, not a final verdict.")
