# Night Scene Detection & Video Processing

A collection of video processing tools for scene detection and splitting, with specialized support for night scene identification using modern FFmpeg filters.

## Overview

This repository contains two main approaches to video scene analysis:

1. **Black Frame Detection** (`split.sh`) - Legacy approach that splits videos at black frame transitions
2. **Night Scene Detection** (`night_detect.sh`) - Modern brightness-based analysis for detecting scenes filmed at night

## Scripts

### night_detect.sh

Modern night scene detection using luminance analysis and scene change detection.

**Features:**
- Brightness-based scene detection using FFmpeg's `signalstats` filter
- Configurable luminance thresholds for different lighting conditions
- Scene change detection to avoid mid-scene splits
- Frame extraction capabilities
- Multiple output formats (MP4, MOV, AVI)
- Detailed reporting with timestamps and durations

**Usage:**
```bash
# Basic night detection
./night_detect.sh -f video.mp4

# Custom thresholds
./night_detect.sh -f video.mp4 -l 40 -s 0.4 -d 2.0

# Extract frames every 0.5 seconds
./night_detect.sh -f video.mp4 -e -i 0.5

# High quality output
./night_detect.sh -f video.mp4 -q 1 --format mov
```

**Options:**
- `-f, --file` - Input video file (required)
- `-o, --out` - Output directory (default: ./night_scenes)
- `-l, --luma` - Luminance threshold 0-255 (default: 30, lower=darker)
- `-s, --scene` - Scene change sensitivity 0.1-1.0 (default: 0.3)
- `-d, --duration` - Minimum scene duration in seconds (default: 1.0)
- `-e, --extract-frames` - Extract individual frames from night scenes
- `-i, --interval` - Frame extraction interval in seconds (default: 1.0)
- `-q, --quality` - Video quality 1-31, lower=better (default: 2)
- `--format` - Output format: mp4, mov, avi (default: mp4)

### split.sh

Legacy black frame detection for scene splitting at complete darkness transitions.

**Features:**
- Uses FFmpeg's `blackdetect` filter
- Splits videos at black frame sequences
- Configurable black detection parameters
- Audio stripping option
- Timestamp adjustment capabilities

**Usage:**
```bash
# Basic splitting
./split.sh -f video.mp4

# Custom black detection duration
./split.sh -f video.mp4 -d 0.5 -o output_folder

# Strip audio
./split.sh -f video.mp4 -sa
```

**Options:**
- `-f, --file` - Input file
- `-o, --out` - Output folder path (default: current folder)
- `-d, --dur` - Duration for black detection in seconds (default: 0.05)
- `-r, --ratio` - Threshold for considering a picture black (default: 1.00)
- `-th, --threshold` - Threshold for considering a pixel black (default: 0.05)
- `-t, --trim` - Subtract from splitting timestamp in seconds
- `-a, --add` - Add to splitting timestamp in seconds
- `-sa, --strip-audio` - Strip audio from output

## Video Chunking for GitHub

To split large videos into GitHub-compatible chunks (under 100MB):

```bash
# Split into 10-minute chunks for GitHub upload
ffmpeg -i input.avi -c copy -ss 0 -t 600 part_001.avi \
  -ss 600 -t 600 part_002.avi \
  -ss 1200 -t 600 part_003.avi \
  -ss 1800 -t 600 part_004.avi \
  -ss 2400 -t 600 part_005.avi \
  -ss 3000 -t 600 part_006.avi \
  -ss 3600 part_007.avi
```

This creates time-based chunks suitable for version control without scene detection processing.

## Output Files

### Night Detection Output
- `night_scene_XXX_filename.mp4` - Detected night scene videos
- `frames/scene_XXX/` - Extracted frames (if `-e` option used)
- `night_detection_report.txt` - Detailed analysis report
- `night_scenes.txt` - Scene timestamps and metadata

### Black Frame Detection Output
- `XXXX_filename.ext` - Numbered scene files
- `filename-Scenes.csv` - Scene analysis with frame counts and timecodes
- `timestamps` - Raw timestamp data
- `ffout` - FFmpeg blackdetect filter output

## Dependencies

- **FFmpeg** - With blackdetect and signalstats filter support
- **FFprobe** - For video metadata analysis
- **bc** - For floating-point calculations
- **awk** - For numerical formatting
- **Python 3** - For advanced timestamp processing (night_detect.sh only)

### Installation

**macOS (Homebrew):**
```bash
brew install ffmpeg bc python3
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg bc python3
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg bc python3
```

## Algorithm Details

### Night Scene Detection Algorithm

1. **Brightness Analysis**: Uses FFmpeg's `signalstats` filter to calculate luminance statistics for each frame
2. **Scene Change Detection**: Applies scene change detection with configurable sensitivity
3. **Frame Filtering**: Selects frames that meet both brightness and scene change criteria
4. **Segmentation**: Groups consecutive qualifying frames into continuous scenes
5. **Duration Filtering**: Removes scenes shorter than minimum duration threshold
6. **Extraction**: Cuts video segments and optionally extracts frames

### Black Frame Detection Algorithm

1. **Black Detection**: Uses FFmpeg's `blackdetect` filter to identify black frame sequences
2. **Timestamp Calculation**: Finds middle point of each black sequence
3. **Scene Cutting**: Splits video at calculated timestamps
4. **Numbering**: Creates sequentially numbered output files

## Troubleshooting

### Common Issues

**No night scenes detected:**
- Try increasing luminance threshold (`-l 50` or higher)
- Decrease scene change sensitivity (`-s 0.2`)
- Reduce minimum duration (`-d 0.5`)

**Too many short segments:**
- Increase minimum duration (`-d 3.0`)
- Increase scene change sensitivity (`-s 0.5`)

**Missing dark scenes:**
- Lower luminance threshold (`-l 20` or lower)
- Check video brightness with: `ffprobe -f lavfi -i "movie=video.mp4,signalstats" -show_frames`

**FFmpeg errors:**
- Ensure FFmpeg version supports required filters
- Check input file format compatibility
- Verify sufficient disk space for output

### Testing Detection Parameters

Before processing long videos, test parameters on a short clip:

```bash
# Extract 30-second test clip
ffmpeg -i long_video.mp4 -t 30 -c copy test_clip.mp4

# Test night detection parameters
./night_detect.sh -f test_clip.mp4 -l 35 -s 0.4
```

## Performance Considerations

- **Processing Time**: Roughly 0.1-0.5x real-time depending on video resolution and complexity
- **Memory Usage**: Minimal, processes frame-by-frame
- **Storage**: Night scenes typically 10-30% of original video size
- **CPU Usage**: Single-threaded FFmpeg processing

## License

This project is provided as-is for educational and research purposes. FFmpeg usage subject to its license terms.

## Contributing

Feel free to submit issues and enhancement requests. When contributing:

1. Test with multiple video formats and lighting conditions
2. Maintain backward compatibility where possible
3. Update documentation for new features
4. Include example usage for new options