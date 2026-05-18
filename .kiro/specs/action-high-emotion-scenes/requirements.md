# Requirements Document

## Introduction

This feature adds a dedicated "Action / High-Emotion Scenes" extraction capability to the Microdrama Intelligence pipeline. After a video completes full pipeline processing, users can click a button to extract and generate clips specifically for action sequences and high-emotion moments. The feature operates on existing Layer 4 output (ranked candidates with drama scores, moment types, and emotion data) without re-running the full pipeline, invoking only the Layer 6 Clipping Engine on filtered candidates.

## Glossary

- **Pipeline**: The existing 6-layer Microdrama video processing system (Ingestion → Understanding → Story Intelligence → Drama Score → Episodic Sequencing → Clipping)
- **Layer_4_Output**: The JSON file produced by the DramaScoreEngine containing `ranked_candidates` with fields including `moment_types`, `drama_score`, `start_time`, `end_time`, and emotion composite scores
- **Clipping_Engine**: Layer 6 component that uses FFmpeg to cut physical video clips from `normalized.mp4` given start and end timestamps
- **Action_Scene**: A ranked candidate whose `moment_types` array contains the value "action"
- **High_Emotion_Scene**: A ranked candidate whose emotion `composite_score` meets or exceeds the Emotion_Threshold
- **Emotion_Threshold**: The minimum emotion composite score (default 0.6 on a 0.0–1.0 scale) required for a candidate to qualify as a High_Emotion_Scene
- **Processed_Job**: A job that has completed at least through Layer 4, producing a `layer4_output.json` file in the `output/{job_id}/` directory
- **Action_Emotion_Endpoint**: The FastAPI POST endpoint at `/api/v1/extract-action-scenes` that performs filtering, ranking, and clip generation
- **Action_Button**: The UI element labeled "🔥 Action / High-Emotion Scenes" displayed in the results workspace after job completion
- **Results_Workspace**: The section of the frontend UI (`static/index.html`) where pipeline output clips and metadata are displayed
- **Progress_Stream**: Newline-delimited JSON messages streamed from the server containing `status` (string) and `progress` (integer 0–100) fields

## Requirements

### Requirement 1: Display Action Button in UI

**User Story:** As a content editor, I want to see an "Action / High-Emotion Scenes" button in the results workspace after a job completes, so that I can extract action-focused clips without re-uploading the video.

#### Acceptance Criteria

1. WHEN a pipeline job completes successfully and the Results_Workspace becomes visible with series data, THE Action_Button SHALL appear in the Results_Workspace within 1 second of results rendering
2. THE Action_Button SHALL display the text "🔥 Action / High-Emotion Scenes"
3. WHILE the Results_Workspace is hidden or contains no Processed_Job series data, THE Action_Button SHALL not be rendered in the DOM
4. WHEN the Action_Button is clicked, THE UI SHALL disable the Action_Button, display a loading indicator on the button, and initiate a request to the Action_Emotion_Endpoint with the current job_id
5. IF the request to the Action_Emotion_Endpoint fails or does not respond within 30 seconds, THEN THE UI SHALL re-enable the Action_Button and display an error message indicating the request failed
6. WHILE a request to the Action_Emotion_Endpoint is in progress, THE Action_Button SHALL remain disabled to prevent duplicate requests

### Requirement 2: Job Selection for Extraction

**User Story:** As a content editor, I want the extraction to use the currently displayed job, so that I can generate action clips from the video I am reviewing.

#### Acceptance Criteria

1. WHEN the Action_Button is clicked, THE UI SHALL use the job_id of the Processed_Job currently displayed in the Results_Workspace and include it in the request body sent to the Action_Emotion_Endpoint
2. WHEN the Action_Emotion_Endpoint receives a job_id, THE Action_Emotion_Endpoint SHALL verify that `output/{job_id}/layer4_output.json` exists before performing any filtering or clip generation
3. IF the specified job_id does not have a Layer_4_Output file, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 404 with a JSON body containing the field "error" set to "Job not found or Layer 4 output missing"
4. IF the Layer_4_Output file exists but cannot be parsed as valid JSON, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 500 with a JSON body containing the field "error" indicating that the Layer 4 output file is corrupted or unreadable

### Requirement 3: Action and High-Emotion Filtering

**User Story:** As a content editor, I want the system to filter candidates for action and high-emotion content and rank them by drama score, so that I receive the most intense clips first.

#### Acceptance Criteria

1. WHEN the Action_Emotion_Endpoint receives a valid job_id, THE Action_Emotion_Endpoint SHALL load the `ranked_candidates` array from the Layer_4_Output file
2. WHEN the `ranked_candidates` array is loaded, THE Action_Emotion_Endpoint SHALL select candidates where the `moment_types` array contains "action" OR where the maximum emotion `composite_score` among emotion detections within the candidate's time range (from `start_time` to `end_time`) is greater than or equal to the Emotion_Threshold
3. WHEN candidates are selected, THE Action_Emotion_Endpoint SHALL rank the selected candidates by `drama_score` in descending order, using earliest `start_time` as tiebreaker when drama_scores are equal
4. WHEN candidates are ranked, THE Action_Emotion_Endpoint SHALL return at most the number of candidates specified by the `max_clips` parameter value (default 20), returning all matching candidates if fewer than `max_clips` qualify
5. IF no candidates meet the action or high-emotion criteria, THEN THE Action_Emotion_Endpoint SHALL return a streaming response with a final message containing an empty clips list and status "No action or high-emotion scenes found"

### Requirement 4: Clip Generation

**User Story:** As a content editor, I want physical video clips generated for the filtered scenes, so that I can preview and download them immediately.

#### Acceptance Criteria

1. WHEN candidates are filtered and ranked, THE Action_Emotion_Endpoint SHALL invoke the Clipping_Engine to cut a video clip for each selected candidate using `start_time` and `end_time` from the candidate data
2. THE Clipping_Engine SHALL read from the `normalized.mp4` file located in the `output/{job_id}/` directory
3. IF the `normalized.mp4` file does not exist in the `output/{job_id}/` directory, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 404 with a JSON body containing the field "error" set to an error message indicating the source video is missing
4. THE Action_Emotion_Endpoint SHALL store generated clips in `output/{job_id}/action_clips/` subdirectory
5. THE Action_Emotion_Endpoint SHALL name each clip file using the pattern `action_clip_{index}.mp4` where index is the 1-based position in the ranked list
6. THE Action_Emotion_Endpoint SHALL include for each clip in the response a JSON object containing the fields: `video_url` formatted as `/output/{job_id}/action_clips/{filename}`, `start_time`, `end_time`, `drama_score`, and `moment_types` copied from the candidate data
7. IF the Clipping_Engine fails to generate a clip for a candidate, THEN THE Action_Emotion_Endpoint SHALL skip that candidate, continue processing remaining candidates, and exclude the failed clip from the final response

### Requirement 5: Progress Streaming

**User Story:** As a content editor, I want to see real-time progress updates while clips are being generated, so that I know the system is working and can estimate completion time.

#### Acceptance Criteria

1. THE Action_Emotion_Endpoint SHALL return a StreamingResponse with media type "text/plain" where each message is a single line of valid JSON followed by a newline character, consistent with the main Pipeline endpoint
2. WHEN filtering begins, THE Action_Emotion_Endpoint SHALL emit a Progress_Stream message with status describing the filtering step and progress set to 5
3. WHEN each clip is being generated, THE Action_Emotion_Endpoint SHALL emit a Progress_Stream message with status identifying the clip number out of total clips and progress calculated as 10 + ((clip_index / total_clips) * 90) rounded to the nearest integer, where clip_index is the 1-based position of the clip currently being processed
4. WHEN all clips are generated, THE Action_Emotion_Endpoint SHALL emit a final Progress_Stream message with progress 100, status "Complete!", and a "result" field containing an array of clip metadata objects each including video_url, drama_score, moment_types, start_time, and end_time
5. IF an error occurs during clip generation, THEN THE Action_Emotion_Endpoint SHALL emit a Progress_Stream message containing an "error" field with a description of the failure and SHALL stop streaming

### Requirement 6: UI Results Display

**User Story:** As a content editor, I want the extracted action clips displayed using the same card format as the main pipeline results, so that I can evaluate them consistently.

#### Acceptance Criteria

1. WHEN the Action_Emotion_Endpoint begins streaming, THE UI SHALL display the progress bar and status text in the Results_Workspace, updating both values as each Progress_Stream message is received
2. WHEN a Progress_Stream message with progress equal to 100 and a "result" field containing the clips metadata array is received, THE UI SHALL render each clip using the existing premium episode card template in the order provided by the ranked array
3. WHEN the clip cards are rendered, THE UI SHALL display the section header "Action & High-Emotion Scenes" above the rendered clip cards
4. THE UI SHALL display each clip card with a video player sourced from the clip video_url, the drama_score as a numeric value, the moment_types as badge labels, and start_time and end_time displayed in HH:MM:SS format
5. IF the Action_Emotion_Endpoint stream returns an error status or the connection fails before a progress 100 message is received, THEN THE UI SHALL hide the progress indicator and display an error message indicating the extraction failed

### Requirement 7: Endpoint API Contract

**User Story:** As a developer, I want a well-defined API contract for the action extraction endpoint, so that the feature integrates consistently with the existing API and can be used by automated workflows.

#### Acceptance Criteria

1. THE Action_Emotion_Endpoint SHALL be accessible at POST /api/v1/extract-action-scenes
2. THE Action_Emotion_Endpoint SHALL accept a JSON request body with required field "job_id" of type string in UUID format
3. THE Action_Emotion_Endpoint SHALL accept an optional field "max_clips" of type integer with default value 20 and valid range 1 to 50
4. THE Action_Emotion_Endpoint SHALL accept an optional field "emotion_threshold" of type float with default value 0.6 and valid range 0.0 to 1.0
5. IF "max_clips" is outside the range 1 to 50, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating the valid range is 1 to 50
6. IF "emotion_threshold" is outside the range 0.0 to 1.0, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating the valid range is 0.0 to 1.0
7. THE Action_Emotion_Endpoint SHALL return Content-Type "text/plain" for the streaming response, consistent with the existing /api/v1/process endpoint
8. IF "job_id" is missing from the request body, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating that job_id is required
9. IF "job_id" is not a valid UUID format string, THEN THE Action_Emotion_Endpoint SHALL return HTTP status 422 with a JSON body containing the field "error" indicating that job_id must be a valid UUID
10. IF an unexpected error occurs during processing, THEN THE Action_Emotion_Endpoint SHALL emit a streaming JSON message containing the field "error" with a description of the failure, consistent with the existing /api/v1/process endpoint error format
