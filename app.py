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
WORKSHEET_NAME = "Learner Tracker"

# ----------------------------
# LOAD SHEET
# ----------------------------
@st.cache_resource
def get_worksheet():
    workbook = client.open_by_key(SPREADSHEET_KEY)
    worksheet = workbook.worksheet(WORKSHEET_NAME)
    return worksheet

worksheet = get_worksheet()

# ----------------------------
# HELPERS
# ----------------------------
def image_to_base64(pil_image):
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def append_attendance_row(row_data):
    worksheet.append_row(row_data, value_input_option="USER_ENTERED")

# ----------------------------
# FORM
# ----------------------------
with st.form("dropoff_form", clear_on_submit=True):
    st.subheader("Learner Details")

    col1, col2, col3 = st.columns(3)

    with col1:
        learner_name = st.text_input("Learner Name")
    with col2:
        grade = st.text_input("Grade")
    with col3:
        gender = st.selectbox("Gender", ["", "Male", "Female"])

    col4, col5, col6 = st.columns(3)

    with col4:
        age = st.text_input("Age")
    with col5:
        direction = st.selectbox("Direction", ["IN"])
    with col6:
        parent_name = st.text_input("Parent / Guardian Name")

    parent_contact = st.text_input("Parent / Guardian Contact Number")
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

# ----------------------------
# SAVE DATA
# ----------------------------
if submitted:
    if not learner_name.strip():
        st.error("Please enter Learner Name.")
    elif not grade.strip():
        st.error("Please enter Grade.")
    elif not parent_name.strip():
        st.error("Please enter Parent / Guardian Name.")
    elif canvas_result.image_data is None:
        st.error("Please add a signature before submitting.")
    else:
        try:
            # Timestamp fields
            now = datetime.now()
            time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
            scan_date = now.strftime("%d-%b-%y")

            # Signature image
            signature_image = Image.fromarray((canvas_result.image_data[:, :, :3]).astype("uint8"))
            signature_b64 = image_to_base64(signature_image)

            # Row must match your Learner Tracker structure
            row_data = [
                time_stamp,        # time_stamp
                scan_date,         # scan_date
                direction,         # direction
                grade,             # Grade
                gender,            # Gender
                age,               # Age
                learner_name,      # extra field
                parent_name,       # extra field
                parent_contact,    # extra field
                notes,             # extra field
                signature_b64      # extra field
            ]

            append_attendance_row(row_data)

            st.success("Attendance saved successfully.")
            st.info(f"Learner {learner_name} has been registered for morning drop-off.")

        except Exception as e:
            st.error(f"An error occurred while saving the attendance: {e}")
