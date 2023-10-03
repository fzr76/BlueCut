import tkinter as tk
from tkinter import filedialog
import os
import cv2
import numpy as np
import PySimpleGUI as sg
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Function for select video button
def select_video():
    # Set the PySimpleGUI theme
    sg.theme('DefaultNoMoreNagging')

    # Create a Tkinter root window and hide it. Not entirely sure if this is necessary
    # However the program works so whatever LOL
    root = tk.Tk()
    root.withdraw()

    # Open a file selection dialog to choose an MP4 video file
    file_path = filedialog.askopenfilename(filetypes=[('MP4 files', '*.mp4')])

    # Return the selected file path
    return file_path

# Function for the process video button
def process_video(file_path):
    # Load the MP4 video file
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
                        unselected_clip = VideoFileClip(file_path).subclip(start_time, end_time)
                        unselected_clips.append(unselected_clip)

                        # Reset the variables for the next selection
                        start_time = None
                        end_time = None

                else:
                    if start_time is None:
                        # Start of an unselected clip
                        start_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

                # Add counter to total frames processed
                total_frames_processed += 1

            else:
                break

        except Exception as e:
            sg.popup_error(f'Error processing frame {total_frames_processed}: {e}')
            break

        if total_frames_processed == frame_count:
            break

    # Release the capture and close all windows
    cap.release()
    cv2.destroyAllWindows()

    # Concatenate the unselected clips into a final video
    final_clip = concatenate_videoclips(unselected_clips)

    # Generate the output file path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_file = os.path.join(desktop_path, "output.mp4")

    # Write the final video to the output file
    final_clip.write_videofile(output_file, fps=fps, verbose=False, logger=None)

    # Print the total number of blue screens detected
    sg.popup(f'Total blue screens detected: {len(unselected_clips)}', 'Video processing completed.')

# GUI layout
layout = [
    [sg.Button('Select Video')],
    [sg.Button('Process Video', disabled=True)],
    [sg.Exit()]
]

# Create the PySimpleGUI window with the specified title and layout
window = sg.Window('Video Processor', layout)

# Start the event loop
while True:
    # Read events and values from the window
    event, values = window.read()

    # Check if the window is closed or the "Exit" button is clicked
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break

    # Check if the "Select Video" button is clicked
    elif event == 'Select Video':
        # Call the select_video() function to choose a video file
        file_path = select_video()
        if file_path:
            # Enable the "Process Video" button if a file is selected
            window['Process Video'].update(disabled=False)

    # Check if the "Process Video" button is clicked
    elif event == 'Process Video':
        if file_path:
            # Call the process_video() function to process the selected video
            process_video(file_path)
        else:
            # Display an error message if no video file is selected
            sg.popup_error('Please select a video file first.')

# Close the window and end the program
window.close()