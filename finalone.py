import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
import os
from clarifai.client.model import Model



# Initialize Clarifai model
model_url = "https://clarifai.com/openai/chat-completion/models/GPT-3_5-turbo"
clarifai_model = Model(url=model_url, pat="8866ee7a609c4b2992a931c11d46ac52")

# Positions dictionary
positions = {
    "CF": "Center Forward",
    "GK": "Goalkeeper",
    "Defence": "Defence",
}

# Save uploaded file
def save_uploaded_file(uploaded_file, file_path):
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

# Convert image to a supported format
def convert_to_supported_image_format(image_path, output_path):
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(output_path, "PNG")
            return output_path
    except Exception as e:
        st.error(f"Error converting image: {e}")
        return None

# PDF class for generating reports
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.set_text_color(0, 0, 128)
        self.cell(0, 10, "Football Performance Analysis Report", 0, 1, "C")

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Generated by Football Performance Analyzer", 0, 0, "C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, "L", 1)
        self.ln(5)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        paragraphs = body.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.startswith("###"):
                self.set_font("Arial", "B", 12)
                paragraph = paragraph.replace("### ", "")
            elif paragraph.startswith("**"):
                self.set_font("Arial", "I", 12)
                paragraph = paragraph.replace("**", "")
            elif ":**" in paragraph:
                self.set_font("Arial", "I", 12)
                paragraph = paragraph.replace(":**", ":")
            else:
                self.set_font("Arial", "", 12)
            self.multi_cell(0, 10, paragraph)
            self.ln()

    def player_stats_table(self, stats_table):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Player Statistics", 0, 1, "L")
        self.set_font("Arial", "", 10)
        col_width = self.w / 4  # Equal column width based on page width
        for row in stats_table:
            for item in row:
                self.cell(col_width, 10, item, border=1)
            self.ln()

# Function to create PDF report
def create_pdf_report(player_name, player_position, analysis_result, image_path, stats_table):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Performance Analysis Report for {player_name}", 0, 1, "C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Position: {player_position}", 0, 1, "L")
    pdf.ln(10)

    if image_path:
        pdf.image(image_path, x=10, y=30, w=40)
        pdf.ln(50)

    pdf.chapter_title("Analysis Result")
    pdf.chapter_body(analysis_result)

    pdf.player_stats_table(stats_table)
    
    return pdf

# Function to analyze player performance
def analyze_performance(file_path, position, player_name, player_image_path):
    try:
        converted_image_path = convert_to_supported_image_format(player_image_path, f"temp_files/converted_{player_name}_image.png")
        
        if not converted_image_path:
            return None
        
        data = pd.read_csv(file_path)
        player_data = data[data["Name"] == player_name]

        if player_data.empty:
            st.error(f"Player '{player_name}' not found in the uploaded file.")
            return None

        if position == "CF":
            stats = {
                "Team": player_data["Team"].iloc[0],
                "Name": player_data["Name"].iloc[0],
                "Average Sofascore rating": player_data["Average Sofascore rating"].iloc[0],
                "Goals": player_data["Goals"].iloc[0],
                "Big chances missed": player_data["Big chances missed"].iloc[0],
                "Succ. dribbles": player_data["Succ. dribbles"].iloc[0],
                "Successful dribbles %": player_data["Successful dribbles %"].iloc[0],
                "Total shots": player_data["Total shots"].iloc[0],
                "Shots on target": player_data["Shots on target"].iloc[0],
                "Shots off target": player_data["Shots off target"].iloc[0],
                "Blocked shots": player_data["Blocked shots"].iloc[0],
                "Goal conversion %": player_data["Goal conversion %"].iloc[0],
                "Penalties taken": player_data["Penalties taken"].iloc[0],
                "Penalty goals": player_data["Penalty goals"].iloc[0],
                "Penalty won": player_data["Penalty won"].iloc[0],
                "Shots from set piece": player_data["Shots from set piece"].iloc[0],
                "Free kick goals": player_data["Free kick goals"].iloc[0],
                "Goals from inside the box": player_data["Goals from inside the box"].iloc[0],
                "Goals from outside the box": player_data["Goals from outside the box"].iloc[0],
                "Headed goals": player_data["Headed goals"].iloc[0],
                "Left foot goals": player_data["Left foot goals"].iloc[0],
                "Right foot goals": player_data["Right foot goals"].iloc[0],
                "Hit woodwork": player_data["Hit woodwork"].iloc[0],
                "Offsides": player_data["Offsides"].iloc[0],
                "Penalty conversion": player_data["Penalty conversion"].iloc[0],
                "Set piece conversion %": player_data["Set piece conversion %"].iloc[0]
            }
            
        elif position == "GK":
            stats = {
                "Team": player_data["Team"].iloc[0],
                "Name": player_data["Name"].iloc[0],
                "Average Sofascore rating": player_data["Average Sofascore rating"].iloc[0],
                "Saves": player_data["Saves"].iloc[0],
                "Clean sheets": player_data["Clean sheets"].iloc[0],
                "Penalties faced": player_data["Penalties faced"].iloc[0],
                "Penalties saved": player_data["Penalties saved"].iloc[0],
                "Saves from inside box": player_data["Saves from inside box"].iloc[0],
                "Saved shots from outside the box": player_data["Saved shots from outside the box"].iloc[0],
                "Goals conceded inside the box": player_data["Goals conceded inside the box"].iloc[0],
                "Goals conceded outside the box": player_data["Goals conceded outside the box"].iloc[0],
                "Punches": player_data["Punches"].iloc[0],
                "Runs out": player_data["Runs out"].iloc[0],
                "Successful runs out": player_data["Successful runs out"].iloc[0],
                "High claims": player_data["High claims"].iloc[0],
                "Crosses not claimed": player_data["Crosses not claimed"].iloc[0]
            }
        elif position == "Defence":
            stats = {
                "Team": player_data["Team"].iloc[0],
                "Name": player_data["Name"].iloc[0],
                "Average Sofascore rating": player_data["Average Sofascore rating"].iloc[0],
                "Tackles": player_data["Tackles"].iloc[0],
                "Interceptions": player_data["Interceptions"].iloc[0],
                "Penalty committed": player_data["Penalty committed"].iloc[0],
                "Clearances": player_data["Clearances"].iloc[0],
                "Errors lead to goal": player_data["Errors lead to goal"].iloc[0],
                "Errors lead to shot": player_data["Errors lead to shot"].iloc[0],
                "Own goals": player_data["Own goals"].iloc[0],
                "Dribbled past": player_data["Dribbled past"].iloc[0],
                "Clean sheets": player_data["Clean sheets"].iloc[0]
            }
        else:
            st.error("Unsupported position. Please choose a valid position.")
            return None

        prompt = f"I need you to be a professional football performance analyst for the individual players so I need you to create a full report to analyze the performance in 2 pages then extract the strengths and weaknesses of a {position} then suggest trainings for weaknesses player based on the following statistics:\n"
        for stat, value in stats.items():
            prompt += f"- {stat}: {value}\n"

        prompt_bytes = prompt.encode("utf-8")
        completion = clarifai_model.predict_by_bytes(prompt_bytes, input_type="text")
        analysis_result = completion.outputs[0].data.text.raw

        stats_table = [[stat, str(value)] for stat, value in stats.items()]

        pdf = create_pdf_report(player_name, positions[position], analysis_result, converted_image_path, stats_table)
        temp_dir = "temp_files"
        os.makedirs(temp_dir, exist_ok=True)
        pdf_output_path = os.path.join(temp_dir, f"{player_name}_performance_report.pdf")
        pdf.output(pdf_output_path)
       

        return analysis_result,pdf_output_path

    except FileNotFoundError:
        st.error("Error: File not found or invalid format.")
    except Exception as e:
        st.error(f"Error processing file: {e}")

    return None

# Streamlit UI
st.markdown(
    """
    <style>
        .section-title {
            color: #2C3E50;
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .section-subtitle {
            color: #2C3E50;
            font-size: 24px;
            margin-bottom: 10px;
        }
        .stat-card {
            background-color: #ECF0F1;
            border-radius: 10px;
            padding: 15px;
            margin: 10px;
            box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
        }
        .stat-card p {
            margin: 0;
            font-size: 16px;
            color: #2C3E50;
        }
        .upload-section {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
        }
        .analysis-result {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Page title
st.markdown("<h1 class='section-title'>Player Performance Analysis</h1>", unsafe_allow_html=True)

# File upload section
st.markdown("<h2 class='section-subtitle'>Upload Player Stats File (CSV)</h2>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type="csv")

# Player position selection
position_selected = st.selectbox("Player Position", list(positions.keys()))

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        temp_dir = "temp_files"
        os.makedirs(temp_dir, exist_ok=True)
        
        csv_file_path = os.path.join(temp_dir, "temp_data.csv")
        save_uploaded_file(uploaded_file, csv_file_path)
        
        player_names = pd.read_csv(csv_file_path)["Name"].tolist()
        selected_player = st.selectbox("Select Player", ["-- Select Player --"] + player_names)

        # Image upload section
        st.markdown("<h2 class='section-subtitle'>Upload Player Image (JPEG or PNG)</h2>", unsafe_allow_html=True)
        player_image = st.file_uploader("", type=["jpg", "jpeg", "png"])

        if player_image:
            image_file_path = os.path.join(temp_dir, f"temp_{selected_player}_image.png")
            save_uploaded_file(player_image, image_file_path)

            if st.button("Analyze Performance"):
                analysis_result, pdf_path = analyze_performance(csv_file_path, position_selected, selected_player, image_file_path)
                if analysis_result and pdf_path:
                    st.markdown("<div class='analysis-result'>", unsafe_allow_html=True)
                    st.markdown("<h2 class='section-subtitle'>Performance Analysis</h2>", unsafe_allow_html=True)
                    st.write(analysis_result)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<h2 class='section-subtitle'>Download PDF Report</h2>", unsafe_allow_html=True)
                    st.write("Click the button below to download the PDF report.")
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    st.download_button(label="Download PDF", data=pdf_bytes, file_name=f"{selected_player}_performance_report.pdf", mime="application/pdf")
