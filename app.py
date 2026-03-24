import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64
from datetime import datetime

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="Morning Drop-off Registration",
    layout="wide"
)

st.title("🚌 Morning Drop-off Registration")

# ----------------------------
# GOOGLE SHEETS CONNECTION
# ----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_KEY = "1bEZcEAxRAcrlo_Aa92a0u_hFCZsaBZ2DSCMIKNqyblM"
TRACKER_SHEET = "Learner Tracker"
REG_SHEET = "Registration Form"

# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_resource
def get_workbook():
    return client.open_by_key(SPREADSHEET_KEY)

@st.cache_data(ttl=300)
def load_registration_data():
    workbook = get_workbook()
    worksheet = workbook.worksheet(REG_SHEET)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [str(col).strip() for col in df.columns]
    return df

def get_tracker_worksheet():
    workbook = get_workbook()
    return workbook.worksheet(TRACKER_SHEET)

reg_df = load_registration_data()
tracker_ws = get_tracker_worksheet()

# ----------------------------
# HELPERS
# ----------------------------
def image_to_base64(pil_image):
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def find_learner_record(df, learner_name_input):
    if df.empty:
        return None

    search_name = learner_name_input.strip().lower()
    if not search_name:
        return None

    # Try exact match first
    possible_name_cols = [col for col in df.columns if "name" in col.lower()]
    if not possible_name_cols:
        return None

    learner_name_col = possible_name_cols[0]

    exact_matches = df[df[learner_name_col].astype(str).str.strip().str.lower() == search_name]
    if not exact_matches.empty:
        return exact_matches.iloc[0]

    # Then partial match
    partial_matches = df[df[learner_name_col].astype(str).str.strip().str.lower().str.contains(search_name, na=False)]
    if not partial_matches.empty:
        return partial_matches.iloc[0]

    return None

def get_value(record, possible_columns):
    for col in possible_columns:
        if col in record.index:
            return record[col]
    return ""

def append_attendance_row(row_data):
    tracker_ws.append_row(row_data, value_input_option="USER_ENTERED")

# ----------------------------
# SEARCH SECTION
# ----------------------------
st.subheader("Search Learner")

learner_search_name = st.text_input("Enter Learner Name")

matched_record = None
if learner_search_name.strip():
    matched_record = find_learner_record(reg_df, learner_search_name)

if learner_search_name.strip() and matched_record is None:
    st.warning("No learner found in Registration Form.")
elif matched_record is not None:
    st.success("Learner found.")

    learner_name = get_value(matched_record, ["Learner Name", "learner_name", "Name", "Full Name"])
    grade = get_value(matched_record, ["Grade", "grade"])
    gender = get_value(matched_record, ["Gender", "gender"])
    age = get_value(matched_record, ["Age", "age"])
    parent_name = get_value(matched_record, ["Parent Name", "Parent / Guardian Name", "parent_name"])
    parent_contact = get_value(matched_record, ["Parent Contact", "Parent / Guardian Contact", "Contact Number", "parent_contact"])

    st.subheader("Learner Details")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Learner Name", value=str(learner_name), disabled=True)
    with col2:
        st.text_input("Grade", value=str(grade), disabled=True)
    with col3:
        st.text_input("Gender", value=str(gender), disabled=True)

    col4, col5 = st.columns(2)
    with col4:
        st.text_input("Age", value=str(age), disabled=True)
    with col5:
        st.text_input("Parent Contact", value=str(parent_contact), disabled=True)

    st.text_input("Parent / Guardian Name", value=str(parent_name), disabled=True)

    # ----------------------------
    # SIGNATURE + SUBMIT
    # ----------------------------
    with st.form("dropoff_form", clear_on_submit=True):
        direction = st.selectbox("Direction", ["IN"])
        notes = st.text_area("Notes")

        st.markdown("### Parent / Guardian Signature")
        st.caption("Use your finger on a tablet or mouse on a computer to sign below.")

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=220,
            width=700,
            drawing_mode="freedraw",
            key="signature_canvas"
        )

        submitted = st.form_submit_button("Save Attendance")

        if submitted:
            if canvas_result.image_data is None:
                st.error("Please add a signature before submitting.")
            else:
                try:
                    now = datetime.now()
                    time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
                    scan_date = now.strftime("%d-%b-%y")

                    signature_image = Image.fromarray(
                        (canvas_result.image_data[:, :, :3]).astype("uint8")
                    )
                    signature_b64 = image_to_base64(signature_image)

                    row_data = [
                        time_stamp,
                        scan_date,
                        direction,
                        grade,
                        gender,
                        age,
                        learner_name,
                        parent_name,
                        parent_contact,
                        notes,
                        signature_b64
                    ]

                    append_attendance_row(row_data)

                    st.success("Attendance saved successfully.")
                    st.info(f"{learner_name} has been registered for morning drop-off.")

                except Exception as e:
                    st.error(f"An error occurred while saving the attendance: {e}")
