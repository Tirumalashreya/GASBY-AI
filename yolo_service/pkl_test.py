#pkl_test.py 
import pickle
import cv2


pkl_file_path = 'video/test_mov' + '/frames.pkl'


with open(pkl_file_path, 'rb') as f:
    frames = pickle.load(f)


for i, frame in enumerate(frames):
    
    cv2.imshow(f'Frame {i}', frame)
    
   
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    
    print(f'Frame {i}: shape = {frame.shape}')