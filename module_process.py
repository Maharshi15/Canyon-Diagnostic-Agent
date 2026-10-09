"""Process Diagnostic screen."""
import io
import textwrap
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import process_engine as PE
from ai_summary import provider_config

SAMPLES = Path(__file__).parent / "samples"
TYPE_COLORS = {"Task": "#E8EEEC", "Data entry": "#F8E1DE", "Check": "#E0E9F3", "Approval": "#F6EAD3", "Handoff": "#EFE7F6"}


def _read_any(up):
    if up.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(up, dtype=str).fillna("")
    return pd.read_csv(up, dtype=str, keep_default_na=False)


def _load(df, source):
    """Put a step table into the editor. A new key forces the editor to show the new table."""
    st.session_state.proc_steps = PE.standard_table(df)
    st.session_state.proc_source = source
    st.session_state.proc_ver = st.session_state.get("proc_ver", 0) + 1
    st.session_state.pop("proc_diag", None)


def _dot(steps, per_row=4):
    """Process map: steps flow left to right and wrap into rows of four, coloured by type."""
    def q(s, width=24):
        return "\\n".join(textwrap.wrap(str(s).replace("\\", " ").replace('"', "'"), width)) or " "
    lines = ['digraph G { rankdir=TB; nodesep=0.3; ranksep=0.45; newrank=true;',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#9DB3AF", width=2.4];',
             'edge [color="#6B807C"];']
    for s in steps:
        sub = " · ".join(x for x in (s["owner"], s["system"]) if x)
        wait = f"\\nwaits {s['wait_h']:g} h" if s["wait_h"] else ""
        lines.append(f'n{s["n"]} [label="{s["n"]}. {q(s["step"])}\\n{q(sub, 30)}{wait}", fillcolor="{TYPE_COLORS[s["type"]]}"];')
    for i in range(0, len(steps), per_row):
        row = steps[i:i + per_row]
        lines.append("{rank=same; " + " ".join(f"n{s['n']}" for s in row) + "}")
        if i:
            lines.append(f"n{steps[i - per_row]['n']} -> n{row[0]['n']} [style=invis];")  # keeps rows left aligned
    for a, b in zip(steps, steps[1:]):
        same_row = (a["n"] - 1) // per_row == (b["n"] - 1) // per_row
        lines.append(f"n{a['n']} -> n{b['n']}" + ("" if same_row else " [constraint=false]") + ";")
    return "\n".join(lines) + "}"


def render(client, secret):
    st.subheader("Process Diagnostic")
    st.write("Map one process as a table of steps: who does it, in which system, how long it takes and how long it waits. "
             "The agent finds data typed twice, approval chains, waiting time and work on spreadsheets or chat, "
             "and ranks what to automate first.")
    pending = st.session_state.pop("proc_pending", None)
    if pending:
        st.session_state.update(pending)

    c1, c2, c3 = st.columns([2, 1, 2])
    process_name = c1.text_input("Process name", placeholder="For example: Retailer scheme claim settlement",
                                 key="proc_name")
    cases = c2.number_input("Cases per month", min_value=0, step=50, key="proc_cases",
                            help="How many times the process runs in a month. Used for manual hours per month.")
    time_source = c3.selectbox("Where do the times come from?", PE.TIME_SOURCES, key="proc_time_source")

    t_upload, t_sop, t_sample = st.tabs(["Upload a step table", "Draft from an SOP with AI", "Illustrative sample"])
    with t_upload:
        st.caption("Columns: Step, Owner, System, Type (Task, Data entry, Check, Approval, Handoff), Work minutes, "
                   "Wait hours, Share of cases % (optional, for steps that only some cases go through). "
                   "Missing columns can be filled in the table below.")
        up = st.file_uploader("Step table", type=["csv", "xlsx"], key="proc_upload")
        u1, u2 = st.columns(2)
        if u1.button("Load this file", disabled=up is None, width="stretch"):
            try:
                _load(_read_any(up), up.name)
            except Exception as e:
                st.error(f"Could not read the file. Save it as .csv or .xlsx. Details: {e}")
        if u2.button("Start an empty table", width="stretch"):
            _load(PE.template(), "Typed in by Canyon")
    with t_sop:
        st.caption("Upload or paste the SOP (Standard Operating Procedure). The AI drafts the step table, then you check it "
                   "and add times. It never invents times: steps without a time in the document show 0.")
        doc = st.file_uploader("SOP document", type=["txt", "md", "docx", "pdf"], key="proc_doc")
        pasted = st.text_area("Or paste the process description", height=120, key="proc_paste")
        if st.button("Draft step table", type="primary"):
            text = pasted.strip()
            if doc is not None:
                try:
                    text = PE.read_document(doc.name, doc.getvalue()) + "\n" + text
                except Exception as e:
                    st.error(f"Could not read the document. Try copying the text in instead. Details: {e}")
                    text = ""
            cfg = provider_config(secret)
            if not text.strip():
                st.error("Add a document or paste the process description first.")
            elif not cfg:
                st.error("The AI settings are missing. Add the Azure OpenAI settings in the app Secrets, "
                         "or upload a step table instead.")
            else:
                with st.spinner("Reading the document..."):
                    try:
                        df, assumptions = PE.draft_steps(cfg, text, process_name)
                    except Exception as e:
                        st.error(f"The AI draft did not complete. Details: {e}")
                        df, assumptions = None, []
                if df is not None and len(df):
                    _load(df, "Drafted by AI from the SOP, checked by Canyon")
                    st.session_state.proc_assumptions = assumptions
                elif df is not None:
                    st.error("No steps were found in the document.")
        for a in st.session_state.get("proc_assumptions", []):
            st.caption("To confirm with the client: " + a)
    with t_sample:
        st.caption("A fictional retailer scheme claim settlement process at a manufacturer. Not client data.")
        if st.button("Use illustrative sample", width="stretch"):
            _load(pd.read_csv(SAMPLES / "process_claim_settlement.csv", dtype=str), "Illustrative sample, not client data")
            st.session_state.proc_pending = {"proc_name": "Retailer scheme claim settlement (fictional)",
                                             "proc_cases": 1200, "proc_time_source": PE.TIME_SOURCES[0]}
            st.rerun()

    if "proc_steps" not in st.session_state:
        st.info("Upload a step table, draft one from an SOP, or try the illustrative sample.")
        return

    st.markdown("#### Step table")
    st.caption("Check every row with the process owner. Edit cells, add rows at the bottom, or delete rows.")
    edited = st.data_editor(
        st.session_state.proc_steps, num_rows="dynamic", hide_index=True, width="stretch",
        key=f"proc_editor_{st.session_state.get('proc_ver', 0)}",
        column_config={"Type": st.column_config.SelectboxColumn("Type", options=PE.TYPES)})

    if st.button("Run process diagnostic", type="primary"):
        res = PE.analyse(edited, cases, time_source)
        if "error" in res:
            st.error(res["error"])
            return
        st.session_state.proc_diag = {"source": st.session_state.get("proc_source", ""), "result": res,
                                      "process_name": process_name, "time_source": time_source}

    data = st.session_state.get("proc_diag")
    if data:
        _show(data, client)


def _show(data, client):
    res = data["result"]
    m, c = res["metrics"], PE.counts(res)
    st.divider()
    st.caption("Source: " + data["source"])
    k = st.columns(4)
    k[0].metric("Steps", m["steps"])
    k[0].caption(f"{m['owners']} owners · {m['handoffs']} handoffs · {m['approvals']} approvals")
    k[1].metric("Findings", sum(c.values()))
    k[1].caption(f"{c['High']} High · {c['Medium']} Medium · {c['Low']} Low")
    if m["timed"]:
        k[2].metric("Cycle time per case", f"{m['cycle_days']:g} days")
        k[2].caption(f"{m['flow_eff']}% of it is active work")
    else:
        k[2].metric("Cycle time per case", "No times given")
    if m["cases"]:
        k[3].metric("Manual hours a month", f"{m['manual_h_month']:,.0f}")
        k[3].caption(f"For {m['cases']:,} cases a month")
    else:
        k[3].metric("Manual hours a month", "Add cases")

    tabs = st.tabs(["Findings", "Process map", "Automation opportunities", "Experiments"])
    with tabs[0]:
        if not res["findings"]:
            st.success("No issues found in this step table.")
        for f in res["findings"]:
            with st.expander(f"{f['title']}", expanded=f["severity"] == "High"):
                lvl = "Level 2 Measured" if f["evidence_level"].startswith("2") else "Level 1 Observed"
                st.markdown(f'<span class="sev {f["severity"]}">{f["severity"].upper()}</span> &nbsp; '
                            f'{f["category"]} · Effort {f["effort"]} · {lvl}', unsafe_allow_html=True)
                st.write("**What we see:** " + f["evidence"])
                st.write("**Recommendation:** " + f["recommendation"])
    with tabs[1]:
        st.graphviz_chart(_dot(res["steps"]), width="stretch")
        st.caption("Colour shows the step type: red data entry, amber approval, blue check, purple handoff, grey task.")
    with tabs[2]:
        st.caption("Ranked by impact (manual hours per month and waiting time), then effort. "
                   "Quick wins are low effort changes doable in under 30 days.")
        st.dataframe(pd.DataFrame(res["opportunities"]), hide_index=True, width="stretch")
    with tabs[3]:
        for i, e in enumerate(res["experiments"], 1):
            st.markdown(f"**Pilot {i}:** {e['hypothesis']}")
            st.write(f"Design: {e['variant']}")
            st.write(f"Primary metric: {e['primary_metric']} · Guardrail: {e['guardrail_metric']}")

    buf = io.BytesIO()
    PE.to_excel(res, buf, client, data.get("process_name", ""))
    st.download_button("Download Excel report", buf.getvalue(),
                       file_name=f"Canyon_Process_Diagnostic_{(client or 'Client').replace(' ', '_')}_{date.today():%Y%m%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
