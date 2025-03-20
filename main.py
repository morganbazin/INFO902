# -*- coding: utf-8 -*-

import nxppy
import time
from flask import Flask, request, jsonify
import sqlite3
import threading

app = Flask(__name__)

# Variable pour suivre si un exercice est en cours
exercise_in_progress = False
current_uid = None

def get_db():
    conn = sqlite3.connect('exercises.db')
    return conn

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS exercises (
                        id INTEGER PRIMARY KEY,
                        badge_uid TEXT,
                        repetitions INTEGER,
                        errors INTEGER,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP)''')
        db.commit()

def read_badge():
    mifare = nxppy.Mifare()
    while True:
        try:
            uid = mifare.select()  # Lire le badge NFC
            return uid
        except nxppy.SelectError:
            pass
        time.sleep(1)

# Fonction pour démarrer ou récupérer l'exercice
def get_or_create_exercise(uid):
    with get_db() as db:
        cursor = db.execute("SELECT * FROM exercises WHERE badge_uid = ? AND end_time IS NULL", (uid,))
        existing_exercise = cursor.fetchone()

        if existing_exercise:
            return existing_exercise  # Retourner l'exercice existant
        else:
            db.execute("INSERT INTO exercises (badge_uid, repetitions, errors, start_time) VALUES (?, 0, 0, CURRENT_TIMESTAMP)",
                       (uid,))
            db.commit()
            return db.execute("SELECT * FROM exercises WHERE badge_uid = ? AND end_time IS NULL", (uid,)).fetchone()

def listen_for_badges():
    global exercise_in_progress, current_uid

    while True:
        uid = read_badge()  # Lire le badge NFC pour obtenir l'UID
        if uid:
            if not exercise_in_progress or uid != current_uid:
                # Nouveau badge ou rescan d'un badge
                current_uid = uid
                exercise_in_progress = True
                print("Exercice commencé pour le badge: {}".format(uid))                # Récupérer ou créer l'exercice
                exercise = get_or_create_exercise(uid)
                time.sleep(5)
            else:
                with get_db() as db:

                    # Marquer l'exercice comme terminé pour ce badge
                    db.execute("UPDATE exercises SET end_time = CURRENT_TIMESTAMP WHERE badge_uid = ? AND end_time IS NULL", (current_uid,))
                    db.commit()
                    current_uid = None
                    exercise_in_progress = False
                    print("Exercice terminé")

@app.route('/repetition', methods=['POST'])
def add_repetition():
    global exercise_in_progress, current_uid
    if exercise_in_progress and current_uid:
        exercise = get_or_create_exercise(current_uid)  # Récupérer ou créer l'exercice
        with get_db() as db:
            db.execute("UPDATE exercises SET repetitions = repetitions + 1 WHERE id = ?", (exercise[0],))  # Mettre à jour l'exercice
            db.commit()
            print("updated repet", current_uid)

        return jsonify({"message": "Répétition ajoutée avec succès"}), 200
    return jsonify({"error": "Aucun exercice en cours ou badge non détecté"}), 400

@app.route('/erreurmvt', methods=['POST'])
def add_error():
    global exercise_in_progress, current_uid
    if exercise_in_progress and current_uid:
        exercise = get_or_create_exercise(current_uid)  # Récupérer ou créer l'exercice
        with get_db() as db:
            db.execute("UPDATE exercises SET errors = errors + 1 WHERE id = ?", (exercise[0],))  # Mettre à jour l'exercice
            db.commit()
            print("updated erreur mvt", current_uid)
        return jsonify({"message": "Erreur de mouvement ajoutée avec succès"}), 200
    return jsonify({"error": "Aucun exercice en cours ou badge non détecté"}), 400


@app.route('/')
def home():
    return """
    <html>
        <body>
            <h1>Page d'Exercices NFC</h1>
            <form action="/start_exercise" method="post">
                <button type="submit">Démarrer l'Exercice</button>
            </form>
        </body>
    </html>
    """

# Initialisation de la base de données
init_db()

# Lancer un thread pour l'écoute des badges
thread = threading.Thread(target=listen_for_badges)
thread.setDaemon(True)  # Manually set the thread as a daemon
thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
