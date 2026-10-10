from youtube_transcript_api import YouTubeTranscriptApi

video_id = "jNQXAC9IVRw"

try:
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    
    print("\n--- TRANSCRIPT START ---")
    for entry in transcript:
        # Use dot notation for object attributes
        text = entry.text
        start = entry.start
        mins = int(start // 60)
        secs = int(start % 60)
        print(f"[{mins:02d}:{secs:02d}] {text}")
    print("--- TRANSCRIPT END ---\n")

except Exception as e:
    print(f"Error: {e}")