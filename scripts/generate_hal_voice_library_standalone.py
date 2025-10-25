#!/usr/bin/env python3
"""
HAL Voice Library Generator
Synthesizes HAL 9000-style voice notifications using Google Cloud TTS.
"""
import os
import sys
import yaml
import json
import logging
from pathlib import Path
from google.cloud import texttospeech

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHRASES_FILE = PROJECT_ROOT / "src/voice/hal_phrases.yaml"
OUTPUT_DIR = PROJECT_ROOT / "src/voice/hal_audio"
INDEX_FILE = OUTPUT_DIR / "index.json"

VOICE_CONFIG = {
    "language_code": "en-US",
    "voice_name": "en-US-Neural2-C",
    "pitch": "-10dB",
    "rate": "0.90",
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_environment() -> bool:
    """Pre-flight checks before synthesis."""
    checks_passed = True
    
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        logger.error("   Set with: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        checks_passed = False
    
    if not PHRASES_FILE.exists():
        logger.error(f"❌ Phrases file not found: {PHRASES_FILE}")
        checks_passed = False
    
    if checks_passed:
        try:
            client = texttospeech.TextToSpeechClient()
            logger.info("✓ Google Cloud TTS client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS: {e}")
            checks_passed = False
    
    return checks_passed

def synthesize_phrase(client, text: str, output_path: Path) -> bool:
    """Synthesize a single phrase with HAL voice characteristics."""
    try:
        ssml_text = f"""<speak>
            <prosody pitch="{VOICE_CONFIG['pitch']}" rate="{VOICE_CONFIG['rate']}">
                {text}
            </prosody>
        </speak>"""
        
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=VOICE_CONFIG["language_code"],
            name=VOICE_CONFIG["voice_name"]
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        with open(output_path, "wb") as f:
            f.write(response.audio_content)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to synthesize: {e}")
        return False

def main():
    """Generate HAL voice library."""
    logger.info("=" * 60)
    logger.info("HAL Voice Library Generator")
    logger.info("=" * 60)
    
    logger.info(f"Loading phrases from: {PHRASES_FILE}")
    with open(PHRASES_FILE, "r") as f:
        data = yaml.safe_load(f)
    
    phrases = data.get("hal_phrases", {})
    if not phrases:
        logger.error("No phrases found in YAML")
        return False
    
    total_chars = sum(len(text) for items in phrases.values() for text in items.values())
    total_phrases = sum(len(items) for items in phrases.values())
    estimated_cost = (total_chars / 1_000_000) * 16.00
    
    logger.info(f"Phrases: {total_phrases}")
    logger.info(f"Characters: {total_chars:,}")
    logger.info(f"Est. cost: ${estimated_cost:.4f}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = texttospeech.TextToSpeechClient()
    
    index = {}
    synthesized = 0
    cached = 0
    
    for category, items in phrases.items():
        for key, text in items.items():
            phrase_id = f"{category}_{key}"
            output_path = OUTPUT_DIR / f"{phrase_id}.mp3"
            
            if output_path.exists():
                logger.info(f"⚡ Cached: {phrase_id}")
                index[phrase_id] = str(output_path)
                cached += 1
                continue
            
            logger.info(f"🔊 Synthesizing: {phrase_id}")
            if synthesize_phrase(client, text, output_path):
                index[phrase_id] = str(output_path)
                synthesized += 1
                logger.info(f"   ✓ {phrase_id}.mp3")
    
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)
    
    logger.info("=" * 60)
    logger.info(f"✓ New: {synthesized} | Cached: {cached}")
    logger.info(f"✓ Index: {INDEX_FILE}")
    logger.info("=" * 60)
    
    return True

if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)
    if not main():
        sys.exit(1)
    logger.info("HAL voice library ready.")
