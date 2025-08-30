#!/usr/bin/env python3

import argparse
import subprocess
import re
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Preset configurations for different detection sensitivities
PRESETS = {
    'high': {
        'luma': 40,           # Higher threshold = more sensitive to darkness
        'duration': 0.5,      # Shorter minimum duration = more scenes
        'interval': 0.5,      # More frequent frame extraction
        'skip_credits': True, # Enable credits filtering
        'credits_sample_interval': 20,
        'description': 'High sensitivity - detects most dark scenes, filters credits'
    },
    'medium': {
        'luma': 30,           # Default threshold
        'duration': 1.0,      # Default minimum duration
        'interval': 1.0,      # Default frame extraction
        'skip_credits': True, # Enable credits filtering
        'credits_sample_interval': 30,
        'description': 'Balanced detection with credits filtering (recommended)'
    },
    'low': {
        'luma': 20,           # Lower threshold = less sensitive, only very dark scenes
        'duration': 2.0,      # Longer minimum duration = fewer scenes
        'interval': 2.0,      # Less frequent frame extraction
        'skip_credits': False, # No credits filtering
        'credits_sample_interval': 30,
        'description': 'Low sensitivity - only very dark, longer scenes'
    },
    'quick': {
        'luma': 25,           # Quick assessment threshold
        'duration': 1.5,      # Moderate duration requirement
        'interval': 3.0,      # Extract fewer frames for speed
        'skip_credits': False, # Skip OCR for speed
        'credits_sample_interval': 60,
        'description': 'Fast processing for quick assessment'
    },
    'tv': {
        'luma': 35,           # TV shows often have more varied lighting
        'duration': 0.8,      # Shorter scenes typical in TV
        'interval': 1.0,      # Standard frame extraction
        'skip_credits': True, # TV shows have opening/closing credits
        'credits_sample_interval': 15, # TV credits are shorter
        'description': 'Optimized for TV shows and series'
    },
    'movie': {
        'luma': 28,           # Movies often have more cinematic dark scenes
        'duration': 1.5,      # Longer scenes typical in movies
        'interval': 1.5,      # Moderate frame extraction
        'skip_credits': True, # Movies have credits
        'credits_sample_interval': 30,
        'description': 'Optimized for movies and films'
    }
}

def get_preset_config(preset_name):
    """Get configuration for a preset"""
    return PRESETS.get(preset_name.lower())

def list_presets():
    """Return formatted list of available presets"""
    preset_list = []
    for name, config in PRESETS.items():
        preset_list.append(f"  {name:8} - {config['description']}")
    return "\n".join(preset_list)

def check_dependencies(require_ocr=False):
    """Check that required external tools are available"""
    required_tools = ['ffmpeg', 'ffprobe']
    if require_ocr:
        required_tools.append('tesseract')
    
    missing_tools = []
    
    for tool in required_tools:
        try:
            if tool == 'tesseract':
                subprocess.run([tool, '--version'], capture_output=True, check=True)
            else:
                subprocess.run([tool, '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Error: Missing required tools: {', '.join(missing_tools)}")
        print("Please install the following tools:")
        for tool in missing_tools:
            if tool == 'tesseract':
                print(f"  - {tool} (for text detection)")
                print("    On macOS: brew install tesseract")
                print("    On Ubuntu/Debian: sudo apt install tesseract-ocr")
            else:
                print(f"  - {tool}")
        if 'ffmpeg' in missing_tools or 'ffprobe' in missing_tools:
            print("\nFFmpeg installation:")
            print("On macOS: brew install ffmpeg")
            print("On Ubuntu/Debian: sudo apt install ffmpeg")
            print("On other systems, visit: https://ffmpeg.org/download.html")
        sys.exit(1)

def log(message):
    """Print timestamped log message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def run_ffmpeg(cmd, description="Running FFmpeg"):
    """Run FFmpeg command and return output"""
    log(f"{description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stderr  # FFmpeg outputs info to stderr
    except subprocess.CalledProcessError as e:
        log(f"FFmpeg error: {e.stderr}")
        raise

def get_video_info(file_path):
    """Get video duration and FPS"""
    log("Getting video information...")
    
    # Get duration
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
           '-of', 'csv=p=0', str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 0
    
    # Get FPS
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'stream=r_frame_rate', 
           '-of', 'csv=p=0', str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    fps_str = result.stdout.strip().split('\n')[0] if result.stdout.strip() else "0/1"
    
    # Convert fractional fps to decimal
    if '/' in fps_str:
        num, den = fps_str.split('/')
        fps = float(num) / float(den) if float(den) != 0 else 0
    else:
        fps = float(fps_str) if fps_str else 0
    
    log(f"Video duration: {duration:.1f}s, FPS: {fps:.2f}")
    return duration, fps

def analyze_brightness(file_path, output_dir, experimental_establishing=False, rich_analysis=False, audio_correlation=False):
    """Analyze video brightness and optionally motion/scene characteristics"""
    if audio_correlation:
        log("Analyzing video with audio-visual correlation...")
    elif rich_analysis:
        log("Analyzing video with comprehensive visual feature detection...")
    elif experimental_establishing:
        log("Analyzing video with experimental establishing shot detection...")
    else:
        log("Analyzing video brightness...")
    
    analysis_file = output_dir / "brightness_analysis.txt"
    
    if audio_correlation:
        # Audio-visual correlation analysis:
        # - showinfo: frame info with luminance
        # - astats: audio statistics per frame
        # - volumedetect: volume level analysis
        cmd = [
            'ffmpeg', '-i', str(file_path),
            '-vf', 'showinfo',
            '-af', 'astats=metadata=1:reset=1,aformat=sample_fmts=fltp',
            '-f', 'null', '-'
        ]
    elif rich_analysis:
        # Comprehensive visual analysis combining multiple attributes:
        # - showinfo: frame info with luminance/color stats
        # - entropy: image complexity/randomness
        # - signalstats: color distribution and saturation
        # - sobel: edge detection for composition analysis
        # - freezedetect: detect static frames
        cmd = [
            'ffmpeg', '-i', str(file_path),
            '-vf', 'showinfo,entropy,signalstats=stat=tout+vrep+brng,sobel,freezedetect=n=-60dB:d=0.5',
            '-f', 'null', '-'
        ]
    elif experimental_establishing:
        # Enhanced filter chain for establishing shot detection:
        # - showinfo: basic frame info with luminance
        # - sobel: edge detection (more edges = more detail/wide shots)
        # - select with scene change detection
        cmd = [
            'ffmpeg', '-i', str(file_path),
            '-vf', 'showinfo,sobel,metadata=print:file=-',
            '-f', 'null', '-'
        ]
    else:
        # Standard brightness analysis
        cmd = [
            'ffmpeg', '-i', str(file_path),
            '-vf', 'showinfo',
            '-f', 'null', '-'
        ]
    
    with open(analysis_file, 'w') as f:
        process = subprocess.run(cmd, stderr=f, text=True)
    
    if process.returncode != 0:
        raise RuntimeError("FFmpeg analysis failed")
    
    log(f"Analysis complete, output saved to {analysis_file}")
    return analysis_file

def detect_text_regions(file_path, output_dir, sample_interval=30):
    """Detect text-heavy regions in video (likely credits) using OCR"""
    log("Detecting text regions (credits) in video...")
    
    text_analysis_file = output_dir / "text_analysis.txt"
    
    # Sample frames at intervals and run OCR
    cmd = [
        'ffmpeg', '-i', str(file_path),
        '-vf', f'fps=1/{sample_interval},ocr',
        '-f', 'null', '-'
    ]
    
    try:
        with open(text_analysis_file, 'w') as f:
            process = subprocess.run(cmd, stderr=f, text=True)
        
        if process.returncode != 0:
            log("Warning: Text detection failed, credits filtering disabled")
            return []
        
    except Exception as e:
        log(f"Warning: Text detection error ({e}), credits filtering disabled")
        return []
    
    # Parse OCR results to find text-heavy regions
    text_regions = parse_text_analysis(text_analysis_file, sample_interval)
    log(f"Found {len(text_regions)} potential credit regions")
    
    return text_regions

def parse_text_analysis(analysis_file, sample_interval):
    """Parse OCR output to identify text-heavy regions"""
    text_regions = []
    
    try:
        with open(analysis_file, 'r') as f:
            content = f.read()
        
        # Look for OCR output patterns in FFmpeg stderr
        # OCR filter outputs detected text with timestamps
        ocr_pattern = r'pts_time:([0-9]*\.?[0-9]+).*lavfi\.ocr\.text=([^\]]+)'
        
        text_timestamps = {}
        for match in re.finditer(ocr_pattern, content):
            timestamp = float(match.group(1))
            text = match.group(2).strip()
            
            # Count significant text (ignore short/noise text)
            if len(text) > 10 and any(c.isalpha() for c in text):
                text_timestamps[timestamp] = len(text)
        
        if not text_timestamps:
            return text_regions
        
        # Find regions with high text density
        sorted_times = sorted(text_timestamps.keys())
        
        # Group consecutive high-text frames
        current_start = None
        text_density_threshold = 50  # characters
        
        for timestamp in sorted_times:
            text_length = text_timestamps[timestamp]
            
            if text_length >= text_density_threshold:
                if current_start is None:
                    current_start = timestamp
            else:
                if current_start is not None:
                    # End of text region
                    text_regions.append((current_start, timestamp))
                    current_start = None
        
        # Don't forget the last region
        if current_start is not None:
            text_regions.append((current_start, sorted_times[-1] + sample_interval))
        
    except Exception as e:
        log(f"Warning: Error parsing text analysis: {e}")
    
    return text_regions

def extract_night_timestamps(analysis_file, luma_threshold, experimental_establishing=False, audio_correlation=False, quiet_threshold=-40.0, loud_threshold=-10.0, audio_mode='both'):
    """Parse FFmpeg output to find dark frames, optionally filtering for establishing shots or audio correlation"""
    if audio_correlation:
        log("Extracting audio-correlated night scene timestamps...")
        return extract_audio_correlated_timestamps(analysis_file, luma_threshold, quiet_threshold, loud_threshold, audio_mode)
    elif experimental_establishing:
        log("Extracting night establishing shot timestamps...")
        return extract_establishing_shot_timestamps(analysis_file, luma_threshold)
    else:
        log("Extracting night scene timestamps...")
        return extract_basic_night_timestamps(analysis_file, luma_threshold)

def extract_basic_night_timestamps(analysis_file, luma_threshold):
    """Basic night scene detection by brightness only"""
    timestamps = []
    
    # Regex patterns
    showinfo_pattern = r'Parsed_showinfo.*pts_time:([0-9]*\.?[0-9]+).*mean:\[([0-9]+)'
    
    with open(analysis_file, 'r') as f:
        for line in f:
            match = re.search(showinfo_pattern, line)
            if match:
                timestamp = float(match.group(1))
                mean_luma = int(match.group(2))
                
                if mean_luma < luma_threshold:
                    timestamps.append(timestamp)
    
    log(f"Found {len(timestamps)} dark frames (luma < {luma_threshold})")
    return timestamps

def extract_establishing_shot_timestamps(analysis_file, luma_threshold):
    """Experimental: Detect night establishing shots using brightness + visual complexity"""
    timestamps = []
    frame_data = []
    
    # Parse both showinfo and metadata for enhanced analysis
    showinfo_pattern = r'Parsed_showinfo.*pts_time:([0-9]*\.?[0-9]+).*mean:\[([0-9]+)'
    
    with open(analysis_file, 'r') as f:
        lines = f.readlines()
    
    # Extract frame data
    for i, line in enumerate(lines):
        showinfo_match = re.search(showinfo_pattern, line)
        if showinfo_match:
            timestamp = float(showinfo_match.group(1))
            mean_luma = int(showinfo_match.group(2))
            
            # Look for edge detection metadata in surrounding lines
            edge_complexity = 0
            for j in range(max(0, i-2), min(len(lines), i+3)):
                if 'sobel' in lines[j].lower() or 'edge' in lines[j].lower():
                    # Extract edge detection metrics if available
                    edge_match = re.search(r'edge.*:([0-9.]+)', lines[j])
                    if edge_match:
                        edge_complexity = float(edge_match.group(1))
                        break
            
            frame_data.append({
                'timestamp': timestamp,
                'luma': mean_luma,
                'edges': edge_complexity
            })
    
    if not frame_data:
        log("No frame data found for establishing shot analysis")
        return timestamps
    
    # Calculate thresholds based on data distribution
    edge_values = [f['edges'] for f in frame_data if f['edges'] > 0]
    if edge_values:
        # Higher edge count suggests more detail (wider shots vs close-ups)
        edge_threshold = sum(edge_values) / len(edge_values) * 1.2  # 20% above average
        log(f"Using edge complexity threshold: {edge_threshold:.2f}")
    else:
        edge_threshold = 0
        log("No edge data available, falling back to brightness-only detection")
    
    # Filter for night establishing shots
    for frame in frame_data:
        is_dark = frame['luma'] < luma_threshold
        is_complex = frame['edges'] >= edge_threshold if edge_threshold > 0 else True
        
        if is_dark and is_complex:
            timestamps.append(frame['timestamp'])
    
    log(f"Found {len(timestamps)} potential night establishing shots")
    log(f"  - Dark frames (luma < {luma_threshold}): {sum(1 for f in frame_data if f['luma'] < luma_threshold)}")
    log(f"  - Complex frames (edges >= {edge_threshold:.2f}): {sum(1 for f in frame_data if f['edges'] >= edge_threshold)}")
    
    return timestamps

def extract_audio_correlated_timestamps(analysis_file, luma_threshold, quiet_threshold, loud_threshold, audio_mode):
    """Extract dark scenes correlated with specific audio volume levels"""
    timestamps = []
    
    # Regex patterns for parsing both video and audio metadata
    showinfo_pattern = r'Parsed_showinfo.*pts_time:([0-9]*\.?[0-9]+).*mean:\[([0-9]+)'
    # Audio RMS level pattern from astats filter
    audio_rms_pattern = r'lavfi\.astats\.Overall\.RMS_level=([+-]?[0-9]*\.?[0-9]+)'
    
    with open(analysis_file, 'r') as f:
        lines = f.readlines()
    
    # Parse frame data with audio correlation
    frame_data = []
    current_timestamp = None
    current_luma = None
    
    for i, line in enumerate(lines):
        # Check for video frame info
        showinfo_match = re.search(showinfo_pattern, line)
        if showinfo_match:
            current_timestamp = float(showinfo_match.group(1))
            current_luma = int(showinfo_match.group(2))
        
        # Check for audio RMS level in surrounding lines
        if current_timestamp is not None and current_luma is not None:
            audio_rms = None
            # Look for audio stats in nearby lines (FFmpeg interleaves output)
            for j in range(max(0, i-5), min(len(lines), i+6)):
                audio_match = re.search(audio_rms_pattern, lines[j])
                if audio_match:
                    audio_rms = float(audio_match.group(1))
                    break
            
            if audio_rms is not None:
                frame_data.append({
                    'timestamp': current_timestamp,
                    'luma': current_luma,
                    'audio_rms': audio_rms
                })
                current_timestamp = None
                current_luma = None
    
    if not frame_data:
        log("No audio-visual correlation data found")
        return timestamps
    
    # Filter based on brightness and audio criteria
    for frame in frame_data:
        is_dark = frame['luma'] < luma_threshold
        audio_rms = frame['audio_rms']
        
        # Determine if audio level matches criteria
        is_quiet = audio_rms < quiet_threshold
        is_loud = audio_rms > loud_threshold
        
        audio_matches = False
        if audio_mode == 'quiet' and is_quiet:
            audio_matches = True
        elif audio_mode == 'loud' and is_loud:
            audio_matches = True
        elif audio_mode == 'both' and (is_quiet or is_loud):
            audio_matches = True
        
        if is_dark and audio_matches:
            timestamps.append(frame['timestamp'])
    
    log(f"Found {len(timestamps)} dark scenes with {audio_mode} audio")
    log(f"  - Audio thresholds: quiet < {quiet_threshold}dB, loud > {loud_threshold}dB")
    
    return timestamps

def filter_credits_from_scenes(scenes, text_regions, video_duration):
    """Remove scenes that overlap with detected credit regions"""
    if not text_regions:
        return scenes
    
    log("Filtering out credit sequences from night scenes...")
    
    # Identify opening and closing credits
    opening_credits = []
    closing_credits = []
    
    for start, end in text_regions:
        # Opening credits: within first 10% of video
        if start < video_duration * 0.1:
            opening_credits.append((start, end))
        # Closing credits: within last 15% of video
        elif start > video_duration * 0.85:
            closing_credits.append((start, end))
    
    # Merge overlapping credit regions
    def merge_regions(regions):
        if not regions:
            return []
        regions.sort()
        merged = [regions[0]]
        for start, end in regions[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged
    
    opening_credits = merge_regions(opening_credits)
    closing_credits = merge_regions(closing_credits)
    
    all_credits = opening_credits + closing_credits
    
    if opening_credits:
        log(f"Found opening credits: {len(opening_credits)} regions")
    if closing_credits:
        log(f"Found closing credits: {len(closing_credits)} regions")
    
    # Filter scenes that don't overlap with credits
    filtered_scenes = []
    filtered_count = 0
    
    for scene_start, scene_end in scenes:
        overlaps_with_credits = False
        
        for credit_start, credit_end in all_credits:
            # Check for overlap: scenes overlap if they don't end before the other starts
            if not (scene_end <= credit_start or scene_start >= credit_end):
                overlaps_with_credits = True
                break
        
        if not overlaps_with_credits:
            filtered_scenes.append((scene_start, scene_end))
        else:
            filtered_count += 1
    
    log(f"Filtered out {filtered_count} scenes overlapping with credits")
    log(f"Remaining scenes: {len(filtered_scenes)}")
    
    return filtered_scenes

def create_scene_segments(timestamps, min_duration):
    """Group timestamps into continuous scenes"""
    log("Creating scene segments...")
    
    if not timestamps:
        return []
    
    timestamps.sort()
    scenes = []
    current_start = timestamps[0]
    current_end = timestamps[0]
    
    for i in range(1, len(timestamps)):
        # If gap is small, extend current scene
        if timestamps[i] - current_end <= min_duration * 2:
            current_end = timestamps[i]
        else:
            # Save current scene if it meets minimum duration
            if current_end - current_start >= min_duration:
                scenes.append((current_start, current_end))
            current_start = timestamps[i]
            current_end = timestamps[i]
    
    # Don't forget the last scene
    if current_end - current_start >= min_duration:
        scenes.append((current_start, current_end))
    
    log(f"Created {len(scenes)} night scenes")
    return scenes

def extract_video_segments(scenes, input_file, output_dir, quality, format_ext, extract_frames, frame_interval):
    """Extract video segments for each scene"""
    if not scenes:
        log("No scenes to extract")
        return
    
    log("Extracting night scene videos...")
    filename = Path(input_file).stem
    
    for i, (start_time, end_time) in enumerate(scenes, 1):
        duration = end_time - start_time
        output_file = output_dir / f"night_scene_{i:03d}_{filename}.{format_ext}"
        
        log(f"Extracting scene {i}: {start_time:.3f}s - {end_time:.3f}s ({duration:.3f}s)")
        
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'warning',
            '-ss', str(start_time),
            '-i', str(input_file),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-crf', str(quality),
            '-c:a', 'aac',
            '-avoid_negative_ts', 'make_zero',
            str(output_file)
        ]
        
        subprocess.run(cmd, check=True)
        
        if extract_frames:
            extract_scene_frames(start_time, end_time, i, filename, 
                               input_file, output_dir, frame_interval)

def extract_scene_frames(start_time, end_time, scene_num, filename, input_file, output_dir, frame_interval):
    """Extract individual frames from a scene"""
    frames_dir = output_dir / "frames" / f"scene_{scene_num:03d}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    duration = end_time - start_time
    log(f"Extracting frames from scene {scene_num} (every {frame_interval}s)")
    
    cmd = [
        'ffmpeg', '-y', '-loglevel', 'warning',
        '-ss', str(start_time),
        '-i', str(input_file),
        '-t', str(duration),
        '-vf', f'fps=1/{frame_interval}',
        '-q:v', '2',
        str(frames_dir / f"{filename}_scene{scene_num}_%04d.jpg")
    ]
    
    subprocess.run(cmd, check=True)

def extract_frames_only(scenes, input_file, output_dir, frame_interval):
    """Extract only frames (no video segments)"""
    if not scenes:
        log("No scenes to extract frames from")
        return
    
    log("Extracting frames from night scenes...")
    filename = Path(input_file).stem
    
    for i, (start_time, end_time) in enumerate(scenes, 1):
        extract_scene_frames(start_time, end_time, i, filename, 
                           input_file, output_dir, frame_interval)

def generate_report(scenes, input_file, output_dir, luma_threshold, min_duration):
    """Generate detection report"""
    report_file = output_dir / "night_detection_report.txt"
    
    with open(report_file, 'w') as f:
        f.write("Night Scene Detection Report\n")
        f.write("============================\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Input file: {input_file}\n")
        f.write(f"Luminance threshold: {luma_threshold}\n")
        f.write(f"Minimum duration: {min_duration}s\n")
        f.write("\n")
        
        if scenes:
            f.write(f"Night scenes detected: {len(scenes)}\n")
            f.write("\n")
            f.write("Scene Details:\n")
            f.write("Scene | Start Time | End Time | Duration\n")
            f.write("------|------------|----------|----------\n")
            for i, (start, end) in enumerate(scenes, 1):
                duration = end - start
                f.write(f"{i:5d} | {start:10.3f}s | {end:8.3f}s | {duration:8.3f}s\n")
        else:
            f.write("No night scenes detected\n")
    
    log(f"Report generated: {report_file}")

def main():
    # Parse arguments first to check if OCR is needed
    parser = argparse.ArgumentParser(
        description="Night scene detection using brightness analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available presets:
{list_presets()}

Examples:
  python3 night_detect.py -f movie.mp4 --preset medium
  python3 night_detect.py -f show.mp4 --preset tv -v
  python3 night_detect.py -f film.mp4 --preset high --no-frames
        """)
    
    parser.add_argument('-f', '--file', required=True, help='Input video file')
    parser.add_argument('-o', '--out', default='./night_scenes', help='Output directory')
    parser.add_argument('--preset', choices=list(PRESETS.keys()), 
                       help='Use predefined settings (overrides individual options)')
    parser.add_argument('-l', '--luma', type=int, help='Luminance threshold (0-255)')
    parser.add_argument('-d', '--duration', type=float, help='Minimum scene duration (seconds)')
    parser.add_argument('-v', '--extract-videos', action='store_true', help='Extract video segments')
    parser.add_argument('--no-frames', action='store_true', help='Skip frame extraction (extract videos only)')
    parser.add_argument('-i', '--interval', type=float, help='Frame extraction interval')
    parser.add_argument('-q', '--quality', type=int, default=2, help='Video quality (1-31)')
    parser.add_argument('--format', default='mp4', help='Output format')
    parser.add_argument('--establishing-shots', action='store_true', 
                       help='[EXPERIMENTAL] Focus on wide establishing shots rather than close-ups')
    parser.add_argument('--rich-analysis', action='store_true',
                       help='[EXPERIMENTAL] Use combined filters for comprehensive visual analysis')
    parser.add_argument('--audio-correlation', action='store_true',
                       help='[EXPERIMENTAL] Correlate dark scenes with audio volume (quiet/loud)')
    parser.add_argument('--quiet-threshold', type=float, default=-40.0,
                       help='dB threshold for quiet audio (default: -40.0)')
    parser.add_argument('--loud-threshold', type=float, default=-10.0,
                       help='dB threshold for loud audio (default: -10.0)')
    parser.add_argument('--audio-mode', choices=['quiet', 'loud', 'both'], default='both',
                       help='Filter for quiet, loud, or both audio levels (default: both)')
    parser.add_argument('--skip-credits', action='store_true',
                       help='Skip opening and closing credits using text detection')
    parser.add_argument('--credits-sample-interval', type=int,
                       help='Sampling interval for credits detection (seconds)')
    
    args = parser.parse_args()
    
    # Apply preset configuration if specified
    if args.preset:
        preset_config = get_preset_config(args.preset)
        if preset_config is None:
            print(f"Error: Unknown preset '{args.preset}'. Available presets: {', '.join(PRESETS.keys())}")
            return 1
        
        log(f"Using preset '{args.preset}': {preset_config['description']}")
        
        # Apply preset values only if not explicitly set by user
        if args.luma is None:
            args.luma = preset_config['luma']
        if args.duration is None:
            args.duration = preset_config['duration']
        if args.interval is None:
            args.interval = preset_config['interval']
        if args.credits_sample_interval is None:
            args.credits_sample_interval = preset_config['credits_sample_interval']
        if not args.skip_credits:  # Only apply preset if user didn't explicitly set it
            args.skip_credits = preset_config['skip_credits']
    else:
        # Set defaults if no preset and no explicit values
        if args.luma is None:
            args.luma = 30
        if args.duration is None:
            args.duration = 1.0
        if args.interval is None:
            args.interval = 1.0
        if args.credits_sample_interval is None:
            args.credits_sample_interval = 30
    
    # Check dependencies based on features requested
    check_dependencies(require_ocr=args.skip_credits)
    
    # Default behavior: extract frames only
    # Use flags to modify: -v for videos, --no-frames to skip frames
    extract_frames = not args.no_frames
    extract_videos = args.extract_videos
    
    # Validate input file
    input_file = Path(args.file)
    if not input_file.exists():
        print(f"Error: Input file does not exist: {input_file}")
        return 1
    
    # Create output directory
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log(f"Starting night scene detection for: {input_file}")
    log(f"Luminance threshold: {args.luma}, Minimum duration: {args.duration}s")
    extract_options = []
    if extract_videos:
        extract_options.append("videos")
    if extract_frames:
        extract_options.append("frames")
    log(f"Will extract: {', '.join(extract_options)}")
    
    try:
        # Get video info
        duration, fps = get_video_info(input_file)
        
        # Analyze brightness (and possibly motion/edges for establishing shots)
        analysis_file = analyze_brightness(input_file, output_dir, args.establishing_shots, args.rich_analysis, args.audio_correlation)
        
        # Extract night timestamps
        timestamps = extract_night_timestamps(analysis_file, args.luma, args.establishing_shots, 
                                            args.audio_correlation, args.quiet_threshold, 
                                            args.loud_threshold, args.audio_mode)
        
        if not timestamps:
            log("No dark frames found. Try increasing --luma threshold.")
            return 0
        
        # Create scene segments
        scenes = create_scene_segments(timestamps, args.duration)
        
        if not scenes:
            log("No scenes meet minimum duration requirement.")
            return 0
        
        # Filter out credits if requested
        if args.skip_credits:
            text_regions = detect_text_regions(input_file, output_dir, args.credits_sample_interval)
            scenes = filter_credits_from_scenes(scenes, text_regions, duration)
            
            if not scenes:
                log("No scenes remain after filtering credits.")
                return 0
        
        # Extract video segments and/or frames
        if extract_videos:
            extract_video_segments(scenes, input_file, output_dir, args.quality, 
                                 args.format, extract_frames, args.interval)
        elif extract_frames:
            # Extract frames only (without videos)
            extract_frames_only(scenes, input_file, output_dir, args.interval)
        
        # Generate report
        generate_report(scenes, input_file, output_dir, args.luma, args.duration)
        
        log("Night scene detection completed successfully!")
        log(f"Output directory: {output_dir}")
        
    except Exception as e:
        log(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())