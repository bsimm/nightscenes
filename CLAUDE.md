# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a video scene detection and splitting utility that uses FFmpeg's blackdetect filter to identify scene boundaries and automatically split videos into separate files. The project centers around a bash script that detects black frames in videos and uses them as scene transition markers.

## Core Architecture

The main workflow follows this pattern:
1. **Black frame detection**: Uses FFmpeg's `blackdetect` filter to identify frames that are completely or mostly black
2. **Timestamp calculation**: Processes black frame durations to find the middle point of each black sequence  
3. **Scene splitting**: Cuts the original video into numbered scene files based on the calculated timestamps
4. **Output generation**: Creates both video files and CSV reports with scene metadata

## Key Components

- **split.sh**: Main script that orchestrates the entire scene detection and splitting process
- **ffout**: Temporary file containing FFmpeg's blackdetect filter output
- **timestamps**: Generated file with calculated split points (middle of black frame sequences)
- **{name}-Scenes.csv**: Detailed scene analysis with frame counts, timecodes, and durations
- **Output videos**: Numbered scene files in format `0001_filename.ext`, `0002_filename.ext`, etc.

## Common Commands

### Basic scene splitting
```bash
./split.sh -f input_video.mp4
```

### Advanced usage with custom parameters
```bash
./split.sh -f input_video.mp4 -o output_folder -d 0.5 -r 0.98 -th 0.02
```

### Strip audio during splitting
```bash
./split.sh -f input_video.mp4 -sa
```

## Key Parameters

- **Duration (-d)**: Minimum black frame duration for scene detection (default: 0.05s)
- **Ratio (-r)**: Threshold for considering a picture black (default: 1.00)
- **Threshold (-th)**: Threshold for considering individual pixels black (default: 0.05)
- **Trim (-t)**: Subtract time from split points
- **Add (-a)**: Add time to split points

## Dependencies

- FFmpeg with blackdetect filter support
- bc (calculator) for timestamp arithmetic
- awk for numerical formatting
- Standard bash utilities (grep, printf)

## File Processing Flow

The script processes videos through multiple stages that create intermediate files. These files can be examined for debugging:
- Check `ffout` for raw blackdetect output
- Review `timestamps` for calculated split points
- Examine CSV files for detailed scene analysis