import streamlit as st
import pandas as pd
import requests
from chat_engine import handle_user_message, ChatMemory
import re
import ast

# --------------------------
# Setup
# --------------------------
st.set_page_config(page_title="Libby - Deine Bibliothekarin", page_icon="📚", layout="centered")

AVATAR_PATH = "./static/avatar.png"
LOGO_PATH = "./static/logo.png"

books_df = pd.read_csv("./00_data/filtered_books.csv")
books_df['isbn13'] = books_df['isbn13'].astype(int)
books_df["author_list"] = books_df["author_list"].apply(ast.literal_eval)

# --------------------------
# Helpers
# --------------------------
def scrape_verfuegbarkeit(medium_id):
    url = f"https://seengen.biblioweb.ch/medium/status/{medium_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.post(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()["ausleihstatus"]["status"]
    except Exception:
        return "Unbekannt"

def get_availability_label(status):
    status_lower = status.lower()
    if "ja" in status_lower or "vorrätig" in status_lower:
        return f'<span style="color:green;font-weight:bold;">✅ {status}</span>'
    elif "reserviert" in status_lower:
        return f'<span style="color:orange;font-weight:bold;">⏳ {status}</span>'
    else:
        return f'<span style="color:red;font-weight:bold;">❌ {status}</span>'

def extract_ids_from_last_line(text):
    lines = text.strip().split("\n")
    last_line = lines[-1]
    match = re.search(r"\[(.*?)\]", last_line)
    if match:
        ids_str = match.group(1)
        ids = list({int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()})
        clean_text = "\n".join(lines[:-1]).strip()
        return ids, clean_text
    return [], text

def shorten_text(text, word_limit=50):
    words = text.split()
    if len(words) <= word_limit:
        return text
    return " ".join(words[:word_limit]) + "..."

def show_book_card(book, availability):
    availability_html = get_availability_label(availability)
    authors = ", ".join(book.get("author_list", []))
    description = shorten_text(book.get("description", "Keine Beschreibung"))
    recommendation = book.get("bot_recommendation", "")
    img_url = book.get("bildlink") if book.get("bildlink") else AVATAR_PATH

    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(img_url, width=100)
        with col2:
            st.markdown(f"### {book.get('title', 'Kein Titel')}")
            st.markdown(f"👤 {authors}")
            st.markdown(f"🏷️ {book.get('categories', 'Genre unbekannt')}")
            st.markdown(description)
            st.markdown(availability_html, unsafe_allow_html=True)
            if recommendation:
                st.info(f"💡 **Meine Empfehlung:** {recommendation}")

# --------------------------
# Streamlit App Layout
# --------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #f0f4f8;
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True
)

# --------------------------
# Header: zentrales Logo
# --------------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(LOGO_PATH, width=250)

# --------------------------
# Libby-Avatar + Titel nebeneinander
# --------------------------
avatar_col, title_col = st.columns([1, 4])
with avatar_col:
    st.image(AVATAR_PATH, width=120)
with title_col:
    st.markdown("<h1 style='color: #0000ee;'>Libby - Deine virtuelle Bibliothekarin</h1>", unsafe_allow_html=True)

# --------------------------
# Chat + Karten
# --------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "memory" not in st.session_state:
    st.session_state.memory = ChatMemory()

for user_msg, bot_response in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(user_msg)
    with st.chat_message("assistant"):
        if isinstance(bot_response, str):
            ids, cleaned_text = extract_ids_from_last_line(bot_response)
            st.markdown(cleaned_text)
            if ids:
                books = books_df[books_df["medium_id"].isin(ids)].to_dict(orient="records")
                for book in books:
                    availability = scrape_verfuegbarkeit(book["medium_id"])
                    show_book_card(book, availability)
        elif isinstance(bot_response, list):
            for book in bot_response:
                medium_id = book.get("medium_id")
                if not medium_id and book.get("isbn13"):
                    row = books_df[books_df['isbn13'] == int(book["isbn13"])]
                    if not row.empty:
                        medium_id = int(row["medium_id"].values[0])
                availability = scrape_verfuegbarkeit(medium_id) if medium_id else "Unbekannt"
                show_book_card(book, availability)

# --------------------------
# Chat Input
# --------------------------
user_input = st.chat_input("Was möchtest du lesen?")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Libby sucht... 📚"):
            response = handle_user_message(user_input, st.session_state.memory)

        if isinstance(response, str):
            ids, cleaned_text = extract_ids_from_last_line(response)
            st.markdown(cleaned_text)
            if ids:
                books = books_df[books_df["medium_id"].isin(ids)].to_dict(orient="records")
                for book in books:
                    availability = scrape_verfuegbarkeit(book["medium_id"])
                    show_book_card(book, availability)
        elif isinstance(response, list):
            for book in response:
                medium_id = book.get("medium_id")
                if not medium_id and book.get("isbn13"):
                    row = books_df[books_df['isbn13'] == int(book["isbn13"])]
                    if not row.empty:
                        medium_id = int(row["medium_id"].values[0])
                availability = scrape_verfuegbarkeit(medium_id) if medium_id else "Unbekannt"
                show_book_card(book, availability)

        st.session_state.chat_history.append((user_input, response))
