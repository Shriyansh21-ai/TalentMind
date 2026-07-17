import streamlit as st


def show_job_dashboard(profile):

    st.header("🧠 AI Job Intelligence")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Role", profile.role)

    c2.metric("Experience", f"{profile.experience}+ yrs")

    c3.metric("Difficulty", profile.hiring_difficulty)

    c4.metric("Complexity", f"{profile.complexity_score:.0f}%")

    st.write("---")

    st.subheader("Mandatory Skills")

    st.write(profile.mandatory_skills)

    st.subheader("Preferred Skills")

    st.write(profile.preferred_skills)

    st.subheader("Technologies")

    st.write(profile.technologies)

    st.subheader("Leadership")

    if profile.leadership_required:
        st.success("Leadership Required")

    else:
        st.info("Individual Contributor")
