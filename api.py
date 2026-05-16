import os
import uuid
import json
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

# Import our pipeline layers
from layer1 import VideoIngestionLayer
from layer2 import VideoUnderstandingPipeline
from layer3 import StoryIntelligenceEngine
from layer4 import DramaScoreEngine
from layer5 import EpisodicSequencingEngine
from layer6 import ClippingEngine

app = FastAPI(title="Microdrama Intelligence API", version="1.0.0")

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount output directory to serve video clips
if not os.path.exists("output"):
    os.makedirs("output")
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# --- Endpoints ---

@app.post("/api/v1/process")
async def process_video_upload(
    video: UploadFile = File(...),
    genre: str = Form("drama"),
    partition_mode: bool = Form(True) # Default to continuous partition mode
):
    """
    Upload a video file, and stream progress updates as each layer completes.
    """
    job_id = str(uuid.uuid4())
    job_dir = os.path.join("output", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    video_path = os.path.join(job_dir, video.filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    async def run_pipeline():
        try:
            yield json.dumps({"status": "Layer 1: Starting Ingestion...", "progress": 5}) + "\n"
            # Layer 1: Ingestion
            l1 = VideoIngestionLayer()
            l1_result = l1.process(video_path, job_id=job_id)
            l1_json_path = os.path.join(l1.output_base_dir, job_id, "layer1_output.json")
            yield json.dumps({"status": "Layer 1 Complete: Video Split.", "progress": 15}) + "\n"
            
            yield json.dumps({"status": "Layer 2: Analyzing Scenes & Audio...", "progress": 20}) + "\n"
            # Layer 2: Understanding
            l2 = VideoUnderstandingPipeline()
            l2_result_path = l2.process_job(l1_json_path, genre=genre)
            yield json.dumps({"status": "Layer 2 Complete: Deep Understanding Extracted.", "progress": 40}) + "\n"
            
            yield json.dumps({"status": f"Layer 3: Story Intelligence (Continuous: {partition_mode})...", "progress": 45}) + "\n"
            # Layer 3: Story Intelligence
            l3 = StoryIntelligenceEngine()
            l3_result_path = l3.process_job(l2_result_path, genre=genre, partition_mode=partition_mode)
            yield json.dumps({"status": "Layer 3 Complete: Narrative Arcs Identified.", "progress": 70}) + "\n"

            yield json.dumps({"status": "Layer 4: Ranking by Drama Score...", "progress": 75}) + "\n"
            # Layer 4: Drama Score Engine
            l4 = DramaScoreEngine()
            l4_result_path = l4.process_job(l3_result_path, l2_result_path, genre=genre)
            yield json.dumps({"status": "Layer 4 Complete: Clips Ranked.", "progress": 85}) + "\n"

            yield json.dumps({"status": f"Layer 5: Sequencing Episodes (Continuous: {partition_mode})...", "progress": 90}) + "\n"
            # Layer 5: Episodic Sequencing Engine
            l5 = EpisodicSequencingEngine()
            l5_result_path = l5.process_job(l4_result_path, genre=genre, partition_mode=partition_mode)
            yield json.dumps({"status": "Layer 5 Complete: Series Structured.", "progress": 95}) + "\n"

            yield json.dumps({"status": "Layer 6: Final Clipping...", "progress": 97}) + "\n"
            # Layer 6: Clipping Engine
            l6 = ClippingEngine()
            l6_result_path = l6.process_job(l5_result_path, job_dir)
            
            # Load final result (which now includes video_urls from Layer 6)
            with open(l6_result_path, "r") as f:
                final_data = json.load(f)
                
            yield json.dumps({"status": "Complete!", "progress": 100, "result": final_data}) + "\n"

        except Exception as e:
            print(f"PIPELINE ERROR: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(run_pipeline(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
