import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Create a Tkinter root window and hide it
root = tk.Tk()
root.withdraw()

# Ask the user to select an MP4 file using a file dialog box
file_path = filedialog.askopenfilename(filetypes=[('MP4 files', '*.mp4')])

# Load the MP4 video file
cap = cv2.VideoCapture(file_path)

if not cap.isOpened():
    print("Error: Could not open video file")
    exit()

# Get the video properties
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

            total_frames_processed += 1
            if total_frames_processed % 1000 == 0:
                print(f'Processed {total_frames_processed} frames...')

        else:
            break

    except Exception as e:
        print(f'Error processing frame {total_frames_processed}: {e}')

    if total_frames_processed == frame_count:
        break

# Release the capture and close all windows
cap.release()
cv2.destroyAllWindows()

# Concatenate the unselected clips into a final video
final_clip = concatenate_videoclips(unselected_clips)

# Generate the output file path
output_file = "output.mp4"

# Write the final video to the output file
final_clip.write_videofile(output_file, fps=fps)

# Print the total number of blue screens detected
print(f'Total blue screens detected: {len(unselected_clips)}')