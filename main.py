import tkinter as tk
from tkinter import filedialog
import os
import cv2
import numpy as np
import PySimpleGUI as sg
from moviepy import VideoFileClip, concatenate_videoclips

# Function for select video button
def select_video():
    # Set the PySimpleGUI theme
    sg.theme('DefaultNoMoreNagging')

    # Create a Tkinter root window and hide it. Not entirely sure if this is necessary
    # However the program works so whatever LOL
    root = tk.Tk()
    root.withdraw()

    # Open a file selection dialog to choose video files
    file_path = filedialog.askopenfilenames(filetypes=[
        ('All Video files', '*.mp4;*.mpg;*.mpeg;*.avi;*.mov;*.wmv;*.mkv;*.flv;*.m4v;*.webm;*.3gp;*.ogv;*.ts;*.mts;*.m2ts'),
        ('MP4 files', '*.mp4'),
        ('MPEG files', '*.mpg;*.mpeg'),
        ('AVI files', '*.avi'),
        ('MOV files', '*.mov'),
        ('WMV files', '*.wmv'),
        ('MKV files', '*.mkv'),
        ('All files', '*.*')
    ])

    # Return the selected file path
    return file_path

# Function for the process video button
def process_video(file_path, window):
    # Load the video file
    cap = cv2.VideoCapture(file_path)

    # Give an error if the video could not be opened
    if not cap.isOpened():
        sg.popup_error("Error: Could not open video file")
        return

    # Get the video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Initialize the blue screen counter
    blue_screen_count = 0
    total_frames_processed = 0

    # Variables to store the unselected clips
    unselected_clips = []

    # Variables to keep track of clip selection
    start_time = None
    end_time = None

    progress_bar = window['progressbar']
    total_frames = frame_count

    # Loop through each frame in the video
    while cap.isOpened():
        try:
            ret, frame = cap.read()
            if ret:
                # Convert the frame to the HSV color space
                hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Define the lower and upper bounds of the blue color range
                lower_blue = np.array([90, 50, 50])
                upper_blue = np.array([130, 255, 255])

                # Threshold the frame to extract only blue pixels
                mask = cv2.inRange(hsv_frame, lower_blue, upper_blue)

                # Calculate the percentage of blue pixels in the frame
                total_pixels = mask.size
                blue_pixels = cv2.countNonZero(mask)
                blue_percentage = (blue_pixels / total_pixels) * 100

                # If the percentage of blue pixels is above a certain threshold,
                # then the frame is likely a blue screen
                if blue_percentage > 30:
                    if start_time is not None and end_time is None:
                        # End of an unselected clip
                        end_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

                        # Add the unselected clip to the list of clips
                        unselected_clip = VideoFileClip(file_path).subclipped(start_time, end_time)
                        unselected_clips.append(unselected_clip)

                        # Reset the variables for the next selection
                        start_time = None
                        end_time = None

                else:
                    if start_time is None:
                        # Start of an unselected clip
                        start_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

                progress_update = total_frames_processed * 1000 / total_frames
                progress_bar.UpdateBar(progress_update)

                # Add counter to total frames processed
                total_frames_processed += 1

            else:
                break

        except Exception as e:
            sg.popup_error(f'Error processing frame {total_frames_processed}: {e}')
            break

        if total_frames_processed == frame_count:
            break

    # Check if we need to add the last clip (if video ends on non-blue frame)
    if start_time is not None:
        # Video ended while in a non-blue section
        end_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        unselected_clip = VideoFileClip(file_path).subclipped(start_time, end_time)
        unselected_clips.append(unselected_clip)

    # Release the capture and close all windows
    cap.release()
    cv2.destroyAllWindows()

    # Check if there are any clips to process
    if not unselected_clips:
        log_message = f'No content to save in {os.path.basename(file_path)} - video is entirely blue screens or empty'
        window['log_box'].update(log_message + '\n', append=True)
        window['progressbar'].UpdateBar(0)
        return

    # Concatenate the unselected clips into a final video
    final_clip = concatenate_videoclips(unselected_clips)

    # Generate the output file path
    # Desktop path seems to have issues on some devices for me
    # desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    directory = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    file_name, file_ext = os.path.splitext(base_name)

    converted_dir = os.path.join(directory, "Converted")
    if not os.path.exists(converted_dir):
        os.makedirs(converted_dir)

    # Determine the best codec and output format based on input format
    output_ext = file_ext.lower()
    codec = 'libx264'  # Default codec for most formats
    audio_codec = 'aac'  # Default audio codec
    
    # Map specific formats to optimal codecs
    if output_ext in ['.webm']:
        codec = 'libvpx'
        audio_codec = 'libvorbis'
    elif output_ext in ['.wmv']:
        codec = 'wmv2'
        audio_codec = 'wmav2'
    elif output_ext in ['.avi', '.mpg', '.mpeg', '.flv']:
        # These formats can use libx264 but output as MP4 for better compatibility
        output_ext = '.mp4'
    
    # For formats that might not work well, default to MP4
    if output_ext not in ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.wmv', '.m4v', '.mpg', '.mpeg']:
        output_ext = '.mp4'

    output_file = os.path.join(converted_dir, f"{file_name}_bc{output_ext}")

    # Write the final video to the output file with appropriate codec
    try:
        final_clip.write_videofile(output_file, fps=fps, codec=codec, audio_codec=audio_codec, logger=None)
        log_message = f'Processed {os.path.basename(file_path)} - Removed {len(unselected_clips)} blue screen section(s)'
        window['log_box'].update(log_message + '\n', append=True)
    except Exception as e:
        # If the specific codec fails, try with default MP4 settings
        output_file = os.path.join(converted_dir, f"{file_name}_bc.mp4")
        final_clip.write_videofile(output_file, fps=fps, codec='libx264', audio_codec='aac', logger=None)
        log_message = f'Processed {os.path.basename(file_path)} (converted to MP4) - Removed {len(unselected_clips)} blue screen section(s)'
        window['log_box'].update(log_message + '\n', append=True)
    
    # Close the clips to free memory
    final_clip.close()
    for clip in unselected_clips:
        clip.close()

    # Reset the progress bar
    window['progressbar'].UpdateBar(0)

# GUI layout
layout = [
    [sg.Button('Select Video')],
    [sg.Button('Process Video', disabled=True)],
    [sg.ProgressBar(1000, orientation='h', size=(20, 20), key='progressbar')],
    [sg.Text('Processing 0/0', key='file_counter')],
    [sg.Exit()],
    [sg.Multiline(default_text='', size=(40, 5), key='log_box')]
]

# Create the PySimpleGUI window with the specified title and layout
window = sg.Window('BlueCut', layout)

# Start the event loop
while True:
    # Read events and values from the window
    event, values = window.read()

    # Check if the window is closed or the "Exit" button is clicked
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break

    # Check if the "Select Video" button is clicked
    # elif event == 'Select Video':
        # Call the select_video() function to choose a video file
        # file_path = select_video()
        # if file_path:
            # total_files = len(file_path)
            # for index, file_paths in enumerate(file_path, start=1):
                # window['file_counter'].update(f'Processing {index}/{total_files}')
                # process_video(file_paths, window)
                # window['progressbar'].UpdateBar(0)
            # Enable the "Process Video" button if a file is selected
            # window['Process Video'].update(disabled=False)
        # else:
            # sg.popup_error('Please select a video file first.')

    elif event == 'Select Video':
        selected_files = select_video()
        if selected_files:
            window['Process Video'].update(disabled=False)
        else:
            sg.popup_error('Please select a video file first.')

    elif event == 'Process Video':
        if selected_files:
            total_files = len(selected_files)
            for index, file_paths in enumerate(selected_files, start=1):
                window['file_counter'].update(f'Processing {index}/{total_files}')
                process_video(file_paths, window)
                window['progressbar'].UpdateBar(0)
            # else:
                # sg.popup_error('No video files selected.')

# Close the window and end the program
window.close()