import cv2
import numpy as np
import mediapipe as mp
import time
import math
from gtts import gTTS
from playsound import playsound
import os

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

def get_camera_index():
    """Essaie de trouver la webcam interne en testant plusieurs index."""
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Caméra trouvée à l'index {i}")
            cap.release()
            return i  # Retourne le premier index valide
    return 0  # Par défaut, utiliser l'index 0

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
    """Analyse la posture pour un squat en vérifiant plusieurs critères."""
    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if not results.pose_landmarks:
        return "Posture non détectée, essaie de te placer bien face à la caméra."

    landmarks = results.pose_landmarks.landmark

    shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
    ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

    # Calcul de l'angle dos-hanche-genou
    angle_dos = calculer_angle(shoulder, hip, knee)
    # Calcul de l'angle hanche-genou-cheville
    angle_jambe = calculer_angle(hip, knee, ankle)

    if angle_dos is None or angle_jambe is None:
        return "Impossible de détecter l'angle correctement."

    print(f"Angle dos-hanche-genou : {angle_dos:.2f}° | Angle hanche-genou-cheville : {angle_jambe:.2f}°")

    # Conditions améliorées pour détecter un squat correct
    if angle_dos > 100:
        message = "Incline-toi légèrement vers l'avant pour un squat plus efficace."
    elif angle_jambe < 60:
        message = "Descends plus bas pour un squat complet."
    elif 85 <= angle_dos <= 100 and 60 <= angle_jambe <= 120:
        message = "Bonne posture, continue comme ça !"
    else:
        message = "Attention, ajuste ta position pour éviter les blessures."

    print(f"Résultat : {message}")
    return message

def synthese_vocale(message):
    """Convertit le message en audio et le joue."""
    audio = gTTS(text=message, lang='fr', slow=False)
    audio_path = "feedback.mp3"
    audio.save(audio_path)
    playsound(audio_path)
    os.remove(audio_path)

def demarrer_camera():
    """Ouvre la webcam et analyse la posture toutes les 5 secondes."""
    camera_index = get_camera_index()
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    dernier_temps = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Erreur : Impossible de capturer l'image.")
            break

        # Affichage de l'image en direct
        cv2.imshow('Analyse de squat', frame)
        
        # Vérifie si 5 secondes se sont écoulées
        if time.time() - dernier_temps >= 5:
            message = analyser_posture(frame)
            synthese_vocale(message)
            dernier_temps = time.time()

        # Quitte avec la touche 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    demarrer_camera()
