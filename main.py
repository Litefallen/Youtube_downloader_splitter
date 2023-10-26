from functools import partial
import ffmpeg
from asynccpu import ProcessTaskPoolExecutor
from asyncffmpeg import FFmpegCoroutineFactory
import asyncio
from pytube import YouTube
import os


# Define a function to get a 'yes' or 'no' input from the user
def yes_no():
    answer = input("Please, type 'yes' or 'no': ").lower().strip()
    while True:
        if answer not in ('yes', 'no'):
            answer = input("Please, type 'yes' or 'no': ").lower().strip()
        return answer


def choose_res(res_list):
    print('Please, select desirable resolution:')
    for res in range(len(res_list)):
        print(res, res_list[res].resolution, res_list[res].itag)
        # print(res_list[res])
    ind = int(input())
    return res_list[ind].itag


# Define a function to extract timestamps (chapters) from video data
def get_timestamps(length, vid_data=None):  # Access the nested data structure to extract chapter information
    data_block = \
        vid_data['playerOverlays']['playerOverlayRenderer']['decoratedPlayerBarRenderer']['decoratedPlayerBarRenderer'][
            'playerBar']['multiMarkersPlayerBarRenderer']['markersMap'][0]['value']['chapters']
    data = [(chapter_block['chapterRenderer']['title']['simpleText'],  # Extract chapter title and start time in seconds
             round(chapter_block['chapterRenderer']['timeRangeStartMillis'] * 0.001)) for chapter_block in data_block]
    data.append(("End", length))  # Add an "End" marker with the video length
    return data


def vid_download(vid_link):  # Define a function to download a video and extract timestamps
    vid = YouTube(vid_link)  # Create a YouTube object from the video link
    length = vid.length  # Get the video length
    file_name = ''.join(i for i in vid.title if i not in """\#<$+%>!`&*'|{"=}/:@""")
    if not os.path.exists(f"{file_name}-Timestamps"):
        os.mkdir(f"{file_name}-Timestamps")
    print(f'The file will be stored in {os.getcwd()}')
    os.chdir(f"{file_name}-Timestamps")
    print(f"Files, cut according to timestamps, will be stored in '{os.getcwd()}' folder.\nIf the files exist - they will be overwritten.")

    print('Do you want to get AUDIO files only?')
    if yes_no() == 'yes':
        return (vid.streams.filter(only_audio=True).order_by('abr')[-1].download(output_path=os.path.dirname(os.getcwd())),), get_timestamps(length,
                                                                                                     vid_data=vid.initial_data)  # Download audio stream and get timestamps
    else:
        res_list = [i for i in vid.streams.filter(mime_type="video/mp4")]
        # print(os.path.dirname(os.getcwd()))
        return (vid.streams.filter(only_audio=True).order_by('abr')[-1].download(output_path=os.path.dirname(os.getcwd())),
                vid.streams.get_by_itag(choose_res(res_list)).download(output_path=os.path.dirname(os.getcwd())),), get_timestamps(length,
                                                                                           vid_data=vid.initial_data)  # Download video stream and get timestamps


async def vid_splitter(num, all_data):  # Define a function to split a video into chapters
    pts = 'PTS-STARTPTS'
    file_name = ''.join(i for i in all_data[1][num][0] if i not in """\#<$+%>!`&*'|{"=}/:@""")
    if os.path.exists(os.path.join(os.getcwd(), f"{num + 1}_{file_name}")):
        os.remove(os.path.join(os.getcwd(), f"{num + 1}_{file_name}"))
    if len(all_data[0]) == 1:
        input_stream = ffmpeg.input(all_data[0][0])
        for t in range(len(all_data[1]) - 1):  # Loop through the chapters and split the audio
            audio = input_stream.filter_('atrim', start=all_data[1][num][1],
                                         end=all_data[1][num + 1][1] + 1)
            output = ffmpeg.output(audio, filename=f'{num + 1}_{file_name}',
                                   format="mp3")
            return output

    else:
        input_v_stream = ffmpeg.input(all_data[0][1])
        input_a_stream = ffmpeg.input(all_data[0][0])
        video = input_v_stream.trim(start=all_data[1][num][1], end=all_data[1][num + 1][1] + 1).setpts(pts)
        audio = input_a_stream.filter_('atrim', start=all_data[1][num][1],
                                       end=all_data[1][num + 1][1] + 1).filter_('asetpts', pts)
        video_and_audio = ffmpeg.concat(video, audio, v=1, a=1)
        output = ffmpeg.output(video_and_audio, filename=f'{num + 1}_{file_name}', format="mp4")
        return output


async def main():
    while True:
        video_link = input('Please, paste link for Youtube clip: ').strip()
        try:
            print(f"The clip title is '{YouTube(video_link).title}'")
            break
        except:
            print('The link you provided is invalid.')
    all_data = vid_download(video_link)
    ffmpeg_coroutine = FFmpegCoroutineFactory.create()

    with ProcessTaskPoolExecutor(max_workers=None, cancel_tasks_when_shutdown=True) as executor:
        awaitables = (
            executor.create_process_task(ffmpeg_coroutine.execute, create_stream_spec)
            for create_stream_spec in [partial(vid_splitter, i, all_data) for i in range(len(all_data[1]) - 1)]
        )
        await asyncio.gather(*awaitables)
    print("Do you want to remove initial full file?")
    if yes_no() == 'yes':
        for i in all_data[0]:
            os.remove(i)


asyncio.run(main())
