"""
Google Cloud Text-to-Speech service with HAL 9000 voice characteristics.

This service provides synthesized speech using Google Cloud TTS with specific
prosody settings to emulate the HAL 9000 voice from 2001: A Space Odyssey.
Features local caching of common phrases and graceful fallback to espeak.
"""

import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, List

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    logging.warning("google-cloud-texttospeech not available, will use espeak fallback")


logger = logging.getLogger(__name__)


class GoogleHALVoiceService:
    """
    HAL 9000 voice synthesis and playback service.

    Provides text-to-speech synthesis using Google Cloud TTS with HAL 9000
    voice characteristics (deep pitch, slow cadence, measured tone). Caches
    synthesized audio locally and provides graceful fallback to espeak.

    Example:
        >>> hal = GoogleHALVoiceService(project_id="my-project")
        >>> hal.speak("detection_motion_detected")
        >>> hal.speak_custom("I'm sorry Dave, I'm afraid I can't do that")
    """

    def __init__(
        self,
        project_id: str,
        voice_name: str = "en-US-Neural2-D",
        cache_dir: str = "src/voice/hal_audio",
        audio_device: str = "default"
    ):
        """
        Initialize the HAL voice service.

        Args:
            project_id: Google Cloud project ID for TTS API
            voice_name: Google TTS voice name (Neural2-D is deeper male voice)
            cache_dir: Directory path for caching synthesized audio files
            audio_device: ALSA audio device name for playback

        Raises:
            ImportError: If google-cloud-texttospeech is not installed
        """
        self.project_id = project_id
        self.voice_name = voice_name
        self.cache_dir = Path(cache_dir)
        self.audio_device = audio_device

        # HAL 9000 voice characteristics
        self.hal_pitch = "-10.0dB"  # Deep, resonant voice
        self.hal_rate = "0.90"       # Slow, measured cadence

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Google TTS client if available
        self.client = None
        if GOOGLE_TTS_AVAILABLE:
            try:
                self.client = texttospeech.TextToSpeechClient()
                logger.info("Google Cloud TTS client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google TTS client: {e}")
                logger.warning("Will use espeak fallback for all synthesis")
        else:
            logger.warning("Google Cloud TTS not available, using espeak fallback")

        # Load phrase index if it exists
        self.phrase_index = self._load_phrase_index()

    def _load_phrase_index(self) -> dict:
        """
        Load the phrase index mapping phrase_ids to file paths.

        Returns:
            Dictionary mapping phrase_id to file path, or empty dict if not found
        """
        index_path = self.cache_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    index = json.load(f)
                logger.debug(f"Loaded phrase index with {len(index)} entries")
                return index
            except Exception as e:
                logger.error(f"Failed to load phrase index: {e}")
                return {}
        else:
            logger.debug("Phrase index not found, starting with empty index")
            return {}

    def _save_phrase_index(self) -> None:
        """Save the phrase index to disk."""
        index_path = self.cache_dir / "index.json"
        try:
            with open(index_path, 'w') as f:
                json.dump(self.phrase_index, f, indent=2)
            logger.debug("Phrase index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save phrase index: {e}")

    def _apply_hal_ssml(self, text: str) -> str:
        """
        Wrap plain text in SSML with HAL 9000 prosody characteristics.

        Args:
            text: Plain text to synthesize

        Returns:
            SSML-formatted string with HAL voice characteristics
        """
        ssml = f"""<speak>
  <prosody pitch="{self.hal_pitch}" rate="{self.hal_rate}">
    {text}
  </prosody>
</speak>"""
        return ssml

    def synthesize(
        self,
        text: str,
        cache_key: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize text to speech using Google Cloud TTS with HAL characteristics.

        Args:
            text: Plain text to synthesize
            cache_key: Optional key for caching (phrase_id or hash)

        Returns:
            Audio bytes in MP3 format, or None if synthesis fails

        Raises:
            Exception: If both Google TTS and espeak fallback fail
        """
        if not self.client:
            logger.warning("Google TTS client not available, cannot synthesize")
            return None

        try:
            # Apply HAL SSML characteristics
            ssml = self._apply_hal_ssml(text)

            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            # Configure voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=self.voice_name
            )

            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,  # Already handled in SSML
                pitch=0.0           # Already handled in SSML
            )

            # Perform synthesis
            logger.debug(f"Synthesizing text: {text[:50]}...")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            audio_bytes = response.audio_content
            logger.info(f"Successfully synthesized {len(audio_bytes)} bytes of audio")

            # Cache if cache_key provided
            if cache_key:
                cache_file = self.cache_dir / f"{cache_key}.mp3"
                try:
                    with open(cache_file, 'wb') as f:
                        f.write(audio_bytes)
                    logger.debug(f"Cached audio to {cache_file}")

                    # Update phrase index
                    self.phrase_index[cache_key] = str(cache_file)
                    self._save_phrase_index()
                except Exception as e:
                    logger.error(f"Failed to cache audio: {e}")

            return audio_bytes

        except Exception as e:
            logger.error(f"Google TTS synthesis failed: {e}")
            return None

    def _play_audio_file(self, audio_path: Path, blocking: bool = True) -> bool:
        """
        Play audio file using aplay.

        Args:
            audio_path: Path to audio file
            blocking: If True, wait for playback to complete

        Returns:
            True if playback succeeded, False otherwise
        """
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return False

        try:
            cmd = ["aplay", "-D", self.audio_device, str(audio_path)]
            logger.debug(f"Playing audio: {cmd}")

            if blocking:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True
                )
                logger.debug("Audio playback completed")
                return True
            else:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.debug("Audio playback started (non-blocking)")
                return True

        except subprocess.CalledProcessError as e:
            logger.error(f"aplay failed: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            logger.error("aplay not found, install with: sudo apt-get install alsa-utils")
            return False
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False

    def _espeak_fallback(self, text: str, blocking: bool = True) -> bool:
        """
        Fallback to espeak for text-to-speech.

        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete

        Returns:
            True if espeak succeeded, False otherwise
        """
        try:
            cmd = ["espeak", text]
            logger.debug(f"Using espeak fallback: {text[:50]}...")

            if blocking:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
                logger.debug("espeak playback completed")
                return True
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.debug("espeak playback started (non-blocking)")
                return True

        except FileNotFoundError:
            logger.error("espeak not found, install with: sudo apt-get install espeak")
            return False
        except Exception as e:
            logger.error(f"espeak fallback failed: {e}")
            return False

    def speak(self, phrase_id: str, blocking: bool = True) -> bool:
        """
        Play a cached HAL phrase by its phrase_id.

        Args:
            phrase_id: Phrase identifier (e.g., "detection_motion_detected")
            blocking: If True, wait for playback to complete

        Returns:
            True if playback succeeded, False otherwise

        Example:
            >>> hal.speak("detection_motion_detected")
            >>> hal.speak("system_startup", blocking=False)
        """
        logger.debug(f"Speaking phrase: {phrase_id}")

        # Check if phrase exists in index
        if phrase_id not in self.phrase_index:
            logger.warning(f"Phrase '{phrase_id}' not found in index")
            logger.info("Attempting to find cached file directly...")

            # Try to find file directly
            audio_path = self.cache_dir / f"{phrase_id}.mp3"
            if not audio_path.exists():
                logger.error(f"Cached audio file not found for '{phrase_id}'")
                logger.info(f"Attempting espeak fallback with phrase_id as text")
                return self._espeak_fallback(phrase_id.replace('_', ' '), blocking)
        else:
            audio_path = Path(self.phrase_index[phrase_id])

        # Try to play cached audio
        if self._play_audio_file(audio_path, blocking):
            return True

        # Fallback to espeak if audio playback failed
        logger.warning(f"Audio playback failed for '{phrase_id}', using espeak fallback")
        return self._espeak_fallback(phrase_id.replace('_', ' '), blocking)

    def speak_custom(self, text: str, blocking: bool = True) -> bool:
        """
        Dynamically synthesize and speak arbitrary text.

        Generates a cache key from text hash for potential reuse.

        Args:
            text: Custom text to synthesize and speak
            blocking: If True, wait for playback to complete

        Returns:
            True if synthesis and playback succeeded, False otherwise

        Example:
            >>> hal.speak_custom("I'm sorry Dave, I'm afraid I can't do that")
            >>> hal.speak_custom("All systems nominal", blocking=False)
        """
        logger.debug(f"Speaking custom text: {text[:50]}...")

        # Generate cache key from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f"custom_{text_hash}"

        # Check if already cached
        cached_path = self.cache_dir / f"{cache_key}.mp3"
        if cached_path.exists():
            logger.debug(f"Using cached audio for custom text")
            return self._play_audio_file(cached_path, blocking)

        # Synthesize new audio
        audio_bytes = self.synthesize(text, cache_key)

        if audio_bytes:
            # Save to temporary file and play
            temp_path = self.cache_dir / f"{cache_key}.mp3"
            try:
                with open(temp_path, 'wb') as f:
                    f.write(audio_bytes)
                return self._play_audio_file(temp_path, blocking)
            except Exception as e:
                logger.error(f"Failed to save synthesized audio: {e}")

        # Fallback to espeak if synthesis failed
        logger.warning("Google TTS synthesis failed, using espeak fallback")
        return self._espeak_fallback(text, blocking)

    def list_available_phrases(self) -> List[str]:
        """
        List all available cached phrase IDs.

        Returns:
            List of phrase_id strings from the phrase index

        Example:
            >>> hal.list_available_phrases()
            ['detection_motion_detected', 'detection_person_identified', ...]
        """
        phrases = list(self.phrase_index.keys())
        logger.debug(f"Found {len(phrases)} cached phrases")
        return phrases

    def verify_cache(self) -> dict:
        """
        Verify integrity of cached audio files.

        Returns:
            Dictionary with verification results:
                - total: Total phrases in index
                - valid: Number of valid files
                - missing: List of missing phrase_ids
                - corrupted: List of potentially corrupted phrase_ids
        """
        results = {
            'total': len(self.phrase_index),
            'valid': 0,
            'missing': [],
            'corrupted': []
        }

        for phrase_id, file_path in self.phrase_index.items():
            path = Path(file_path)
            if not path.exists():
                results['missing'].append(phrase_id)
            elif path.stat().st_size < 100:  # Suspiciously small file
                results['corrupted'].append(phrase_id)
            else:
                results['valid'] += 1

        logger.info(f"Cache verification: {results['valid']}/{results['total']} files valid")
        if results['missing']:
            logger.warning(f"Missing files: {results['missing']}")
        if results['corrupted']:
            logger.warning(f"Potentially corrupted files: {results['corrupted']}")

        return results
