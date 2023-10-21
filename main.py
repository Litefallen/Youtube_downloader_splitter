from datetime import datetime # Import the datetime module to measure the execution time of the script

# Define a function to get a 'yes' or 'no' input from the user
def yes_no():
    answer = input("Please, type 'yes' or 'no'").lower().strip()
    while True:
        if answer not in ('yes', 'no'):
            answer = input("Please, type 'yes' or 'no'").lower().strip()
        return answer

# Define a function to extract timestamps (chapters) from video data
def get_timestamps(length, vid_data=None): # Access the nested data structure to extract chapter information
    data_block = \
    vid_data['playerOverlays']['playerOverlayRenderer']['decoratedPlayerBarRenderer']['decoratedPlayerBarRenderer'][
        'playerBar']['multiMarkersPlayerBarRenderer']['markersMap'][0]['value']['chapters']
    data = [(chapter_block['chapterRenderer']['title']['simpleText'], # Extract chapter title and start time in seconds
             round(chapter_block['chapterRenderer']['timeRangeStartMillis'] * 0.001)) for chapter_block in data_block]
    data.append(("End", length))  # Add an "End" marker with the video length
    return data


def vid_download(vid_link): # Define a function to download a video and extract timestamps
    from pytube import YouTube
    vid = YouTube(vid_link)     # Create a YouTube object from the video link
    length = vid.length# Get the video length
    return vid.streams.get_lowest_resolution().download(), get_timestamps(length, vid_data=vid.initial_data)    # Download video stream and get timestamps


def vid_splitter(all_data: tuple[str, list]): # Define a function to split a video into chapters
    import ffmpeg
    import os
    pts = 'PTS-STARTPTS'
    input_stream = ffmpeg.input(all_data[0])
    for t in range(len(all_data[1]) - 1):     # Loop through the chapters and split the video and audio
        file_name = all_data[1][t][0].replace(':', '_')
        video = input_stream.trim(start=all_data[1][t][1], end=all_data[1][t + 1][1]).setpts(pts)
        audio = input_stream.filter_('atrim', start=all_data[1][t][1], end=all_data[1][t + 1][1]).filter_('asetpts',
                                                                                                          pts)
        video_and_audio = ffmpeg.concat(video, audio, v=1, a=1)
        output = ffmpeg.output(video_and_audio, filename=f'{t + 1}_{file_name}', format="mp4")
        output.run()
        # print("Do you want to remove initial full file?")
        # if yes_no() == 'yes':
        #     os.remove(all_data[0])


video_link = 'https://www.youtube.com/watch?v=8qCc_hMCB0w'
begin = datetime.now()
vid_splitter(vid_download(video_link))
end = datetime.now()
with open('ttc.txt', 'a') as f:
    print(f'The code has been completed in {end - begin}', file=f)
