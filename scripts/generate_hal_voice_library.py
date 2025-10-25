#!/usr/bin/env python3
"""
Generate HAL 9000 voice library by synthesizing all phrases from hal_phrases.yaml.

This script reads the phrase definitions and synthesizes each one using Google
Cloud Text-to-Speech, caching the results locally for fast playback. The script
is idempotent and can be run multiple times safely.

Usage:
    python scripts/generate_hal_voice_library.py
    python scripts/generate_hal_voice_library.py --force
    python scripts/generate_hal_voice_library.py --phrases="detection:motion_detected"
    python scripts/generate_hal_voice_library.py --phrases="detection:*"
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.google_tts_hal_service import GoogleHALVoiceService


def setup_logging(log_file: Path) -> logging.Logger:
    """
    Configure logging to both file and console.

    Args:
        log_file: Path to log file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create log directory if needed
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def load_phrases(phrases_file: Path) -> Dict[str, Dict[str, str]]:
    """
    Load phrases from YAML configuration file.

    Args:
        phrases_file: Path to hal_phrases.yaml

    Returns:
        Dictionary of categorized phrases

    Raises:
        FileNotFoundError: If phrases file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if not phrases_file.exists():
        raise FileNotFoundError(f"Phrases file not found: {phrases_file}")

    with open(phrases_file, 'r') as f:
        data = yaml.safe_load(f)

    return data.get('hal_phrases', {})


def flatten_phrases(phrases: Dict[str, Dict[str, str]]) -> List[Tuple[str, str]]:
    """
    Flatten nested phrase dictionary into list of (phrase_id, text) tuples.

    Args:
        phrases: Nested dictionary of categorized phrases

    Returns:
        List of (phrase_id, text) tuples
        phrase_id format: "category_phrase_name"
    """
    flattened = []
    for category, category_phrases in phrases.items():
        for phrase_name, phrase_text in category_phrases.items():
            phrase_id = f"{category}_{phrase_name}"
            flattened.append((phrase_id, phrase_text))
    return flattened


def filter_phrases(
    phrases: List[Tuple[str, str]],
    filter_spec: str
) -> List[Tuple[str, str]]:
    """
    Filter phrases based on specification.

    Args:
        phrases: List of (phrase_id, text) tuples
        filter_spec: Filter specification in format "category:phrase_name"
                     Supports wildcards: "detection:*" or "*:motion_detected"

    Returns:
        Filtered list of phrases
    """
    if not filter_spec:
        return phrases

    parts = filter_spec.split(':')
    if len(parts) != 2:
        logging.warning(f"Invalid filter spec: {filter_spec}, ignoring")
        return phrases

    category_filter, phrase_filter = parts

    filtered = []
    for phrase_id, phrase_text in phrases:
        category, phrase_name = phrase_id.split('_', 1)

        category_match = (category_filter == '*' or category == category_filter)
        phrase_match = (phrase_filter == '*' or phrase_name == phrase_filter)

        if category_match and phrase_match:
            filtered.append((phrase_id, phrase_text))

    return filtered


def generate_library(
    hal_service: GoogleHALVoiceService,
    phrases: List[Tuple[str, str]],
    force: bool = False,
    logger: logging.Logger = None
) -> Dict[str, any]:
    """
    Generate voice library by synthesizing all phrases.

    Args:
        hal_service: GoogleHALVoiceService instance
        phrases: List of (phrase_id, text) tuples to synthesize
        force: If True, re-synthesize existing phrases
        logger: Logger instance

    Returns:
        Statistics dictionary with synthesis results
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    stats = {
        'total': len(phrases),
        'synthesized': 0,
        'skipped': 0,
        'failed': 0,
        'total_bytes': 0,
        'errors': []
    }

    logger.info(f"Starting synthesis of {stats['total']} phrases...")
    logger.info(f"Force mode: {force}")
    logger.info("-" * 60)

    for i, (phrase_id, phrase_text) in enumerate(phrases, 1):
        # Check if already cached
        cached_file = hal_service.cache_dir / f"{phrase_id}.mp3"
        if cached_file.exists() and not force:
            logger.info(f"[{i}/{stats['total']}] SKIP: {phrase_id} (already cached)")
            stats['skipped'] += 1
            stats['total_bytes'] += cached_file.stat().st_size
            continue

        # Synthesize phrase
        logger.info(f"[{i}/{stats['total']}] Synthesizing: {phrase_id}")
        logger.debug(f"  Text: {phrase_text}")

        try:
            audio_bytes = hal_service.synthesize(phrase_text, cache_key=phrase_id)

            if audio_bytes:
                stats['synthesized'] += 1
                stats['total_bytes'] += len(audio_bytes)
                logger.info(f"  ✓ Success ({len(audio_bytes)} bytes)")
            else:
                stats['failed'] += 1
                error_msg = f"Synthesis returned None for {phrase_id}"
                stats['errors'].append(error_msg)
                logger.error(f"  ✗ Failed: {error_msg}")

        except Exception as e:
            stats['failed'] += 1
            error_msg = f"{phrase_id}: {str(e)}"
            stats['errors'].append(error_msg)
            logger.error(f"  ✗ Exception: {e}")

    logger.info("-" * 60)
    return stats


def print_summary(stats: Dict[str, any], logger: logging.Logger) -> None:
    """
    Print synthesis summary statistics.

    Args:
        stats: Statistics dictionary from generate_library()
        logger: Logger instance
    """
    total_mb = stats['total_bytes'] / (1024 * 1024)

    logger.info("=" * 60)
    logger.info("SYNTHESIS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total phrases:     {stats['total']}")
    logger.info(f"✓ Synthesized:     {stats['synthesized']}")
    logger.info(f"⊘ Skipped:         {stats['skipped']}")
    logger.info(f"✗ Failed:          {stats['failed']}")
    logger.info(f"Total size:        {total_mb:.2f} MB")
    logger.info("=" * 60)

    if stats['failed'] > 0:
        logger.warning("ERRORS ENCOUNTERED:")
        for error in stats['errors']:
            logger.warning(f"  - {error}")
        logger.info("=" * 60)

    if stats['synthesized'] > 0 or stats['skipped'] > 0:
        success_count = stats['synthesized'] + stats['skipped']
        logger.info(f"✓ Voice library ready: {success_count}/{stats['total']} phrases available")
    else:
        logger.error("✗ Voice library generation failed")


def main():
    """Main entry point for voice library generation."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate HAL 9000 voice library from phrase definitions"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-synthesis of all phrases (overwrite existing)'
    )
    parser.add_argument(
        '--phrases',
        type=str,
        default='',
        help='Filter phrases to synthesize (e.g., "detection:*" or "detection:motion_detected")'
    )
    parser.add_argument(
        '--project-id',
        type=str,
        default=os.environ.get('GOOGLE_CLOUD_PROJECT', ''),
        help='Google Cloud project ID (default: GOOGLE_CLOUD_PROJECT env var)'
    )
    parser.add_argument(
        '--voice',
        type=str,
        default='en-US-Neural2-D',
        help='Google TTS voice name (default: en-US-Neural2-D)'
    )
    parser.add_argument(
        '--cache-dir',
        type=str,
        default='src/voice/hal_audio',
        help='Directory for cached audio files (default: src/voice/hal_audio)'
    )

    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent
    phrases_file = project_root / "src" / "voice" / "hal_phrases.yaml"
    log_file = project_root / args.cache_dir / "synthesis.log"

    # Setup logging
    logger = setup_logging(log_file)
    logger.info("=" * 60)
    logger.info(f"HAL Voice Library Generation - {datetime.now().isoformat()}")
    logger.info("=" * 60)

    try:
        # Validate Google Cloud credentials
        if not args.project_id:
            logger.error("Google Cloud project ID not specified")
            logger.error("Set GOOGLE_CLOUD_PROJECT env var or use --project-id")
            sys.exit(1)

        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
        if credentials_path:
            logger.info(f"Using credentials: {credentials_path}")
        else:
            logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set")
            logger.warning("Relying on default credentials (may fail)")

        # Load phrases
        logger.info(f"Loading phrases from: {phrases_file}")
        phrase_dict = load_phrases(phrases_file)
        all_phrases = flatten_phrases(phrase_dict)
        logger.info(f"Loaded {len(all_phrases)} phrases from {len(phrase_dict)} categories")

        # Filter phrases if requested
        if args.phrases:
            logger.info(f"Applying filter: {args.phrases}")
            all_phrases = filter_phrases(all_phrases, args.phrases)
            logger.info(f"Filtered to {len(all_phrases)} phrases")

        if not all_phrases:
            logger.warning("No phrases to synthesize after filtering")
            sys.exit(0)

        # Initialize HAL service
        logger.info("Initializing Google HAL Voice Service...")
        hal_service = GoogleHALVoiceService(
            project_id=args.project_id,
            voice_name=args.voice,
            cache_dir=args.cache_dir
        )

        # Generate library
        stats = generate_library(
            hal_service=hal_service,
            phrases=all_phrases,
            force=args.force,
            logger=logger
        )

        # Print summary
        print_summary(stats, logger)

        # Verify cache integrity
        logger.info("Verifying cache integrity...")
        verification = hal_service.verify_cache()
        logger.info(f"Cache verification: {verification['valid']}/{verification['total']} files valid")

        if verification['missing']:
            logger.warning(f"Missing files: {len(verification['missing'])}")
        if verification['corrupted']:
            logger.warning(f"Potentially corrupted files: {len(verification['corrupted'])}")

        # Exit with appropriate code
        if stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
