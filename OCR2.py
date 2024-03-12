import os , io , re
from Service import Create_Service
from googleapiclient.http import MediaIoBaseDownload
import cv2
import easyocr
import numpy as np
from scipy.ndimage import interpolation as inter
from ROI import ROI

SECRET_FILE="secret.json"
API_NAME= "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive"]
PRICE = ""
PHONE = ""
PHONE_NUMBER_FOUND = False
PRICE_FOUND = False
REFERENCE_FOUND = False


def read_image(file_id,file_name):
    service = Create_Service(SECRET_FILE,API_NAME,API_VERSION,SCOPES)

    request = service.files().get_media(fileId = file_id)

    output = io.BytesIO()
    downloader = MediaIoBaseDownload(fd = output,request=request)

    done = False

    while not done:
        status, done =downloader.next_chunk()
        print("Download progress {0}".format(status.progress()*100))

        output.seek(0)

        with open(os.path.join("./Images",file_name),"wb") as f:
            f.write(output.read())
            f.close()

    img = cv2.imread("./Images/"+file_name)

    return img

def correct_skew(image, delta=1, limit=5):
    def determine_score(arr, angle):
        data = inter.rotate(arr, angle, reshape=False, order=0)
        histogram = np.sum(data, axis=1, dtype=float)
        score = np.sum((histogram[1:] - histogram[:-1]) ** 2, dtype=float)
        return histogram, score

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1] 

    scores = []
    angles = np.arange(-limit, limit + delta, delta)
    for angle in angles:
        histogram, score = determine_score(thresh, angle)
        scores.append(score)

    best_angle = angles[scores.index(max(scores))]

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, best_angle, 1.0)
    corrected = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, \
            borderMode=cv2.BORDER_REPLICATE)

    return corrected

def increase_dpi(image, new_dpi):
    # Calculate the scaling factor
    scaling_factor = new_dpi / image.shape[0]  # Assuming equal scaling for width and height

    # Resize the image
    resized_image = cv2.resize(image, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_CUBIC)

    return resized_image

def preprocessing(img,pay_method, resize = True, process = True):
    img = correct_skew(img)

    if pay_method== "فودافون كاش":
        print('in Vodafone preprocessing')
        if process == True:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            gray = cv2.GaussianBlur(gray, (7, 7), 0)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            # thresh = increase_dpi(thresh, 400)

        else:
            thresh = img
            thresh = increase_dpi(thresh, 400)

        if resize == True:
            # Get the dimensions of the image
            height, width, channels = img.shape

            # Calculate the top and bottom crop sizes (10% of the height)
            top_crop = int(0.25 * height)
            bottom_crop = int(0.3 * height)

            # Crop the image
            thresh = thresh[top_crop:height-bottom_crop, :]
            thresh = increase_dpi(thresh, 400)
            # print('preprocessing done')
        cv2.imwrite('Images/processed_Vodafone.jpg', thresh)

    else:
        height, width, channels = img.shape
        
        if pay_method == "إنستا باي" or pay_method == 'انستا باي':
            print('in instapay processing')
            # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # gray = cv2.GaussianBlur(gray, (3, 3), 0)
            # thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            # Calculate the top and bottom crop sizes (10% of the height)
            top_crop = int(0.1 * height)
            bottom_crop = int(0.2 * height)

            # Crop the image
            thresh = img[top_crop:height-bottom_crop, :]

            cv2.imwrite('Images/processed_Instapay.jpg', thresh)

        if pay_method == "فيزا":
            print('in visa processing')
            top_crop = int(0.3 * height)
            bottom_crop = int(0 * height)
            # Crop the image
            thresh = img[top_crop:height-bottom_crop, :]

            cv2.imwrite('Images/processed_Visa.jpg', thresh)


    return thresh

def OCR(preprocessed_img, pay_method):
    global PHONE_NUMBER_FOUND, PRICE_FOUND
    PHONE_NUMBER_FOUND = False
    PRICE_FOUND = False
    phone, price = "", ""
    reader = easyocr.Reader(['en',"ar"])
    # reader = easyocr.Reader(['en'])
    result = reader.readtext(preprocessed_img)
    # print('in OCR function')

    if pay_method == 'فودافون كاش':


        phone_pattern = r'01[0-9]{9}'
        price_pattern = r'\b\d+(\.\d{1,2})?\b'
        # print('In OCR pattern of codafone cash')

        if PHONE_NUMBER_FOUND == False:
            print('phone number not found')
            for text in result:
                phone_matches = re.findall(phone_pattern, text[1])
                if phone_matches: #and price_matches:
                    phone = phone_matches[0]
                    # print('phone is ',phone)
                    PHONE_NUMBER_FOUND = True
                    # phone = PHONE
                    # price = PRICE
                    break
        print('before phone',PHONE_NUMBER_FOUND)
        print('before price',PRICE_FOUND)
        if PRICE_FOUND == False and PHONE_NUMBER_FOUND == True:
                print('in price')
                for text in result:
                    price_matches = re.search(price_pattern, text[1])
                    print('match',price_matches)
                    if price_matches:
                        cash = float(price_matches.group())
                        # print("searching for price")
                        if cash > 100 and cash <3000:
                            price = cash
                            # print(price)
                            PRICE_FOUND = True
                            break
    elif pay_method == "إنستا باي" or pay_method == 'انستا باي':
        price_pattern = r"\d+(?:[,.]\d{1,2})?"
        reference_pattern = r"\b3\d{11}\b"

        if PRICE_FOUND == False:

            for text in result:
                text = text[1].replace(',',"")
                price_matches = re.search(price_pattern,text)
                # print(price_matches)
                if price_matches:
                    
                    # print('--')
                    cash = float(price_matches.group())
                    if cash > 100 and len(str(cash)) < 8:
                        price = cash
                        # phone = '01096998805'
                        PRICE_FOUND = True
                        # PHONE_NUMBER_FOUND = True
                        print(price)
                        break

        if PRICE_FOUND == True and REFERENCE_FOUND == False:
            for text in result:
                # print(text[1])
                text = text[1].replace(',',"")
                # price_matches = re.search(price_pattern,text)
                reference_matches = re.search(reference_pattern,text)

                if reference_matches:
                    reference = reference_matches.group()
                    phone = reference
                    PHONE_NUMBER_FOUND = True
                    # print(reference)
                    break

    elif pay_method == 'فيزا':
        price_pattern = r"\d+(?:[,.]\d{1,2})?"


        if PRICE_FOUND == False:

            for text in result:
                # print(text[1])
                text = text[1].replace(',',".")
                price_matches = re.findall(price_pattern,text)
                # print(price_matches)
                if price_matches:
                    print(price_matches)
                    for element in price_matches:
                        if len(element) < 8:
                        # print('--')
                            cash = float(element)#.group())
                            if cash > 150 and (cash % 2 == 0 or cash % 5 ==0) and cash < 2000:
                                price = cash
                                phone = "01096998805"
                                PRICE_FOUND = True
                                PHONE_NUMBER_FOUND = True
                                # print(price)
                                break


        
        
    
        if PHONE_NUMBER_FOUND == False or PRICE_FOUND == False:
            print("Phone number / reference number not found or price not found")
        # return PHONE , PRICE
        # phone = PHONE
        # price = PRICE

    return phone,price

def Main(image_url, pay_method, file_name = 'test.jpg'):
    global PHONE_NUMBER_FOUND, PRICE_FOUND

    PRICE_FOUND = False
    PHONE_NUMBER_FOUND = False
    # REFERENCE_FOUND = False
    # print('phone before',PHONE_NUMBER_FOUND)
    # print('price before',PRICE_FOUND)
    
    if 'open?id=' in image_url:
        FILE_ID = image_url.split('=')[1]
        # print(FILE_ID)
        
    elif '/d/' in image_url:
    # This is the second format, so we can extract the ID using the split method
        FILE_ID = image_url.split('/')[-2]
        # print(FILE_ID)
    else:
    # This URL format is not supported
        # FILE_ID = ''
        print("Invalid Google Drive URL format")
        # print(image_url)
    
    if FILE_ID:
        img = read_image(FILE_ID , file_name)
        if img is None or not np.any(img):
            return -1, -1
        else:
            print('pay_method:',pay_method)
            preprocessed_img = preprocessing(img,pay_method)
            phone,price = OCR(preprocessed_img,pay_method)
            # OCR(preprocessed_img)
            if PHONE_NUMBER_FOUND == False or PRICE_FOUND == False and pay_method == "فودافون كاش":
                # print('in condition')
                roi = ROI(img)
                preprocessed_img = preprocessing(roi,pay_method, resize = False, process = False)
                phone,price = OCR(preprocessed_img,pay_method)
            
            if price == '':
                price = 0

        # print('phone',PHONE_NUMBER_FOUND)
        # print('price',PRICE_FOUND)
        print("phone is :",phone)
        print("price is :",price)

        return phone, price


def Instapay(image_url, file_name = 'test.jpg'):
    global  PRICE_FOUND

    PRICE_FOUND = False
    # print('price before',PRICE_FOUND)

    if 'open?id=' in image_url:
        FILE_ID = image_url.split('=')[1]
        # print(FILE_ID)

    elif '/d/' in image_url:
    # This is the second format, so we can extract the ID using the split method
        FILE_ID = image_url.split('/')[-2]
        # print(FILE_ID)
    else:
    # This URL format is not supported
        # FILE_ID = ''
        print("Invalid Google Drive URL format")
        # print(image_url)
    
    if FILE_ID:
        img = read_image(FILE_ID , file_name)
        # preprocessed_img = preprocessing(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        height, width, channels = img.shape

        # Calculate the top and bottom crop sizes (10% of the height)
        top_crop = int(0.1 * height)
        bottom_crop = int(0.3 * height)

        # Crop the image
        thresh = thresh[top_crop:height-bottom_crop, :]
        cv2.imwrite('Images/processed.jpg', thresh)


        reader = easyocr.Reader(['en',"ar"])
        result = reader.readtext(thresh)

        # price_pattern = r'\b\d+(\.\d{1,2})?\b'
        price_pattern = r"\d+(?:[,.]\d{1,2})?"

        for text in result:
            text = text[1].replace(',',"")
            price_matches = re.search(price_pattern,text)
            # print(price_matches)
            if price_matches:
                
                # print('--')
                cash = float(price_matches.group())
                if cash > 100:
                    price = cash
                    # print(price)
                    break 
                
        # phone,price = OCR(preprocessed_img)
        # OCR(preprocessed_img)
        # if PRICE_FOUND == False:
        #     print('in condition')
        #     roi = ROI(img)
        #     preprocessed_img = preprocessing(roi, resize = False)
        #     phone,price = OCR(preprocessed_img)
    # print('phone',PHONE_NUMBER_FOUND)
    # print('price',PRICE_FOUND)
    # print("phone is :",phone)
    print("price is :",price)

    return price



        



if __name__ == "__main__":

    # file_id = "1CRfAkbEKYcAD3C961wOOYLKpNINTn8mU"
    # file_name = "image4.jpg"
    # img = read_image(file_id , file_name)
    # preprocessed_img = preprocessing(img)
    # OCR(preprocessed_img)

    # if PHONE_NUMBER_FOUND == False or PRICE_FOUND == False:
    #     roi = ROI(img)
    #     preprocessed_img = preprocessing(roi, resize = False)
    #     OCR(preprocessed_img)
    phone, price = Main('https://drive.google.com/open?id=11ore1U-Fl_0KkyjEHiMMCs6ql0QZyQRA', "فودافون كاش")

