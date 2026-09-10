from pathlib import Path
import html
import json
import shutil
import streamlit as st

from engine.video import VideoAnalyzer
from engine.assistant import SupervisorAssistant
from engine.config import SCENARIOS, ENGINE, risk_color

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
EVIDENCE = OUT / "evidence"
OUT.mkdir(exist_ok=True)
EVIDENCE.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Godrej Warehouse AI",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide the Streamlit deployment/menu chrome so the product looks like a finished
# local application rather than a development page.
st.markdown(
    """
<style>
#MainMenu {visibility:hidden;}
header {visibility:hidden;}
footer {visibility:hidden;}
div[data-testid="stToolbar"] {display:none;}
div[data-testid="stDecoration"] {display:none;}
.stApp {
    background: #061014;
    color: #edf7f5;
}
.block-container {max-width: 1500px; padding: 1.2rem 2rem 3rem;}
h1,h2,h3,h4 {color:#edf7f5 !important;}
.topbar {display:flex;justify-content:space-between;align-items:center;
         border-bottom:1px solid #20353d;padding:4px 0 18px;margin-bottom:24px;}
.brand {display:flex;align-items:center;gap:12px;}
.brand-mark {width:40px;height:40px;border:1px solid #42d6a8;display:flex;
             align-items:center;justify-content:center;color:#42d6a8;font-weight:800;font-size:20px;}
.brand-name {font-weight:800;letter-spacing:.08em;font-size:.88rem;}
.brand-sub {color:#8ea6ad;font-size:.72rem;margin-top:2px;}
.status {border:1px solid #2b5149;border-radius:999px;padding:7px 12px;color:#42d6a8;
         font-size:.68rem;letter-spacing:.04em;}
.hero {padding:22px 0 30px;}
.eyebrow {color:#42d6a8;font-size:.68rem;letter-spacing:.15em;font-weight:700;}
.hero h1 {font-size:3rem;line-height:1.03;margin:.55rem 0 .8rem;letter-spacing:-.04em;}
.hero h1 span {color:#42d6a8;}
.hero p {max-width:900px;color:#8ea6ad;font-size:.96rem;line-height:1.7;}
.meta-row {display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;}
.meta {border:1px solid #20353d;background:#0b171c;padding:7px 10px;border-radius:999px;
       color:#b8c8cc;font-size:.68rem;}
.panel {background:#0b171c;border:1px solid #20353d;border-radius:15px;padding:16px;}
.kicker {color:#42d6a8;font-size:.62rem;letter-spacing:.14em;font-weight:700;}
.muted {color:#8ea6ad;font-size:.72rem;line-height:1.55;}
.metric {min-height:105px;}
.metric-label {color:#8ea6ad;font-size:.59rem;letter-spacing:.10em;}
.metric-value {font-size:1.8rem;font-weight:800;margin-top:6px;}
.metric-sub {color:#71878e;font-size:.65rem;margin-top:4px;}
.finding {border:1px solid #29474c;background:#09161a;border-radius:12px;padding:13px;margin:8px 0;}
.pill {display:inline-block;border:1px solid currentColor;border-radius:999px;padding:4px 8px;
       font-size:.61rem;font-weight:800;margin-right:7px;}
.timeline {border-left:2px solid #29474c;padding-left:14px;margin:10px 0;}
.timeline-item {background:#09161a;border:1px solid #20353d;border-radius:11px;padding:11px;margin:9px 0;}
.note {color:#8ea6ad;font-size:.68rem;line-height:1.55;}
.stButton>button {border-radius:9px !important;border:1px solid #29474c !important;
                  background:#0c1c21 !important;color:#e7f4f1 !important;font-weight:700 !important;}
.stButton>button:hover {border-color:#42d6a8 !important;color:#42d6a8 !important;}
.stButton>button[kind="primary"] {background:#42d6a8 !important;color:#03100c !important;border-color:#42d6a8 !important;}
.stProgress>div>div {background:#42d6a8 !important;}
div[data-testid="stFileUploader"] {border:1px dashed #31545a;border-radius:12px;padding:3px;background:#081418;}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value):
    return html.escape(str(value))


def clear_analysis():
    for key in [
        "incidents", "meta", "copilot_answer", "copilot_question",
        "video_bytes", "video_name", "video_path",
    ]:
        st.session_state.pop(key, None)

    if OUT.exists():
        for child in OUT.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
    OUT.mkdir(exist_ok=True)
    EVIDENCE.mkdir(exist_ok=True)
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1


if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0


st.markdown(
    """
<div class="topbar">
  <div class="brand">
    <div class="brand-mark">G</div>
    <div>
      <div class="brand-name">GODREJ WAREHOUSE AI</div>
      <div class="brand-sub">Video Intelligence for Damage Prevention</div>
    </div>
  </div>
  <div class="status">● LOCAL AI · EVIDENCE FIRST</div>
</div>

<div class="hero">
  <div class="eyebrow">VIDEO INTELLIGENCE • DAMAGE PREVENTION</div>
  <h1>Understand handling.<br><span>Prevent damage.</span></h1>
  <p>
    A conservative computer-vision pipeline that detects people, products and
    equipment, maintains persistent tracks, reasons over motion and spatial
    relationships, and reports only evidence-backed potential risks.
  </p>
  <div class="meta-row">
    <div class="meta">Object detection</div>
    <div class="meta">Persistent tracking</div>
    <div class="meta">Temporal reasoning</div>
    <div class="meta">Risk classification</div>
    <div class="meta">Timestamped evidence</div>
    <div class="meta">Human review</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="panel">
  <div class="kicker">VIDEO INPUT</div>
  <h3>Analyze warehouse footage</h3>
  <div class="muted">
    High-precision defaults are intentionally conservative. The system does not
    claim that damage occurred; it reports observed behaviour and potential risk.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "Warehouse footage",
    type=["mp4", "mov", "avi", "mkv", "m4v"],
    label_visibility="collapsed",
    key=f"warehouse_uploader_{st.session_state['uploader_key']}",
)

if uploaded:
    suffix = Path(uploaded.name).suffix.lower() or ".mp4"
    input_path = OUT / f"source_video{suffix}"
    data = uploaded.getvalue()
    input_path.write_bytes(data)

    st.session_state["video_bytes"] = data
    st.session_state["video_name"] = uploaded.name
    st.session_state["video_path"] = str(input_path)

    left, right = st.columns([2.3, 1], gap="medium")
    with left:
        st.markdown(
            f"""
<div class="panel">
  <div class="kicker">SOURCE FOOTAGE</div>
  <h3>{esc(uploaded.name)}</h3>
  <div class="muted">{len(data)/1024/1024:.1f} MB · Ready for analysis</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.video(data)

    with right:
        st.markdown(
            """
<div class="panel">
  <div class="kicker">ANALYSIS PROFILE</div>
  <h3>Precision-first</h3>
  <div class="muted">These settings reduce duplicate/noisy behaviour alerts.</div>
</div>
""",
            unsafe_allow_html=True,
        )

        stride = st.select_slider(
            "Detection interval",
            options=[1, 2, 3],
            value=1,
            help="1 analyses every frame. Larger values are faster but reduce temporal resolution.",
        )
        imgsz = st.select_slider(
            "Inference size",
            options=[512, 640, 768],
            value=640,
        )
        conf = st.slider(
            "Minimum detection confidence",
            min_value=0.25,
            max_value=0.60,
            value=0.35,
            step=0.05,
            help="Higher values reduce false detections. Lower values may recover smaller objects.",
        )

        run = st.button(
            "RUN AI ANALYSIS",
            type="primary",
            use_container_width=True,
        )
        reset = st.button("RESET", use_container_width=True)

        if reset:
            clear_analysis()
            st.rerun()

    if run:
        progress = st.progress(0)
        status = st.empty()

        def progress_cb(value):
            progress.progress(max(0.0, min(1.0, value)))
            status.caption(f"Analyzing source video · {value*100:.0f}%")

        try:
            analyzer = VideoAnalyzer(
                detection_stride=stride,
                imgsz=imgsz,
                confidence=conf,
            )
            incidents, meta = analyzer.analyze(
                input_path,
                OUT,
                progress_cb,
                save_evidence=True,
                save_annotated_video=True,
            )
            st.session_state["incidents"] = sorted(
                incidents, key=lambda x: x.get("timestamp", 0)
            )
            st.session_state["meta"] = meta
            st.session_state.pop("copilot_answer", None)
            progress.progress(1.0)
            status.success(
                f"Analysis complete · {meta.get('processing_s', 0)}s · "
                f"{meta.get('realtime_factor', 0)}× realtime"
            )
            st.rerun()
        except Exception as exc:
            st.error(
                "Analysis failed. Check the video format and the local model/dependencies. "
                f"Technical detail: {exc}"
            )


incidents = st.session_state.get("incidents", [])
meta = st.session_state.get("meta", {})

if incidents or meta:
    high = sum(e.get("risk") in {"HIGH", "CRITICAL"} for e in incidents)
    critical = sum(e.get("risk") == "CRITICAL" for e in incidents)
    behaviour_count = len({e.get("behaviour") for e in incidents})
    duration = meta.get("duration_s", 0)
    findings = meta.get("key_findings", [])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
<div>
  <div class="kicker">RISK INTELLIGENCE</div>
  <h2>Evidence-backed overview</h2>
  <div class="muted">
    Repeated observations are consolidated. At most two strongest distinct
    behaviours are surfaced as key findings so the result stays readable.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    metrics = [
        ("VALIDATED EVENTS", len(incidents), "after temporal gates"),
        ("CRITICAL", critical, "human review"),
        ("HIGH / CRITICAL", high, "intervention review"),
        ("DISTINCT BEHAVIOURS", behaviour_count, "evidence-backed"),
        ("VIDEO", f"{duration}s", "source duration"),
    ]
    for col, (label, value, sub) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
<div class="panel metric">
  <div class="metric-label">{label}</div>
  <div class="metric-value">{esc(value)}</div>
  <div class="metric-sub">{esc(sub)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
<div class="kicker">KEY FINDINGS</div>
<h2>What the AI actually found</h2>
""",
        unsafe_allow_html=True,
    )

    if findings:
        for finding in findings[:ENGINE["summary_behaviour_limit"]]:
            timestamps = ", ".join(
                f"{float(t):.2f}s" for t in finding.get("timestamps_s", [])
            )
            colour = risk_color(finding.get("risk", "LOW"))
            st.markdown(
                f"""
<div class="finding">
  <span class="pill" style="color:{colour}">{esc(finding.get("risk"))} · {esc(finding.get("risk_score"))}/100</span>
  <strong>{esc(finding.get("behaviour"))}</strong>
  <div class="muted" style="margin-top:7px">
    Evidence timestamp: {esc(timestamps)}<br>
    {esc(finding.get("reason", ""))}
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No behaviour passed the configured evidence gates.")

    tabs = st.tabs(["Incident Timeline", "Evidence Review", "Supervisor Assistant", "Audit"])

    with tabs[0]:
        ordered = sorted(incidents, key=lambda e: e.get("timestamp", 0))
        if not ordered:
            st.info("No validated incidents.")
        else:
            st.markdown(
                '<div class="muted">Each item is an accepted, timestamped event. '
                'The engine suppresses the same behaviour/track during its cooldown window.</div>',
                unsafe_allow_html=True,
            )
            for event in ordered:
                colour = risk_color(event.get("risk", "LOW"))
                st.markdown(
                    f"""
<div class="timeline">
<div class="timeline-item">
  <span class="pill" style="color:{colour}">{esc(event.get("risk"))} · {esc(event.get("risk_score"))}/100</span>
  <strong>{esc(event.get("behaviour"))}</strong>
  <div class="muted" style="margin-top:6px">
    {event.get("timestamp", 0):.2f}s · Track {esc(event.get("track_id"))}
  </div>
  <div style="margin-top:8px;font-size:.78rem"><b>Observed:</b> {esc(event.get("explanation"))}</div>
  <div class="muted" style="margin-top:6px"><b>Why risky:</b> {esc(event.get("why_risky"))}</div>
  <div style="margin-top:7px;font-size:.76rem"><b>Recommended action:</b> {esc(event.get("recommended_action"))}</div>
</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    with tabs[1]:
        ordered = sorted(incidents, key=lambda e: e.get("timestamp", 0))
        if not ordered:
            st.info("No evidence frames available.")
        else:
            options = [
                f"{e.get('timestamp', 0):.2f}s · {e.get('behaviour')} · {e.get('risk')}"
                for e in ordered
            ]
            selected = st.selectbox("Select an incident", options)
            selected_event = ordered[options.index(selected)]

            if st.session_state.get("video_bytes"):
                st.video(
                    st.session_state["video_bytes"],
                    start_time=max(0, int(float(selected_event.get("timestamp", 0)))),
                )

            frame = selected_event.get("evidence_frame")
            if frame and Path(frame).exists():
                st.image(frame, caption=f"Evidence at {selected_event.get('timestamp', 0):.2f}s")
            st.json({
                "behaviour": selected_event.get("behaviour"),
                "risk": selected_event.get("risk"),
                "risk_score": selected_event.get("risk_score"),
                "timestamp_s": selected_event.get("timestamp"),
                "track_id": selected_event.get("track_id"),
                "evidence": selected_event.get("evidence"),
            })

    with tabs[2]:
        st.markdown(
            """
<div class="panel">
  <div class="kicker">EVIDENCE-GROUNDED ASSISTANT</div>
  <h3>Ask about this analysis</h3>
  <div class="muted">
    Answers are computed from detected incidents only. The assistant does not
    invent timestamps, behaviours or damage claims.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        prompts = [
            "Give me the shift brief",
            "What are the most common risky behaviours?",
            "Show me the high and critical risks",
            "Why was an incident flagged?",
        ]
        pc = st.columns(4)
        for i, prompt in enumerate(prompts):
            if pc[i].button(prompt, key=f"copilot_prompt_{i}", use_container_width=True):
                st.session_state["copilot_question"] = prompt

        question = st.text_input(
            "Question",
            value=st.session_state.get("copilot_question", "Give me the shift brief"),
        )
        if st.button("ASK ASSISTANT", type="primary"):
            st.session_state["copilot_answer"] = SupervisorAssistant().answer(
                question, incidents, meta
            )

        answer = st.session_state.get("copilot_answer")
        if answer:
            st.markdown(
                f"""
<div class="finding">
  <strong>{esc(answer.get("title"))}</strong>
  <div style="margin-top:8px">{esc(answer.get("summary"))}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            if answer.get("recommendations"):
                st.markdown("**Recommended intervention**")
                for recommendation in answer["recommendations"][:2]:
                    st.markdown(f"- {recommendation}")

    with tabs[3]:
        audit_path = OUT / "analysis.json"
        st.markdown(
            """
<div class="kicker">AUDITABILITY</div>
<h2>Analysis audit</h2>
<div class="muted">
  The audit preserves model settings, tracking statistics, event evidence and
  the distinction between observed behaviour and confirmed damage.
</div>
""",
            unsafe_allow_html=True,
        )
        audit = {
            "meta": meta,
            "scenario_coverage": sorted({e.get("behaviour") for e in incidents}),
            "incidents": incidents,
        }
        st.json(audit)

        st.download_button(
            "DOWNLOAD ANALYSIS JSON",
            json.dumps(audit, indent=2),
            file_name="warehouse_analysis.json",
            mime="application/json",
            use_container_width=True,
        )

        annotated = OUT / "annotated_analysis.mp4"
        if annotated.exists():
            st.video(annotated.read_bytes())
            st.download_button(
                "DOWNLOAD ANNOTATED VIDEO",
                annotated.read_bytes(),
                file_name="warehouse_annotated_analysis.mp4",
                mime="video/mp4",
                use_container_width=True,
            )

    st.markdown(
        """
<div class="panel" style="margin-top:18px">
  <div class="kicker">ACCURACY & RESPONSIBLE AI</div>
  <div class="note">
    This prototype reports potential risk, not confirmed damage. Physical weight,
    fragility, floor wetness and actual product condition cannot be established
    reliably from generic RGB footage alone. Behaviour accuracy must be validated
    with labelled warehouse footage using precision, recall and false-positive rate.
    Significant incidents require human review.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

else:
    st.markdown(
        """
<div class="panel" style="margin-top:18px">
  <div class="kicker">READY FOR ANALYSIS</div>
  <h3>From CCTV footage to prevention intelligence.</h3>
  <div class="note">
    Upload a warehouse video to start. The pipeline detects and tracks entities,
    validates behaviour over time, assigns evidence-based risk, and surfaces up to
    two strongest distinct findings rather than repeating noisy alerts.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
