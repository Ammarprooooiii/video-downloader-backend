from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt-dlp

app = FastAPI(title="Video Downloader Backend")

# السماح للتطبيق بالاتصال بالسيرفر بدون مشاكل CORS
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
    # إعدادات متطورة لتشبه متصفح حقيقي وتتخطى حظر يوتيوب
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    
    try:
        with yt-dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # حماية في حال لم يرجع يوتيوب أي بيانات
            if info is None:
                raise HTTPException(status_code=400, detail="لم يتمكن السيرفر من قراءة بيانات الفيديو، قد يكون الرابط خاصاً أو محظوراً.")
            
            # استخراج الخيارات المتاحة بأمان (السطر 81 القديم اللي كان يسبب المشكلة)
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            
            # تجهيز روابط الفيديو والصوت المتاحة
            formats_list = []
            formats = info.get('formats', [])
            
            for f in formats:
                # تصفية الروابط التي تحتوي على صوت وفيديو معاً وتعمل مباشرة
                if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    formats_list.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution', '🔥 الجودة التلقائية'),
                        'url': f.get('url')
                    })
            
            # إذا لم نجد صيغ مدمجة، نضع الرابط الأساسي كخيار احتياطي
            if not formats_list and info.get('url'):
                formats_list.append({
                    'format_id': 'default',
                    'ext': info.get('ext', 'mp4'),
                    'resolution': 'Default Resolution',
                    'url': info.get('url')
                })

            return {
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'formats': formats_list
            }
            
    except Exception as e:
        # تحويل الخطأ إلى 400 واضح بدلاً من انهيار السيرفر بخطأ 500
        raise HTTPException(status_code=400, detail=f"خطأ أثناء استخراج الفيديو: {str(e)}")

@app.post("/api/extract")
async def extract_video(request: ExtractionRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="الرجاء إرسال رابط صحيح")
    return extract_video_info(request.url)

@app.get("/")
async def root():
    return {"status": "السيرفر يعمل بنجاح وكود التخطي مفعل جاهز يا عمار! 🚀"}
