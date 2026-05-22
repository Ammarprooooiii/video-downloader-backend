from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from typing import List, Dict, Optional
import traceback

# تعريف التطبيق الأساسي (تأكد من وجود هذا السطر)
app = FastAPI(title="Snaptube Backend API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    url: str

class StreamOption(BaseModel):
    quality: str
    url: str
    size: str

class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: str
    audio_options: List[StreamOption]
    video_options: List[StreamOption]

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_filesize(bytes: int) -> str:
    """Format file size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def extract_video_info(url: str) -> Dict:
    """Extract video information using yt-dlp"""
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as extract_error:
                print(f"First attempt failed: {str(extract_error)}. Trying fallback client...")
                ydl_opts['extractor_args']['youtube']['player_client'] = ['web']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_fallback:
                    info = ydl_fallback.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(
                    status_code=400, 
                    detail="يوتيوب حجب الطلب حالياً. يرجى تجربة فيديو آخر أو المحاولة لاحقاً."
                )
                
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            duration = format_duration(info.get('duration', 0))
            
            audio_options = []
            if 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none']
                seen_qualities = set()
                
                for fmt in audio_formats:
                    abr = fmt.get('abr', 0)
                    ext = fmt.get('ext', 'mp3')
                    
                    if abr:
                        quality_label = f"{int(abr)}kbps {ext.upper()}"
                    else:
                        quality_label = f"Audio {ext.upper()}"
                    
                    if quality_label not in seen_qualities:
                        seen_qualities.add(quality_label)
                        filesize = fmt.get('filesize', 0)
                        size_str = format_filesize(filesize) if filesize else "Unknown size"
                        
                        audio_options.append(StreamOption(
                            quality=quality_label,
                            url=fmt.get('url', ''),
                            size=size_str
                        ))
            
            video_options = []
            if 'formats' in info:
                video_formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                target_resolutions = ['1080p', '720p', '480p', '360p', '240p']
                seen_resolutions = set()
                
                for target_res in target_resolutions:
                    for fmt in video_formats:
                        height = fmt.get('height', 0)
                        if height:
                            res_label = f"{height}p"
                            if res_label == target_res and res_label not in seen_resolutions:
                                seen_resolutions.add(res_label)
                                ext = fmt.get('ext', 'mp4')
                                filesize = fmt.get('filesize', 0)
                                size_str = format_filesize(filesize) if filesize else "Unknown size"
                                
                                video_options.append(StreamOption(
                                    quality=f"{res_label} {ext.upper()}",
                                    url=fmt.get('url', ''),
                                    size=size_str
                                ))
                                break
                
                if not video_options:
                    for fmt in video_formats[:5]:
                        height = fmt.get('height', 0)
                        ext = fmt.get('ext', 'mp4')
                        quality_label = f"{height}p {ext.upper()}" if height else f"Video {ext.upper()}"
                        
                        if quality_label not in seen_resolutions:
                            seen_resolutions.add(quality_label)
                            filesize = fmt.get('filesize', 0)
                            size_str = format_filesize(filesize) if filesize else "Unknown size"
                            
                            video_options.append(StreamOption(
                                quality=quality_label,
                                url=fmt.get('url', ''),
                                size=size_str
                            ))
            
            return {
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'audio_options': [opt.model_dump() for opt in audio_options],
                'video_options': [opt.model_dump() for opt in video_options]
            }
            
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print("Error during extraction:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"فشل استخراج بيانات الفيديو: {str(e)}")

@app.post("/api/extract", response_model=VideoInfo)
async def extract_video(request: ExtractRequest):
    """Extract video information from a URL"""
    try:
        print(f"Received extraction request for URL: {request.url}")
        video_info = extract_video_info(request.url)
        return VideoInfo(**video_info)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print("Exception in /api/extract:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to extract video info: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Snaptube Backend API",
        "version": "1.0.0",
        "endpoints": {
            "extract": "/api/extract (POST)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
