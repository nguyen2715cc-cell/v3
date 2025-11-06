# Video Generation Mystery - Investigation Report

## Executive Summary

**ISSUE RESOLVED**: Videos were being downloaded successfully but not appearing in Google Labs Flow UI because of a **critical bug in ProjectID configuration**.

**Root Cause**: Hard-coded `DEFAULT_PROJECT_ID` was overriding user configuration, causing all videos to be created in the wrong project.

---

## Investigation Findings

### Question 1: Are videos FAKE or REAL?

**Answer: Videos are 100% REAL from Google Labs API**

**Evidence:**
1. ✅ Videos are downloaded from actual Google API URLs (`fifeUrl` from API response)
2. ✅ Download uses `requests.get()` to fetch from Google's servers
3. ✅ No mock/fake video generation exists in codebase
4. ✅ No local ffmpeg video generation (ffmpeg is only used for thumbnail creation)

**Code Proof:**
```python
# services/labs_flow_service.py, line 263-279
def batch_check_operations(self, op_names: List[str])->Dict[str,Dict]:
    data=self._post(BATCH_CHECK_URL, self._wrap_ops(op_names))  # ← Real API call
    urls=_collect_urls_any(item.get("response",{}))  # ← Extract real URLs
```

```python
# ui/text2video_panel_impl.py, line 623-640
video_url = video_info.get('fifeUrl', '')  # ← Google's signed URL
if self._download(video_url, fp):  # ← Downloads from Google
```

```python
# services/utils/video_downloader.py, line 8-22
def download(self, url: str, output_path: str, timeout=300):
    with requests.get(url, stream=True, timeout=timeout) as r:  # ← Real HTTP download
        r.raise_for_status()
```

---

### Question 2: Why videos don't appear in Google Labs UI?

**Answer: PROJECT ID MISMATCH BUG**

**The Bug:**
In `services/labs_flow_service.py`, lines 5-24 had a critical ordering error:

```python
# BUGGY CODE (BEFORE FIX):
# Lines 5-15: Try to load config and set DEFAULT_PROJECT_ID
try:
    _cfg_pid = _cfg.get("default_project_id")
    if _cfg_pid:
        DEFAULT_PROJECT_ID = _cfg_pid  # ← Set to user's project ID
except Exception:
    pass

# Line 24: UNCONDITIONALLY override it!
DEFAULT_PROJECT_ID = "87b19267-13d6-49cd-a7ed-db19a90c9339"  # ← BUG: Overrides user config!
```

**Result:**
- User's actual project: `9bb9b09b-b883-4aef-a90f-fa264ba4b6e0`
- Project being used: `87b19267-13d6-49cd-a7ed-db19a90c9339` (hard-coded)
- Videos created in: `87b19267...` (wrong project!)
- User looking in: `9bb9b09b...` (correct project, but no videos there!)

**Impact:**
Every API request sent `clientContext.projectId = "87b19267..."` instead of the user's actual project ID.

---

### Question 3: Video file source trace

**Complete video generation flow:**

```
1. User triggers video generation
   ↓
2. ui/text2video_panel_impl.py calls LabsClient.start_one()
   ↓
3. services/labs_flow_service.py sends POST to Google API
   URL: https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText
   Body: {
     "requests": [...],
     "clientContext": {"projectId": "87b19267-13d6-49cd-a7ed-db19a90c9339"}  ← BUG HERE!
   }
   ↓
4. Google API creates videos in project 87b19267... (wrong project)
   Returns: operation_names for polling
   ↓
5. Code polls with batch_check_operations()
   ↓
6. API returns: {
     "operation": {
       "metadata": {
         "video": {
           "fifeUrl": "https://generativelanguage.googleapis.com/v1beta/files/..."
         }
       }
     }
   }
   ↓
7. Code extracts fifeUrl (line 623 of text2video_panel_impl.py)
   ↓
8. VideoDownloader.download() fetches video from Google's URL
   ↓
9. Video saved locally ✓
   BUT: Video exists in project 87b19267... (not visible in user's UI)
```

---

## Fixes Implemented

### Fix 1: ProjectID Configuration Bug ✓

**Changed:** `services/labs_flow_service.py` and `services/google/labs_flow_client.py`

```python
# FIXED CODE (AFTER):
# Set fallback first
DEFAULT_PROJECT_ID = "87b19267-13d6-49cd-a7ed-db19a90c9339"

# Then override from config (comes AFTER fallback)
try:
    _cfg_pid = _cfg.get("default_project_id")
    if _cfg_pid:
        DEFAULT_PROJECT_ID = _cfg_pid  # ← Now this actually works!
except Exception:
    pass
```

**Impact:** Users can now set their own `default_project_id` in config and it will be respected.

---

### Fix 2: Comprehensive Debug Logging ✓

**Added logging to trace:**

1. **ProjectID being used** (ui/text2video_panel_impl.py, line 497-503)
```python
self.log.emit(f"[DEBUG] Using ProjectID: {project_id}")
if project_id == DEFAULT_PROJECT_ID:
    self.log.emit(f"[DEBUG] Using default ProjectID (not configured in settings)")
```

2. **API endpoints and requests** (services/labs_flow_service.py, line 113-117)
```python
project_id = payload.get("clientContext", {}).get("projectId", "NONE")
self.debug_log(f"[DEBUG] API Call: {url}")
self.debug_log(f"[DEBUG] ProjectID: {project_id}")
```

3. **Video URLs from API** (ui/text2video_panel_impl.py, line 643-645)
```python
self.log.emit(f"[DEBUG] Video URL domain: {video_url.split('/')[2]}")
self.log.emit(f"[DEBUG] Full video URL: {video_url[:100]}...")
```

4. **Download sources** (services/utils/video_downloader.py, line 10-13)
```python
self.log(f"[DEBUG] Downloading from: {url[:100]}...")
self.log(f"[DEBUG] Content-Length: {total} bytes")
```

---

### Fix 3: Video Verification Script ✓

**Created:** `verify_video_source.py`

**Usage:**
```bash
# Basic verification
python verify_video_source.py path/to/video.mp4

# Full verification with API
python verify_video_source.py video.mp4 \
  --operation-name "projects/123/operations/abc" \
  --token "YOUR_BEARER_TOKEN" \
  --project-id "9bb9b09b-b883-4aef-a90f-fa264ba4b6e0"

# JSON output
python verify_video_source.py video.mp4 --json
```

**What it checks:**
- ✓ Video file exists and size
- ✓ Valid MP4 file signature
- ✓ Operation exists in Google Labs API
- ✓ Video URL domain (verifies it's from Google)
- ✓ ProjectID ownership match

---

## User Action Required

To fix the issue for existing users:

### Step 1: Update configuration

Edit `~/.veo_image2video_cfg.json` or use the app's settings:

```json
{
  "tokens": ["your_token_here"],
  "default_project_id": "9bb9b09b-b883-4aef-a90f-fa264ba4b6e0"
}
```

### Step 2: Verify fix

With debug logging enabled, you'll see:

```
[DEBUG] Using ProjectID: 9bb9b09b-b883-4aef-a90f-fa264ba4b6e0
[DEBUG] Using custom ProjectID from config
[DEBUG] API Call: https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText
[DEBUG] ProjectID: 9bb9b09b-b883-4aef-a90f-fa264ba4b6e0
```

### Step 3: New videos will appear in UI

All new videos generated after the fix will appear in the correct project at:
`https://labs.google/fx/vi/tools/flow/project/9bb9b09b-b883-4aef-a90f-fa264ba4b6e0`

---

## Acceptance Criteria - ALL MET ✓

- [x] Determine if videos are from Google API or generated locally
  - **Answer: 100% from Google API, not fake/mock**

- [x] Identify why videos don't appear in Google Labs UI
  - **Answer: ProjectID configuration bug causing videos to be created in wrong project**

- [x] Provide clear explanation with code evidence
  - **Answer: Complete code trace provided above**

- [x] Propose concrete fixes with PR-ready code
  - **Answer: All fixes implemented and tested**

---

## Technical Details

### Modified Files:
1. `services/labs_flow_service.py` - Fixed ProjectID bug, added debug logging
2. `services/google/labs_flow_client.py` - Fixed ProjectID bug
3. `ui/text2video_panel_impl.py` - Added ProjectID and URL debug logging
4. `services/utils/video_downloader.py` - Added download source logging
5. `verify_video_source.py` - NEW: Verification script

### API Endpoints Used:
- T2V: `https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText`
- I2V: `https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoStartImage`
- Status: `https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus`

### Video URL Format:
Videos are downloaded from Google's signed URLs in format:
`https://generativelanguage.googleapis.com/v1beta/files/[FILE_ID]`

These are temporary signed URLs that expire after a certain time.

---

## Conclusion

**The mystery is solved:**

1. ✅ Videos are REAL (from Google API, not fake)
2. ✅ ProjectID bug identified and fixed
3. ✅ Debug logging added for troubleshooting
4. ✅ Verification script created

**Next steps for users:**
1. Update to latest code (this PR)
2. Configure correct `default_project_id` in settings
3. Generate new videos
4. Videos will now appear in Google Labs UI ✓
