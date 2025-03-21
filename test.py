import cv2

cap = cv2.VideoCapture(0)  # Essaye 0, 1, ou 2 si plusieurs caméras

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Erreur : Impossible de capturer l'image.")
        break

    cv2.imshow('Webcam Test', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):  # Quitter avec 'q'
        break

cap.release()
cv2.destroyAllWindows()
