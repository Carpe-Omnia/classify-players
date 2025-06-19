import os
import cv2 # OpenCV for image loading (DeepFace uses it internally too)
import requests
from deepface import DeepFace

# --- 1. Preparation: Install DeepFace ---
# If you haven't already, install deepface using pip:
# pip install deepface
# DeepFace will automatically download necessary models on its first run.

# --- 2. Image Acquisition (Example) ---
# For this example, we'll use a placeholder image that should reliably have a face.
dummy_image_path = "sample_player_expanded_analysis.jpg"
if not os.path.exists(dummy_image_path):
    print(f"Creating a dummy image at {dummy_image_path} for demonstration.")
    try:
        # Using a public domain image URL for a clear human human face.
        image_url = "https://upload.wikimedia.org/wikipedia/commons/8/8c/Cristiano_Ronaldo_2018.jpg" 
        img_data = requests.get(image_url).content
        with open(dummy_image_path, 'wb') as handler:
            handler.write(img_data)
        print("Dummy image created successfully.")
    except Exception as e:
        print(f"Could not create dummy image (check internet connection or requests library): {e}")
        exit("Cannot proceed without a sample image.")


# --- 3. Perform Facial Analysis ---
print(f"\nAnalyzing image: {dummy_image_path}")

try:
    # DeepFace.analyze returns a list of dictionaries, one for each face detected.
    # We now specify multiple 'actions' to tell DeepFace what attributes to analyze.
    actions_to_analyze = ['age', 'emotion'] # Changed to exclude 'gender' and 'race'
    
    demography = DeepFace.analyze(
        img_path=dummy_image_path,
        actions=actions_to_analyze,
        detector_backend='opencv', # You can experiment with other backends
        enforce_detection=False # Set to False to allow analysis even if no face is perfectly detected
    )

    if demography:
        print("\n--- Analysis Results ---")
        for face_idx, face_data in enumerate(demography):
            print(f"\nFace {face_idx + 1}:")
            
            # --- Age Analysis ---
            inferred_age = face_data.get('age')
            if inferred_age is not None:
                print(f"  Inferred Age: {inferred_age} years old")
            else:
                print("  Age inference not available.")

            # --- Gender Analysis (will not be available if not in actions_to_analyze) ---
            inferred_gender = face_data.get('gender')
            gender_confidence = face_data.get('gender_confidence')
            if inferred_gender is not None:
                print(f"  Inferred Gender: {inferred_gender} (Confidence: {gender_confidence:.2f}%)")
            else:
                print("  Gender inference not available (not requested or not found).")

            # --- Emotion Analysis ---
            emotion_probabilities = face_data.get('emotion', {})
            if emotion_probabilities:
                most_likely_emotion = max(emotion_probabilities, key=emotion_probabilities.get)
                emotion_confidence = emotion_probabilities[most_likely_emotion] * 100
                print(f"  Inferred Emotion: {most_likely_emotion.title()} (Confidence: {emotion_confidence:.2f}%)")
            else:
                print("  Emotion inference not available.")

            # --- Race Analysis (will not be available if not in actions_to_analyze) ---
            race_probabilities = face_data.get('race', {})
            if race_probabilities:
                most_likely_race = max(race_probabilities, key=race_probabilities.get)
                race_confidence = race_probabilities[most_likely_race] * 100
                print(f"  Inferred Race: {most_likely_race.title()} (Confidence: {race_confidence:.2f}%)")
            else:
                print("  Race inference not available (not requested or not found).")

            # You might also want to access the detected face region if needed
            # facial_area = face_data.get('region', {})
            # if facial_area:
            #     x, y, w, h = facial_area.get('x'), facial_area.get('y'), facial_area.get('w'), facial_area.get('h')
            #     print(f"  Face Region (x,y,w,h): ({x},{y},{w},{h})")

    else:
        print("No faces detected in the image, or analysis failed.")

except Exception as e:
    print(f"An error occurred during DeepFace analysis: {e}")
    print("This might be due to no face being detected, issues with model download/installation, or an unsupported image format.")
    print("Try setting enforce_detection=False if you suspect no face was found.")

