def extract_video_info(url: str) -> Dict:
    """Extract video information using yt-dlp"""
    # تم تحديث الخيارات وتطوير آليات التخفي لتفادي حظر يوتيوب الصارم
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,  # نغيرها إلى False لكي نلتقط الخطأ الفعلي ولا نترك الكود يكمل ببيانات فارغة
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],  # التركيز على مشغلات الجوال لأن حمايتها أخف
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
                # محاولة أخيرة بمشغل مختلف إذا فشلت الأولى
                print(f"First attempt failed: {str(extract_error)}. Trying fallback client...")
                ydl_opts['extractor_args']['youtube']['player_client'] = ['web']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_fallback:
                    info = ydl_fallback.extract_info(url, download=False)
            
            # التأكد بشكل صارم أن يوتيوب أرجع بيانات وليس قيم فارغة
            if info is None:
                raise HTTPException(
                    status_code=400, 
                    detail="يوتيوب يطلب تسجيل الدخول حالياً لتأكيد أنك لست روبوت. يرجى تجربة رابط فيديو آخر أو المحاولة لاحقاً."
                )
                
            # Extract basic info
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            duration = format_duration(info.get('duration', 0))
            
            # Extract audio options
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
            
            # Extract video options
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
