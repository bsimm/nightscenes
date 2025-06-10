# Night Scene Detection & Video Processing

A collection of video processing tools for scene detection and splitting, with specialized support for night scene identification using modern FFmpeg filters.

## Overview

This repository contains two main approaches to video scene analysis:

1. **Black Frame Detection** (`split.sh`) - Legacy approach that splits videos at black frame transitions
2. **Night Scene Detection** (`night_detect.sh` / `night_detect.py`) - Modern brightness-based analysis for detecting scenes filmed at night, available in bash and Python implementations

## Scripts

### night_detect.sh & night_detect.py

Modern night scene detection using luminance analysis. Available in both bash and Python implementations with different features.

#### Bash Version (night_detect.sh)
Lightweight, dependency-minimal implementation with scene change detection.

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

#### Python Version (night_detect.py)
Enhanced implementation with advanced analysis, preset configurations, and experimental features.

**Additional Features:**
- Pure brightness analysis (no scene change dependency)
- **Preset configurations** for different content types and sensitivity levels
- **Credits filtering** using OCR text detection to skip opening/closing credits
- Experimental establishing shot detection using edge detection
- More detailed logging and progress tracking
- Separate video and frame extraction controls
- Enhanced reporting capabilities

**Quick Start with Presets:**
```bash
# Recommended balanced settings
python3 night_detect.py -f video.mp4 --preset medium

# TV show optimized (shorter scenes, credits filtering)
python3 night_detect.py -f show.mp4 --preset tv -v

# Movie optimized settings
python3 night_detect.py -f movie.mp4 --preset movie

# High sensitivity detection
python3 night_detect.py -f video.mp4 --preset high

# Fast processing for quick assessment
python3 night_detect.py -f video.mp4 --preset quick
```

**Advanced Usage:**
```bash
# Extract frames only (default behavior)
python3 night_detect.py -f video.mp4

# Extract video segments
python3 night_detect.py -f video.mp4 -v

# Skip opening/closing credits
python3 night_detect.py -f movie.mp4 --skip-credits

# Experimental establishing shot detection
python3 night_detect.py -f video.mp4 --establishing-shots

# Custom parameters override preset values
python3 night_detect.py -f video.mp4 --preset tv -l 40 -d 0.5
```

**Common Options:**
- `-f, --file` - Input video file (required)
- `-o, --out` - Output directory (default: ./night_scenes)
- `-l, --luma` - Luminance threshold 0-255 (default: 30, lower=darker)
- `-d, --duration` - Minimum scene duration in seconds (default: 1.0)
- `-i, --interval` - Frame extraction interval in seconds (default: 1.0)
- `-q, --quality` - Video quality 1-31, lower=better (default: 2)
- `--format` - Output format: mp4, mov, avi (default: mp4)

**Bash-specific Options:**
- `-s, --scene` - Scene change sensitivity 0.1-1.0 (default: 0.3)
- `-e, --extract-frames` - Extract individual frames from night scenes

**Python-specific Options:**
- `--preset` - Use predefined settings: high, medium, low, quick, tv, movie
- `-v, --extract-videos` - Extract video segments (default: frames only)
- `--no-frames` - Skip frame extraction when extracting videos
- `--skip-credits` - Skip opening and closing credits using text detection
- `--credits-sample-interval` - Credits detection sampling interval in seconds
- `--establishing-shots` - [EXPERIMENTAL] Focus on wide establishing shots

**Available Presets:**
- **high** - High sensitivity, detects most dark scenes, filters credits
- **medium** - Balanced detection with credits filtering (recommended)
- **low** - Low sensitivity, only very dark/longer scenes
- **quick** - Fast processing for quick assessment
- **tv** - Optimized for TV shows and series
- **movie** - Optimized for movies and films

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

To split large videos into GitHub-compatible chunks (25MB each):

```bash
# Split into 25MB chunks for GitHub upload
ffmpeg -i input.avi -c copy -fs 25M -f segment -segment_format avi part_%03d.avi
```

This creates size-based chunks (25MB each) suitable for version control without scene detection processing.

## Output Files

### Night Detection Output
- `night_scene_XXX_filename.mp4` - Detected night scene videos
- `frames/scene_XXX/` - Extracted frames directory structure
- `night_detection_report.txt` - Detailed analysis report (Python version)
- `night_scenes.txt` - Scene timestamps and metadata (bash version)
- `brightness_analysis.txt` - Raw FFmpeg analysis output (Python version)

### Black Frame Detection Output
- `XXXX_filename.ext` - Numbered scene files
- `filename-Scenes.csv` - Scene analysis with frame counts and timecodes
- `timestamps` - Raw timestamp data
- `ffout` - FFmpeg blackdetect filter output

## Dependencies

- **FFmpeg** - With blackdetect, signalstats, and ocr filter support
- **FFprobe** - For video metadata analysis
- **bc** - For floating-point calculations
- **awk** - For numerical formatting
- **Python 3** - For advanced timestamp processing (night_detect.sh only)
- **Tesseract OCR** - For credits detection (optional, when using `--skip-credits`)

### Installation

**macOS (Homebrew):**
```bash
brew install ffmpeg bc python3 tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg bc python3 tesseract-ocr
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg bc python3 tesseract
```

**Note:** Tesseract is only required when using the `--skip-credits` feature in `night_detect.py`.

## Algorithm Details

### Night Scene Detection Algorithm

#### Bash Version (night_detect.sh)
1. **Brightness Analysis**: Uses FFmpeg's `signalstats` filter to calculate luminance statistics for each frame
2. **Scene Change Detection**: Applies scene change detection with configurable sensitivity
3. **Frame Filtering**: Selects frames that meet both brightness and scene change criteria
4. **Segmentation**: Groups consecutive qualifying frames into continuous scenes
5. **Duration Filtering**: Removes scenes shorter than minimum duration threshold
6. **Extraction**: Cuts video segments and optionally extracts frames

#### Python Version (night_detect.py)
1. **Brightness Analysis**: Uses FFmpeg's `showinfo` filter for detailed frame-by-frame luminance analysis
2. **Credits Detection** (optional): Uses FFmpeg's `ocr` filter with Tesseract to identify text-heavy regions
3. **Credits Filtering**: Removes scenes overlapping with detected opening (first 10%) and closing (last 15%) credits
4. **Edge Detection** (experimental): Optional `sobel` filter for detecting wide shots vs close-ups
5. **Pure Brightness Filtering**: Selects frames based solely on luminance threshold (no scene change dependency)
6. **Segmentation**: Groups consecutive dark frames into continuous scenes with gap tolerance
7. **Duration Filtering**: Removes scenes shorter than minimum duration threshold
8. **Selective Extraction**: Separate controls for video segments and frame extraction

### Black Frame Detection Algorithm

1. **Black Detection**: Uses FFmpeg's `blackdetect` filter to identify black frame sequences
2. **Timestamp Calculation**: Finds middle point of each black sequence
3. **Scene Cutting**: Splits video at calculated timestamps
4. **Numbering**: Creates sequentially numbered output files

## Troubleshooting

### Common Issues

**No night scenes detected:**
- Try increasing luminance threshold (`-l 50` or higher)
- Use a different preset: `--preset high` for maximum sensitivity
- Decrease scene change sensitivity (`-s 0.2`) [bash version only]
- Reduce minimum duration (`-d 0.5`)
- Switch to Python version for pure brightness analysis (no scene change dependency)

**Too many short segments:**
- Increase minimum duration (`-d 3.0`)
- Use `--preset low` for fewer, longer scenes
- Increase scene change sensitivity (`-s 0.5`) [bash version only]
- Use Python version with higher duration thresholds

**Missing dark scenes:**
- Lower luminance threshold (`-l 20` or lower)
- Use `--preset high` for maximum sensitivity
- Check video brightness with: `ffprobe -f lavfi -i "movie=video.mp4,signalstats" -show_frames`
- Try experimental establishing shot detection: `python3 night_detect.py --establishing-shots`

**Credits filtering issues:**
- Ensure Tesseract is installed: `tesseract --version`
- Check FFmpeg OCR filter support: `ffmpeg -filters | grep ocr`
- Try different sampling intervals: `--credits-sample-interval 15`
- Disable credits filtering if causing issues: omit `--skip-credits`

**Preset not working as expected:**
- Override specific parameters: `--preset tv -l 40 -d 1.5`
- Check preset description: `python3 night_detect.py --help`
- Use manual parameters instead of presets for fine control

**FFmpeg errors:**
- Ensure FFmpeg version supports required filters (ocr, showinfo, sobel)
- Check input file format compatibility
- Verify sufficient disk space for output
- For OCR errors, ensure Tesseract language data is installed

### Testing Detection Parameters

Before processing long videos, test parameters on a short clip:

```bash
# Extract 30-second test clip
ffmpeg -i long_video.mp4 -t 30 -c copy test_clip.mp4

# Test different presets quickly
python3 night_detect.py -f test_clip.mp4 --preset quick
python3 night_detect.py -f test_clip.mp4 --preset medium
python3 night_detect.py -f test_clip.mp4 --preset high

# Test with credits filtering
python3 night_detect.py -f test_clip.mp4 --preset movie --skip-credits

# Test bash version parameters
./night_detect.sh -f test_clip.mp4 -l 35 -s 0.4

# Compare results between implementations
python3 night_detect.py -f test_clip.mp4 --establishing-shots

# Fine-tune after finding good preset
python3 night_detect.py -f test_clip.mp4 --preset tv -l 40 -d 0.8
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