# Splits video to separate scenes files when full black frames are found in the video
# Inspired by https://gist.github.com/achesco/4dc2ebf13378a0a61fc26c7fe01f539e
# Who got inspired by https://stackoverflow.com/a/38205105

#!/bin/bash

file=""
out="./"
dur=0.05
stripaudio=""
ratio=1.00
th=0.05
add=0.00
trim=0.00

usage () {
  echo "Usage: $(basename $0) [[[-o folder] [-d black duration]] | [-h]] -f file.mp4"
  echo
  echo "Options:"
  echo "-f, --file          Input file"
  echo "-o, --out           Outpup files folder path, default"
  echo "                    to current folder"
  echo "-d, --dur           Duration for black detection in seconds. 0.05 default (practical single frame)"
  echo "-r, --ratio        ffmpeg pic_th : Set the threshold for considering a picture black. 1.00 default"
  echo "-th, --threshold   ffmpeg pix_th : Set the threshold for considering a pixel black. 0.00 default."
  echo "-t, --trim          Substracts to splitting timestamp in seconds. 0 default"
  echo "-a, --add           Adds to splitting timestamp in seconds. 0 default"
  echo "-sa, --strip-audio  Strip audio"
  echo "-h, --help          Display this help message"
  echo
  echo "Example: split.sh -d 0.5 -o /tmp/parts -f file.mp4"
  echo "Splits file.mp4 file to scenes with black frames during more than 0.5 second"
  echo "and saves output parts to /tmp/parts folder"
}

if [ "$1" = "" ]; then
  usage
fi

while [ "$1" != "" ]; do
  case $1 in
    -f | --file )
      shift
      file=$1
      ;;
    -d | --dur )
      shift
      dur=$1
      ;;
    -r | --ratio )
      shift
      ratio=$1
      ;;
    -th | --threshold )
      shift
      th=$1
      ;;
    -o | --out )
      shift
      out=$1
      ;;
    -t | --trim )
      shift
      trim=$1
      ;;
    -a | --add )
      shift
      add=$1
      ;;
    -sa | --strip-audio )
      stripaudio="-an"
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

cut_part () {
  duration_flag=""
  if [[ "$3" != "" ]]; then
    duration_flag="-t"
  fi
  echo "cutting from $1 during $3"
  printf -v fileout "$out/%04d_%s" $2 $filename
  ffmpeg -y -loglevel error -hide_banner -ss $1 -i $file -c:v copy -c:a copy $stripaudio $duration_flag $3 $fileout < /dev/null
}

filename=`basename $file`
mkdir -p $out
timefrom=0
i=1

ffmpeg -i $file -vf blackdetect=d=$dur:pic_th=$ratio:pix_th=$th -f null - 2> ffout
black_start=( $(grep blackdetect ffout | grep black_start:[0-9.]* -o | grep "[0-9]*\.[0-9]*" -o) )
black_duration=( $(grep blackdetect ffout | grep black_duration:[0-9.]* -o | grep "[0-9]*\.[0-9]*" -o) )
> timestamps
for ii in "${!black_start[@]}"; do
  half=$(bc -l <<< "${black_duration[$ii]}/2")
  middletime=$(bc -l <<< "${black_start[$ii]} + $half")
  echo $middletime | LC_ALL=en_US.UTF-8 awk '{printf "%f", $0}' >> timestamps
  echo "" >> timestamps
done

while read -r timestamp; do
  duration=`bc -l <<< "$timestamp-$timefrom+$add-$trim" | LC_ALL=en_US.UTF-8 awk '{printf "%f", $0}'`
  cut_part $timefrom $i $duration
  timefrom=`bc -l <<< "$timestamp+$add-$trim" | LC_ALL=en_US.UTF-8 awk '{printf "%f", $0}'`
  i=`expr $i + 1`
done < timestamps

if [[ "$timefrom" != 0 ]]; then
  cut_part $timefrom $i
fi

