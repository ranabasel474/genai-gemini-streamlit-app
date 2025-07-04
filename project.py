# ============================ Import libraries ============================
import streamlit as st
import google.generativeai as genai
from PIL import Image
import streamlit.components.v1 as components
import json
import re
import requests

# ============================ Constants ============================
prompt_templates = {
    "Choose a template...": "",
    "Write a story...": "Write a compelling story, approximately [# of words] words, about [topic or situation]. Focus on developing [character(s)] and include a [resolution/theme].",
    "Summarize text...": "Read the following text and provide a concise, objective summary, no longer than 150 words. Focus on the main arguments and key takeaways, avoiding personal opinions:\n\n[insert text here]",
    "Explain a concept...": "Explain [concept] in simple, accessible terms for a complete beginner, assuming no prior knowledge. Use analogies or examples to clarify complex ideas.",
    "Write an email...": "Compose a [professional, polite, formal] email to [recipient] regarding [topic]. The purpose of this email is to [specific goal, e.g., request information, confirm attendance, propose a meeting]. Include a clear call to action if necessary.",
    "Generate a caption...": "Create a concise and engaging social media caption for [image or post context]. The tone should be [e.g., humorous, inspiring, informative], and it should encourage [desired user action, e.g., likes, comments, clicks].",
    "Describe an image...": "As an objective observer, describe the key elements and overall scene depicted in the image related to [brief image description]. Focus on visual details, actions, and potential interpretations without making assumptions.",
    "Create a product pitch...": "Write a persuasive, 60-second product pitch for [product/service], specifically targeting [audience]. Highlight the core benefit, unique selling points, and a clear call to action.",
    "List pros and cons...": "Analyze [idea, decision, or product] and provide a balanced list of its top [#] pros and top [#] cons. For each point, briefly explain your reasoning."
}

personas = ["Creative Writer", "Technical Expert", "Witty Historian"]

# ============================ Initialization Functions ============================
def configure_api():
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

# ============================ Sidebar UI ============================
def render_sidebar():
    with st.sidebar:
        tab1, tab2 = st.tabs(["⚙️ Settings", "📁 Content Setup"])

        with tab1:
            st.header("Run Settings")
            temperature = st.slider('Temperature', 0.0, 1.0, 0.7)
            max_output_tokens = st.number_input('Token count', 50, 2048, 512)
            if st.button("Clear Chat Window", use_container_width=True, type="primary"):
                st.session_state.messages = []
                st.rerun()

        with tab2:
            persona = st.radio("Choose an AI persona/role", personas, index=None)
            selected_prompt = st.selectbox("Pre-defined prompt templates", list(prompt_templates.keys()))
            template_text = prompt_templates.get(selected_prompt, "")
            uploaded_images = st.file_uploader("Upload images here", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="file_uploader")
    return temperature, max_output_tokens, persona, selected_prompt, template_text, uploaded_images

# ============================ Utility Functions ============================
#function to build the prompt
def build_prompt(persona, selected_prompt, template_text):
    prompt = ""
    if persona:
        prompt = f"Act as a {persona} to "
    if template_text and selected_prompt != "Choose a template...":
        prompt += template_text
    return prompt

#function to get the news from the API
def fetch_top_news(country: str = "us", category: str = "general") -> str:
    api_key = st.secrets["NEWS_API_KEY"]
    url = 'https://newsapi.org/v2/top-headlines'
    params = {'country': country, 'category': category, 'apiKey': api_key}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("status") == "ok":
            articles = data.get("articles", [])[:5]
            headlines = [f"- {article['title']}" for article in articles if article.get('title')]
            return "\n".join(headlines) if headlines else "No headlines found."
        else:
            return f"API Error: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error occurred: {e}"

# ============================ Chat Functions ============================
def display_chat_history():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("image") and msg["role"] == "user":
                st.image(msg["image"], width=200)

def handle_user_input(model, uploaded_images):
    if prompt := st.chat_input("Type your message here..."):
        if prompt.strip() == "":
            st.warning("Prompt can't be empty.")
            return

        image = Image.open(uploaded_images[0]) if uploaded_images else None
        user_msg = {"role": "user", "content": prompt}
        if image:
            user_msg["image"] = image
        st.session_state.messages.append(user_msg)

        with st.chat_message("user"):
            st.markdown(prompt)
            if image:
                st.image(image, width=200)

        with st.chat_message("assistant"):
            with st.status("🔍 Step 1: Understanding the request...", expanded=True) as status1:
                step1_prompt = f"Break this task down into subtasks or steps: {prompt}"
                step1_output = model.generate_content(step1_prompt).text
                st.markdown(f"**Step 1 Output:**\n{step1_output}")
                status1.update(label="✅ Step 1 Complete", state="complete")

        with st.chat_message("assistant"):
            with st.status("📝 Step 2: Executing the task...", expanded=True) as status2:
                step2_prompt = f"Now, perform these steps sequentially and provide the final answer: {step1_output}"
                step2_output = ""
                container = st.empty()
                stream = model.generate_content(step2_prompt, stream=True)
                for chunk in stream:
                    if chunk.text:
                        step2_output += chunk.text
                        container.markdown(step2_output)
                status2.update(label="✅ Step 2 Complete", state="complete")

        st.session_state.messages.append({"role": "assistant", "content": step2_output})

# ============================ Auto-fill prompt ============================
def autofill_prompt(current_prompt):
    if current_prompt and len(st.session_state.messages) == 0:
        escaped_prompt = current_prompt.replace('"', '\\"').replace("'", "\\'").replace("\n", "\n")
        js = f"""
        <script>
            function insertText(dummy_var_to_force_repeat_execution) {{
                var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                if (chatInput) {{
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(chatInput, "{escaped_prompt}");
                    chatInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }}
            insertText({len(st.session_state.messages)});
        </script>
        """
        components.html(js, height=0)
        if "[" in current_prompt and "]" in current_prompt:
            st.warning("Remember to replace the [placeholders] in the template with your specific values before sending.")

# ============================ Main Application ============================
def main():
    model = configure_api()
    initialize_session_state()
    st.title("AI Generator with Gemeni API")
    temperature, max_output_tokens, persona, selected_prompt, template_text, uploaded_images = render_sidebar()
    current_prompt = build_prompt(persona, selected_prompt, template_text)
    display_chat_history()
    handle_user_input(model, uploaded_images)
    autofill_prompt(current_prompt)

if __name__ == "__main__":
    main()
