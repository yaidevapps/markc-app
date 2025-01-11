import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv # type: ignore
from PIL import Image
from io import BytesIO
import base64
from typing import Optional

load_dotenv()

# --- Constants ---
BASE_API_URL = "https://api.langflow.astra.datastax.com"
LANGFLOW_ID = "cd71f509-33bf-4839-9b28-c8ecef44c7ee"
ENDPOINT = "mark_cristalli"  # The endpoint name of the flow
APPLICATION_TOKEN = os.getenv("ASTRA_APPLICATION_TOKEN")
print("Application Token:", os.getenv("ASTRA_APPLICATION_TOKEN"))

# --- Tweaks ---
TWEAKS = {
    "ChatInput-c1hCe": {},
    "ChatOutput-LYW8u": {},
    "Prompt-pVgGQ": {},
    "GoogleGenerativeAIModel-oCqMu": {},
    "Memory-TKh6U": {},
}

# --- Helper Functions ---
def encode_image(image):
    """Encodes an image to base64 for sending through API"""
    # Convert to RGB if the image has an alpha channel
    if image.mode == "RGBA":
      image = image.convert("RGB")
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def run_flow(message: str,
  endpoint: str,
  output_type: str = "chat",
  input_type: str = "chat",
  tweaks: Optional[dict] = None,
  application_token: Optional[str] = None) -> dict:
    """
    Run a flow with a given message and optional tweaks.

    :param message: The message to send to the flow
    :param endpoint: The ID or the endpoint name of the flow
    :param tweaks: Optional tweaks to customize the flow
    :return: The JSON response from the flow
    """
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{endpoint}"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }
    headers = {"Content-Type": "application/json"} # initialize the headers
    if tweaks:
        payload["tweaks"] = tweaks
    if application_token:
        headers["Authorization"] = "Bearer " + application_token # add token to header
    print("Headers being used:", headers)
    response = requests.post(api_url, json=payload, headers=headers)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return {"error": f"Failed to decode JSON response: {e}"}

# --- Streamlit App ---
st.title("Mark Cristalli Chat App")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        elif isinstance(message["content"], list):
            for item in message["content"]:
                if isinstance(item, str):
                   st.markdown(item)
                elif isinstance(item,dict) and "image" in item:
                   st.image(item["image"], use_column_width=True)

# Image Upload
uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])

# Chat Input
if prompt := st.chat_input("Type your message here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if uploaded_file is not None:
            # Read the image and convert to base64
            image = Image.open(uploaded_file)
            image_str = encode_image(image)
            tweaks_with_image = TWEAKS.copy()
            tweaks_with_image["ChatInput-c1hCe"] = {"image": f"data:image/jpeg;base64,{image_str}"}

            with st.chat_message("assistant"):
                st.markdown("Processing your image...")
                response = run_flow(message=prompt, endpoint=ENDPOINT,tweaks=tweaks_with_image, application_token=APPLICATION_TOKEN)
                print("Raw API Response (Image):", response)  # Debug print
                if "error" in response:
                    st.error(f"Error: {response['error']}")
                elif response and response.get("outputs"):
                    first_output = response["outputs"][0]
                    if first_output.get("outputs"):
                        first_component_output = first_output["outputs"][0]
                        if first_component_output.get("results") and first_component_output["results"].get("message"):
                            if first_component_output["results"]["message"].get("text"):
                              text_content = first_component_output["results"]["message"]["text"]
                              st.session_state.messages.append({"role": "assistant", "content": [text_content]})
                              st.markdown(text_content)
                            elif first_component_output["results"]["message"].get("image"):
                                  image_content = first_component_output["results"]["message"]["image"]
                                  st.session_state.messages.append({"role": "assistant", "content": [{"image": image_content}]})
                                  st.image(image_content, use_column_width=True)
                            else:
                                st.error(f"Error: No 'message' key in the first component output results. Response: {first_component_output}")
                        elif isinstance(first_component_output,dict) and "message" in first_component_output:
                             text_content = first_component_output["message"]["text"]
                             st.markdown(text_content)
                             st.session_state.messages.append({"role": "assistant", "content": [text_content]})
                        else:
                            st.error(f"Error: No 'outputs' key in the first component output. Response: {first_component_output}")
                    else:
                        st.error(f"Error: No 'outputs' key in the first output. Response: {first_output}")
                else:
                    st.error(f"Error: Could not retrieve the output from the langflow API. Response: {response}")

    else:
        # Run the Langflow flow without image if no image is given
        with st.chat_message("assistant"):
            st.markdown("Processing your message...")
            response = run_flow(message=prompt, endpoint=ENDPOINT, tweaks=TWEAKS, application_token=APPLICATION_TOKEN)
            print("Raw API Response (Text):", response)  # Debug print

            if response and response.get("outputs"):
                first_output = response["outputs"][0]
                if first_output.get("outputs"):
                    first_component_output = first_output["outputs"][0]
                    if first_component_output.get("results") and first_component_output["results"].get("message") and first_component_output["results"]["message"].get("text"):
                        text_content = first_component_output["results"]["message"]["text"]
                        st.markdown(text_content)
                        st.session_state.messages.append({"role": "assistant", "content": [text_content]})
                    elif first_component_output.get("outputs") :
                        output = first_component_output["outputs"]
                        content_to_display=[]
                        for single_output in output:
                            if isinstance(single_output,dict) and "message" in single_output:
                                text_content = single_output["message"]["text"]
                                content_to_display.append(text_content)
                            elif isinstance(single_output, dict) and "image" in single_output:
                                image_content = single_output["image"]
                                content_to_display.append({"image":image_content})
                            elif isinstance(single_output,str):
                                content_to_display.append(single_output)

                        st.session_state.messages.append({"role": "assistant", "content": content_to_display})
                        for item in content_to_display:
                            if isinstance(item, str):
                                st.markdown(item)
                            elif isinstance(item,dict) and "image" in item:
                                 st.image(item["image"], use_column_width=True)
                    elif isinstance(first_component_output,dict) and "message" in first_component_output:
                        text_content = first_component_output["message"]["text"]
                        st.markdown(text_content)
                        st.session_state.messages.append({"role": "assistant", "content": [text_content]})
                    else:
                        st.error(f"Error: No 'outputs' key in the first component output. Response: {first_component_output}")
                else:
                    st.error(f"Error: No 'outputs' key in the first output. Response: {first_output}")
            else:
                st.error(f"Error: Could not retrieve the output from the langflow API. Response: {response}")
