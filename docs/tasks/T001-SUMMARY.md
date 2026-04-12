What was implemented
- Added ffmpeg-based fallback for cutting in VideoService.cut_clip when moviepy is missing or fails at runtime.
- In main UI: added health re-check, warning banner when cutting is unavailable, and an offline fallback checkbox to opt into degraded Pollinations heuristic.
- Modified processing flow to skip actual cutting when neither moviepy nor ffmpeg are detected, but still provide placeholder files so the UI remains stable.

Why this approach
- Using ffmpeg directly via subprocess provides a lightweight and deterministic fallback when moviepy import fails in hosted environments.
- Keeping moviepy as preferred path preserves format handling when available.
- UI changes allow the app to remain usable in Streamlit Cloud while we diagnose the moviepy import problem.

Decisions & edge cases
- If moviepy fails at runtime, we try ffmpeg fallback. If ffmpeg returns non-zero exit code, we raise a clear VideoServiceError.
- Placeholders are created when cutting is disabled to avoid breaking the UI and to allow users to still download a (empty) file with metadata.

How to test
- Unit tests already cover VideoService.transcribe and cut_clip timestamp validation. Run pytest locally.
- Manually test in an environment with ffmpeg installed but without moviepy to verify subprocess path is used.

Remaining technical debt
- We currently do not probe the input video duration using ffprobe; ffmpeg fallback uses requested timestamps and ensures a minimum duration. This may cause truncated outputs if timestamps are outside range.
- Consider adding ffprobe-based duration check for more robust normalization instead of optimistic assumptions.
