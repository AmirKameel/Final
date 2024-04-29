import streamlit as st
import pandas as pd
from fpdf import FPDF
from clarifai.client.model import Model
import os

# Initialize Clarifai model
model_url = "https://clarifai.com/openai/chat-completion/models/gpt-4-turbo"
clarifai_model = Model(url=model_url, pat="a859318378284560beec23442a19ba57")

# Positions dictionary
positions = {
    "CF": "Center Forward",
    "GK": "Goalkeeper",
    "Defence": "Defence",
}


def save_uploaded_file(uploaded_file, file_path):
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

from PIL import Image

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

from fpdf import FPDF
from fpdf import HTMLMixin
import pandas as pd

class PDF(FPDF, HTMLMixin):
    pass

def create_pdf_report(player_name, player_position, analysis_result, image_path, stats_table):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Add title
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(0, 0, 128)  # Dark blue color
    pdf.cell(200, 10, f"Football Performance Analysis Report for {player_name}", ln=True, align="C")

    # Add player image
    pdf.image(image_path, x=10, y=25, w=50)
    
    # Add analysis section
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(0, 0, 0)  # Black color
    pdf.set_xy(10, 90)
    pdf.multi_cell(0, 10, analysis_result)
    

    col_widths = [60, 40, 40]
    
    for row in stats_table:
        for i in range(len(row)):
            pdf.cell(col_widths[i], 10, txt=row[i], border=1)
        pdf.ln()

    # Add footer
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(128, 128, 128)  # Gray color
    pdf.set_y(-15)
    pdf.cell(0, 10, "Generated by Football Performance Analyzer", 0, 1, "C")
    
    return pdf


def analyze_performance(file_path, position, player_name, player_image_path):
    try:
        converted_image_path = convert_to_supported_image_format(player_image_path, f"temp_files/converted_{player_name}_image.png")
        
        if not converted_image_path:
            return None
        
        # Read uploaded data using Pandas
        data = pd.read_csv(file_path)

        # Filter data for the specified player based on name
        player_data = data[data["Name"] == player_name]

        if player_data.empty:
            st.error(f"Player '{player_name}' not found in the uploaded file.")
            return None

        # Extract relevant stats based on position
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

        # Generate report using Clarifai model
        stats_table = []
        prompt = f"I need you to be a professional football performance analyst for the indivdual players so I need you to create a full report to Analyze the performance and extrcting the strenght and weaknesses of a {position} player based on the following statistics:\n but doesnot return the stats it to the user please."
        for stat, value in stats.items():
            prompt += f"- {stat}: {value}\n"

        if isinstance(prompt, str):
    # If prompt is a string, encode it
            prompt_bytes = prompt.encode("utf-8")
        else:
    # If prompt is already in bytes or bytearray format, no need to encode
            prompt_bytes = prompt

# Use prompt_bytes for further processing


        prompt_bytes = prompt.encode("utf-8")

# Construct Input object from encoded prompt

# Pass the Input object to the predict method
        completion = clarifai_model.predict_by_bytes(b"""I need you to be a professional football performance analyst for the indivdual players so I need you to create a full report to Analyze the performance and extrcting the strenght and weaknesses of a {position} player based on the following statistics:\n but doesnot return the stats it to the user please.""", input_type="text")

# Extract the analysis result from completion
        analysis_result = completion.outputs[0].data.text.raw

# Extract the analysis result from completion
 


        # Convert stats dictionary to table format for PDF
        lines = analysis_result.split("\n")
        for line in lines:
            if "|" in line:
                stats_table.append(line.split("|")[1:-1])

        #print("Stats Table:", stats_table)  # Add this line for debugging


        # Create PDF report
        pdf = create_pdf_report(player_name, positions[position], analysis_result, converted_image_path, stats_table)

        
        # Download functionality using Streamlit
        filename = f"{player_name}_Performance_Analysis.pdf"
        pdf_data = pdf.output(dest="S").encode("latin-1")
        st.download_button("Download Report", data=pdf_data, file_name=filename, mime="application/pdf")

        return analysis_result

    except FileNotFoundError:
        st.error("Error: File not found or invalid format.")
    except Exception as e:
        st.error(f"Error processing file: {e}")

    return None

# User Interface Elements
st.title("Football Performance Analyzer (File Upload & Player Search)")

uploaded_file = st.file_uploader("Upload Player Stats File (CSV)", type="csv")
position_selected = st.selectbox("Player Position", list(positions.keys()))

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        # Create a temporary directory to store uploaded files
        temp_dir = "temp_files"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save uploaded CSV file
        csv_file_path = os.path.join(temp_dir, "temp_data.csv")
        save_uploaded_file(uploaded_file, csv_file_path)
        
        # Get player names from uploaded file
        player_names = pd.read_csv(csv_file_path)["Name"].tolist()

        selected_player = st.selectbox("Select Player", ["-- Select Player --"] + player_names)

        # Upload player image
        player_image = st.file_uploader("Upload Player Image (JPEG or PNG)", type=["jpg", "jpeg", "png"])
        if player_image:
            # Save uploaded image
            image_file_path = os.path.join(temp_dir, f"temp_{selected_player}_image.png")
            save_uploaded_file(player_image, image_file_path)

            # Add a button to trigger the analysis
            if st.button("Analyze Performance"):
                # Call analyze_performance function with selected player name, position, and image path
                analysis_result = analyze_performance(csv_file_path, position_selected, selected_player, image_file_path)
                if analysis_result:
                    # Display the analysis result
                    st.markdown("## Performance Analysis")
                    st.write(analysis_result)
