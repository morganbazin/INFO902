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
lock = threading.Lock()  # Verrou pour synchroniser l'accès à l'exercice

def get_db():
    conn = sqlite3.connect('exercises.db')
    conn.text_factory = str  # Set text_factory to str to support Unicode
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
    uid = str(uid)  # Ensure the UID is treated as a string
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
        uid = read_badge()
        if uid:
            with lock:  # Verrouiller l'accès concurrent
                if not exercise_in_progress or uid != current_uid:
                    current_uid = uid
                    exercise_in_progress = True
                    print("Exercice commencé pour le badge:", uid)
                    exercise = get_or_create_exercise(uid)
                    time.sleep(5)  # Laisser un peu de temps avant de pouvoir scanner à nouveau
                else:
                    with get_db() as db:
                        db.execute("UPDATE exercises SET end_time = CURRENT_TIMESTAMP WHERE badge_uid = ? AND end_time IS NULL", (current_uid,))
                        db.commit()
                        current_uid = None
                        exercise_in_progress = False
                        print("Exercice terminé")

@app.route('/repetition', methods=['GET'])
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

@app.route('/erreurmvt', methods=['GET'])
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


@app.route('/', methods=['GET'])
def home():
    # Serve the frontend with the form to input the badge UID
    return """
    <html>
        <body>
            <h1>Page d'Exercices NFC</h1>
            <form action="/badge" method="POST" id="badgeForm">
                <input type="text" name="badge_uid" placeholder="Numéro de badge" required>
                <button type="submit">Soumettre</button>
            </form>
            <div id="exerciseDetails"></div>
            <script>
                // Fetch form data when submitted and display the result
                document.getElementById("badgeForm").addEventListener("submit", async function(event) {
                    event.preventDefault();
                    let formData = new FormData(this);
                    let response = await fetch("/badge", {
                        method: "POST",
                        body: formData
                    });
                    let result = await response.json();
                    displayExercise(result);
                });

                function displayExercise(data) {
                    const detailsDiv = document.getElementById("exerciseDetails");
                    if (data.error) {
                        detailsDiv.innerHTML = "<p>" + data.error + "</p>";
                    } else {
                        detailsDiv.innerHTML = `
                            <h3>Exercice pour le badge ${data.badge_uid}</h3>
                            <table border="1">
                                <tr>
                                    <th>ID</th>
                                    <th>Répétitions</th>
                                    <th>Erreurs</th>
                                    <th>Début</th>
                                    <th>Fin</th>
                                </tr>
                                <tr>
                                    <td>${data.exercise[0]}</td>
                                    <td>${data.exercise[2]}</td>
                                    <td>${data.exercise[3]}</td>
                                    <td>${data.exercise[4]}</td>
                                    <td>${data.exercise[5]}</td>
                                </tr>
                            </table>
                        `;
                    }
                }
            </script>
        </body>
    </html>
    """


@app.route('/badge', methods=['POST'])
def handle_badge():
    badge_uid = request.form['badge_uid']
    
    with get_db() as db:
        cursor = db.execute("SELECT * FROM exercises WHERE badge_uid = ?", (badge_uid,))
        exercise = cursor.fetchone()

    if exercise:
        return jsonify({
            "badge_uid": badge_uid,
            "exercise": exercise
        })
    else:
        return jsonify({
            "error": f"Aucun exercice trouvé pour le badge {badge_uid}"
        })


# Initialisation de la base de données
init_db()

# Lancer un thread pour l'écoute des badges
thread = threading.Thread(target=listen_for_badges)
thread.setDaemon(True)  # Manually set the thread as a daemon
thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
