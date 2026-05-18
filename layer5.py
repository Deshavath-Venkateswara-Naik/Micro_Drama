import os
import json
import time
from utils import time_to_seconds

class EpisodicSequencingEngine:
    def __init__(self):
        pass

    def sequence_candidates(self, candidates: list) -> list:
        """
        Groups and sequences candidates into a series format based on Movie Moment Types and Narrative Arcs.
        """
        if not candidates:
            return []
            
        # Group by Movie Moment Categories or Star Highlights
        categories = {
            "Action & High-Emotion": [],
            "Comedy & Punchlines": [],
            "High-Engagement Dialogues": [],
            "Suspense & Climax": [],
            "Star Spotlight": []
        }
        
        for cand in candidates:
            moment_types = cand.get("moment_types") or [cand.get("narrative_arc")] or []
            if isinstance(moment_types, str):
                moment_types = [moment_types.lower()]
            else:
                moment_types = [str(m).lower() for m in moment_types]
                
            added = False
            
            # 1. Celebrity check
            if cand.get("primary_celebrities") or "celebrity" in moment_types:
                categories["Star Spotlight"].append(cand)
                added = True
                
            # 2. Action check
            if "action" in moment_types or any("action" in m for m in moment_types):
                categories["Action & High-Emotion"].append(cand)
                added = True
                
            # 3. Comedy check
            if "comedy" in moment_types or any("comedy" in m for m in moment_types):
                categories["Comedy & Punchlines"].append(cand)
                added = True
                
            # 4. Suspense check
            if "suspense" in moment_types or any("suspense" in m for m in moment_types):
                categories["Suspense & Climax"].append(cand)
                added = True
                
            # 5. Dialogue check
            if "dialogue" in moment_types or any("dialogue" in m for m in moment_types) or not added:
                categories["High-Engagement Dialogues"].append(cand)
                added = True
                
        series_list = []
        for cat_name, cat_candidates in categories.items():
            if not cat_candidates:
                continue
                
            # Sort candidates chronologically
            def sort_key(x):
                val = x.get("start_time") or x.get("startTime") or x.get("start") or "00:00:00"
                return time_to_seconds(val)
            cat_candidates.sort(key=sort_key)
            
            series_id = f"series_{len(series_list) + 1:03d}"
            episodes = []
            for idx, cand in enumerate(cat_candidates):
                episode = cand.copy()
                episode["episode_number"] = idx + 1
                episode["series_id"] = series_id
                
                # Assign arc position
                if idx == 0:
                    episode["narrative_arc_position"] = "setup"
                elif idx == len(cat_candidates) - 1:
                    episode["narrative_arc_position"] = "peak"
                else:
                    episode["narrative_arc_position"] = "escalation"
                episodes.append(episode)
                
            series_list.append({
                "series_id": series_id,
                "series_title": f"{cat_name} Collection",
                "total_episodes": len(episodes),
                "episodes": episodes
            })
            
        return series_list

    def stitch_continuous_segments(self, candidates: list) -> list:
        """
        Stitches candidates together into a single continuous sequence.
        Handles overlaps from Layer 1 chunking.
        """
        if not candidates:
            return []

        # Sort all candidates by start time
        def sort_key(x):
            val = x.get("start_time") or x.get("startTime") or x.get("start") or "00:00:00"
            return time_to_seconds(val)
        candidates.sort(key=sort_key)

        stitched_episodes = []
        last_end_time = -1.0

        for idx, cand in enumerate(candidates):
            start_time = time_to_seconds(cand.get("start_time"))
            end_time = time_to_seconds(cand.get("end_time"))

            # Overlap removal:
            # If this candidate starts before the last one ended, it's redundant coverage
            # caused by Layer 1's overlap. We skip it unless it starts after last_end_time.
            if start_time < last_end_time - 0.5: # 0.5s tolerance
                continue
            
            episode = cand.copy()
            episode["episode_number"] = len(stitched_episodes) + 1
            episode["series_id"] = "series_continuous_001"
            stitched_episodes.append(episode)
            last_end_time = end_time

        return [{
            "series_id": "series_continuous_001",
            "series_title": "Continuous Drama Sequence",
            "total_episodes": len(stitched_episodes),
            "episodes": stitched_episodes
        }]

    def _time_to_seconds(self, time_str) -> float:
        return time_to_seconds(time_str)

    def process_job(self, layer4_output_path: str, genre: str = "drama", partition_mode: bool = False) -> str:
        print(f"Loading Layer 4 output from: {layer4_output_path}")
        
        with open(layer4_output_path, "r") as f:
            l4_data = json.load(f)
            
        job_id = l4_data.get("job_id", "unknown_job")
        candidates = l4_data.get("ranked_candidates", [])
        
        if partition_mode:
            print(f"Stitching {len(candidates)} candidates into continuous sequence...")
            series = self.stitch_continuous_segments(candidates)
        else:
            print(f"Sequencing {len(candidates)} candidates into series...")
            series = self.sequence_candidates(candidates)
        
        output_data = {
            "job_id": job_id,
            "layer5_completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_series": len(series),
            "series": series
        }
        
        output_dir = os.path.dirname(layer4_output_path)
        output_path = os.path.join(output_dir, "final_output.json")
        
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"Layer 5 Processing Complete! Generated {len(series)} series.")
        print(f"Output saved to: {output_path}")
        
        return output_path

if __name__ == "__main__":
    pass
