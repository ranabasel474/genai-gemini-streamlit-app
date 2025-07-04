# import libraries
import streamlit as st
import google.generativeai as genai
from PIL import Image  
import streamlit.components.v1 as components

# Configure Gemini API
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# Prompt templates
prompt_templates = {
    "Choose a template...": "",
    "Write a story...": "Write a compelling story, approximately [# of words] words, about [topic or situation]. Focus on developing [character(s)] and include a clear [plot point/conflict] and a [resolution/theme].",
    "Generate a poem...": "Compose a lyrical poem, at least 4 stanzas, about [emotion, place, or person]. Incorporate [specific poetic device, e.g., metaphor, alliteration] and evoke a sense of [mood or atmosphere].",
    "Summarize text...": "Read the following text and provide a concise, objective summary, no longer than 150 words. Focus on the main arguments and key takeaways, avoiding personal opinions:\n\n[insert text here]",
    "Explain a concept...": "Explain [concept] in simple, accessible terms for a complete beginner, assuming no prior knowledge. Use analogies or examples to clarify complex ideas.",
    "Write an email...": "Compose a [professional, polite, formal] email to [recipient] regarding [topic]. The purpose of this email is to [specific goal, e.g., request information, confirm attendance, propose a meeting]. Include a clear call to action if necessary.",
    "Generate a caption...": "Create a concise and engaging social media caption for [image or post context]. The tone should be [e.g., humorous, inspiring, informative], and it should encourage [desired user action, e.g., likes, comments, clicks].",
    "Describe an image...": "As an objective observer, describe the key elements and overall scene depicted in the image related to [brief image description]. Focus on visual details, actions, and potential interpretations without making assumptions.",
    "Create a product pitch...": "Write a persuasive, 60-second product pitch for [product/service], specifically targeting [audience]. Highlight the core benefit, unique selling points, and a clear call to action.",
    "List pros and cons...": "Analyze [idea, decision, or product] and provide a balanced list of its top [#] pros and top [#] cons. For each point, briefly explain your reasoning."
}
personas = ["Creative Writer", "Technical Expert", "Witty Historian"]

# ============================ Sidebar settings ============================
with st.sidebar:
    st.header("Run Settings")

    temperature = st.sidebar.slider('Temperature', 0.0, 1.0, 0.7)
    st.caption('Temperature adjusts the randomness of the output.')

    max_output_tokens = st.number_input('Token count', 50, 2048, 512)

    persona = st.radio(
        "Choose an AI persona/role",
        personas,
        index=None,
    )

    selected_prompt = st.selectbox("Pre-defined prompt templates", list(prompt_templates.keys()))
    template_text = prompt_templates.get(selected_prompt, "")

    if st.button("Clear Chat Window", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

st.title("AI Generator")
# ============================ Build Current Prompt ============================
current_prompt = ""
has_image_template = False

if persona:
    current_prompt = f"Act as a {persona} to  "


if current_prompt and "[" in current_prompt and "]" in current_prompt:
    st.warning("Remember to replace the [placeholders] in the template with your specific values before sending.")

# ============================ Chat Area ============================
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("image") and msg["role"] == "user":
            st.image(msg["image"], width=200)

# Chat input with file attachment
chat_container = st.container()
with chat_container:
    uploaded_files = st.file_uploader(
        "Upload images",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed"
    )
    
    if prompt := st.chat_input("Type your message here..."):
        if prompt.strip() == "":
            st.warning("Prompt can't be empty, please enter a message.")
        else:
            # Process uploaded images
            image = None
            if uploaded_files:
                # Use the first image
                image = Image.open(uploaded_files[0])
            
            # Show user's message
            message_data = {"role": "user", "content": prompt}
            if image:
                message_data["image"] = image
            
            st.session_state.messages.append(message_data)
            
            with st.chat_message("user"):
                st.markdown(prompt)
                if image:
                    st.image(image, width=200)
            
            # Generate and show AI response
            with st.chat_message("assistant"):
                with st.spinner("Generating..."):
                    try:
                        if image:
                            response = model.generate_content(
                                [prompt, image],
                                generation_config={
                                    "temperature": temperature,
                                    "max_output_tokens": max_output_tokens
                                }
                            )
                        else:
                            response = model.generate_content(
                                prompt,
                                generation_config={
                                    "temperature": temperature,
                                    "max_output_tokens": max_output_tokens
                                }
                            )
                        
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"Error: {e}")

# JavaScript to insert prompt into chat input
if current_prompt:
    # Escape quotes in the prompt for JavaScript
    escaped_prompt = current_prompt.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
    
    js = f"""
    <script>
        function insertText(dummy_var_to_force_repeat_execution) {{
            var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {{
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeInputValueSetter.call(chatInput, "{escaped_prompt}");
                var event = new Event('input', {{ bubbles: true}});
                chatInput.dispatchEvent(event);
            }}
        }}
        insertText({len(st.session_state.messages)});
    </script>
    """
    components.html(js, height=0)