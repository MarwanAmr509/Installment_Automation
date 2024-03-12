import cv2

# Define the ROI selection function
def ROI(img):
    # Create a variable to hold the ROI
    roi = None

    # Define a callback function for the mouse events
    def mouse_callback(event, x, y, flags, param):
        nonlocal roi
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_callback.start_x, mouse_callback.start_y = x, y
        elif event == cv2.EVENT_LBUTTONUP:
            end_x, end_y = x, y
            roi = img[min(mouse_callback.start_y, end_y):max(end_y, mouse_callback.start_y), min(mouse_callback.start_x, end_x):max(end_x, mouse_callback.start_x)]

            # Display the ROI in a separate window
            cv2.namedWindow("ROI", cv2.WINDOW_NORMAL)
            cv2.imshow("ROI", roi)

            # Assign the coordinates to global variables
            global start_x, start_y
            start_x, start_y = mouse_callback.start_x, mouse_callback.start_y

    # Create a window to display the image
    cv2.namedWindow("Image", cv2.WINDOW_NORMAL)

    # Set the mouse callback function for the window
    cv2.setMouseCallback("Image", mouse_callback)

    # Display the image
    cv2.imshow("Image", img)

    # Wait for the user to close the window
    cv2.waitKey(0)

    # Release the window resources
    cv2.destroyAllWindows()

    # Return the ROI
    return roi


