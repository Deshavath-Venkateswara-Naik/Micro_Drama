import os
import json
import subprocess
import time
from utils import time_to_seconds

class ClippingEngine:
    def __init__(self):
        pass

    def cut_clip(self, source_video: str, start_time: str, end_time: str, output_path: str):
        """
        Cuts a video segment using FFmpeg with high precision.
        Maintains original aspect ratio.
        """
        # Calculate duration
        start_sec = time_to_seconds(start_time)
        end_sec = time_to_seconds(end_time)
        duration = end_sec - start_sec

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec), # Fast seeking before input
            "-i", source_video,
            "-t", str(duration),   # Accurate duration
            "-c:v", "libx264", 
            "-preset", "medium",   # Good quality/speed balance
            "-crf", "18",          # High quality
            "-c:a", "aac", "-b:a", "192k",
            "-avoid_negative_ts", "make_non_negative",
            output_path
        ]
        
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _time_to_seconds(self, time_str) -> float:
        return time_to_seconds(time_str)

    def process_job(self, layer5_output_path: str, job_dir: str) -> str:
        print(f"Loading Layer 5 output from: {layer5_output_path}")
        
        with open(layer5_output_path, "r") as f:
            l5_data = json.load(f)
            
        job_id = l5_data.get("job_id", "unknown_job")
        series_list = l5_data.get("series", [])
        
        # We need the normalized video from Layer 1
        source_video = os.path.join(job_dir, "normalized.mp4")
        if not os.path.exists(source_video):
            print(f"[Warning] normalized.mp4 not found in {job_dir}")
            return layer5_output_path

        clips_dir = os.path.join(job_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        
        print(f"Generating physical clips for {len(series_list)} series...")
        
        for series in series_list:
            for ep in series.get("episodes", []):
                start = ep.get("start_time")
                end = ep.get("end_time")
                ep_num = ep.get("episode_number")
                series_id = ep.get("series_id")
                
                clip_filename = f"{series_id}_ep{ep_num}.mp4"
                clip_path = os.path.join(clips_dir, clip_filename)
                
                print(f"  [Layer 6] Cutting Clip: {clip_filename} ({start} -> {end})...")
                self.cut_clip(source_video, start, end, clip_path)
                
                # Add the relative path to the episode metadata
                ep["video_url"] = f"/output/{job_id}/clips/{clip_filename}"
        
        # Save the updated final output with video URLs
        output_path = os.path.join(job_dir, "final_output_with_clips.json")
        with open(output_path, "w") as f:
            json.dump(l5_data, f, indent=2)
            
        print(f"Layer 6 Processing Complete! Clips saved in: {clips_dir}")
        print(f"Updated output saved to: {output_path}")
        
        return output_path

if __name__ == "__main__":
    pass
