#!/bin/bash

# Night Scene Detection and Frame Extraction Script
# Detects scenes that appear to be filmed at night based on brightness analysis
# Uses modern FFmpeg filters for accurate scene detection

file=""
out="./night_scenes"
luma_threshold=30     # Average luminance threshold (0-255, lower = darker)
scene_threshold=0.3   # Scene change sensitivity (0.1-1.0, higher = less sensitive)
min_duration=1.0      # Minimum duration for a night scene (seconds)
extract_frames=false  # Extract individual frames from night scenes
frame_interval=1      # Extract one frame every N seconds
quality=2            # Video quality (1=best, 31=worst)
format="mp4"         # Output format

usage() {
    echo "Usage: $(basename $0) [OPTIONS] -f input_video"
    echo
    echo "Modern night scene detection using brightness analysis and scene changes"
    echo
    echo "Options:"
    echo "  -f, --file FILE          Input video file (required)"
    echo "  -o, --out DIR            Output directory (default: ./night_scenes)"
    echo "  -l, --luma INT          Luminance threshold 0-255 (default: 30, lower=darker)"
    echo "  -s, --scene FLOAT       Scene change threshold 0.1-1.0 (default: 0.3)"
    echo "  -d, --duration FLOAT    Minimum scene duration in seconds (default: 1.0)"
    echo "  -e, --extract-frames    Extract individual frames from night scenes"
    echo "  -i, --interval FLOAT    Frame extraction interval in seconds (default: 1.0)"
    echo "  -q, --quality INT       Video quality 1-31, lower=better (default: 2)"
    echo "  --format FORMAT         Output format: mp4, mov, avi (default: mp4)"
    echo "  -h, --help              Show this help"
    echo
    echo "Examples:"
    echo "  $(basename $0) -f video.mp4                    # Basic night detection"
    echo "  $(basename $0) -f video.mp4 -l 40 -s 0.4      # Higher brightness threshold"
    echo "  $(basename $0) -f video.mp4 -e -i 0.5         # Extract frames every 0.5s"
    echo "  $(basename $0) -f video.mp4 --format mov      # Output as MOV files"
}

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

error() {
    echo "[ERROR] $1" >&2
    exit 1
}

check_dependencies() {
    command -v ffmpeg >/dev/null 2>&1 || error "ffmpeg is required but not installed"
    command -v ffprobe >/dev/null 2>&1 || error "ffprobe is required but not installed"
    command -v bc >/dev/null 2>&1 || error "bc is required but not installed"
}

parse_args() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi

    while [ "$1" != "" ]; do
        case $1 in
            -f | --file)
                shift
                file="$1"
                ;;
            -o | --out)
                shift
                out="$1"
                ;;
            -l | --luma)
                shift
                luma_threshold="$1"
                ;;
            -s | --scene)
                shift
                scene_threshold="$1"
                ;;
            -d | --duration)
                shift
                min_duration="$1"
                ;;
            -e | --extract-frames)
                extract_frames=true
                ;;
            -i | --interval)
                shift
                frame_interval="$1"
                ;;
            -q | --quality)
                shift
                quality="$1"
                ;;
            --format)
                shift
                format="$1"
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
        shift
    done

    [ -z "$file" ] && error "Input file is required (-f option)"
    [ ! -f "$file" ] && error "Input file does not exist: $file"
}

get_video_info() {
    local duration fps
    duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$file" 2>/dev/null)
    fps=$(ffprobe -v quiet -show_entries stream=r_frame_rate -of csv=p=0 "$file" 2>/dev/null | head -1)
    
    # Convert fractional fps to decimal
    if [[ $fps == *"/"* ]]; then
        fps=$(echo "scale=3; $fps" | bc -l)
    fi
    
    echo "Video duration: ${duration}s, FPS: $fps"
}

analyze_brightness() {
    local temp_analysis="$out/brightness_analysis.txt"
    
    log "Analyzing video brightness and scene changes..."
    
    # Modern FFmpeg filter chain for comprehensive analysis:
    # 1. signalstats: Calculate luminance statistics 
    # 2. select: Detect scene changes and filter by brightness
    # 3. showinfo: Display frame information
    ffmpeg -i "$file" \
        -vf "signalstats,select='gt(scene,$scene_threshold)+lt(lavfi.signalstats.YAVG,$luma_threshold)',showinfo" \
        -f null - 2> "$temp_analysis"
    
    if [ ! -s "$temp_analysis" ]; then
        error "Failed to analyze video brightness"
    fi
    
    echo "$temp_analysis"
}

extract_night_scenes() {
    local analysis_file="$1"
    local scene_count=0
    local current_start=""
    local scene_timestamps="$out/night_timestamps.txt"
    
    log "Extracting night scene timestamps..."
    
    # Parse FFmpeg output to find night scenes
    # Look for frames that passed our brightness and scene change filters
    grep "Parsed_showinfo" "$analysis_file" | \
    grep -o "pts_time:[0-9]*\.*[0-9]*" | \
    cut -d: -f2 > "$scene_timestamps"
    
    if [ ! -s "$scene_timestamps" ]; then
        log "No night scenes detected with current thresholds"
        log "Try adjusting --luma (higher value) or --scene (lower value)"
        return 1
    fi
    
    local frame_count=$(wc -l < "$scene_timestamps")
    log "Found $frame_count potential night scene frames"
    
    # Group consecutive frames into scenes
    create_scene_segments "$scene_timestamps"
}

create_scene_segments() {
    local timestamps_file="$1"
    local scenes_file="$out/night_scenes.txt"
    local scene_count=0
    
    > "$scenes_file"
    
    # Group timestamps into continuous segments
    python3 -c "
import sys
timestamps = []
with open('$timestamps_file', 'r') as f:
    for line in f:
        timestamps.append(float(line.strip()))

if not timestamps:
    sys.exit(1)

timestamps.sort()
scenes = []
current_start = timestamps[0]
current_end = timestamps[0]

for i in range(1, len(timestamps)):
    if timestamps[i] - current_end <= $min_duration * 2:  # Allow gaps up to 2x min_duration
        current_end = timestamps[i]
    else:
        if current_end - current_start >= $min_duration:
            scenes.append((current_start, current_end))
        current_start = timestamps[i]
        current_end = timestamps[i]

# Don't forget the last scene
if current_end - current_start >= $min_duration:
    scenes.append((current_start, current_end))

with open('$scenes_file', 'w') as f:
    for i, (start, end) in enumerate(scenes, 1):
        f.write(f'{i},{start:.3f},{end:.3f},{end-start:.3f}\n')
        
print(f'Created {len(scenes)} night scenes')
" || error "Failed to process scene segments (requires python3)"

    if [ ! -s "$scenes_file" ]; then
        log "No night scenes meet minimum duration requirement"
        return 1
    fi
    
    # Extract the actual video segments
    extract_video_segments "$scenes_file"
}

extract_video_segments() {
    local scenes_file="$1"
    local filename=$(basename "$file" | sed 's/\.[^.]*$//')
    
    log "Extracting night scene videos..."
    
    while IFS=',' read -r scene_num start_time end_time duration; do
        local output_file="$out/night_scene_$(printf "%03d" $scene_num)_${filename}.$format"
        
        log "Extracting scene $scene_num: ${start_time}s - ${end_time}s (${duration}s)"
        
        ffmpeg -y -loglevel warning \
            -ss "$start_time" \
            -i "$file" \
            -t "$duration" \
            -c:v libx264 \
            -crf "$quality" \
            -c:a aac \
            -avoid_negative_ts make_zero \
            "$output_file"
        
        if [ "$extract_frames" = true ]; then
            extract_scene_frames "$start_time" "$end_time" "$scene_num" "$filename"
        fi
        
    done < "$scenes_file"
}

extract_scene_frames() {
    local start_time="$1"
    local end_time="$2" 
    local scene_num="$3"
    local filename="$4"
    local frames_dir="$out/frames/scene_$(printf "%03d" $scene_num)"
    
    mkdir -p "$frames_dir"
    
    log "Extracting frames from scene $scene_num (every ${frame_interval}s)"
    
    ffmpeg -y -loglevel warning \
        -ss "$start_time" \
        -i "$file" \
        -t "$(echo "$end_time - $start_time" | bc -l)" \
        -vf "fps=1/$frame_interval" \
        -q:v 2 \
        "$frames_dir/${filename}_scene${scene_num}_%04d.jpg"
}

generate_report() {
    local report_file="$out/night_detection_report.txt"
    local scenes_file="$out/night_scenes.txt"
    
    {
        echo "Night Scene Detection Report"
        echo "============================"
        echo "Generated: $(date)"
        echo "Input file: $file"
        echo "Luminance threshold: $luma_threshold"
        echo "Scene change threshold: $scene_threshold"
        echo "Minimum duration: ${min_duration}s"
        echo ""
        
        if [ -f "$scenes_file" ]; then
            local scene_count=$(wc -l < "$scenes_file")
            echo "Night scenes detected: $scene_count"
            echo ""
            echo "Scene Details:"
            echo "Scene | Start Time | End Time | Duration"
            echo "------|------------|----------|----------"
            while IFS=',' read -r scene_num start_time end_time duration; do
                printf "%5s | %10.3fs | %8.3fs | %8.3fs\n" "$scene_num" "$start_time" "$end_time" "$duration"
            done < "$scenes_file"
        else
            echo "No night scenes detected"
        fi
    } > "$report_file"
    
    log "Report generated: $report_file"
}

main() {
    check_dependencies
    parse_args "$@"
    
    log "Starting night scene detection for: $file"
    log "Luminance threshold: $luma_threshold, Scene threshold: $scene_threshold"
    
    mkdir -p "$out"
    
    get_video_info
    
    local analysis_file
    analysis_file=$(analyze_brightness)
    
    if extract_night_scenes "$analysis_file"; then
        generate_report
        log "Night scene detection completed successfully!"
        log "Output directory: $out"
    else
        log "No night scenes detected. Try adjusting thresholds."
    fi
    
    # Cleanup temporary files
    rm -f "$out/brightness_analysis.txt" "$out/night_timestamps.txt"
}

main "$@"