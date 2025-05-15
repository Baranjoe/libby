# chat_engine.py

# Dieses Modul ist das „Gehirn“ deines Buch-Chatbots:
# Es verbindet Nutzereingaben mit GPT-4, führt bei Bedarf Python-Funktionen aus
# und verwaltet den Dialogverlauf.

from IPython.display import Image, display
import json  # Für das Umwandeln von Funktionsargumenten und Ergebnissen
from openai import OpenAI  # Die OpenAI-Schnittstelle zum Kommunizieren mit GPT-Modellen
from tools import tools  # Liste der verfügbaren „Werkzeuge“, also Funktionen, die GPT aufrufen darf
from dotenv import load_dotenv
import streamlit as st
from recommender import (
    find_similar_books_by_title,
    recommend_by_shared_reads,
    find_books_by_author,
    find_books_by_keyword,
    is_book_in_library,
)

import os



# Verbindung zum OpenAI-Client herstellen
# load_dotenv()
client = OpenAI(api_key=st.secrets["openai_api_key"])

# --------------------------------------
# Gedächtnisobjekt für den Chatverlauf
# --------------------------------------
class ChatMemory:
    def __init__(self):
        self.last_book_title = None  # Zuletzt angefragter Buchtitel
        self.last_book_info = None   # Metadaten des zuletzt gefundenen Buchs
        self.last_tool_used = None   # Name des zuletzt genutzten Werkzeugs/Funktion
        self.message_history = []    # Alle Nachrichten der Unterhaltung: User, GPT, Tool-Ergebnisse

# --------------------------------------
# Zuordnung Funktionsname → Python-Funktion
# --------------------------------------
function_map = {
    "find_similar_books_by_title": find_similar_books_by_title,
    "recommend_by_shared_reads": recommend_by_shared_reads,
    "find_books_by_author": find_books_by_author,
    "find_books_by_keyword": find_books_by_keyword,
    "is_book_in_library": is_book_in_library,
}

# --------------------------------------
# Hauptfunktion für jede Nutzereingabe
# --------------------------------------
def handle_user_message(user_input: str, memory: ChatMemory):
    """
    Diese Funktion verarbeitet jede neue Eingabe eines Users.
    GPT entscheidet, ob es direkt antwortet oder zunächst eine interne Funktion aufruft.
    Wird eine Funktion aufgerufen, führen wir sie lokal aus und geben das Ergebnis an GPT zurück.
    GPT kann dann mit dem Ergebnis eine passende Antwort generieren.

    Dieser Zyklus wiederholt sich, bis GPT eine finale Antwort gibt (ohne weiteren Funktionsaufruf).
    """

    print("\n🟡 [User Input]")
    print(user_input)

    # 1. Nachricht des Users zum Verlauf hinzufügen
    memory.message_history.append({"role": "user", "content": user_input})

    while True:
        # 2. Nachrichtenverlauf für GPT vorbereiten
        messages = [
            {
                "role": "system",
                "content": (
                    """
                    You are a helpful virtual librarian assistant for a German library. 
                    Always answer the user fluently in German, but use the defined internal function names in English.
                
                    When a user mentions a book by title:
                    1. **Check if the book exists in the library**:
                    - Use 'is_book_in_library' to retrieve one or more matches with ISBN, medium_id and metadata. 
                    - If multiple books are returned (e.g. a series or multiple editions), they will be found inside the 'results' list.
                
                    2. **Make personalized recommendations**:
                    - If the user asks for similar books, use 'find_similar_books_by_title' with the title, 
                      or if you already have the ISBN, use 'recommend_by_shared_reads' in addition.
                    - If you used both functions 'find_similar_books_by_title' and 'recommend_by_shared_reads' 
                      make sure to reference the results of both calls in your reply.
                    - If the user does not mention a specific book but describes what they want to read (e.g. genre, topics, type of story), 
                      use 'find_books_by_keyword' with the full natural language query.
                      
                    3. **Format the response clearly**:
                    - Always formulate a polite and informative response for the user in fluent German, as if you were a friendly librarian giving personal advice.
                    - Always try to refer to the user’s original question or request, so the answer feels natural and personal.
                    - Write a short natural text that recommends between 3 and 5 suitable books from the found results. Do NOT mention more than 5 books.
                    - You do not need to mention every book or give detailed lists. Focus only on the books that seem most relevant for the user request.
                    - For each book, mention title and author(s). Optionally, add a very short description or a brief comment why the book fits well.
                    - Do NOT list the books as numbered lists. Present them in a natural flowing text as a librarian would talk to a visitor.
                    - The response should feel personal and human, not like a database output.
                    - As the very last line of your response, output ONLY the list of medium_ids of the recommended books as plain Python list format, e.g. [12345, 67896].
                    - Do NOT add any introduction, explanation, or extra words before or after the list. Only the list itself.
                    """
                )
            },
            *memory.message_history
        ]

        # 3. Anfrage an GPT senden
        print("\n📤 [Sending to GPT]")
        response = client.chat.completions.create(
            model="gpt-4.1",        # GPT-4 mit Funktionsaufruf-Fähigkeit
            messages=messages,      # Der komplette Verlauf
            tools=tools,            # Welche Funktionen darf GPT nutzen
            tool_choice="auto"      # GPT entscheidet selbst, ob/wann es eine Funktion braucht
        )

        # 4. GPT gibt eine Antwort zurück (entweder Text oder Tool-Call)
        assistant_msg = response.choices[0].message
        memory.message_history.append(assistant_msg)

        # 5. Wenn es eine reine Textantwort ist → fertig
        if not assistant_msg.tool_calls:
            print("\n✅ [GPT returned final text answer]")
            print("Answer:", assistant_msg.content)
            return assistant_msg.content

        # 6. GPT möchte eine oder mehrere Funktionen aufrufen
        tool_calls = assistant_msg.tool_calls
        print(f"\n🔧 [GPT made {len(tool_calls)} function call(s)]")

        new_messages = []

        # 7. Alle gewünschten Funktionen nacheinander ausführen
        for tc in tool_calls:
            call_id = tc.id
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)  # JSON → Python-Daten

            print(f"   ↳ Calling {func_name} with {func_args}")

            # 8. Funktion lokal aufrufen
            py_func = function_map.get(func_name)
            if not py_func:
                result_data = {"error": f"Unknown function: {func_name}"}
            else:
                try:
                    result_data = py_func(**func_args)

                    print('Tool response:')
                    print(result_data)

                    # Speichere ggf. Infos über das zuletzt angefragte Buch
                    if func_name == "is_book_in_library" and result_data.get("exists"):
                        # Wenn mehrere Bücher, nimm das erste als Referenz
                        first_book = result_data["results"][0]
                        memory.last_book_title = first_book["title"]
                        memory.last_book_info = first_book
                except Exception as e:
                    result_data = {"error": f'Error: {str(e)}'}

            # 9. Rückgabe der Funktion für GPT aufbereiten
            tool_msg = {
                "role": "tool",
                "tool_call_id": call_id,
                "name": func_name,
                "content": json.dumps(result_data, default=str)
            }

            new_messages.append(tool_msg)

        # 10. Alle Tool-Antworten dem Chatverlauf hinzufügen
        memory.message_history.extend(new_messages)

        # GPT wird in der nächsten Runde eine endgültige Antwort geben oder weitere Tools aufrufen
