# -*- coding: utf-8 -*-

import cv2
import numpy as np
import mediapipe as mp
from pydub import AudioSegment
from pydub.playback import play
import threading
import requests
import time

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

son_en_cours = threading.Event()
dernier_envoi = 0

def get_camera_index():
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.release()
            return i
    return 0

def angle_btn_3points(p1, p2, p3):
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
    angle = np.abs(radians*180.0/np.pi)
    return angle if angle <= 180 else 360-angle

def dos_est_droit(angle_dos, seuil=140):
    return angle_dos > seuil

def exercice_commence(angle_genou_gauche, angle_genou_droit, seuil=150):
    return angle_genou_gauche < seuil and angle_genou_droit < seuil

def jouer_bip():
    if not son_en_cours.is_set():
        son_en_cours.set()
        def jouer():
            play(AudioSegment.from_file("buzzer.mp3"))
            son_en_cours.clear()
        threading.Thread(target=jouer, daemon=True).start()

def envoyer_requetes():
    global dernier_envoi
    temps_actuel = time.time()
    if temps_actuel - dernier_envoi > 2:  # Limite à une fois toutes les 2 secondes
        dernier_envoi = temps_actuel
        def requetes():
            try:
                requests.get("http://192.168.4.100/erreurmvt", timeout=0.5)
                requests.get("http://192.168.4.1/erreursquat", timeout=0.5)
            except requests.RequestException as e:
                print("Erreur lors de l'envoi des requêtes :", e)
        threading.Thread(target=requetes, daemon=True).start()

def analyser_posture(landmarks):
    kp = mp_pose.PoseLandmark

    milieu_epaules = [
        (landmarks[kp.LEFT_SHOULDER.value].x + landmarks[kp.RIGHT_SHOULDER.value].x) / 2,
        (landmarks[kp.LEFT_SHOULDER.value].y + landmarks[kp.RIGHT_SHOULDER.value].y) / 2
    ]

    milieu_hanches = [
        (landmarks[kp.LEFT_HIP.value].x + landmarks[kp.RIGHT_HIP.value].x) / 2,
        (landmarks[kp.LEFT_HIP.value].y + landmarks[kp.RIGHT_HIP.value].y) / 2
    ]

    angle_dos = angle_btn_3points(
        milieu_hanches,
        milieu_epaules,
        [landmarks[kp.NOSE.value].x, landmarks[kp.NOSE.value].y]
    )

    print(f"Angle du dos actuel : {angle_dos:.2f}")

    dos_droit = dos_est_droit(angle_dos)

    if not dos_droit:
        jouer_bip()
        envoyer_requetes()

    return "True" if dos_droit else "False"

def test_image(image):
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    try:
        landmarks = results.pose_landmarks.landmark

        genou_gauche = angle_btn_3points(
            [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y],
            [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y],
            [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        )

        genou_droit = angle_btn_3points(
            [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y],
            [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y],
            [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        )

        if exercice_commence(genou_gauche, genou_droit):
            status = analyser_posture(landmarks)
            texte = f"Dos droit : {status}"
            couleur = (0,255,0) if status=="True" else (0,0,255)
        else:
            texte = "En attente de flexion"
            couleur = (255,255,0)

        mp_drawing.draw_landmarks(
            image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0,255,255), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(255,255,0), thickness=2, circle_radius=2)
        )

        cv2.putText(image, texte, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1, couleur, 2)

    except:
        pass

    return image

def demarrer_camera():
    camera_index = get_camera_index()
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        output = test_image(frame)
        cv2.imshow("Analyse de la posture du dos", output)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    demarrer_camera()
