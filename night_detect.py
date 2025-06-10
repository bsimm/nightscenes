#!/usr/bin/env python3

import argparse
import subprocess
import re
import os
from pathlib import Path
from datetime import datetime
import json

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

def analyze_brightness(file_path, output_dir, experimental_establishing=False):
    """Analyze video brightness and optionally motion/scene characteristics"""
    if experimental_establishing:
        log("Analyzing video with experimental establishing shot detection...")
    else:
        log("Analyzing video brightness...")
    
    analysis_file = output_dir / "brightness_analysis.txt"
    
    if experimental_establishing:
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

def extract_night_timestamps(analysis_file, luma_threshold, experimental_establishing=False):
    """Parse FFmpeg output to find dark frames, optionally filtering for establishing shots"""
    if experimental_establishing:
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
    parser = argparse.ArgumentParser(description="Night scene detection using brightness analysis")
    parser.add_argument('-f', '--file', required=True, help='Input video file')
    parser.add_argument('-o', '--out', default='./night_scenes', help='Output directory')
    parser.add_argument('-l', '--luma', type=int, default=30, help='Luminance threshold (0-255)')
    parser.add_argument('-d', '--duration', type=float, default=1.0, help='Minimum scene duration (seconds)')
    parser.add_argument('-v', '--extract-videos', action='store_true', help='Extract video segments')
    parser.add_argument('--no-frames', action='store_true', help='Skip frame extraction (extract videos only)')
    parser.add_argument('-i', '--interval', type=float, default=1.0, help='Frame extraction interval')
    parser.add_argument('-q', '--quality', type=int, default=2, help='Video quality (1-31)')
    parser.add_argument('--format', default='mp4', help='Output format')
    parser.add_argument('--establishing-shots', action='store_true', 
                       help='[EXPERIMENTAL] Focus on wide establishing shots rather than close-ups')
    
    args = parser.parse_args()
    
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
        analysis_file = analyze_brightness(input_file, output_dir, args.establishing_shots)
        
        # Extract night timestamps
        timestamps = extract_night_timestamps(analysis_file, args.luma, args.establishing_shots)
        
        if not timestamps:
            log("No dark frames found. Try increasing --luma threshold.")
            return 0
        
        # Create scene segments
        scenes = create_scene_segments(timestamps, args.duration)
        
        if not scenes:
            log("No scenes meet minimum duration requirement.")
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