"""Canyon Diagnostic Agent: web app (version 0.1, Master Data module).

Run locally:  streamlit run app.py
"""
import io
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from diag_engine import read_table, scan, to_excel

APP_DIR = Path(__file__).parent
SAMPLE = APP_DIR / "sample_material_master.csv"

st.set_page_config(page_title="Canyon Diagnostic Agent", page_icon="🩺", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:2rem;max-width:1200px}
.sev{font-family:monospace;font-size:.75rem;font-weight:700;padding:2px 8px;border-radius:4px}
.High{background:#F8E1DE;color:#B3372B}.Medium{background:#F6EAD3;color:#9A6412}.Low{background:#E0E9F3;color:#3F6488}
.note{background:rgba(11,110,105,.10);padding:12px 16px;border-radius:8px}
</style>""", unsafe_allow_html=True)


def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


# Simple password gate. Set APP_PASSWORD in the hosting secrets to switch it on.
password = secret("APP_PASSWORD")
if password and not st.session_state.get("authed"):
    st.title("Canyon Diagnostic Agent")
    entered = st.text_input("Access password", type="password")
    if st.button("Sign in"):
        if entered == password:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("That password is not correct. Ask Canyon Data Labs for access.")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### CANYON DIAGNOSTIC AGENT")
    st.caption("Discover · Diagnose · Recommend · Transform")
    client = st.text_input("Client name", placeholder="For example: ABC Manufacturing")
    module = st.radio("Module", ["Master Data Diagnostic", "Application Diagnostic (coming next)",
                                 "Process Diagnostic (planned)"], index=0)
    st.divider()
    st.caption("Version 0.1 · Canyon Data Labs, Ahmedabad")

st.title("Before you transform your business systems, diagnose them.")

if module != "Master Data Diagnostic":
    st.info("This module is on the roadmap. Version 0.1 runs the Master Data Diagnostic.")
    st.stop()

st.subheader("Master Data Diagnostic")
st.write("Upload a material, customer or distributor master as Excel or CSV (Comma Separated Values). "
         "Columns are detected automatically: code, description, unit of measure, group, plant.")

c1, c2 = st.columns([3, 1])
with c1:
    up = st.file_uploader("Master data file", type=["csv", "tsv", "xlsx", "xls"])
with c2:
    st.write("")
    use_sample = st.button("Use illustrative sample", width='stretch')
if use_sample:
    st.session_state.source = "sample"
if up is not None:
    st.session_state.source = "upload"

source = st.session_state.get("source")
if not source:
    st.markdown('<div class="note">Upload a file or try the illustrative sample to see a full diagnostic.</div>',
                unsafe_allow_html=True)
    st.stop()

try:
    if source == "upload" and up is not None:
        df = read_table(up, up.name)
        src_label = up.name
    else:
        df = read_table(SAMPLE)
        src_label = "Illustrative sample, not client data"
except Exception as e:
    st.error(f"Could not read the file. Save it as .xlsx or .csv and try again. Details: {e}")
    st.stop()

res = scan(df)
if "error" in res:
    st.error(res["error"])
    st.stop()

st.caption(f"Source: {src_label}")

# Headline numbers
k = st.columns(4)
k[0].metric("Records reviewed", res["total"])
k[1].metric("Data quality score", f"{res['overall']} / 100")
k[2].metric("Duplicate clusters to validate", len(res["dup_groups"]))
k[3].metric("Records with an issue", res["total"] - res["clean"])

left, right = st.columns([1, 2.2])
with left:
    st.markdown("#### Quality by dimension")
    for d in res["dim_scores"]:
        st.write(f"{d['dim']}: **{d['score']}**")
        st.progress(d["score"] / 100)
    st.caption("Uniqueness counts records that would be retired if each duplicate cluster is confirmed.")

    # Downloads
    st.markdown("#### Download")
    buf = io.BytesIO()
    to_excel(res, buf, client)
    fname = f"Canyon_Master_Data_Diagnostic_{(client or 'Client').replace(' ', '_')}_{date.today():%Y%m%d}.xlsx"
    st.download_button("Excel report (4 sheets)", buf.getvalue(), file_name=fname,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       width='stretch')

with right:
    t1, t2, t3, t4 = st.tabs(["Findings", "Duplicate clusters", "All records", "Executive summary"])
    with t1:
        for f in res["findings"]:
            with st.expander(f"{f['label']}  ·  {f['count']} records", expanded=f["severity"] == "High"):
                st.markdown(f'<span class="sev {f["severity"]}">{f["severity"].upper()}</span> &nbsp; '
                            f'Dimension: {f["dim"]} · Evidence level 2, measured from the data extract',
                            unsafe_allow_html=True)
                st.write("**Recommendation:** " + f["rec"])
                st.dataframe(pd.DataFrame([{"Code": r["code"], "Description": r["desc"], "Unit": r["uom"],
                                            "Group": r["group"]} for r in f["rows"][:10]]),
                             hide_index=True, width='stretch')
                if f["count"] > 10:
                    st.caption(f"Showing 10 of {f['count']}. The Excel report lists all.")
    with t2:
        if not res["dup_groups"]:
            st.success("No potential duplicates found.")
        for g in res["dup_groups"]:
            flags = (" · unit conflict" if g["uom_conflict"] else "") + (" · group conflict" if g["group_conflict"] else "")
            st.markdown(f"**{g['id']}** · {len(g['records'])} records · suggested: `{g['std']}`{flags}")
            st.dataframe(pd.DataFrame([{"Code": r["code"], "Description": r["desc"], "Unit": r["uom"],
                                        "Group": r["group"], "Plant": r["plant"]} for r in g["records"]]),
                         hide_index=True, width='stretch')
    with t3:
        only = st.checkbox("Show only records with issues", value=True)
        rows = [r for r in res["recs"] if (r["issues"] or not only)]
        st.dataframe(pd.DataFrame([{"Row": r["line"], "Code": r["code"], "Description": r["desc"],
                                    "Suggested standard": r["std"],
                                    "Issues": "; ".join(dict.fromkeys(x[1] for x in r["issues"])) or "Clean"}
                                   for r in rows]), hide_index=True, width='stretch')
    with t4:
        from ai_summary import provider_config, write_summary
        cfg = provider_config(secret)
        if not cfg:
            st.info("The AI (Artificial Intelligence) summary switches on once the Azure OpenAI settings "
                    "(AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT) are added to the app "
                    "secrets. Everything else works without them.")
        else:
            st.caption("AI provider: " + ("Azure OpenAI" if cfg["provider"] == "azure" else "Anthropic Claude"))
            if st.button("Write executive summary"):
                with st.spinner("Writing summary..."):
                    try:
                        st.session_state.summary = write_summary(res, client, cfg)
                    except Exception as e:
                        st.error("The AI service did not respond. Check the endpoint, key and deployment name "
                                 f"in the secrets. Details: {e}")
        if st.session_state.get("summary"):
            st.markdown(st.session_state.summary)

st.divider()
st.caption("The agent flags potential issues. Business owners approve every correction before master data is changed. "
           "Canyon works with the systems a business already runs on, no need to replace anything.")
