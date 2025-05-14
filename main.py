# main.py

# Importiere die zentrale Chatlogik und das Gedächtnisobjekt
from chat_engine import handle_user_message, ChatMemory

# Erstelle ein neues Speicherobjekt für den Verlauf des Gesprächs
memory = ChatMemory()

# Begrüssungstext in der Konsole
print("📚 Welcome to BookBot! Type 'exit' to quit.\n")

# Starte die Endlosschleife für den Dialog
while True:
    # Frage den/die Nutzer:in nach einer Eingabe
    user_input = input("You: ")

    # Wenn Benutzer "exit" oder "quit" eingibt → Programm beenden
    if user_input.lower() in ["exit", "quit"]:
        break

    # Übergib die Eingabe an den Chatbot (GPT + Tools)
    response = handle_user_message(user_input, memory)

    # Gib die Antwort des Bots aus
    print('\n\n========== FINAL RESPONSE ==========\n')
    print(f"\nBookBot: {response}\n")
