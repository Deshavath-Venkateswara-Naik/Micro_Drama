import os
import json
import time
from utils import time_to_seconds

class DramaScoreEngine:
    def __init__(self):
        pass

    def detect_genre(self, source_title: str, chunk_data: dict) -> str:
        """Heuristic-based genre detection."""
        title = source_title.lower()
        if any(w in title for w in ["news", "broadcast", "report", "anchor"]):
            return "news"
        if any(w in title for w in ["cartoon", "anime", "animation", "manga"]):
            return "cartoon"
        
        # Data-driven hints
        ocr_count = len(chunk_data.get("ocr_detections", []))
        if ocr_count > 50: # High text density usually means news or education
            return "news"
            
        return "drama" # Default to drama

    def calculate_drama_score(self, candidate: dict, l2_chunk_data: dict, genre: str = "drama") -> float:
        """
        Calculates a composite drama score for a candidate based on Layer 2 data.
        Genre-specific weighting for maximum accuracy.
        """
        # Flexible key handling for Gemini output
        start_str = candidate.get("start_time") or candidate.get("startTime") or candidate.get("start") or "00:00:00"
        end_str = candidate.get("end_time") or candidate.get("endTime") or candidate.get("end") or "00:00:00"
        
        start = time_to_seconds(start_str)
        end = time_to_seconds(end_str)
        
        # 1. Emotion Intensity
        emotions = [e for e in l2_chunk_data.get("emotions", []) if start <= e["timestamp"] <= end]
        emotion_intensity = sum(e.get("composite_score", 0) for e in emotions) / len(emotions) if emotions else 0
        
        # 2. Face Reaction Peak
        face_reaction_peak = max([e.get("composite_score", 0) for e in emotions] + [0])
        
        # 3. OCR Density (Important for News/Educational)
        ocr_detections = [o for o in l2_chunk_data.get("ocr_detections", []) if start <= o["timestamp"] <= end]
        ocr_density = min(1.0, len(ocr_detections) / 10.0)
        
        # 4. Silence Tension (Drama)
        audio_events = [a for a in l2_chunk_data.get("audio_events", []) if start <= a["start"] <= end]
        silence_events = [a for a in audio_events if a.get("type") == "silence"]
        silence_tension = min(1.0, len(silence_events) / 3.0)
        
        # 5. Audio Peak (Cartoons/Drama)
        peaks = [a for a in audio_events if a.get("type") == "dialogue_peak"]
        audio_peak = max([(a.get("intensity_db", -30) + 30) / 30 for a in peaks] + [0])
        audio_peak = min(1.0, max(0.0, audio_peak))
        
        # Apply Genre-Specific Weights
        if genre == "news":
            # News values information density and OCR peaks
            composite = (
                emotion_intensity * 0.10 +
                ocr_density * 0.50 +
                audio_peak * 0.40
            )
        elif genre == "cartoon":
            # Cartoons value movement (audio peaks) and sudden emotion shifts
            composite = (
                face_reaction_peak * 0.40 +
                audio_peak * 0.60
            )
        else:
            # Drama (Default) values emotion and tension
            composite = (
                emotion_intensity * 0.35 +
                face_reaction_peak * 0.20 +
                silence_tension * 0.25 +
                audio_peak * 0.20
            )
        
        # Bonus Signals
        bonus = 30 # Baseline bonus for being selected by Gemini
        if "cliffhanger" in candidate.get("cliffhanger_ending", "").lower():
            bonus += 10
            
        final_score = (composite * 70) + bonus # Weighted composite + baseline bonus
        return min(100.0, final_score)

    def _time_to_seconds(self, time_str: str) -> float:
        return time_to_seconds(time_str)

    def process_job(self, layer3_output_path: str, layer2_output_path: str, genre: str = "drama") -> str:
        print(f"Loading Layer 3 output from: {layer3_output_path}")
        print(f"Loading Layer 2 output from: {layer2_output_path}")
        
        with open(layer3_output_path, "r") as f:
            l3_data = json.load(f)
            
        with open(layer2_output_path, "r") as f:
            l2_data = json.load(f)
            
        job_id = l3_data.get("job_id", "unknown_job")
        candidates = l3_data.get("microdrama_candidates", [])
        l2_chunks = {c.get("chunk_id"): c for c in l2_data.get("understanding_data", [])}
        
        print(f"Ranking {len(candidates)} candidates...")
        
        scored_candidates = []
        for candidate in candidates:
            chunk_id = candidate.get("source_chunk_id")
            chunk_data = l2_chunks.get(chunk_id, {})
            
            # Detect genre for accurate scoring
            genre = self.detect_genre(l3_data.get("source", ""), chunk_data)
            
            score = self.calculate_drama_score(candidate, chunk_data, genre)
            candidate["drama_score"] = round(score, 1)
            candidate["detected_genre"] = genre
            
            # Determine Tier
            # Determine Tier
            if score >= 80:
                candidate["tier"] = "Tier 1 - Premium Drama"
            elif score >= 60:
                candidate["tier"] = "Tier 2 - High Drama"
            elif score >= 40:
                candidate["tier"] = "Tier 3 - Moderate"
            else:
                candidate["tier"] = "Tier 4 - Potential"
                
            # Lower threshold to 25 - Gemini suggested these, so they have value
            if score >= 25:
                scored_candidates.append(candidate)
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["drama_score"], reverse=True)
        
        output_data = {
            "job_id": job_id,
            "layer4_completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_ranked_candidates": len(scored_candidates),
            "ranked_candidates": scored_candidates
        }
        
        output_dir = os.path.dirname(layer3_output_path)
        output_path = os.path.join(output_dir, "layer4_output.json")
        
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"Layer 4 Processing Complete! Ranked {len(scored_candidates)} candidates.")
        print(f"Output saved to: {output_path}")
        
        return output_path

if __name__ == "__main__":
    # Test execution placeholder
    pass
