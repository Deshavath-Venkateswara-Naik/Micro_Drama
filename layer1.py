import os
import subprocess
import uuid
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VideoIngestionLayer:
    def __init__(self, output_base_dir="output"):
        self.output_base_dir = output_base_dir
        os.makedirs(self.output_base_dir, exist_ok=True)

    def get_video_duration(self, video_path):
        """Get the duration of the video in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def process(self, video_path, job_id=None):
        """
        Executes Layer 1 Pipeline:
        1. Normalize (Transcode to H.264)
        2. Chunk (10 min chunks with 30s overlap)
        3. Extract Audio & Frames per chunk
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        job_dir = os.path.join(self.output_base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        print(f"Starting Job {job_id} for video: {video_path}")

        # 1. Normalize to H.264
        normalized_path = os.path.join(job_dir, "normalized.mp4")
        print("1. Normalizing video to H.264...")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac",
            normalized_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        duration = self.get_video_duration(normalized_path)
        print(f"   Normalized video duration: {duration} seconds")

        # 2. Chunking with 30s overlap
        # Chunk duration: 600 seconds (10 mins), overlap: 30 seconds
        chunk_length = 600
        overlap = 30
        
        chunks = []
        start_time = 0.0
        chunk_index = 0

        from scenedetect import detect, ContentDetector
        
        while start_time < duration:
            # Optimal end time (hard limit)
            target_end_time = min(start_time + chunk_length, duration)
            
            # Intelligent boundary: look for scenes near the target end time
            actual_end_time = target_end_time
            if target_end_time < duration:
                print(f"   -> Searching for natural scene cut near {target_end_time}s...")
                # Scan a 60s window around target (±30s)
                window_start = max(0, target_end_time - 30)
                window_end = min(duration, target_end_time + 30)
                
                # Detect scenes in this window only
                try:
                    scene_list = detect(normalized_path, ContentDetector(), start_time=window_start, end_time=window_end)
                    if scene_list:
                        # Find the scene change closest to target_end_time
                        closest_cut = min(scene_list, key=lambda s: abs(s[1].get_seconds() - target_end_time))
                        actual_end_time = closest_cut[1].get_seconds() # Use the end of that scene
                        print(f"   -> Found optimal cut at {actual_end_time}s (Scene Boundary)")
                except Exception as e:
                    print(f"   -> Scene detection failed, falling back to hard cut: {e}")

            chunk_dir = os.path.join(job_dir, f"chunk_{chunk_index}")
            os.makedirs(chunk_dir, exist_ok=True)
            
            chunk_video_path = os.path.join(chunk_dir, "video.mp4")
            audio_path = os.path.join(chunk_dir, "audio.wav")
            frames_dir = os.path.join(chunk_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            print(f"2. Processing Chunk {chunk_index} ({start_time}s to {actual_end_time}s)...")
            
            # Extract the chunk video with transcoding for accuracy
            subprocess.run([
                "ffmpeg", "-y", "-i", normalized_path,
                "-ss", str(start_time),
                "-to", str(actual_end_time),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac",
                chunk_video_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Extract Audio (16kHz, mono, wav)
            print(f"   -> Extracting audio for Chunk {chunk_index}...")
            subprocess.run([
                "ffmpeg", "-y", "-i", chunk_video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                audio_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # 3. ADAPTIVE FRAME EXTRACTION
            # Baseline: 1 FPS for global context
            # Boost: Extract specific frames at scene boundaries for narrative precision
            print(f"   -> Performing Adaptive Frame Extraction for Chunk {chunk_index}...")
            
            # Baseline extraction (1 FPS)
            subprocess.run([
                "ffmpeg", "-y", "-i", chunk_video_path,
                "-vf", "fps=1", "-q:v", "2",
                os.path.join(frames_dir, "frame_%04d.jpg")
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Scene-aware boost: Extract frames at every scene change
            try:
                scene_list = detect(chunk_video_path, ContentDetector())
                for i, scene in enumerate(scene_list):
                    cut_time = scene[0].get_seconds()
                    # Use -ss for fast seeking and extract 1 frame
                    subprocess.run([
                        "ffmpeg", "-y", "-ss", str(cut_time), "-i", chunk_video_path,
                        "-frames:v", "1", "-q:v", "2",
                        os.path.join(frames_dir, f"scene_cut_{i:03d}.jpg")
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"   -> Adaptive boost: Extracted {len(scene_list)} additional scene-boundary frames.")
            except Exception as e:
                print(f"   -> Adaptive boost failed, baseline only: {e}")

            chunks.append({
                "chunk_id": chunk_index,
                "start": start_time,
                "end": actual_end_time,
                "video_path": chunk_video_path,
                "audio_path": audio_path,
                "frames_path": frames_dir
            })

            # Calculate next start time considering overlap
            # We use actual_end_time - overlap to ensure we don't miss anything
            start_time = actual_end_time - overlap
            chunk_index += 1

            # BREAK CONDITION: If we've reached the end of the video, stop.
            if actual_end_time >= duration:
                break

        output_json = {
            "job_id": job_id,
            "source": video_path,
            "duration_seconds": duration,
            "chunks": chunks
        }
        
        # Save output JSON
        with open(os.path.join(job_dir, "layer1_output.json"), "w") as f:
            json.dump(output_json, f, indent=2)

        print("Layer 1 Processing Complete!")
        return output_json

if __name__ == "__main__":
    # Example usage
    # Ensure you have a video.mp4 in the current directory to test
    video_file = "sample.mp4"
    if os.path.exists(video_file):
        layer1 = VideoIngestionLayer()
        layer1.process(video_file)
    else:
        print(f"Please place a '{video_file}' in this directory to test Layer 1.")
