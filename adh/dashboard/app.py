"""Streamlit Dashboard — pipeline overview, approval queue, replies inbox, CRM."""

import streamlit as st
from datetime import datetime
from sqlmodel import Session, select, func

st.set_page_config(
    page_title="ADH — AI Outreach Dashboard",
    page_icon="🎯",
    layout="wide",
)


def get_session():
    from adh.models.database import engine
    return Session(engine)


def page_overview():
    from adh.models.company import Company, CompanyStatus
    from adh.models.message import OutreachMessage, MessageStatus
    import plotly.graph_objects as go

    st.title("Pipeline Overview")

    with get_session() as session:
        statuses = [
            ("Scoperte", CompanyStatus.discovered),
            ("Qualificate", CompanyStatus.qualified),
            ("Approvate", CompanyStatus.approved),
            ("Contattate", CompanyStatus.contacted),
            ("Risposte", CompanyStatus.replied),
            ("Meeting", CompanyStatus.meeting_booked),
        ]

        counts = []
        labels = []
        for label, status in statuses:
            count = session.exec(
                select(func.count(Company.id)).where(Company.status == status)
            ).one()
            labels.append(label)
            counts.append(count)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    cols = [col1, col2, col3, col4, col5, col6]
    for i, (label, count) in enumerate(zip(labels, counts)):
        cols[i].metric(label, count)

    fig = go.Figure(go.Funnel(
        y=labels,
        x=counts,
        textinfo="value+percent initial",
        marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"],
    ))
    fig.update_layout(title="Funnel di Outreach", height=400)
    st.plotly_chart(fig, use_container_width=True)


def page_approval_queue():
    from adh.models.message import OutreachMessage, MessageStatus
    from adh.models.company import Company
    from sqlmodel import Session

    st.title("Approval Queue")
    st.caption("Revisiona e approva i messaggi prima dell'invio.")

    with get_session() as session:
        pending = session.exec(
            select(OutreachMessage, Company)
            .join(Company)
            .where(OutreachMessage.status == MessageStatus.pending_approval)
        ).all()

    if not pending:
        st.success("Nessun messaggio in attesa di approvazione.")
        return

    for msg, company in pending:
        with st.expander(f"📧 {company.name} — {msg.subject}", expanded=True):
            col_info, col_msg = st.columns([1, 2])

            with col_info:
                st.write(f"**Azienda:** {company.name}")
                st.write(f"**Settore:** {company.sector}")
                st.write(f"**Regione:** {company.region}")
                st.write(f"**Angolo:** {msg.pitch_angle}")
                st.write(f"**Segnale:** {msg.pain_signal_used}")
                st.write(f"**Step:** {msg.sequence_step}")

            with col_msg:
                st.text_area(
                    "Subject",
                    value=msg.subject,
                    key=f"subject_{msg.id}",
                    height=50,
                )
                st.text_area(
                    "Body",
                    value=msg.body,
                    key=f"body_{msg.id}",
                    height=200,
                )

            col_approve, col_reject = st.columns(2)

            with col_approve:
                if st.button(f"✅ Approva", key=f"approve_{msg.id}", type="primary"):
                    with get_session() as session2:
                        message = session2.get(OutreachMessage, msg.id)
                        if message:
                            message.status = MessageStatus.approved
                            message.approved_at = datetime.utcnow()
                            # Update edited content
                            message.subject = st.session_state.get(f"subject_{msg.id}", msg.subject)
                            message.body = st.session_state.get(f"body_{msg.id}", msg.body)
                            session2.add(message)
                            session2.commit()
                    st.success("Approvato!")
                    st.rerun()

            with col_reject:
                feedback = st.text_input(
                    "Motivo rifiuto",
                    key=f"feedback_{msg.id}",
                    placeholder="Es: troppo generico, non menziona la recensione...",
                )
                if st.button(f"❌ Rifiuta", key=f"reject_{msg.id}"):
                    with get_session() as session2:
                        message = session2.get(OutreachMessage, msg.id)
                        if message:
                            message.status = MessageStatus.rejected
                            message.rejection_feedback = feedback
                            session2.add(message)
                            session2.commit()
                    st.warning("Rifiutato. Il Writer Agent lo riscriverà con questo feedback.")
                    st.rerun()


def page_replies():
    from adh.models.message import OutreachMessage, MessageStatus, ReplyIntent
    from adh.models.company import Company

    st.title("Replies Inbox")

    with get_session() as session:
        replies = session.exec(
            select(OutreachMessage, Company)
            .join(Company)
            .where(OutreachMessage.status == MessageStatus.replied)
            .order_by(OutreachMessage.reply_received_at.desc())
        ).all()

    if not replies:
        st.info("Nessuna risposta ancora.")
        return

    intent_colors = {
        ReplyIntent.interested: "🔥",
        ReplyIntent.question: "❓",
        ReplyIntent.not_now: "⏳",
        ReplyIntent.not_interested: "🚫",
        ReplyIntent.unsubscribe: "⛔",
        ReplyIntent.out_of_office: "✈️",
    }

    for msg, company in replies:
        icon = intent_colors.get(msg.reply_intent, "📩")
        with st.expander(f"{icon} {company.name} — {msg.reply_intent}"):
            st.write(f"**Ricevuta:** {msg.reply_received_at}")
            st.write(f"**Risposta:**")
            st.text(msg.reply_body or "")

            if msg.reply_draft:
                st.write("**Bozza risposta (da approvare):**")
                st.text_area("Bozza", value=msg.reply_draft, height=150, key=f"draft_{msg.id}")

                if st.button("Invia bozza", key=f"send_draft_{msg.id}"):
                    st.success("Bozza inviata! (implementa il send qui)")


def page_companies():
    from adh.models.company import Company, CompanyStatus

    st.title("CRM — Aziende")

    with get_session() as session:
        companies = session.exec(select(Company).order_by(Company.created_at.desc())).all()

    if not companies:
        st.info("Nessuna azienda nel database.")
        return

    search = st.text_input("Cerca azienda", placeholder="Nome, settore, regione...")
    status_filter = st.selectbox("Filtra per status", ["Tutti"] + [s.value for s in CompanyStatus])

    filtered = companies
    if search:
        filtered = [c for c in filtered if search.lower() in (c.name + c.sector + c.region).lower()]
    if status_filter != "Tutti":
        filtered = [c for c in filtered if c.status.value == status_filter]

    st.write(f"**{len(filtered)} aziende**")

    data = [
        {
            "Nome": c.name,
            "Settore": c.sector,
            "Regione": c.region,
            "Score": c.qualification_score or "—",
            "Status": c.status.value,
            "Sito": c.website or "—",
            "Email": c.email or "—",
        }
        for c in filtered[:200]
    ]
    st.dataframe(data, use_container_width=True)


def page_settings():
    st.title("Settings")

    st.subheader("ICP Configuration")
    st.caption("Modifica adh/config/icp.yaml per cambiare settori, regioni e soglie.")

    import yaml
    from pathlib import Path

    icp_path = Path(__file__).parent.parent / "config" / "icp.yaml"
    if icp_path.exists():
        with open(icp_path) as f:
            icp_content = f.read()
        edited = st.text_area("icp.yaml", value=icp_content, height=500)
        if st.button("Salva ICP"):
            with open(icp_path, "w") as f:
                f.write(edited)
            st.success("ICP salvato!")

    st.subheader("Kill Switch")
    st.warning("Il Kill Switch blocca immediatamente tutti gli invii.")
    if st.button("🔴 ATTIVA KILL SWITCH", type="secondary"):
        import os
        os.environ["KILL_SWITCH"] = "true"
        st.error("Kill switch attivato! Riavvia il server per disattivare.")


PAGES = {
    "Pipeline Overview": page_overview,
    "Approval Queue": page_approval_queue,
    "Replies Inbox": page_replies,
    "CRM": page_companies,
    "Settings": page_settings,
}

page = st.sidebar.selectbox("Navigazione", list(PAGES.keys()))
PAGES[page]()
