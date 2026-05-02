# trend_engine/youtube_trends.py

from core.llm import call_llm

async def get_trending_niches():
    return await call_llm(
        "You are a viral content analyst for YouTube.",
        """
Find trending African YouTube video ideas that are likely to go viral.
Focus on:
- high engagement topics
- emotional storytelling
- curiosity hooks
Return 10 ideas with titles.
"""
    )# content_factory/script_writer.py

from core.llm import call_llm

async def write_script(topic):
    return await call_llm(
        "You are a viral YouTube scriptwriter.",
        f"""
Write a 60–180 second YouTube script.

Requirements:
- strong hook in first 3 seconds
- emotional storytelling
- simple English
- African audience focus
- retention-based pacing

Topic: {topic}
"""
    )# video_engine/tts_voice.py

from gtts import gTTS

def text_to_speech(text, filename="output.mp3"):
    tts = gTTS(text=text, lang="en")
    tts.save(filename)
    return filename# video_engine/video_builder.py

from moviepy.editor import *

def build_video(audio_path, image_path, output="final.mp4"):
    audio = AudioFileClip(audio_path)
    image = ImageClip(image_path).set_duration(audio.duration)

    video = image.set_audio(audio)
    video.write_videofile(output, fps=24)

    return output# thumbnail_engine/thumbnail_ai.py

from core.llm import call_llm

async def generate_thumbnail_text(topic):
    return await call_llm(
        "You are a YouTube thumbnail expert.",
        f"Create a short viral thumbnail text for: {topic}"
    )# uploader/youtube_upload.py

from googleapiclient.discovery import build

def upload_video(youtube, file, title, description):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["africa", "viral", "trending"],
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=file
    )

    return request.execute()# growth_engine/seo_tags.py

from core.llm import call_llm

async def generate_tags(topic):
    return await call_llm(
        "You are a YouTube SEO expert.",
        f"Generate high-viral SEO tags for: {topic}"
    )# main.py

from trend_engine.youtube_trends import get_trending_niches
from content_factory.script_writer import write_script

async def run_pipeline():

    trends = await get_trending_niches()

    script = await write_script(trends)

    print("VIDEO SCRIPT GENERATED")
    print(script)