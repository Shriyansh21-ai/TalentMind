import streamlit as st


def show_candidate(candidate):

    st.subheader(
        f"{candidate.profile.current_title}"
    )

    st.write(
        f"Company: {candidate.profile.current_company}"
    )

    st.write(
        f"Experience: {candidate.profile.years_of_experience} years"
    )

    st.write(
        f"Location: {candidate.profile.location}"
    )

    st.write(
        f"Notice Period: "
        f"{candidate.redrob_signals.notice_period_days} days"
    )

    st.write(
        f"Open To Work: "
        f"{candidate.redrob_signals.open_to_work_flag}"
    )

    st.markdown("### Skills")

    for skill in candidate.skills:
        st.write(skill.name)