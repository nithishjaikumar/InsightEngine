
import requests
import pandas as pd
import streamlit as st

API_BASE = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="InsightEngine",
    page_icon="📊",
    layout="wide",
)

st.title("📊 InsightEngine")
st.caption("Consumer Feedback Analysis Dashboard")

# API helpers
def get_api(path, params=None):
    response = requests.get(
        f"{API_BASE}{path}",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_items(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("items", "results", "data"):
            if isinstance(data.get(key), list):
                return data[key]

    return []


# Backend connection
try:
    health_response = requests.get(
        "http://127.0.0.1:8000/health",
        timeout=5,
    )
    health_response.raise_for_status()
    st.success("Connected to FastAPI backend")
except requests.RequestException:
    st.error(
        "Cannot connect to FastAPI. Start your backend in another "
        "terminal using: uvicorn app.main:app --reload"
    )
    st.stop()


# Load projects
try:
    projects_response = get_api(
        "/projects",
        params={"limit": 100, "offset": 0},
    )
    projects = get_items(projects_response)
except (requests.RequestException, ValueError) as exc:
    st.error(f"Could not load projects: {exc}")
    st.stop()


project_options = {
    f'{project["name"]} (ID: {project["id"]})': project
    for project in projects
    if "name" in project and "id" in project
}

if not project_options:
    st.warning(
        "No projects were returned. Create a project using "
        "the FastAPI documentation at http://127.0.0.1:8000/docs."
    )
    st.stop()


# Project selection
selected_project_name = st.selectbox(
    "Select a project",
    options=list(project_options.keys()),
)

selected_project = project_options[selected_project_name]
project_id = selected_project["id"]

st.divider()
st.subheader(f'Project: {selected_project["name"]}')


# Load analytics and reviews
try:
    analytics = get_api(
        f"/projects/{project_id}/analytics/summary"
    )

    reviews_response = get_api(
        f"/projects/{project_id}/reviews",
        params={"limit": 100, "offset": 0},
    )

    reviews = get_items(reviews_response)

except (requests.RequestException, ValueError) as exc:
    st.error(f"Could not load project analytics: {exc}")
    st.stop()


# Summary cards
total_reviews = analytics.get("total_reviews", 0)
average_rating = analytics.get("average_rating") or 0

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Reviews",
    total_reviews,
)

col2.metric(
    "Average Rating",
    f"{float(average_rating):.2f} / 5",
)

col3.metric(
    "Project ID",
    project_id,
)


# Rating distribution
st.divider()
st.subheader("⭐ Rating Distribution")

rating_counts = analytics.get("rating_counts", {})

chart_data = pd.DataFrame({
    "Rating": [f"{rating} Star" for rating in range(1, 6)],
    "Reviews": [
        int(
            rating_counts.get(
                str(rating),
                rating_counts.get(rating, 0),
            )
        )
        for rating in range(1, 6)
    ],
}).set_index("Rating")

st.bar_chart(chart_data)


# Customer reviews
st.divider()
st.subheader("Customer Reviews")

if reviews:
    review_df = pd.DataFrame(reviews)

    preferred_columns = [
        column
        for column in [
            "id",
            "customer_name",
            "rating",
            "review_text",
            "created_at",
        ]
        if column in review_df.columns
    ]

    if preferred_columns:
        review_df = review_df[preferred_columns]

    st.dataframe(
        review_df,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No reviews are available for this project.")


# CSV import
st.divider()
st.subheader("📁 Import Customer Reviews")

st.write(
    "Upload a CSV file to import customer reviews through "
    "your existing API."
)

uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=["csv"],
)

if st.button(
    "Import CSV",
    disabled=uploaded_file is None,
):
    try:
        upload_response = requests.post(
            f"{API_BASE}/projects/{project_id}/reviews/import-csv",
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "text/csv",
                )
            },
            timeout=60,
        )

        try:
            result = upload_response.json()
        except ValueError:
            result = {"detail": upload_response.text}

        if upload_response.ok:
            st.success(
                result.get("message", "CSV import completed.")
            )
            st.json(result)
            st.rerun()
        else:
            st.error("CSV import was rejected by the API.")
            st.json(result)

    except requests.RequestException as exc:
        st.error(f"CSV upload failed: {exc}")


st.divider()
st.caption(
    "InsightEngine | FastAPI • MySQL • SQLAlchemy • Streamlit"
)
