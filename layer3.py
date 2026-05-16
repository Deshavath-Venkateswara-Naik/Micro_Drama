import os
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.oauth2 import service_account
from dotenv import load_dotenv
from gemini_config import get_generative_model

# Load environment variables
load_dotenv()

SYSTEM_PROMPT = """You are a World-Class Cinematic Editor specializing in Microdrama conversion.
Your mission is to extract the absolute best dramatic clips from any genre (News, Movies, Cartoons, TV Shows) in any language (including Hindi, English, etc.).
Do NOT cut mid-emotion or mid-sentence.

ACCURACY RULES:
1. SEMANTIC SNAPPING: Every clip MUST start and end at a natural boundary.
   - START: Snap to the beginning of a Scene or the start of a Transcript segment.
   - END: Snap to the end of a Scene or the end of a Transcript segment.
2. MULTI-LANGUAGE: The transcript might be in Hindi or other languages. Analyze the emotional arc and narrative regardless of language.
3. GENRE-SPECIFIC FOCUS:
   - NEWS: Extract complete reports or high-impact soundbites. Ensure tickers/OCR context is considered.
   - CARTOONS: Focus on physical comedy beats or iconic catchphrases.
   - DRAMA/MOVIES: Focus on character tension, long silences (tension), and emotional peaks.
4. CLIFFHANGERS: Ensure the ending leaves the viewer wanting more, but do NOT cut the final word or emotional reaction.

5. PARTITION MODE (CRITICAL): If 'partition_mode' is active, your goal is NOT to find just the best clips. Your goal is to DIVIDE THE ENTIRE SEGMENT into a chain of continuous clips (30-90s each) that cover 100% of the timeline from the very first second to the very last.

Use the provided Scene and Transcript IDs to specify your timestamps.
"""

GENRE_PROMPTS = {
    "drama": """Focus on CHARACTER TENSION, long silences (tension), and emotional peaks. 
    Look for deep character development or high-stakes conflict. 
    Ensure the clip captures a complete emotional arc from setup to peak emotional payoff.""",
    
    "news": """Focus on HEADLINE SUMMARIES, key facts, and clear transitions. 
    Look for high-impact soundbites or concise reports. 
    Ensure tickers and OCR context are preserved for maximum information density.""",
    
    "cartoon": """Focus on VISUAL SLAPSTICK, high-energy sequences, and comedic beats. 
    Look for iconic catchphrases or physical humor. 
    Preserve the rapid pacing and vibrant energy characteristic of animation.""",
    
    "documentary": """Focus on EDUCATIONAL INSIGHTS, breathtaking visuals, and clear narration. 
    Look for "did you know" moments and compelling expert quotes."""
}

USER_PROMPT_TEMPLATE = """Analyze this video chunk for Microdrama potential.

GENRE: {genre}
SPECIALIZED FOCUS: {genre_focus}

DATA LAYERS:
- SCENES: {scene_json}
- TRANSCRIPT: {transcript_json}
- OCR (On-Screen Text): {ocr_json}
- EMOTIONS: {emotion_json}

INSTRUCTIONS:
1. Identify {count_instruction}.
2. For each candidate, provide the exact 'start_time' and 'end_time' that SNAPS to a scene or segment boundary.
3. Classify each clip into a NARRATIVE ARC (e.g., Revenge, Romance, Comedy, Breaking News, Hero Journey).
4. Explain why this clip is high-accuracy and preserves the emotional arc.
{partition_instruction}

Return JSON in the MicrodramaCandidate format, including a 'narrative_arc' field.
"""

class StoryIntelligenceEngine:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        self.mock_mode = False
        
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            print(f"\n[WARNING] Service account credentials not found at: {self.credentials_path}")
            self.mock_mode = True
        else:
            try:
                # Use centralized configuration
                # Using Gemini 2.5 Pro for Maximum Accuracy in Narrative Analysis
                self.model = get_generative_model("gemini-2.5-pro", system_instruction=SYSTEM_PROMPT)
                print(f"  [Layer 3] Vertex AI initialized via gemini_config with Gemini 2.5 Pro")
            except Exception as e:
                print(f"  [Layer 3] Failed to initialize Vertex AI: {e}")
                self.mock_mode = True

    def process_chunk(self, job_id: str, source: str, chunk_data: dict, genre: str = "drama", partition_mode: bool = False) -> dict:
        """Sends chunk video and metadata to Gemini for analysis via Vertex AI."""
        
        if self.mock_mode:
            time.sleep(1)
            return {"candidates": []}

        video_path = chunk_data.get("video_path")
        if not video_path or not os.path.exists(video_path):
            return {"candidates": []}

        # Prepare prompt with Layer 2 context and Genre Focus
        genre_focus = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["drama"])
        
        if partition_mode:
            count_instruction = "a sequence of continuous clips"
            partition_instruction = """
5. PARTITION RULE: You MUST partition the ENTIRE segment from {chunk_start}s to {chunk_end}s. 
   - Clip 1 must start at {chunk_start}.
   - Clip N+1 must start exactly where Clip N ends.
   - The final clip must end at {chunk_end}.
   - Every single second of the video must be included in one of the clips.
            """.format(chunk_start=chunk_data.get("start", 0), chunk_end=chunk_data.get("end", 0))
        else:
            count_instruction = "1-3 candidates (30-90 seconds)"
            partition_instruction = ""

        prompt = USER_PROMPT_TEMPLATE.format(
            genre=genre,
            genre_focus=genre_focus,
            count_instruction=count_instruction,
            partition_instruction=partition_instruction,
            scene_json=json.dumps(chunk_data.get("scenes", []), indent=2),
            transcript_json=json.dumps(chunk_data.get("transcript", []), indent=2),
            ocr_json=json.dumps(chunk_data.get("ocr_detections", []), indent=2),
            emotion_json=json.dumps(chunk_data.get("emotions", []), indent=2)
        )
        
        try:
            print(f"  [Layer 3] Reading video: {os.path.basename(video_path)}")
            with open(video_path, "rb") as f:
                video_bytes = f.read()
            video_part = Part.from_data(data=video_bytes, mime_type="video/mp4")

            # Try primary model
            try:
                response = self.model.generate_content(
                    [video_part, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
            except Exception as model_err:
                print(f"  [Layer 3] Primary model failed, trying fallback: {model_err}")
                # Fallback to flash which is almost always available
                fallback_model = get_generative_model("gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)
                response = fallback_model.generate_content(
                    [video_part, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
                
        except Exception as e:
            print(f"  [Layer 3] Gemini API error: {e}")
            return {"candidates": []}

    def process_job(self, layer2_output_path: str, genre: str = "drama", partition_mode: bool = False) -> str:
        """Loads Layer 2 structured data and extracts story intelligence using Gemini."""
        print(f"Loading Layer 2 output from: {layer2_output_path}")
        
        with open(layer2_output_path, "r") as f:
            l2_data = json.load(f)
            
        job_id = l2_data.get("job_id", "unknown_job")
        source = l2_data.get("source", "unknown_video")
        chunks = l2_data.get("understanding_data", [])
        
        print(f"Found {len(chunks)} processed chunks. Running Story Intelligence...")
        
        all_candidates = []
        
        for idx, chunk in enumerate(chunks):
            print(f"  [Layer 3] Analyzing narrative for Chunk {chunk.get('chunk_id')} (Genre: {genre})...")
            result = self.process_chunk(job_id, source, chunk, genre=genre, partition_mode=partition_mode)
            
            # Robust parsing for Gemini's output
            candidates_list = []
            if isinstance(result, list):
                candidates_list = result
            elif isinstance(result, dict):
                # Try common keys
                candidates_list = result.get("candidates") or result.get("microdrama_candidates") or result.get("segments") or []
                
            # Annotate candidates with chunk id for traceability
            for candidate in candidates_list:
                if not isinstance(candidate, dict): continue
                candidate["source_chunk_id"] = chunk.get("chunk_id")
                all_candidates.append(candidate)
                
        output_data = {
            "job_id": job_id,
            "source": source,
            "layer3_completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_candidates": len(all_candidates),
            "microdrama_candidates": all_candidates
        }
        
        output_dir = os.path.dirname(layer2_output_path)
        output_path = os.path.join(output_dir, "layer3_output.json")
        
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"Layer 3 Processing Complete! Found {len(all_candidates)} high-potential candidates.")
        print(f"Output saved to: {output_path}")
        
        return output_path

if __name__ == "__main__":
    # Test execution
    dummy_l2_path = "output/dummy_job/layer2_output.json"
    if os.path.exists(dummy_l2_path):
        engine = StoryIntelligenceEngine()
        engine.process_job(dummy_l2_path)
    else:
        print(f"Dummy file {dummy_l2_path} not found. Run main.py first.")
