from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp  # تم التصحيح هنا

app = FastAPI(title="Video Downloader Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractionRequest(BaseModel):
    url: str

def extract_video_info(url: str):
    # إعدادات التخطي: جعل السيرفر يظهر كأنه جهاز أندرويد
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise HTTPException(status_code=400, detail="لم يتمكن السيرفر من قراءة الرابط.")
            
            formats_list = []
            formats = info.get('formats', [])
            
            for f in formats:
                # نختار الصيغ التي تحتوي على فيديو وصوت معاً
                if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    formats_list.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution', '🔥 الجودة التلقائية'),
                        'url': f.get('url')
                    })
            
            return {
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'formats': formats_list
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.post("/api/extract")
async def extract_video(request: ExtractionRequest):
    return extract_video_info(request.url)

@app.get("/")
async def root():
    return {"status": "السيرفر شغال وأندرويد مود مفعل! 🚀"}
