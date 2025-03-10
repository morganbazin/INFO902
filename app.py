from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import mediapipe as mp
from gtts import gTTS
from playsound import playsound
import os
import math

app = Flask(__name__)

# Configuration CORS pour accepter les requêtes de l'application front-end
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]}}, supports_credentials=True)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

def calculer_angle(a, b, c):
    """Calcule l'angle entre trois points."""
    vecteur_ab = np.array([b.x - a.x, b.y - a.y])
    vecteur_bc = np.array([c.x - b.x, c.y - b.y])

    produit_scalaire = np.dot(vecteur_ab, vecteur_bc)
    norme_ab = np.linalg.norm(vecteur_ab)
    norme_bc = np.linalg.norm(vecteur_bc)

    if norme_ab == 0 or norme_bc == 0:
        return None  # Évite la division par zéro

    cos_theta = produit_scalaire / (norme_ab * norme_bc)
    angle = math.degrees(math.acos(np.clip(cos_theta, -1.0, 1.0)))
    return angle

def analyser_posture(image):
    """Analyse la posture pour un squat."""
    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if not results.pose_landmarks:
        return "Posture non détectée, essaie de te placer bien face à la caméra."

    landmarks = results.pose_landmarks.landmark

    shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]

    # Calcul de l'angle dos-hanche-genou
    angle_dos = calculer_angle(shoulder, hip, knee)

    if angle_dos is None:
        return "Impossible de détecter l'angle correctement."

    # Définition des seuils ajustés pour un squat correct
    print(f"Angle détecté: {angle_dos:.2f}°")

    if angle_dos > 100:  # Trop droit
        message = "Incline-toi légèrement vers l'avant pour un squat plus efficace."
    elif 85 <= angle_dos <= 100:  # Squat optimal
        message = "Bonne posture, continue comme ça !"
    else:  # Trop courbé
        message = "Attention, ton dos est trop courbé, redresse-toi légèrement."

    print(f"Résultat : {message}")

    # Synthèse vocale pour donner un retour audio
    audio = gTTS(text=message, lang='fr', slow=False)
    audio_path = "feedback.mp3"
    audio.save(audio_path)
    playsound(audio_path)
    os.remove(audio_path)

    return message

@app.route('/upload', methods=['POST'])
def upload_image():
    """Traite une image envoyée et analyse la posture."""
    if not request.data:
        return jsonify({"error": "Aucune image reçue"}), 400

    img_data = np.frombuffer(request.data, np.uint8)
    frame = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"error": "Image invalide"}), 400

    message = analyser_posture(frame)
    return jsonify({"message": message}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5675, debug=True)
