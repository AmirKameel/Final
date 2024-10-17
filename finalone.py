# loads genai API Key from .env file

import google.generativeai as genai  # Gemini API key

import io  # file conversions
import os  # system import
from PIL import Image  # file conversions

import streamlit as st  # build up website
from RealtimeSTT import AudioToTextRecorder  # audio recorder


def gemini_answer(prompt, img=None):
    # Sends response
    if prompt == '':
        return None
    if img:
        response = st.session_state.model.generate_content([prompt, img])
    else:
        response = st.session_state.model.generate_content(prompt)
    try:
        return response.text
    except ValueError:
        return 'Please rephrase your prompt to a more appropriate inquiry.'


def stImg_convert(st_img):
    '''
    Converts the image returned from streamlit's format into\nanotherformat readable by Gemini Pro Vision: pil
    '''
    image_data = st_img.read()
    # converts streamlit image to pil image
    pil_image = Image.open(io.BytesIO(image_data))
    return pil_image


def answer_output(answer):
    '''
    Shows Gemini response in the output text area
    '''
    print(f"HY: answer_output AI Answer: {answer}")
    st.session_state.answer = answer
    st.markdown('<p class="big-font">Gemini Answer</p>',
                unsafe_allow_html=True)
    st.text_area(label='Gemini Answer:', label_visibility='collapsed', value=st.session_state.answer,
                 height=250, key='answer_output')
    st.divider()


def save_history(prompt, answer):
    '''
    Saves prompt and response to session_state.history
    '''
    st.session_state.history = f'Question: {prompt}\n\nAnswer: {answer}\n\n{"-"*100}\n\n{st.session_state.history}'
    st.markdown('<p class="big-font">Session history</p>',
                unsafe_allow_html=True)
    st.text_area(label="Session history", label_visibility='collapsed', height=400,
                 value=st.session_state.history, key='history_text_area')


def submit_history():
    '''
    submits the current text into another session_state var and clears .widget
    '''
    st.session_state.prompt = st.session_state.widget
    st.session_state.widget = ''


def start_listening():
    # callback for the button ' Start Conversation' click
    st.session_state.recorder.start()
    st.session_state.already_listening = True


def stop_listening():
    # callback for the button ' Stop Conversation' click
    if st.session_state.already_listening:
        # stop recording
        st.session_state.recorder.stop()
        print("Stopped Listening")
        # set the recorded text to session_state.prompt
        st.session_state.prompt = st.session_state.recorder.text()
        print("Recorder Prompt Assigned")
        st.session_state.already_listening = False
    else:
        pass


import os
import toml

def configure_gemini():
    # Load the secrets from the secrets.toml file
    

    # Configure Gemini model
    st.session_state.model = genai.GenerativeModel("gemini-pro")
    
    # Get the API key from secrets.toml and configure it to Gemini API
    google_api_key = os.environ["google_api_key"]
     

    if google_api_key:
        genai.configure(api_key=google_api_key)
        print("Gemini Configured")
    else:
        print("API key not found in secrets.toml")



def img_exists(img):
    '''
    Change the Gemini model by determining if 
    there is an img inserted or not.
    '''
    if img:
        st.session_state.model = genai.GenerativeModel("gemini-1.5-flash")
        print(f"-- Gemini-Pro-Vision Enabled")
    elif not img:
        st.session_state.model = genai.GenerativeModel("gemini-pro")
        print(f"-- Gemini-Pro Enabled")


def send_to_Gemini(prompt, pil_img=None):
    print('AI Response Processing Started')
    if pil_img:
        answer = gemini_answer(prompt=prompt, img=pil_img)
    elif not pil_img:
        answer = gemini_answer(prompt=prompt)
    answer_output(answer=answer)
    save_history(prompt=prompt, answer=answer)
    # Reset prompt and response
    st.session_state.prompt = ''
    prompt = ''
    answer = ''


def initialize_page():
    # initialize the webpage title
    st.set_page_config(layout="centered")
    st.session_state.markdown2 = st.markdown(
        """ <style> .big-font {font-size:100px !important;}</style>""", unsafe_allow_html=True)
    st.title(':orange[Blind Date Show]')


def st_start():
    initialize_page()

    # Run one time to configure gemini api
    if 'model' not in st.session_state:
        configure_gemini()

    # Initialize other session_state global variables
    if 'prompt' not in st.session_state:
        st.session_state.prompt = ''
    if 'recorder' not in st.session_state:
        st.session_state.recorder = AudioToTextRecorder(
            spinner=False, language='en')
    if 'history' not in st.session_state:
        st.session_state.history = ''
    if 'already_listening' not in st.session_state:
        st.session_state.already_listening = False
    if 'answer' not in st.session_state:
        st.session_state.answer = ''

    # Create two columns
    left_column, right_column = st.columns(2)

    # Display image
    st.session_state.markdown = st.markdown(
        """ <style> .big-font {font-size:25px !important;}</style>""", unsafe_allow_html=True)
    right_column.markdown(
        '<p class="big-font">Insert an image</p>', unsafe_allow_html=True)
    img = right_column.file_uploader(
        label='nothing', label_visibility='collapsed', type=['jpg', 'jpeg', 'png', 'gif'])
    if img:
        st.image(img, caption="Ask some questions about this image.")

    # Initialize voice buttons
    left_column.markdown(
        '<p class="big-font">Ask with your voice!</p>', unsafe_allow_html=True)
    left_column.button(' Start Conversation', on_click=start_listening)
    left_column.button(' End Conversation', on_click=stop_listening)

    # Initialize text areas for prompt, response, and history
    st.markdown('<p class="big-font">Ask a question</p>',
                unsafe_allow_html=True)
    st.text_area(label=" Ask the AI a question", label_visibility='collapsed',
                 on_change=submit_history, key='widget', height=200)

    # create the prompt attribute to session_state to store current prompt
    prompt = st.session_state.prompt

    print("Widgets Loaded")
    if len(prompt):
        # determine which gemini modal to use (pro or pro-vision)
        img_exists(img=img)
        # send the prompt to AI if img is True
        if img:
            pil_image = stImg_convert(img)
            with st.spinner('Running...'):
                send_to_Gemini(prompt=prompt, pil_img=pil_image)
            print(f'AI Response Process Completed')
        # send the prompt to AI if img is False
        else:
            with st.spinner('Running...'):
                send_to_Gemini(prompt=prompt)
            print(f'AI Vision Response Process Completed')


if __name__ == "__main__":
    st_start()
