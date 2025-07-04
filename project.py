# ============================ Import Libraries ============================
import streamlit as st
import google.generativeai as genai
from PIL import Image
import streamlit.components.v1 as components
import json
import re
import requests

# ============================ Constants ============================
PERSONAS = ["Creative Writer", "Technical Expert", "Witty Historian"]
PROMPT_TEMPLATES = {
    "Choose a template...": "",
    "Write a story...": "Write a compelling story, approximately [# of words] words, about [topic or situation]. Focus on developing [character(s)] and include a clear [plot point/conflict] and a [resolution/theme].",
    "Summarize text...": "Read the following text and provide a concise, objective summary, no longer than 150 words. Focus on the main arguments and key takeaways, avoiding personal opinions:\n\n[insert text here]",
    "Explain a concept...": "Explain [concept] in simple, accessible terms for a complete beginner, assuming no prior knowledge. Use analogies or examples to clarify complex ideas.",
    "Write an email...": "Compose a [professional, polite, formal] email to [recipient] regarding [topic]. The purpose of this email is to [specific goal, e.g., request information, confirm attendance, propose a meeting]. Include a clear call to action if necessary.",
    "Generate a caption...": "Create a concise and engaging social media caption for [image or post context]. The tone should be [e.g., humorous, inspiring, informative], and it should encourage [desired user action, e.g., likes, comments, clicks].",
    "Describe an image...": "As an objective observer, describe the key elements and overall scene depicted in the image related to [brief image description]. Focus on visual details, actions, and potential interpretations without making assumptions.",
    "Create a product pitch...": "Write a persuasive, 60-second product pitch for [product/service], specifically targeting [audience]. Highlight the core benefit, unique selling points, and a clear call to action.",
    "List pros and cons...": "Analyze [idea, decision, or product] and provide a balanced list of its top [#] pros and top [#] cons. For each point, briefly explain your reasoning."
}

# ============================ Setup and Configuration ============================
# function to configure gemeni API
def configure_api():
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")
# function for the news API
def fetch_top_news(country: str = "us", category: str = "general") -> str:
    api_key = st.secrets["NEWS_API_KEY"]
    url = 'https://newsapi.org/v2/top-headlines'
    params = {'country': country, 'category': category, 'apiKey': api_key}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("status") == "ok":
            articles = data.get("articles", [])[:5]
            return "\n".join(f"- {a['title']}" for a in articles if a.get('title'))
        return f"API Error: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error occurred: {e}"

# ============================ Sidebar UI ============================
def sidebar_settings():
    with st.sidebar:
        tab1, tab2 = st.tabs(["⚙️ Settings", "📁 Content Setup"])
        with tab1:
            st.header("Run Settings")
            temp = st.slider('Temperature', 0.0, 1.0, 0.7)
            tokens = st.number_input('Token count', 50, 2048, 512)
            if st.button("Clear Chat Window", use_container_width=True, type="primary"):
                st.session_state.messages = []
                st.rerun()
        with tab2:
            persona = st.radio("Choose an AI persona/role", PERSONAS, index=None)
            selected_prompt = st.selectbox("Pre-defined prompt templates", list(PROMPT_TEMPLATES.keys()))
            template = PROMPT_TEMPLATES.get(selected_prompt, "")
            uploaded_imgs = st.file_uploader("Upload images here", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="file_uploader")
    return temp, tokens, persona, selected_prompt, template, uploaded_imgs

# ============================ Display Chat History ============================
def display_history():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("image") and msg["role"] == "user":
                st.image(msg["image"], width=200)

# ============================ Handle News Query ============================
def handle_news_query(prompt, model):
    with st.chat_message("assistant"):
        with st.status("Extracting news topic and country using Gemini...", expanded=True) as status:
            extraction_prompt = f"""Extract the country and category for news from the following request.
Respond only in JSON with two fields: "country" and "category".

User Request: {prompt}"""
            response = model.generate_content(extraction_prompt)
            try:
                match = re.search(r'\{.*?\}', response.text, re.DOTALL)
                tool_inputs = json.loads(match.group()) if match else {}
                country = tool_inputs.get("country", "us")
                category = tool_inputs.get("category", "general")
            except Exception as e:
                country, category = "us", "general"
                st.warning(f"Defaulting to US/general. Error: {e}")
            st.markdown(f"**Inputs:** Country: `{country.upper()}` | Category: `{category}`")
            status.update(label="✅ Tool inputs ready", state="complete")

    with st.chat_message("assistant"):
        with st.status("📰 Fetching news from NewsAPI...", expanded=True) as status:
            tool_result = fetch_top_news(country, category)
            st.markdown(f"**News Headlines:**\n{tool_result}")
            status.update(label="✅ News fetched", state="complete")

    with st.chat_message("assistant"):
        ai_input = f"The user asked for news in country: {country.upper()} and category: {category}. Here are the top headlines:\n\n{tool_result}\n\nPlease summarize them."
        with st.spinner("Generating response..."):
            container = st.empty()
            response_text = ""
            stream = model.generate_content(ai_input, stream=True)
            for chunk in stream:
                if chunk.text:
                    response_text += chunk.text
                    container.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})

# ============================ Regular Prompt Handler ============================
def handle_regular_prompt(prompt, model, image=None):
    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            container = st.empty()
            response_text = ""
            history = "".join(
                f"{msg['role'].capitalize()}: {msg['content']}\n"
                for msg in st.session_state.messages
            ) + f"User: {prompt}\nAssistant:"
            try:
                stream = model.generate_content([history, image], stream=True) if image else model.generate_content(history, stream=True)
                for chunk in stream:
                    if chunk.text:
                        response_text += chunk.text
                        container.markdown(response_text)
            except Exception as e:
                container.error(f"Error: {e}")
            st.session_state.messages.append({"role": "assistant", "content": response_text})

# ============================ Auto-Fill Prompt ============================
def auto_fill_prompt(current_prompt):
    if current_prompt and len(st.session_state.messages) == 0:
        escaped = current_prompt.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
        js = f"""
        <script>
            var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {{
                var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                setter.call(chatInput, "{escaped}");
                chatInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        </script>
        """
        components.html(js, height=0)
        if "[" in current_prompt and "]" in current_prompt:
            st.warning("Remember to replace the [placeholders] in the template with your specific values before sending.")

# ============================ Main App ============================
def main():
    model = configure_api()
    st.title("AI Generator with Gemini API")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    temp, tokens, persona, selected_prompt, template, uploaded_imgs = sidebar_settings()

    display_history()

    current_prompt = f"Act as a {persona} to {template}" if persona and selected_prompt != "Choose a template..." else ""

    if prompt := st.chat_input("Type your message here..."):
        if prompt.strip() == "":
            st.warning("Prompt can't be empty.")
            return

        image = Image.open(uploaded_imgs[0]) if uploaded_imgs else None
        user_msg = {"role": "user", "content": prompt}
        if image:
            user_msg["image"] = image
        st.session_state.messages.append(user_msg)

        with st.chat_message("user"):
            st.markdown(prompt)
            if image:
                st.image(image, width=200)

        if "news" in prompt.lower() or "headlines" in prompt.lower():
            handle_news_query(prompt, model)
        else:
            handle_regular_prompt(prompt, model, image)

    auto_fill_prompt(current_prompt)

# ============================ Run ============================
if __name__ == "__main__":
    main()
