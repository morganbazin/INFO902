import cv2
import numpy as np
import mediapipe as mp
import time
import math
import os
import threading
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Verrou pour s'assurer qu'une seule annonce vocale est en cours
speech_lock = threading.Lock()
last_posture_time = 0  # Temps de la dernière posture stable
STABILISATION_TIME = 2  # Temps en secondes avant d'annoncer une posture

def get_camera_index():
    """Essaie de trouver la webcam en testant plusieurs index."""
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Caméra trouvée à l'index {i}")
            cap.release()
            return i
    return 0

def angle_btn_3points(p1, p2, p3):
    """Calcule l'angle entre trois points."""
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    radians = np.arctan2(p3[1] - p2[1], p3[0] - p2[0]) - np.arctan2(p1[1] - p2[1], p1[0] - p2[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return angle if angle <= 180 else 360 - angle

def analyser_posture(landmarks):
    """Analyse la posture et détecte un squat."""
    kp = mp_pose.PoseLandmark
    angles = {}

    for (name, p1, p2, p3) in [
        ("HANCHE_GAUCHE", kp.LEFT_SHOULDER, kp.LEFT_HIP, kp.LEFT_KNEE),
        ("HANCHE_DROITE", kp.RIGHT_SHOULDER, kp.RIGHT_HIP, kp.RIGHT_KNEE),
        ("GENOUX_GAUCHE", kp.LEFT_HIP, kp.LEFT_KNEE, kp.LEFT_ANKLE),
        ("GENOUX_DROIT", kp.RIGHT_HIP, kp.RIGHT_KNEE, kp.RIGHT_ANKLE),
        ("DOS", kp.LEFT_HIP, kp.RIGHT_HIP, kp.RIGHT_SHOULDER)
    ]:
        angles[name] = angle_btn_3points(
            [landmarks[p1.value].x, landmarks[p1.value].y],
            [landmarks[p2.value].x, landmarks[p2.value].y],
            [landmarks[p3.value].x, landmarks[p3.value].y]
        )

    est_en_squat = angles["GENOUX_GAUCHE"] < 120 and angles["GENOUX_DROIT"] < 120
    posture = "Bonne posture" if angles["GENOUX_GAUCHE"] > 90 and angles["GENOUX_DROIT"] > 90 and angles["DOS"] > 140 else "Mauvaise posture"

    return est_en_squat, posture

def synthese_vocale(message):
    """Exécute la synthèse vocale dans un thread séparé avec verrouillage."""
    def _speak():
        with speech_lock:
            audio_path = "feedback.mp3"
            gTTS(text=message, lang='fr', slow=False).save(audio_path)
            play(AudioSegment.from_file(audio_path))
            os.remove(audio_path)

    threading.Thread(target=_speak, daemon=True).start()

def test_image(image, posture_state, dernier_message, last_posture_time):
    """Effectue l'analyse de posture et gère l'état avec stabilisation avant synthèse vocale."""
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    current_time = time.time()

    if results.pose_landmarks:
        squat_detecte, posture_qualite = analyser_posture(results.pose_landmarks.landmark)

        if posture_state == "debout" and squat_detecte:
            posture_state = "exercice"
        elif posture_state == "exercice":
            posture_state = "analyse"
        elif posture_state == "analyse" and not squat_detecte:
            posture_state = "debout"

        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        cv2.putText(image, f"Etat: {posture_state}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

        if posture_state == "analyse":
            cv2.putText(image, f"Posture: {posture_qualite}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if posture_qualite == "Bonne posture" else (0, 0, 255), 2, cv2.LINE_AA)

            # 🔄 Vérification de la stabilisation avant l'annonce
            if posture_qualite == dernier_message:
                if current_time - last_posture_time > STABILISATION_TIME and not speech_lock.locked():
                    synthese_vocale(f"Vous avez {posture_qualite}")
                    last_posture_time = current_time  # Mise à jour du temps de stabilisation
            else:
                last_posture_time = current_time  # Réinitialiser le temps si la posture change
                dernier_message = posture_qualite

    return image, posture_state, dernier_message, last_posture_time

def demarrer_camera():
    """Capture vidéo et analyse la posture en temps réel avec stabilisation avant synthèse vocale."""
    camera_index = get_camera_index()
    cap = cv2.VideoCapture(camera_index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 30)

    frame_count = 0
    posture_state = "debout"
    dernier_message = ""
    last_posture_time = time.time()  # Temps de stabilisation

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Erreur : Impossible de capturer l'image.")
            break

        frame_count += 1

        if frame_count % 2 == 0:  # Traite une image sur 2 pour améliorer la fluidité
            frame, posture_state, dernier_message, last_posture_time = test_image(frame, posture_state, dernier_message, last_posture_time)
            cv2.imshow("Analyse de squat", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    demarrer_camera()
