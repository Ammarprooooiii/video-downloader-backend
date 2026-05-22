from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pytube import YouTube # استخدمنا مكتبة pytube وهي أخف

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

@app.post("/api/extract")
async def extract_video(request: ExtractionRequest):
    try:
        # إنشاء كائن يوتيوب مع تحديد هوية متصفح موبايل
        yt = YouTube(request.url)
        
        # استخراج البيانات
        title = yt.title
        thumbnail = yt.thumbnail_url
        duration = yt.length
        
        # الحصول على الروابط المتاحة
        formats_list = []
        for stream in yt.streams.filter(progressive=True, file_extension='mp4'):
            formats_list.append({
                'format_id': stream.itag,
                'ext': stream.mime_type.split('/')[-1],
                'resolution': stream.resolution or '720p',
                'url': stream.url
            })
            
        return {
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats_list
        }
        
    except Exception as e:
        # إذا فشل، نرجع خطأ واضح للتطبيق عشان يعرضه للمستخدم
        raise HTTPException(status_code=400, detail=f"تعذر الاستخراج: {str(e)}")

@app.get("/")
async def root():
    return {"status": "سيرفر الأندرويد الاحترافي شغال! 🚀"}
