#!/bin/bash

# Chunks video files into segments of specified size
# Default target size is 25MB

file=""
target_size="25M"
clobber=""

usage () {
  echo "Usage: $(basename $0) [-c] -f file.mp4"
  echo
  echo "Options:"
  echo "-f, --file          Input file"
  echo "-c, --clobber       Overwrite existing output files"
  echo "-h, --help          Display this help message"
  echo
  echo "Chunks video into 25MB segments by default"
  echo "Output files: filename_part_001.ext, filename_part_002.ext, etc."
}

if [ "$1" = "" ]; then
  usage
  exit 1
fi

while [ "$1" != "" ]; do
  case $1 in
    -f | --file )
      shift
      file=$1
      ;;
    -c | --clobber )
      clobber="-y"
      ;;
    -h | --help )
      usage
      exit
      ;;
    * )
      usage
      exit 1
  esac
  shift
done

if [ "$file" = "" ]; then
  echo "Error: Input file required"
  usage
  exit 1
fi

if [ ! -f "$file" ]; then
  echo "Error: File '$file' not found"
  exit 1
fi

filename=$(basename "$file")
name="${filename%.*}"
ext="${filename##*.}"

echo "Chunking video: $file"
echo "Target size: $target_size per segment"
echo ""

# Get video duration in seconds
duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$file")
if [ $? -ne 0 ]; then
  echo "Error: Could not read video duration"
  exit 1
fi

# Get file size in bytes
file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "Error: Could not read file size"
  exit 1
fi

# Convert target size to bytes (25M = 25 * 1024 * 1024)
target_bytes=$((25 * 1024 * 1024))

# Calculate number of segments needed
num_segments=$(echo "scale=0; ($file_size + $target_bytes - 1) / $target_bytes" | bc -l)

# Calculate segment duration
segment_duration=$(echo "scale=2; $duration / $num_segments" | bc -l)

echo "Video duration: ${duration}s"
echo "File size: $file_size bytes"
echo "Number of segments needed: $num_segments"
echo "Segment duration: ${segment_duration}s"
echo ""

# Split the video
echo "Starting chunking process..."
chunk_count=0
start_time=0

for ((i=0; i<num_segments; i++)); do
  if [ $i -eq $((num_segments-1)) ]; then
    # Last segment - no duration limit
    printf -v output_file "${name}_part_%03d.${ext}" $i
    echo "Creating segment $((i+1))/$num_segments: ${output_file} (from ${start_time}s to end)"
    ffmpeg $clobber -loglevel error -ss $start_time -i "$file" -c copy "${output_file}"
  else
    # Regular segment with duration limit
    printf -v output_file "${name}_part_%03d.${ext}" $i
    echo "Creating segment $((i+1))/$num_segments: ${output_file} (from ${start_time}s for ${segment_duration}s)"
    ffmpeg $clobber -loglevel error -ss $start_time -t $segment_duration -i "$file" -c copy "${output_file}"
  fi
  
  if [ $? -eq 0 ]; then
    chunk_count=$((chunk_count + 1))
    start_time=$(echo "$start_time + $segment_duration" | bc -l)
  else
    echo "Error: Failed to create ${output_file}"
    exit 1
  fi
done

echo ""
echo "Chunking complete! Created $chunk_count segments."