import os
import json
import time
import random
import uuid
import concurrent.futures
import cv2
import whisper
import librosa
import numpy as np
import easyocr
import torch
from typing import Dict, List, Any
from scenedetect import ContentDetector, SceneManager, open_video
from deepface import DeepFace

# Global Device Detection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[SYSTEM] Hardware Acceleration: {DEVICE.upper()} detected for PyTorch/Whisper.")

# TensorFlow GPU check (for DeepFace)
try:
    import tensorflow as tf
    tf_gpus = tf.config.list_physical_devices('GPU')
    print(f"[SYSTEM] TensorFlow GPU(s) found: {len(tf_gpus)} (Used by DeepFace)")
except Exception as e:
    print(f"[SYSTEM] TensorFlow GPU detection skipped: {e}")

def json_serializable(obj):
    """Recursively converts objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_serializable(i) for i in obj]
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

class SceneDetector:
    """
    4.1 Scene Detection
    Splits the video into semantic scenes at shot boundaries.
    Library integration to add: PySceneDetect
    """
    def process(self, chunk_data: Dict) -> List[Dict]:
        video_path = chunk_data.get("video_path")
        if not video_path or not os.path.exists(video_path):
            print(f"      [SceneDetector] Video path missing: {video_path}")
            return []
            
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()
        
        scenes = []
        for i, scene in enumerate(scene_list):
            start_time = scene[0].get_seconds()
            end_time = scene[1].get_seconds()
            scenes.append({
                "scene_id": i + 1,
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration_seconds": round(end_time - start_time, 2)
            })
            
        return scenes

class ASRProcessor:
    """
    4.2 Speech Recognition (ASR)
    Transcribes all dialogue with word-level timestamps.
    Upgrade: Using 'base' model for significantly better accuracy.
    """
    def __init__(self):
        # GPU-first loading with automatic fallback
        print(f"      [ASRProcessor] Loading Whisper 'base' model on {DEVICE}...")
        try:
            self.model = whisper.load_model("base", device=DEVICE)
        except Exception as e:
            print(f"      [ASRProcessor] GPU Loading failed, falling back to CPU: {e}")
            self.model = whisper.load_model("base", device="cpu")

    def process(self, chunk_data: Dict) -> List[Dict]:
        audio_path = chunk_data.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            print(f"      [ASRProcessor] Audio path missing: {audio_path}")
            return []
            
        print(f"      [ASRProcessor] Transcribing {audio_path} (High Accuracy Base Model)...")
        
        try:
            # ROBUST LOADING: Use librosa to load audio as float32 at 16kHz.
            # This prevents "reshape tensor of 0 elements" errors caused by ffmpeg pipe issues.
            audio, _ = librosa.load(audio_path, sr=16000)
            
            if len(audio) == 0:
                print(f"      [ASRProcessor] Audio is empty: {audio_path}")
                return []

            # Pass the numpy array directly to transcribe
            result = self.model.transcribe(audio, verbose=False, word_timestamps=True)
            
            transcripts = []
            for segment in result.get("segments", []):
                transcripts.append({
                    "start": round(segment["start"], 2),
                    "end": round(segment["end"], 2),
                    "text": segment["text"].strip(),
                    "confidence": round(segment.get("avg_logprob", 0), 2)
                })
                
            return transcripts
            
        except Exception as e:
            print(f"      [ASRProcessor] Transcription error: {e}")
            return []

class DiarizationProcessor:
    """
    4.3 Speaker Diarization
    Identifies and labels individual speakers.
    """
    def process(self, chunk_data: Dict, transcripts: List[Dict]) -> List[Dict]:
        # Improved Diarization logic: Grouping segments by flow and turn detection
        # Real pyannote integration would go here, but requires HF_TOKEN.
        # For now, we simulate turn detection based on gaps > 1.5s
        speakers_map = {}
        current_speaker_idx = 0
        
        last_end = 0
        for idx, segment in enumerate(transcripts):
            # If gap > 1.5s, likely a speaker turn or pause
            if segment["start"] - last_end > 1.5:
                current_speaker_idx = (current_speaker_idx + 1) % 5 # Simulate 5 speakers max
            
            speaker_id = f"SPEAKER_{current_speaker_idx:02d}"
            
            if speaker_id not in speakers_map:
                speakers_map[speaker_id] = {
                    "speaker_id": speaker_id,
                    "label": f"Character_{current_speaker_idx + 1}",
                    "segments": []
                }
            
            speakers_map[speaker_id]["segments"].append({
                "start": segment["start"],
                "end": segment["end"]
            })
            
            segment["speaker"] = speaker_id
            last_end = segment["end"]
            
        return list(speakers_map.values())

class EmotionDetector:
    """
    4.4 Emotion Detection
    Detects facial and vocal emotion per scene.
    Upgrade: Sample every 2 seconds for high resolution.
    """
    def process(self, chunk_data: Dict, transcripts: List[Dict]) -> List[Dict]:
        frames_dir = chunk_data.get("frames_path")
        if not frames_dir or not os.path.exists(frames_dir):
            return []
            
        frame_files = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".jpg")])
        
        emotions = []
        # Sample every 2 frames (approx every 2 seconds at 1fps) for high accuracy
        for i, frame_path in enumerate(frame_files):
            if i % 2 != 0:
                continue
                
            try:
                analysis = DeepFace.analyze(img_path=frame_path, actions=['emotion'], enforce_detection=False, silent=True)
                if analysis:
                    res = analysis[0]
                    dominant = res.get("dominant_emotion")
                    confidence = res.get("emotion", {}).get(dominant, 0) / 100.0
                    
                    emotions.append({
                        "timestamp": float(i), 
                        "face_emotion": dominant,
                        "face_confidence": round(confidence, 2),
                        "composite_score": round(confidence, 2)
                    })
            except Exception as e:
                pass
                
        return emotions

class AudioAnalyzer:
    """
    4.5 Audio Intensity Analysis
    Detects dramatic audio events: Pitch variance, Loudness spikes, Silence tension.
    """
    def process(self, chunk_data: Dict, genre: str = "drama") -> Dict:
        audio_path = chunk_data.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            return {}
            
        y, sr = librosa.load(audio_path)
        
        # 1. Pitch Variance (detects emotional tonal shifts)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0
        pitch_var = np.var(pitches[pitches > 0]) if np.any(pitches > 0) else 0
        
        # 2. Energy & Loudness Spikes
        rms = librosa.feature.rms(y=y)[0]
        rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
        loudness_spikes = np.where(rms_norm > 0.8)[0]
        
        # 3. Silence / Tension (Gaps in speech)
        # Using a low threshold for RMS to find "dead air"
        silence_mask = rms_norm < 0.05
        silence_ratio = np.mean(silence_mask)
        
        # 4. Music/Action Intensity (Spectral Flux)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        intensity_score = np.mean(onset_env)

        # Detect specific dramatic events
        events = []
        hop_length = 512
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
        
        # Detect peaks (climax)
        peak_threshold = 0.8
        is_peak = rms_norm > peak_threshold
        
        start_idx = None
        for i, peak in enumerate(is_peak):
            if i >= len(times): break
            if peak and start_idx is None:
                start_idx = i
            elif not peak and start_idx is not None:
                duration = times[i] - times[start_idx]
                if duration > 0.2:
                    events.append({
                        "start": round(times[start_idx], 2),
                        "end": round(times[i], 2),
                        "type": "dialogue_peak",
                        "intensity": "high",
                        "signal": "climax"
                    })
                start_idx = None

        return {
            "overall_pitch_variance": round(float(pitch_var), 2),
            "overall_intensity": round(float(intensity_score), 2),
            "silence_ratio": round(float(silence_ratio), 2),
            "loudness_spikes_count": len(loudness_spikes),
            "audio_events": events
        }

class OCRProcessor:
    """
    4.6 OCR Text Analysis
    Extracts on-screen text using easyocr.
    Upgrade: Real OCR for News/Cartoons/Title cards.
    """
    def __init__(self):
        print(f"      [OCRProcessor] Initializing EasyOCR Reader on {DEVICE}...")
        try:
            use_gpu = (DEVICE == "cuda")
            self.reader = easyocr.Reader(['en'], gpu=use_gpu)
        except Exception as e:
            print(f"      [OCRProcessor] GPU OCR failed, falling back to CPU: {e}")
            self.reader = easyocr.Reader(['en'], gpu=False)

    def process(self, chunk_data: Dict) -> List[Dict]:
        frames_dir = chunk_data.get("frames_path")
        if not frames_dir or not os.path.exists(frames_dir):
            return []
            
        frame_files = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".jpg")])
        
        detections = []
        # Sample OCR every 10 frames to avoid redundant text detection
        for i, frame_path in enumerate(frame_files):
            if i % 10 != 0:
                continue
                
            try:
                results = self.reader.readtext(frame_path)
                for (bbox, text, prob) in results:
                    if prob > 0.6: # Only high-confidence text
                        detections.append({
                            "timestamp": float(i),
                            "text": text,
                            "confidence": round(float(prob), 2)
                        })
            except Exception as e:
                pass
                
        return detections


class VideoUnderstandingPipeline:
    """
    Layer 2 Pipeline Orchestrator.
    Runs all detection models in parallel over chunks.
    """
    def __init__(self):
        self.scene_detector = SceneDetector()
        self.asr_processor = ASRProcessor()
        self.diarization_processor = DiarizationProcessor()
        self.emotion_detector = EmotionDetector()
        self.audio_analyzer = AudioAnalyzer()
        self.ocr_processor = OCRProcessor()

    def process_chunk(self, chunk_data: Dict, genre: str = "drama") -> Dict:
        """Process a single video chunk through all Layer 2 sub-components."""
        print(f"  [Chunk {chunk_data['chunk_id']}] Starting Layer 2 analysis (Genre: {genre})...")
        
        # 1. Scene Detection
        scenes = []
        try:
            scenes = self.scene_detector.process(chunk_data)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] Scene Detection failed: {e}")
        
        # 2. ASR (Speech Recognition)
        transcript = []
        try:
            transcript = self.asr_processor.process(chunk_data)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] ASR failed: {e}")
        
        # 3. Speaker Diarization (Mutates transcript to add speakers)
        speakers = []
        try:
            speakers = self.diarization_processor.process(chunk_data, transcript)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] Diarization failed: {e}")
        
        # 4. Emotion Detection
        emotions = []
        try:
            emotions = self.emotion_detector.process(chunk_data, transcript)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] Emotion Detection failed: {e}")
        
        # 5. Audio Intensity Analysis (Enhanced)
        audio_data = {}
        try:
            audio_data = self.audio_analyzer.process(chunk_data, genre=genre)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] Audio Analysis failed: {e}")
        
        # 6. OCR Text Analysis
        ocr_detections = []
        try:
            ocr_detections = self.ocr_processor.process(chunk_data)
        except Exception as e:
            print(f"  [Chunk {chunk_data['chunk_id']}] OCR failed: {e}")
        
        print(f"  [Chunk {chunk_data['chunk_id']}] Completed.")
        
        return {
            "chunk_id": chunk_data["chunk_id"],
            "start": chunk_data["start"],
            "end": chunk_data["end"],
            "video_path": chunk_data.get("video_path"),
            "audio_path": chunk_data.get("audio_path"),
            "frames_path": chunk_data.get("frames_path"),
            "scenes": scenes,
            "transcript": transcript,
            "speakers": speakers,
            "emotions": emotions,
            "audio_data": audio_data,
            "audio_events": audio_data.get("audio_events", []),
            "ocr_detections": ocr_detections
        }

    def process_job(self, layer1_output_path: str, genre: str = "drama") -> str:
        """
        Loads the output from Layer 1, processes all chunks in parallel,
        and saves the combined understanding output.
        """
        print(f"Loading Layer 1 output from: {layer1_output_path}")
        
        with open(layer1_output_path, "r") as f:
            layer1_data = json.load(f)
            
        job_id = layer1_data.get("job_id", str(uuid.uuid4()))
        chunks = layer1_data.get("chunks", [])
        
        print(f"Found {len(chunks)} chunks to process.")
        
        processed_chunks = []
        
        # Use ThreadPoolExecutor to process chunks in parallel
        # Note: If real ML models are used, ProcessPoolExecutor might be needed to bypass GIL, 
        # or ThreadPoolExecutor if models run mostly on GPU/C++ backends.
        max_workers = min(4, len(chunks) if len(chunks) > 0 else 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {executor.submit(self.process_chunk, chunk, genre=genre): chunk for chunk in chunks}
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    result = future.result()
                    processed_chunks.append(result)
                except Exception as exc:
                    print(f"  [Chunk {chunk['chunk_id']}] generated an exception: {exc}")

        # Sort processed chunks back into chronological order
        processed_chunks.sort(key=lambda x: x["chunk_id"])

        output_data = {
            "job_id": job_id,
            "source": layer1_data.get("source"),
            "duration_seconds": layer1_data.get("duration_seconds"),
            "layer2_completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "understanding_data": processed_chunks
        }
        
        output_dir = os.path.dirname(layer1_output_path)
        output_path = os.path.join(output_dir, "layer2_output.json")
        
        # Ensure all numeric types are standard Python floats/ints for JSON
        serializable_data = json_serializable(output_data)
        
        with open(output_path, "w") as f:
            json.dump(serializable_data, f, indent=2)
            
        print(f"Layer 2 Processing Complete! Output saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    # Test execution
    # First, we need to create a dummy layer1 output to test if one doesn't exist.
    dummy_l1_path = "output/dummy_job/layer1_output.json"
    os.makedirs(os.path.dirname(dummy_l1_path), exist_ok=True)
    
    if not os.path.exists(dummy_l1_path):
        dummy_data = {
            "job_id": str(uuid.uuid4()),
            "source": "sample.mp4",
            "duration_seconds": 1200,
            "chunks": [
                {"chunk_id": 0, "start": 0, "end": 600, "audio_path": "chunk_0.wav", "frames_path": "frames_0"},
                {"chunk_id": 1, "start": 570, "end": 1170, "audio_path": "chunk_1.wav", "frames_path": "frames_1"},
                {"chunk_id": 2, "start": 1140, "end": 1200, "audio_path": "chunk_2.wav", "frames_path": "frames_2"}
            ]
        }
        with open(dummy_l1_path, "w") as f:
            json.dump(dummy_data, f, indent=2)
    
    pipeline = VideoUnderstandingPipeline()
    pipeline.process_job(dummy_l1_path)
