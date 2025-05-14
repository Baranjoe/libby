# tools.py

# Dieses Skript definiert eine Liste von Werkzeugen („tools“), die extern aufgerufen werden können.
# Sie werden z.B. von einem Sprachmodell wie GPT-4 verwendet, um gezielt eine Funktion auszuführen.

tools = [
    {
        "type": "function",  # Typ: Funktion, d.h. diese Einheit ruft eine bestimmte Python-Funktion auf
        "function": {
            "name": "find_similar_books_by_title",  # Funktionsname → muss genau so im Hauptcode existieren
            "description": "Finds books that are similar to a given title based on content.",
            # Beschreibung auf Englisch → Benutzer:innen sehen diesen Text ggf. im Frontend
            "parameters": {  # Welche Eingaben die Funktion erwartet
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of a book, e.g. 'Harry Potter'"
                    }
                },
                "required": ["title"]  # Der Titel ist zwingend erforderlich
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_by_shared_reads",
            "description": (
                "Recommends books that were also read by users who read a specific book. "
                "If the user provides a book title, first use 'is_book_in_library' to get the ISBN."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "isbn": {
                        "type": "string",
                        "description": (
                            "The ISBN-13 of a book, e.g. '9780439064873'. "
                            "Obtain this from 'is_book_in_library' if the user provides a title."
                        )
                    }
                },
                "required": ["isbn"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_books_by_author",
            "description": "Finds books written by a specific author.",
            "parameters": {
                "type": "object",
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "The author's name, e.g. 'John Grisham'"
                    }
                },
                "required": ["author"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_books_by_keyword",
            "description": (
                "Finds books related to the given natural language query. "
                "The input string will be embedded and compared against the book descriptions "
                "in the library's vector database to return the most relevant results. "
                "Example: 'a legal thriller about a young lawyer in New York'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": (
                            "A natural language query describing the type of books you are looking for. "
                            "E.g. 'legal thriller with young lawyer', 'fantasy novels about dragons', etc."
                        )
                    }
                },
                "required": ["keywords"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "is_book_in_library",
            "description": (
                "Checks if one or more books with a given title exist in the dataset and returns metadata for all matches. "
                "If multiple books match the title (e.g. a series), all are returned in the 'results' list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the book to look up"
                    }
                },
                "required": ["title"]
            }
        }
    }
]
