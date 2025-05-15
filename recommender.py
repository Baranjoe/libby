# recommender.py

# Bibliotheken importieren
import pandas as pd  # für Datenmanipulation und Tabellen
import ast  # um Zeichenketten in Listen (z.B. aus CSV) umzuwandeln
import numpy as np  # für numerische Operationen (z.B. Matrizen)
from collections import Counter  # zählt wie oft ein Wert in einer Liste vorkommt
import requests
import streamlit as st

# Modell zur Umwandlung von Texten in Vektoren
from sklearn.metrics.pairwise import cosine_similarity  # misst Ähnlichkeit zwischen Vektoren
from sentence_transformers import SentenceTransformer  # Modell für sogenannte "Sentence Embeddings"

# Ein kleines, aber effektives Modell zur Umwandlung von Texten in Zahlenvektoren
@st.cache_resource
def load_model():
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

model = load_model()

# Datensätze laden
books_df = pd.read_csv("./00_data/filtered_books.csv")  # enthält Buchdaten (Titel, Autor, Beschreibung usw.)'isbn13
books_df['isbn13'] = books_df['isbn13'].astype(int)  ## WICHTIG
books_df = books_df.reset_index(drop=True)
user_df = pd.read_csv("./00_data/synthetic_user_reads_seengen.csv")  # simulierte Nutzer-Buchdaten

# Die Bücherlisten in der User-Datei liegen als Text vor, müssen also zuerst in echte Listen umgewandelt werden
user_df["books"] = user_df["books"].apply(ast.literal_eval)  ## WICHTIG

# Bücher aus user_df entfernen, die nicht im Datensatz sind
valid_isbns = set(books_df['isbn13'].tolist())
user_df["books"] = user_df["books"].apply(
    lambda books: [int(float(b)) for b in books if int(float(b)) in valid_isbns]
)

# Vorgefertigte Dateien laden, um Berechnungen zu beschleunigen
book_embeddings = np.load("./00_data/book_embeddings.npy")  # enthält Vektoren für alle Bücher


# --------------------------
# HILFSFUNKTIONEN
# --------------------------

# Sucht den Index eines Buches in der Tabelle anhand des Titels
def get_book_index_by_title(title: str):
    # Erst exakte Übereinstimmung
    exact_matches = books_df[books_df["title"].str.lower() == title.lower()]
    if not exact_matches.empty:
        return exact_matches.index[0]

    # Sonst: enthält (teilweise Übereinstimmung)
    partial_matches = books_df[books_df["title"].str.contains(title, case=False, na=False)]
    if not partial_matches.empty:
        return partial_matches.index[0]

    # Wenn nichts gefunden
    return None


# Gibt alle Buchinformationen zu einer bestimmten ISBN-Nummer zurück
def get_book_by_isbn(isbn):
    return books_df[books_df["isbn13"] == isbn].to_dict(orient="records")


# Prüft, ob ein Buch mit einem bestimmten Titel in der Datenbank vorhanden ist
def is_book_in_library(title: str):
    matches = books_df[books_df["title"].str.lower().str.contains(title.lower(), na=False)]
    if not matches.empty:
        books = []
        for _, book in matches.iterrows():
            books.append({
                "isbn13": book["isbn13"] if pd.notna(book["isbn13"]) else "unbekannt",
                "medium_id": book["medium_id"],
                "title": book["title"],
                "authors": book["author_list"],
                "bildlink": book["bildlink"],
                "description": book["description"]
            })
        return {"exists": True, "results": books}
    return {"exists": False, "results": []}


# --------------------------
# FUNKTION 1: Ähnliche Bücher finden
# --------------------------

# Findet Bücher, die inhaltlich einem gegebenen Titel ähneln
def find_similar_books_by_title(title: str, top_n: int = 5):
    print(f"🔎 Searching similar books for title: {title}")
    try:
        idx = get_book_index_by_title(title)
        if idx is None:
            print(f"❌ No book found with title '{title}'")
            return [{"error": f"No book found with title '{title}'."}]

        print(f"✅ Found book index: {idx}")
        query_emb = book_embeddings[idx].reshape(1, -1)
        print(f"✅ Query embedding shape: {query_emb.shape}")

        similarities = cosine_similarity(query_emb, book_embeddings).flatten()
        print(f"✅ Similarity scores calculated. Shape: {similarities.shape}")

        # Top-N ähnliche (ohne sich selbst)
        top_idxs = similarities.argsort()[-(top_n + 1):][::-1]
        top_idxs = [i for i in top_idxs if i != idx][:top_n]
        print(f"✅ Top indices: {top_idxs}")

        results = books_df.iloc[top_idxs][["isbn13", "medium_id", "title", "description", "author_list"]].copy()
        results["similarity_score"] = similarities[top_idxs]
        print(f"✅ Results found: {results.shape[0]} books")
        return results.to_dict(orient="records")
    except Exception as e:
        print(f"❌ ERROR in find_similar_books_by_title: {e}")
        return []


# --------------------------
# FUNKTION 1B: Keyword-Suche
# --------------------------

# Findet Bücher basierend auf eingegebenen Stichwörtern (z.B. "magic school")
def find_books_by_keyword(keywords: str, top_n: int = 5):
    print(f'KWS: {keywords}')
    try:
        print("Step 1: Encoding keywords...")
        user_emb = model.encode([keywords])
        print("Step 2: Calculating similarities...")
        similarities = cosine_similarity(user_emb, book_embeddings).flatten()
        print("Step 3: Sorting results...")
        top_idxs = similarities.argsort()[-top_n:][::-1]
        results = books_df.iloc[top_idxs][["isbn13", "medium_id", "title", "author_list", "bildlink"]].copy()
        results["similarity_score"] = similarities[top_idxs]
        print(f'RES: {results.to_dict(orient="records")}')
        return results.to_dict(orient="records")
    except Exception as e:
        print(f"❌ ERROR in find_books_by_keyword: {e}")
        return []


# --------------------------
# FUNKTION 2: Co-Reads (gemeinschaftlich gelesene Bücher)
# --------------------------

# Empfiehlt Bücher, die von denselben Nutzern wie ein bestimmtes Buch gelesen wurden
def recommend_by_shared_reads(isbn: str, top_n: int = 5):
    isbn = int(isbn)

    #print('Suche für: ', isbn)
    # Filtere Nutzer, die dieses Buch gelesen haben
    #relevant_users = user_df[user_df["books"].apply(lambda books: isbn in books)]
    relevant_users = user_df[user_df["books"].apply(lambda books: isinstance(books, list) and isbn in books)]

    #print('relevant_users')
    #print(relevant_users)


    # Sammle alle anderen Bücher, die diese Nutzer auch gelesen haben
    co_read = []
    for books in relevant_users["books"]:
        co_read.extend([b for b in books if b != isbn])

    if not co_read:
        return [{"info": "No Co-Reads found."}]

    # Zähle, welche Bücher am häufigsten gemeinsam gelesen wurden
    counts = Counter(co_read).most_common(top_n)
    isbns = [int(b) for b, _ in counts]

    #print('isbns')
    #print(isbns)

    # Hole Infos zu den meistgelesenen gemeinsamen Büchern
    result = books_df[books_df["isbn13"].isin(isbns)][["isbn13", "medium_id", "title", "author_list"]].copy()
    result["co_read_count"] = result["isbn13"].map(dict(counts))
    return result.sort_values("co_read_count", ascending=False).to_dict(orient="records")


# --------------------------
# FUNKTION 3: Autorensuche
# --------------------------

# Findet Bücher basierend auf einem eingegebenen Autorennamen
def find_books_by_author(author: str, top_n: int = 5):
    # Vor- und Nachnamen extrahieren
    parts = author.lower().split()
    if len(parts) < 2:
        print("Bitte vollständigen Namen (Vorname Nachname) angeben.")
        return [{"info": "Ungültiger Autorenname."}]

    first_name, last_name = parts[0], parts[1]

    # Beide Namen müssen im String vorkommen
    matches = books_df[
        books_df["author_list"].str.lower().str.contains(first_name) &
        books_df["author_list"].str.lower().str.contains(last_name)
        ]

    if matches.empty:
        return [{"info": f"No match for author '{author}'."}]

    matches = matches[["medium_id", "isbn13", "title", "author_list", "bildlink"]].head(top_n)
    return matches.to_dict(orient="records")


# --------------------------
# FUNKTION 4: verfügbare Bücher
# --------------------------

# Findet Verfügbarkeitsstatus eines Buches
def scrape_verfuegbarkeit(medium_id):

    url = f"https://seengen.biblioweb.ch/medium/status/{medium_id}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.post(url, headers=headers, timeout=5)
        response.raise_for_status()

        status_data = response.json()
        status_text = status_data["ausleihstatus"]["status"]
        return status_text

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Fehler bei medium_id {medium_id}: {e}")
        return None
# --------------------------
