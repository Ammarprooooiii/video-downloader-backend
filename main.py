def extract_video_info(url: str) -> Dict:
    """Extract video information using yt-dlp"""
    # تم تحديث الخيارات بالكامل بإضافة الـ User-Agent وإعدادات التخفي لتخطي الحجب
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['webpage']
            }
        },
        # أسطر التخفي السحرية لمنع السيرفر من الظهور كبوت:
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # التأكد من أن يوتيوب أعطانا معلومات كاملة ولم يحجب الطلب داخلياً
            if not info:
                raise Exception("YouTube blocked the request or returned empty data. Try again.")
                
            # Extract basic info
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            duration = format_duration(info.get('duration', 0))
            
            # Extract audio options
            audio_options = []
            if 'formats' in info:
                # Get unique audio formats
                audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none']
                seen_qualities = set()
                
                for fmt in audio_formats:
                    abr = fmt.get('abr', 0)
                    ext = fmt.get('ext', 'mp3')
                    
                    # Create quality label
                    if abr:
                        quality_label = f"{int(abr)}kbps {ext.upper()}"
                    else:
                        quality_label = f"Audio {ext.upper()}"
                    
                    if quality_label not in seen_qualities:
                        seen_qualities.add(quality_label)
                        filesize = fmt.get('filesize', 0)
                        if filesize:
                            size_str = format_filesize(filesize)
                        else:
                            size_str = "Unknown size"
                        
                        audio_options.append(StreamOption(
                            quality=quality_label,
                            url=fmt.get('url', ''),
                            size=size_str
                        ))
            
            # Extract video options
            video_options = []
            if 'formats' in info:
                # Get video formats with specific resolutions
                video_formats = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                
                # Prioritize common resolutions
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
                                if filesize:
                                    size_str = format_filesize(filesize)
                                else:
                                    size_str = "Unknown size"
                                
                                video_options.append(StreamOption(
                                    quality=f"{res_label} {ext.upper()}",
                                    url=fmt.get('url', ''),
                                    size=size_str
                                ))
                                break
                
                # If no specific resolutions found, add available ones
                if not video_options:
                    for fmt in video_formats[:5]:  # Limit to first 5
                        height = fmt.get('height', 0)
                        ext = fmt.get('ext', 'mp4')
                        if height:
                            quality_label = f"{height}p {ext.upper()}"
                        else:
                            quality_label = f"Video {ext.upper()}"
                        
                        if quality_label not in seen_resolutions:
                            seen_resolutions.add(quality_label)
                            filesize = fmt.get('filesize', 0)
                            if filesize:
                                size_str = format_filesize(filesize)
                            else:
                                size_str = "Unknown size"
                            
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
            
    except Exception as e:
        print("Error during extraction:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
