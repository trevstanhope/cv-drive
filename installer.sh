#!/bin/sh

# Aptitude
apt-get update
apt-get upgrade -y
apt-get install unzip -y
apt-get install build-essential -y
apt-get install python-dev -y
apt-get install cmake -y
apt-get install python-serial -y
apt-get install python-pip -y
apt-get install python-gps -y # python dependencies
apt-get install mongodb -y # MongoDB
apt-get install gpsd -y
apt-get install gpsd-clients -y
apt-get install python-gps -y # GPS
apt-get install python-matplotlib -y
apt-get install libgtk2.0-dev -y
apt-get install python-numpy -y
apt-get install libqt4-dev -y
apt-get install libopencv-dev -y
apt-get install build-essential -y
apt-get install checkinstall -y
apt-get install pkg-config -y
apt-get install yasm -y
apt-get install libjpeg-dev -y
apt-get install libjasper-dev -y
apt-get install libavcodec-dev -y
apt-get install libavformat-dev -y
apt-get install libswscale-dev -y
apt-get install libdc1394-22-dev -y
apt-get install libxine-dev -y
apt-get install libgstreamer0.10-dev -y
apt-get install libgstreamer-plugins-base0.10-dev -y
apt-get install libv4l-dev -y
apt-get install python-numpy -y
apt-get install libtbb-dev -y
apt-get install libqt4-dev -y
apt-get install libgtk2.0-dev -y
apt-get install libfaac-dev -y
apt-get install libmp3lame-dev
apt-get install libopencore-amrnb-dev -y
apt-get install libopencore-amrwb-dev -y
apt-get install libtheora-dev -y
apt-get install libvorbis-dev -y
apt-get install libxvidcore-dev -y
apt-get install x264 -y
apt-get install v4l-utils -y

## OpenCV Dependencies
cd /usr/include/linux
ln -s ../libv4l1-videodev.h videodev.h
ln -s ../libavformat/avformat.h avformat.h

# OpenCV
wget http://downloads.sourceforge.net/project/opencvlibrary/opencv-unix/2.4.9/opencv-2.4.9.zip
unzip opencv-2.4.9.zip
cd opencv-2.4.9
mkdir release
cd release
cmake -D CMAKE_BUILD_TYPE=RELEASE CMAKE_INSTALL_PREFIX=/usr/local ..
make -j4
make install

## Pip
pip install pymongo
