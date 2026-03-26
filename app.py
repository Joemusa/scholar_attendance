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

    child_name_col = "Child's name:"
    if child_name_col not in df.columns:
        return None

    exact_matches = df[
        df[child_name_col].astype(str).str.strip().str.lower() == search_name
    ]
    if not exact_matches.empty:
        return exact_matches.iloc[0]

    partial_matches = df[
        df[child_name_col].astype(str).str.strip().str.lower().str.contains(search_name, na=False)
    ]
    if not partial_matches.empty:
        return partial_matches.iloc[0]

    return None

def append_attendance_row(row_data):
    tracker_ws.append_row(row_data, value_input_option="USER_ENTERED")

# ----------------------------
# SEARCH SECTION
# ----------------------------
st.subheader("Search Learner")

learner_search_name = st.text_input("Enter Child's Name")

matched_record = None
if learner_search_name.strip():
    matched_record = find_learner_record(reg_df, learner_search_name)

if learner_search_name.strip() and matched_record is None:
    st.warning("No learner found in Registration Form.")
elif matched_record is not None:
    st.success("Learner found.")

    learner_name = str(matched_record.get("Child's name:", "")).strip()
    grade = str(matched_record.get("Grade of the child:", "")).strip()
    gender = str(matched_record.get("Gender", "")).strip()
    age = str(matched_record.get("Scholar's age", "")).strip()
    parent_name = str(matched_record.get("Parent name:", "")).strip()
    school_name = str(matched_record.get("School Name", "")).strip()
    chat_id = str(matched_record.get("chat_id", "")).strip()
    subscription_plan = str(matched_record.get("Subscription plan", "")).strip()

    st.subheader("Learner Details")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Learner Name", value=learner_name, disabled=True)
    with col2:
        st.text_input("Grade", value=grade, disabled=True)
    with col3:
        st.text_input("Gender", value=gender, disabled=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.text_input("Age", value=age, disabled=True)
    with col5:
        st.text_input("Parent Name", value=parent_name, disabled=True)
    with col6:
        st.text_input("School Name", value=school_name, disabled=True)

    col7, col8 = st.columns(2)
    with col7:
        st.text_input("Chat ID", value=chat_id, disabled=True)
    with col8:
        st.text_input("Subscription Plan", value=subscription_plan, disabled=True)

    # ----------------------------
    # SIGNATURE + SUBMIT
    # ----------------------------
    with st.form("dropoff_form", clear_on_submit=True):
        direction = st.selectbox("Direction", ["IN"])
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
                        time_stamp,          # time_stamp
                        scan_date,           # scan_date
                        direction,           # direction
                        grade,               # Grade
                        gender,              # Gender
                        age,                 # Age
                        learner_name,        # learner_name
                        parent_name,         # parent_name
                        #school_name,         # school_name
                        #chat_id,             # chat_id
                        #subscription_plan,   # subscription_plan
                        #signature_b64        # signature_b64
                    ]

                    append_attendance_row(row_data)

                    st.success("Attendance saved successfully.")
                    st.info(f"{learner_name} has been registered for morning drop-off.")

                except Exception as e:
                    st.error(f"An error occurred while saving the attendance: {e}")
