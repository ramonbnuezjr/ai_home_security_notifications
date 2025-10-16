# AI Model Selection Rationale

## Hardware Configuration
- **Device**: Raspberry Pi 5
- **RAM**: 16GB (upgraded from 4GB)
- **CPU**: Quad-core ARM Cortex-A76 @ 2.4GHz
- **Available Memory for AI**: ~14GB (leaving 2GB for system)

## Model Selection Strategy

### 1. Object Detection: YOLOv8s (Small)

**Selected Model**: YOLOv8s
**Previous Model**: YOLOv8n (nano)

**Rationale:**
- **Memory Footprint**: ~20MB model file, ~500MB during inference
- **Parameters**: ~11M parameters (vs 3M in YOLOv8n)
- **Accuracy Improvement**: ~5-7% better mAP than YOLOv8n
- **Performance**: Still maintains <500ms inference on Pi 5
- **16GB Benefit**: Comfortable memory headroom for larger model

**Fallback Option**: YOLOv8n remains available for performance-critical scenarios

### 2. Speech Processing: Whisper Small

**Selected Model**: Whisper Small
**Previous Model**: Whisper Base
**Fallback**: TinyLlama for basic descriptions

**Rationale:**
- **Memory Footprint**: ~1GB loaded
- **Parameters**: 244M parameters (vs 74M in base)
- **Accuracy**: Significantly better transcription, especially with accents/noise
- **Word Error Rate**: ~15% improvement over base model
- **Latency**: <3 seconds for 10-second clips (acceptable for security alerts)
- **16GB Benefit**: Memory available to keep model loaded continuously

**Performance Comparison:**
```
Model    | Size  | WER   | Latency | Memory
---------|-------|-------|---------|--------
tiny     | 39M   | ~7%   | <1s     | 400MB
base     | 74M   | ~5%   | <2s     | 600MB
small    | 244M  | ~3.5% | <3s     | 1GB
medium   | 769M  | ~2.5% | >10s    | 3GB (too slow)
```

### 3. Language Model: Llama 3.2 3B (Optional)

**Selected Model**: Llama 3.2 3B (4-bit quantized)
**Existing Model**: TinyLlama 1.1B
**Configuration**: Lazy-loaded, optional feature

**Rationale:**
- **Memory Footprint**: ~2-3GB with 4-bit quantization
- **Parameters**: 3B (vs 1.1B in TinyLlama)
- **Use Case**: Generate intelligent, context-aware event descriptions
- **Quality**: Significantly better natural language generation
- **16GB Benefit**: Enough memory to run alongside YOLO + Whisper when needed

**Example Output Comparison:**
```
TinyLlama:
"Person detected at front door. Motion detected."

Llama 3.2 3B:
"A person approached the front door at 10:34 PM and remained 
visible for 15 seconds. This is outside normal visitor hours."
```

**Configuration Strategy:**
- **Default**: Disabled (keep system lightweight)
- **Enable When**: User wants enhanced, intelligent descriptions
- **Lazy Loading**: Only load model when actually needed

## Memory Allocation with 16GB RAM

### Typical Load (All Models Active)
```
Component                Memory Usage
------------------------|--------------
System/OS               | 1-2 GB
YOLOv8s (loaded)        | 0.5 GB
Whisper Small (loaded)  | 1.0 GB
Llama 3.2 3B (4-bit)    | 2-3 GB
Video Buffers           | 0.5 GB
Application/Web         | 1.0 GB
Redis/Database          | 0.2 GB
------------------------|--------------
Total Used              | 6-8 GB
Available Headroom      | 8-10 GB
```

### Conservative Mode (No LLM)
```
Total Used              | 4-5 GB
Available Headroom      | 11-12 GB
```

## Performance Targets

### Object Detection (YOLOv8s)
- **Inference Time**: <500ms per frame
- **Detection Accuracy**: >90% mAP
- **False Positive Rate**: <5%
- **Concurrent Operations**: Can process detection while other models run

### Speech Processing (Whisper Small)
- **Transcription Time**: <3s for 10s audio
- **Word Error Rate**: <3.5%
- **Language Support**: 99 languages (multilingual)
- **Concurrent Operations**: Can transcribe while detection runs

### Language Generation (Llama 3.2 3B - Optional)
- **Generation Time**: 2-5s for 100-word description
- **Quality**: Human-like, contextual descriptions
- **Memory Impact**: Loaded on-demand, unloaded when idle
- **Use Cases**: Email bodies, SMS messages, event logs

## Migration from 4GB Configuration

### Previous Configuration (Pi 5 4GB)
- YOLOv8n (nano) - minimal model
- Whisper base - basic transcription
- TinyLlama 1.1B - lightweight descriptions
- Constant memory pressure
- Limited to one AI model at a time

### New Configuration (Pi 5 16GB)
- YOLOv8s (small) - better detection
- Whisper small - better transcription
- Llama 3.2 3B (optional) - intelligent descriptions
- TinyLlama (retained as fallback)
- Multiple models can run simultaneously
- ~10GB headroom for peak loads

## Fallback Strategy

### If Memory Issues Occur:
1. **First**: Disable LLM (saves 2-3GB)
2. **Second**: Switch Whisper small → base (saves 400MB)
3. **Third**: Switch YOLOv8s → YOLOv8n (saves minimal, but faster)

### Automatic Fallback Triggers:
- Memory usage > 13GB sustained for 60 seconds
- System temperature > 80°C
- CPU throttling detected
- Manual override via configuration

## Recommendations

### For Optimal Performance:
1. **Enable**: YOLOv8s + Whisper Small
2. **Test**: System performance for 24 hours
3. **Optionally Enable**: Llama 3.2 3B for enhanced descriptions
4. **Monitor**: Memory usage and adjust as needed

### For Maximum Reliability:
1. **Start**: YOLOv8s + Whisper base (conservative)
2. **Upgrade**: To Whisper small after stability confirmed
3. **Add**: LLM only if description quality is priority
4. **Always**: Keep fallback models available

## Testing Plan

### Phase 1: Base Configuration
- Deploy YOLOv8s + Whisper small
- Monitor memory, CPU, temperature
- Run for 48 hours
- Verify <14GB memory usage

### Phase 2: LLM Integration (Optional)
- Enable Llama 3.2 3B lazy loading
- Test event description generation
- Monitor memory spikes
- Verify acceptable latency

### Phase 3: Load Testing
- Simulate multiple concurrent detections
- Test all models running simultaneously
- Verify system stability under load
- Document performance metrics

## Conclusion

The upgrade to 16GB RAM unlocks significantly better AI capabilities:
- **Better Detection**: YOLOv8s provides 5-7% accuracy improvement
- **Better Speech**: Whisper small reduces transcription errors by 15%
- **Better Descriptions**: Optional Llama 3.2 3B for human-like event descriptions
- **Future-Proof**: 10GB headroom for future enhancements

The system maintains fallback options and can gracefully degrade if resource constraints are encountered.
