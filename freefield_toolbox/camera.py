import os
import numpy as np #for some reason numpy must be imported before PySpin
import PySpin
import cv2
import dlib
from imutils import face_utils
system = PySpin.System.GetInstance()     # Retrieve singleton reference to system object
version = system.GetLibraryVersion() # Get current library version
print('PySpin Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))
cam_list = system.GetCameras()    # Retrieve list of cameras from the system
num_cameras = cam_list.GetSize()
_location_ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# configuration for head extracting the head pose of an image
face_landmark_path = os.path.join(_location_, "shape_predictor_68_face_landmarks.dat")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(face_landmark_path)

if num_cameras != 1:    # Finish if there are no cameras
    cam_list.Clear()# Clear camera list before releasing system
    system.ReleaseInstance() # Release system instance
    print('Error! There must be exactly one camera attached to the system!')
else:
    cam = cam_list[0]
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    node_device_information = PySpin.CCategoryPtr(nodemap_tldevice.GetNode('DeviceInformation'))
    if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
        features = node_device_information.GetFeatures()
        for feature in features:
            node_feature = PySpin.CValuePtr(feature)
            print('%s: %s' % (node_feature.GetName(),
            node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
        else:
            print('Device control information not available.')

    cam.Init() # Initialize camera
    nodemap = cam.GetNodeMap() # Retrieve GenICam nodemap

def acquire_images(filename, n=1):
    # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
    node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
    if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
        print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
        return False
    # Retrieve entry node from enumeration node
    node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
    if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
        print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
        return False
    # Retrieve integer value from entry node
    acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
    # Set integer value from entry node as new value of enumeration node
    node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
    # What happens when the camera begins acquiring images depends on the
    # acquisition mode. Single frame captures only a single image, multi
    # frame catures a set number of images, and continuous captures a
    # continuous stream of images
    cam.BeginAcquisition()
    for i in range(n):
        image_result = cam.GetNextImage()
        if image_result.IsIncomplete():
            print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
        image_result.Release()
        image_converted.Save(filename)
        print('Image saved at %s' % filename)
        cam.EndAcquisition()

def deinit():
    global cam
    cam.DeInit()        # Deinitialize camera
    print("Deinitializing camera...")

def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """
    print('*** DEVICE INFORMATION ***\n')
    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))
        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def get_pose_from_image(image_path, plot=False):
    im = cv2.imread(image_path)
    size = im.shape
    # Camera matrix describing the transformtaion from camera to image coordinates
    # the focal lenth is approximated as as the image width and the optical center
    # as the center of the image
    focal_length = size[1]
    center = (size[1]/2, size[0]/2)
    cam_matrix = np.array(
                             [[focal_length, 0, center[0]],
                             [0, focal_length, center[1]],
                             [0, 0, 1]], dtype = "double"
                             )
    dist_coeffs = np.zeros((4,1)) # assuming no lens distortion

    # Array of object points in the world coordinate space.
    # The elements represent points in a generic 3D model
    object_pts = np.float32([[6.825897, 6.760612, 4.402142],
                            [1.330353, 7.122144, 6.903745],
                            [-1.330353, 7.122144, 6.903745],
                            [-6.825897, 6.760612, 4.402142],
                            [5.311432, 5.485328, 3.987654],
                            [1.789930, 5.393625, 4.413414],
                            [-1.789930, 5.393625, 4.413414],
                            [-5.311432, 5.485328, 3.987654],
                            [2.005628, 1.409845, 6.165652],
                            [-2.005628, 1.409845, 6.165652],
                            [2.774015, -2.080775, 5.048531],
                            [-2.774015, -2.080775, 5.048531],
                            [0.000000, -3.116408, 6.097667],
                            [0.000000, -7.415691, 4.070434]])

    # Get corresponding 2D points in the image:
    face_rects = detector(im, 0)
    if not face_rects:
        print("ERROR! Are you sure this is a face?")
        return None, None, None
    shape = predictor(im, face_rects[0])
    shape = face_utils.shape_to_np(shape)
    image_pts = np.float32([shape[17], shape[21], shape[22],shape[26], shape[36],shape[39],
    shape[42], shape[45], shape[31], shape[35], shape[48], shape[54], shape[57], shape[8]])
    #estimate the translation and rotation coefficients:
    success, rotation_vec, translation_vec = cv2.solvePnP(object_pts, image_pts, cam_matrix, dist_coeffs)
    # get the angles out of the transformation matrix:
    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = cv2.hconcat((rotation_mat, translation_vec))
    _, _, _, _, _, _, euler_angle = cv2.decomposeProjectionMatrix(pose_mat)
    if plot:
        project_points_on_image(im, shape, euler_angle, rotation_vec, translation_vec, cam_matrix, dist_coeffs)
    return euler_angle[0, 0], euler_angle[1, 0], euler_angle[2, 0] # x, y, z

def project_points_on_image(im, shape, euler_angle, rotation_vec, translation_vec, cam_matrix, dist_coeffs):

    reprojectsrc = np.float32([[10.0, 10.0, 10.0],
                            [10.0, 10.0, -10.0],
                            [10.0, -10.0, -10.0],
                            [10.0, -10.0, 10.0],
                            [-10.0, 10.0, 10.0],
                            [-10.0, 10.0, -10.0],
                            [-10.0, -10.0, -10.0],
                            [-10.0, -10.0, 10.0]])

    reprojectdst, _ = cv2.projectPoints(reprojectsrc, rotation_vec, translation_vec, cam_matrix, dist_coeffs)
    reprojectdst = tuple(map(tuple, reprojectdst.reshape(8, 2)))

    for (x, y) in shape:
        cv2.circle(im, (x, y), 1, (0, 0, 255), -1)
        cv2.putText(im, "X: " + "{:7.2f}".format(euler_angle[0, 0]), (20, 20), cv2.FONT_HERSHEY_SIMPLEX,
            0.75, (0, 0, 0), thickness=2)
        cv2.putText(im, "Y: " + "{:7.2f}".format(euler_angle[1, 0]), (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
            0.75, (0, 0, 0), thickness=2)
        cv2.putText(im, "Z: " + "{:7.2f}".format(euler_angle[2, 0]), (20, 80), cv2.FONT_HERSHEY_SIMPLEX,
            0.75, (0, 0, 0), thickness=2)
        cv2.imshow("Head Pose", im)
    cv2.waitKey(0)


if __name__ == "__main__":
    import camera
    camera.init()
    filename="C:/Projects/Spinnaker_Python/tmp.jpg"
    camera.acquire_images(filename)
    camera.deinit()
