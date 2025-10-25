#!/usr/bin/env python3
"""
Test script for YOLO detection and HAL voice playback
"""
import cv2
import subprocess
from pathlib import Path
from ultralytics import YOLO

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
YOLO_MODEL = PROJECT_ROOT / "yolov8s.pt"
HAL_AUDIO_DIR = PROJECT_ROOT / "src/voice/hal_audio"

def test_yolo_detection():
    """Test YOLO on a test image or webcam frame."""
    print("=" * 60)
    print("🔍 Testing YOLO Object Detection")
    print("=" * 60)
    
    # Load YOLO model
    print(f"\n1. Loading YOLO model: {YOLO_MODEL}")
    model = YOLO(str(YOLO_MODEL))
    print("   ✓ Model loaded successfully")
    
    # Create a test image (or use webcam if available)
    print("\n2. Creating test image (640x480 with colored rectangles)")
    test_image = cv2.imread(str(PROJECT_ROOT / "motion_test_output/motion_0001.jpg"))
    
    if test_image is None:
        # Create a synthetic test image if no real image available
        print("   No saved images found, creating synthetic test image")
        import numpy as np
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 100, 100)  # Gray background
        cv2.rectangle(test_image, (100, 100), (200, 200), (255, 0, 0), -1)
        cv2.rectangle(test_image, (300, 150), (400, 250), (0, 255, 0), -1)
        cv2.rectangle(test_image, (450, 300), (550, 400), (0, 0, 255), -1)
    else:
        print(f"   ✓ Using saved test image")
    
    # Run detection
    print("\n3. Running YOLO detection...")
    results = model(test_image, verbose=False)
    
    # Display results
    print(f"\n   ✓ Detection complete!")
    print(f"\n   📊 Results:")
    
    detected_objects = []
    for result in results:
        boxes = result.boxes
        if len(boxes) > 0:
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[class_id]
                detected_objects.append((class_name, confidence))
                print(f"      - {class_name}: {confidence:.2%} confidence")
        else:
            print("      - No objects detected in image")
    
    return detected_objects

def test_hal_voice(detected_objects=None):
    """Test HAL voice playback."""
    print("\n" + "=" * 60)
    print("🎙️  Testing HAL 9000 Voice")
    print("=" * 60)
    
    # Check available audio files
    audio_files = list(HAL_AUDIO_DIR.glob("*.mp3"))
    print(f"\n1. Found {len(audio_files)} HAL voice phrases")
    
    # Select appropriate phrase based on detection
    if detected_objects and any('person' in obj[0].lower() for obj in detected_objects):
        phrase_file = HAL_AUDIO_DIR / "detection_person_identified.mp3"
        phrase_text = "A person has been identified in the monitored area"
    else:
        phrase_file = HAL_AUDIO_DIR / "system_startup.mp3"
        phrase_text = "System online. I'm fully operational"
    
    if not phrase_file.exists():
        # Fallback to any available phrase
        phrase_file = audio_files[0] if audio_files else None
        phrase_text = phrase_file.stem if phrase_file else "Unknown"
    
    if phrase_file:
        print(f"\n2. Selected phrase: {phrase_file.stem}")
        print(f"   Text: \"{phrase_text}\"")
        print(f"\n3. Playing audio...")
        
        # Try multiple audio players (mpg123 first - handles MP3 best)
        players = ['mpg123', 'ffplay', 'cvlc', 'aplay']
        played = False
        
        for player in players:
            try:
                if player == 'aplay':
                    result = subprocess.run(
                        ['aplay', str(phrase_file)],
                        capture_output=True,
                        timeout=10
                    )
                elif player == 'ffplay':
                    result = subprocess.run(
                        ['ffplay', '-nodisp', '-autoexit', str(phrase_file)],
                        capture_output=True,
                        timeout=10
                    )
                elif player == 'mpg123':
                    result = subprocess.run(
                        ['mpg123', '-q', str(phrase_file)],
                        capture_output=True,
                        timeout=10
                    )
                elif player == 'cvlc':
                    result = subprocess.run(
                        ['cvlc', '--play-and-exit', str(phrase_file)],
                        capture_output=True,
                        timeout=10
                    )
                
                if result.returncode == 0:
                    print(f"   ✓ Audio played successfully using {player}")
                    played = True
                    break
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"   ⚠️  {player} failed: {e}")
                continue
        
        if not played:
            print("   ⚠️  No audio player found. Install aplay, ffplay, mpg123, or vlc")
            print("   💡 Command: sudo apt-get install alsa-utils")
    else:
        print("   ❌ No HAL audio files found")
        print("   💡 Generate them with: python scripts/generate_hal_voice_library_standalone.py")

def main():
    """Run complete test."""
    print("\n" + "=" * 60)
    print("🧪 YOLO + HAL Voice Integration Test")
    print("=" * 60)
    
    # Test YOLO
    detected_objects = test_yolo_detection()
    
    # Test HAL voice
    test_hal_voice(detected_objects)
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)
    print("\nNote: If you can't hear audio over SSH, connect directly to the Pi")
    print("      (HDMI monitor + keyboard, or VNC)")

if __name__ == "__main__":
    main()

