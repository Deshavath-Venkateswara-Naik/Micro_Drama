# Requirements Document

## Introduction

This feature adds short-form trailer generation to the Microdrama Intelligence pipeline. After a video completes full pipeline processing (Layers 1–4 minimum), users can generate cinematic trailers of 15, 30, or 60 seconds by clicking a dedicated button in the results workspace. The Trailer_Generator reads existing Layer 4 or Layer 5 output data (ranked candidates with drama scores, moment types, and cliffhanger metadata), applies a deterministic rule-based assembly algorithm to select and sequence clips for maximum narrative impact, and stitches them using FFmpeg. No pipeline layers are re-run and no LLM or Gemini API calls are made, ensuring fast and cost-effective trailer production.

## Glossary

- **Pipeline**: The existing 6-layer Microdrama video processing system (Ingestion → Understanding → Story Intelligence → Drama Score → Episodic Sequencing → Clipping)
- **Layer_4_Output**: The JSON file (`layer4_output.json`) produced by the DramaScoreEngine containing `ranked_candidates` with fields including `moment_types`, `drama_score`, `start_time`, `end_time`, `cliffhanger_ending`, and `primary_celebrities`
- **Layer_5_Output**: The JSON file (`final_output.json`) produced by the EpisodicSequencingEngine containing `series` grouped by category (Action & High-Emotion, Comedy & Punchlines, High-Engagement Dialogues, Suspense & Climax, Star Spotlight)
- **Trailer_Generator**: The new backend module responsible for selecting, sequencing, and stitching clips into a short-form trailer using deterministic rules
- **Trailer_Endpoint**: The FastAPI POST endpoint at `/api/v1/generate-trailer` that orchestrates trailer generation
- **Trailer_Button**: The UI element labeled "🎬 Short-Form Trailer Generation" displayed in the results workspace after job completion
- **Clipping_Engine**: Layer 6 component (`layer6.py`) that uses FFmpeg to cut physical video clips from `normalized.mp4` given start and end timestamps
- **Trailer_Assembly_Algorithm**: The deterministic rule-based logic that selects and orders clips by narrative role: suspense for hook, action/high-emotion for escalation, dialogue/celebrity for engagement, and cliffhanger for ending
- **Trailer_Length**: The target duration of the generated trailer in seconds; valid values are 15, 30, or 60
- **Target_Style**: The stylistic profile applied during clip selection; valid values are "cinematic", "action", or "suspense"
- **Processed_Job**: A job that has completed at least through Layer 4, producing a `layer4_output.json` file in the `output/{job_id}/` directory
- **Results_Workspace**: The section of the frontend UI (`static/index.html`) where pipeline output clips and metadata are displayed
- **Progress_Stream**: Newline-delimited JSON messages streamed from the server containing `status` (string) and `progress` (integer 0–100) fields
- **Trailer_Output_Directory**: The directory `output/{job_id}/trailers/` where generated trailer files are stored

## Requirements

### Requirement 1: Display Trailer Generation Button in UI

**User Story:** As a content editor, I want to see a "Short-Form Trailer Generation" button always visible and clickable in the UI, so that I can upload a video and generate a trailer in one click without needing to run the pipeline separately first.

#### Acceptance Criteria

1. THE Trailer_Button SHALL be rendered in the DOM at page load, positioned prominently in the main action area of the UI alongside the video upload controls
2. THE Trailer_Button SHALL display the text "🎬 Short-Form Trailer Generation" with full opacity and an enabled clickable state at all times (not disabled or greyed out)
3. WHEN the Trailer_Button is clicked and a video file has been selected or uploaded, THE UI SHALL initiate the full pipeline processing (Layers 1–4) followed by trailer generation in a single continuous workflow
4. WHEN the Trailer_Button is clicked and a Processed_Job already exists from a previous pipeline run, THE UI SHALL skip pipeline processing and directly call the Trailer_Endpoint with the existing job_id
5. IF the Trailer_Button is clicked but no video file has been selected and no Processed_Job exists, THEN THE UI SHALL prompt the user to select a video file first
6. WHEN the Trailer_Button is clicked, THE UI SHALL disable the Trailer_Button and display a loading indicator to prevent duplicate requests
7. IF the pipeline or trailer generation request fails or does not respond within 120 seconds, THEN THE UI SHALL re-enable the Trailer_Button, hide the loading indicator, and display an error message indicating the operation failed
8. WHEN the pipeline completes and trailer generation begins, THE UI SHALL continue displaying progress updates seamlessly transitioning from pipeline progress to trailer generation progress
9. WHEN the Trailer_Button is rendered, THE UI SHALL display a trailer duration selection control adjacent to the Trailer_Button offering options of 15, 30, and 60 seconds with a default selection of 30 seconds

### Requirement 2: Trailer Generation Endpoint API Contract

**User Story:** As a developer, I want a well-defined API contract for the trailer generation endpoint, so that the feature integrates consistently with the existing API and supports automation.

#### Acceptance Criteria

1. THE Trailer_Endpoint SHALL be accessible at POST `/api/v1/generate-trailer`
2. THE Trailer_Endpoint SHALL accept a JSON request body with Content-Type "application/json" containing the required field "job_id" of type string in UUID format
3. THE Trailer_Endpoint SHALL accept an optional field "trailer_length" of type integer with valid values 15, 30, or 60 and default value 30
4. THE Trailer_Endpoint SHALL accept an optional field "target_style" of type string with valid values "cinematic", "action", or "suspense" and default value "cinematic"
5. IF "job_id" is missing from the request body, THEN THE Trailer_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating that job_id is required
6. IF "job_id" is not a valid UUID format string, THEN THE Trailer_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating that job_id must be a valid UUID
7. IF "trailer_length" is provided and is not one of 15, 30, or 60, THEN THE Trailer_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating valid values are 15, 30, or 60
8. IF "target_style" is provided and is not one of "cinematic", "action", or "suspense", THEN THE Trailer_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating valid values are cinematic, action, or suspense
9. IF the job_id is a valid UUID but no corresponding processed job exists in the `output/{job_id}/` directory, THEN THE Trailer_Endpoint SHALL return HTTP status 404 with a JSON body containing the field "error" indicating that the specified job was not found
10. THE Trailer_Endpoint SHALL return Content-Type "text/plain" for the streaming response where each message is a single line of valid JSON followed by a newline character, consistent with the existing `/api/v1/process` endpoint
11. WHEN trailer generation completes successfully, THE Trailer_Endpoint SHALL emit a final streaming JSON message containing the field "progress" set to 100, the field "status" set to "Complete!", and a "result" field containing the trailer metadata
12. IF an error occurs during processing that prevents trailer generation from completing, THEN THE Trailer_Endpoint SHALL emit a streaming JSON message containing the field "error" with a message indicating the nature of the failure, and SHALL stop streaming with no further messages

### Requirement 3: No Reprocessing of Pipeline Layers

**User Story:** As a system operator, I want trailer generation to use only existing pipeline outputs without re-running Layers 1–4 or invoking Gemini, so that trailer generation is fast and cost-free.

#### Acceptance Criteria

1. WHEN the Trailer_Endpoint receives a valid request, THE Trailer_Generator SHALL read candidate data exclusively from existing Layer_4_Output or Layer_5_Output files in the `output/{job_id}/` directory
2. THE Trailer_Generator SHALL NOT invoke any Pipeline layer processing (Layers 1 through 6) during trailer generation
3. THE Trailer_Generator SHALL NOT make any calls to the Gemini API or any external LLM service during trailer generation
4. WHEN the Trailer_Endpoint receives a job_id, THE Trailer_Endpoint SHALL verify that `output/{job_id}/layer4_output.json` exists before performing any trailer assembly
5. IF the specified job_id does not have a Layer_4_Output file, THEN THE Trailer_Endpoint SHALL return HTTP status 404 with a JSON body containing the field "error" set to "Job not found or Layer 4 output missing"
6. IF the Layer_4_Output file exists but cannot be parsed as valid JSON, THEN THE Trailer_Endpoint SHALL return HTTP status 500 with a JSON body containing the field "error" indicating that the Layer 4 output file is corrupted or unreadable

### Requirement 4: Trailer Assembly Algorithm

**User Story:** As a content editor, I want trailers assembled using a narrative structure (hook → escalation → engagement → cliffhanger ending), so that the generated trailers feel professionally paced and compelling.

#### Acceptance Criteria

1. WHEN the Trailer_Generator assembles a trailer, THE Trailer_Generator SHALL select clips from the `ranked_candidates` array and assign each clip exactly one narrative role from the set: hook, escalation, engagement, ending, such that the assembled trailer contains exactly 1 hook clip, at least 1 escalation clip, at least 1 engagement clip, and exactly 1 ending clip
2. WHEN selecting the hook segment, THE Trailer_Generator SHALL prioritize candidates whose `moment_types` array contains "suspense" and rank them by `drama_score` in descending order, using earliest `start_time` as tiebreaker when drama_scores are equal
3. WHEN selecting escalation segments, THE Trailer_Generator SHALL prioritize candidates whose `moment_types` array contains "action" or whose `drama_score` is at or above the 75th percentile value of all candidates' drama_scores
4. WHEN selecting engagement segments, THE Trailer_Generator SHALL prioritize candidates whose `moment_types` array contains "dialogue" or "celebrity", or whose `primary_celebrities` field is non-empty
5. WHEN selecting the ending segment, THE Trailer_Generator SHALL prioritize candidates whose `cliffhanger_ending` field contains a non-empty value, ranked by `drama_score` in descending order, using earliest `start_time` as tiebreaker when drama_scores are equal
6. THE Trailer_Generator SHALL sequence selected clips in the order: hook first, escalation segments second, engagement segments third, ending segment last
7. THE Trailer_Generator SHALL select clips such that the total combined duration of all selected clips is between Trailer_Length minus 2 seconds and Trailer_Length plus 2 seconds inclusive
8. IF no candidates with `moment_types` containing "suspense" are available for the hook, THEN THE Trailer_Generator SHALL select the candidate with the highest `drama_score` as the hook
9. IF no candidates with a non-empty `cliffhanger_ending` are available for the ending, THEN THE Trailer_Generator SHALL select the candidate with the highest `drama_score` among remaining unselected candidates as the ending
10. WHEN "target_style" is "action", THE Trailer_Generator SHALL increase the proportion of escalation segments to at least 50 percent of the total trailer duration
11. WHEN "target_style" is "suspense", THE Trailer_Generator SHALL increase the proportion of hook and ending segments to at least 40 percent of the total trailer duration
12. THE Trailer_Generator SHALL NOT select the same candidate for multiple narrative roles within a single trailer
13. IF the `ranked_candidates` array contains fewer than 4 candidates, THEN THE Trailer_Generator SHALL not assemble a trailer and SHALL return an error indication stating that insufficient candidates are available to fill all narrative roles
14. IF the total combined duration of all available candidates in `ranked_candidates` is less than Trailer_Length minus 2 seconds, THEN THE Trailer_Generator SHALL assemble the trailer using all available candidates and indicate in the output that the requested duration could not be met

### Requirement 5: FFmpeg Stitching

**User Story:** As a content editor, I want the selected clips stitched into a single continuous video file using FFmpeg, so that I receive a ready-to-use trailer without manual editing.

#### Acceptance Criteria

1. WHEN clips are selected and sequenced by the Trailer_Assembly_Algorithm, THE Trailer_Generator SHALL cut each selected clip from the `normalized.mp4` file located in `output/{job_id}/` using the Clipping_Engine, where each clip's duration is defined by its `start_time` and `end_time` timestamps from the sequenced candidate data
2. WHEN individual clips are cut, THE Trailer_Generator SHALL concatenate all clips in narrative sequence order into a single output video file using FFmpeg
3. THE Trailer_Generator SHALL use FFmpeg exclusively for all video cutting and concatenation operations, with no LLM or external API calls
4. THE Trailer_Generator SHALL produce the output file encoded with H.264 video codec (libx264) and AAC audio codec at 192 kbps audio bitrate, preserving the source video resolution and frame rate
5. IF the `normalized.mp4` file does not exist in the `output/{job_id}/` directory, THEN THE Trailer_Endpoint SHALL return HTTP status 404 with a JSON body containing the field "error" indicating the source video is missing
6. IF FFmpeg fails during clip cutting or concatenation, THEN THE Trailer_Endpoint SHALL emit a streaming error message describing the FFmpeg failure and stop processing
7. IF only one clip is selected by the Trailer_Assembly_Algorithm, THEN THE Trailer_Generator SHALL produce the output file containing that single clip without concatenation
8. WHEN the trailer file is successfully produced, THE Trailer_Generator SHALL remove any intermediate individual clip files created during the cutting step to free disk space

### Requirement 6: Trailer Output Location and Naming

**User Story:** As a content editor, I want trailers saved in a predictable location with clear filenames, so that I can find and download them easily.

#### Acceptance Criteria

1. IF the Trailer_Output_Directory at `output/{job_id}/trailers/` does not already exist, THEN THE Trailer_Generator SHALL create the directory including any necessary parent directories before writing the trailer file
2. THE Trailer_Generator SHALL save the generated trailer file in the Trailer_Output_Directory with the filename `trailer_{length}s.mp4` where `{length}` is the Trailer_Length value (15, 30, or 60)
3. IF a trailer file with the same filename already exists in the Trailer_Output_Directory, THEN THE Trailer_Generator SHALL overwrite the existing file with the newly generated trailer
4. WHEN trailer generation completes successfully, THE Trailer_Endpoint SHALL include in the final response a `video_url` field formatted as `/output/{job_id}/trailers/trailer_{length}s.mp4` pointing to the generated trailer file
5. WHEN the trailer file is written to disk, THE Trailer_Generator SHALL verify that the output file exists and has a file size greater than 0 bytes before reporting success
6. IF the Trailer_Output_Directory cannot be created or the trailer file cannot be written to disk, THEN THE Trailer_Endpoint SHALL emit a streaming error message indicating the file system operation that failed and SHALL stop processing

### Requirement 7: Progress Streaming

**User Story:** As a content editor, I want to see real-time progress updates while the trailer is being generated, so that I know the system is working and can estimate completion time.

#### Acceptance Criteria

1. THE Trailer_Endpoint SHALL return a StreamingResponse with media type "text/plain" where each message is a single line of valid JSON followed by a newline character, consistent with the existing Pipeline `/api/v1/process` endpoint format
2. WHEN trailer assembly begins, THE Trailer_Endpoint SHALL emit a Progress_Stream message with status "Loading ranked candidates..." and progress set to 10
3. WHEN clip selection is complete, THE Trailer_Endpoint SHALL emit a Progress_Stream message with status identifying the number of clips selected and progress set to 30
4. WHEN each clip is being cut from the source video, THE Trailer_Endpoint SHALL emit a Progress_Stream message with status identifying the clip number out of total clips and progress calculated as 30 + ((clip_index / total_clips) * 50) rounded to the nearest integer, where clip_index is the 1-based position of the clip currently being processed
5. WHEN concatenation begins, THE Trailer_Endpoint SHALL emit a Progress_Stream message with status "Stitching trailer..." and progress set to 85
6. WHEN the trailer file is written successfully, THE Trailer_Endpoint SHALL emit a final Progress_Stream message with progress 100, status "Complete!", and a "result" field containing a JSON object with fields: `video_url`, `trailer_length`, `target_style`, `total_clips_used`, and `clips` (array of clip metadata with start_time, end_time, drama_score, moment_types, and narrative_role)
7. IF an error occurs at any stage, THEN THE Trailer_Endpoint SHALL emit a Progress_Stream message containing an "error" field with a description of the failure and SHALL stop streaming

### Requirement 8: UI Trailer Display

**User Story:** As a content editor, I want the generated trailer displayed in the frontend using the existing premium card UI, so that I can preview it immediately after generation.

#### Acceptance Criteria

1. WHEN the Trailer_Endpoint begins streaming, THE UI SHALL display the progress bar and status text in the Results_Workspace, updating the progress bar width to match the `progress` percentage value and the status text to match the `status` string as each Progress_Stream message is received
2. WHEN a Progress_Stream message with progress equal to 100 and a "result" field is received, THE UI SHALL hide the progress indicator and render the trailer using the existing premium episode card template within the Results_Workspace
3. WHEN the trailer card is rendered, THE UI SHALL display the section header "🎬 Generated Trailer ({length}s - {style})" above the trailer card, where {length} is the Trailer_Length and {style} is the Target_Style
4. THE UI SHALL display the trailer card with a video player sourced from the trailer video_url, the total_clips_used count, the target_style as a badge label, and the trailer_length displayed in seconds
5. WHEN the trailer card is rendered, THE UI SHALL display a list of the individual clips used in the trailer with their narrative_role, start_time, end_time, and drama_score
6. IF the Trailer_Endpoint stream returns an error status or the connection fails before a progress 100 message is received, THEN THE UI SHALL hide the progress indicator and display an error message indicating trailer generation failed
7. WHEN the trailer card is rendered successfully, THE UI SHALL insert the trailer section above the existing series content in the Results_Workspace and re-enable the Trailer_Button to allow subsequent trailer generation with different parameters

### Requirement 9: Cost Optimization Through Reuse

**User Story:** As a system operator, I want trailer generation to reuse existing pipeline components and data structures, so that the feature adds minimal computational cost and no external API expenses.

#### Acceptance Criteria

1. THE Trailer_Generator SHALL import and instantiate the existing ClippingEngine class from `layer6.py` and invoke its `cut_clip` method for all FFmpeg clip cutting operations, without reimplementing FFmpeg command construction
2. THE Trailer_Generator SHALL read the `ranked_candidates` array from Layer_4_Output by opening the file in read-only mode, and SHALL NOT write to, rename, or modify the original `layer4_output.json` file
3. THE Trailer_Generator SHALL use deterministic rule-based logic for all clip selection and sequencing decisions such that given identical input data and identical parameters (job_id, trailer_length, target_style), two consecutive executions produce a byte-identical output trailer file
4. THE Trailer_Generator SHALL NOT install or import any Python packages beyond those already imported across the existing layer modules (layer1.py through layer6.py), specifically limiting external tool usage to the `subprocess` module for FFmpeg invocation via ClippingEngine
5. WHEN Layer_5_Output (`final_output.json`) is available in the `output/{job_id}/` directory, THE Trailer_Generator SHALL read category-grouped candidate data from Layer_5_Output as the primary data source for clip selection instead of Layer_4_Output
6. IF Layer_5_Output (`final_output.json`) is available but cannot be parsed as valid JSON, THEN THE Trailer_Generator SHALL fall back to reading `ranked_candidates` from Layer_4_Output and continue trailer generation without error

### Requirement 10: Modular Code Design

**User Story:** As a developer, I want the trailer generation code to be modular and production-ready, so that it can be maintained, tested, and extended independently of other pipeline layers.

#### Acceptance Criteria

1. THE Trailer_Generator SHALL be implemented as a separate Python module file that does not modify or extend existing layer modules (layer1.py through layer6.py), while permitted to import from them for reuse as specified in Requirement 9
2. THE Trailer_Generator SHALL expose a class with a public method that accepts job_id (string), trailer_length (integer), and target_style (string) parameters and returns the absolute file path as a string to the generated trailer file on disk
3. THE Trailer_Generator SHALL separate clip selection logic, clip sequencing logic, and FFmpeg stitching logic into distinct callable methods within the class, each invocable independently for unit testing
4. THE Trailer_Generator SHALL raise exceptions that include the operation name that failed, the job_id being processed, and a human-readable description of the failure cause, rather than returning None or empty results on error
5. THE Trailer_Generator SHALL log each major processing step (candidate loading, clip selection, clip cutting, concatenation) to standard output using print statements prefixed with "[Trailer_Generator]" consistent with the "[Layer N]" prefix pattern used in existing layer modules
6. THE Trailer_Generator module SHALL be importable without executing any processing logic or producing side effects at import time, enabling isolated unit testing of individual methods
