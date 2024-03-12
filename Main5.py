import pandas as pd
from Service import Create_Service
from Due import calculate_due
# from OCR import Vodafone,Instapay
from OCR2 import Main
from datetime import datetime
import datetime as dt
import re

SECRET_FILE="secret.json"
API_NAME= "sheets"
API_VERSION = "v4"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GOOGLE_SHEET_ID = ""#"14SBpuNYd4dDlz07gOlTFkOd-dlI1yNu9NjF8FI5wRcc"
CASH_REPORT_ID = "" #"792468227"
CORRECT_PHONE = True
INSTALLMENT_SHEET_TITLE = ""
CASH_REPORT_SHEET_TITLE = ""
CORRECT_PHONE_NUMBERS = ['01007762877','01006020138','01067367209','01096998805','01096997727','01032710868','01091536425']

def cleanphone(phone):
    phone = phone.replace('+20', '0')
    if phone.startswith('0020'):
        phone = phone[3:]
    elif not phone.startswith('0'):
        phone = '0' + phone
    return phone

def read_sheets(google_sheet_id):
    global INSTALLMENT_SHEET_TITLE, CASH_REPORT_SHEET_TITLE

    service = Create_Service(SECRET_FILE,API_NAME,API_VERSION,SCOPES)
    mySpreadSheets = service.spreadsheets().get(spreadsheetId=google_sheet_id).execute()

    sheets = mySpreadSheets["sheets"]

    for sheet in sheets:
        index = sheet['properties']['index']
        if index == 4:
            break
        if 'cash' in sheet['properties']['title']:
            CASH_REPORT_SHEET_TITLE = sheet['properties']['title']
            dataset = service.spreadsheets().values().get(spreadsheetId=google_sheet_id, range = sheet['properties']['title'], majorDimension = "ROWS").execute()
            # print(dataset['values'])
            df3 = pd.DataFrame(dataset['values'])
            df3.columns = df3.iloc[0]
            df3 = df3.iloc[1:]
            # df3_columns = df3.columns.tolist()
        if "أقساط" in sheet["properties"]['title']:
            INSTALLMENT_SHEET_TITLE = sheet['properties']['title']
            dataset = service.spreadsheets().values().get(spreadsheetId=google_sheet_id, range = sheet['properties']['title'], majorDimension = "ROWS").execute()
            # print(dataset['values'])
            df1 = pd.DataFrame(dataset['values'])
            df1.columns = df1.iloc[0]
            df1 = df1.iloc[1:]
            # df = df.replace("",np.nan)
        elif 'تسجيل' in sheet["properties"]['title']:
            dataset = service.spreadsheets().values().get(spreadsheetId=google_sheet_id, range = sheet['properties']['title'], majorDimension = "ROWS").execute()
            df2 = pd.DataFrame(dataset['values'])
            df2.columns = df2.iloc[0]
            df2 = df2.iloc[1:]

    # add 0 as a prefix to each phone number
    df1['رقم الواتساب'] = df1['رقم الواتساب'].astype(str)
    df2['رقم الواتساب'] = df2['رقم الواتساب'].astype(str)

    df1['رقم الواتساب'] = df1['رقم الواتساب'].apply(cleanphone)
    df2['رقم الواتساب'] = df2['رقم الواتساب'].apply(cleanphone)
 

    return df1, df2, df3, service

def get_ids(df1, df2):
    # df1['id'] = df1['رقم الواتساب'] + df1['تم سداد قسط كورس']
    # df2['id'] = df2['رقم الواتساب'] + df2['اختر التدريب/ التدريبات التي تود الالتحاق بها']
    df1['id'] = df1['رقم الواتساب'].astype(str).str[-6:] + df1['تم سداد قسط كورس']
    df2['id'] = df2['رقم الواتساب'].astype(str).str[-6:] + df2['اختر التدريب/ التدريبات التي تود الالتحاق بها']
    return df1, df2

def get_emptyoffers(df1):
    empty_offers = df1[df1["offer"]==""]["id"].values.tolist()    # get phone numbers that has empty offer
    empty_offers = [item for item in empty_offers if item != '0']
    return empty_offers

def sheet2_due(df2, empty_offers):
    """
    get due in sheet2 which it's phone number has empty offer in sheet1
    Return:
        due2:
    """
    due2 = df2[['id', 'Due']]
    due2 = due2[due2['id'].isin(empty_offers)]                       # get due in sheet2 which it's phone number has empty offer in sheet1
    due2 = due2.set_index('id')
    return due2


def get_min_due(df1, df2, empty_offers):
    due2 = sheet2_due(df2, empty_offers)
    due1 = df1.groupby('id').Due.min()                              # get minimum due for each phone number in sheet1
    due1 = pd.DataFrame(due1)

    due2['Due'] = due2['Due'].replace('',None).astype('float')

    min_dues = due2.join(due1, lsuffix='_2').apply(min, axis=1)                  # get minimum due for each phone number in the 2 sheets
    return min_dues

def get_urls_df(df1, empty_offers):
    urls = df1[(df1['Actual paid'].isna()) & (df1['id'].isin(empty_offers))]["من فضلك ارفق صورة من إيصال الدفع (فودافون كاش / رسالة خصم الفيزا/ بوسطه/ إنستا باي /رسالة المنحة)"]
    row_indices = urls.index.tolist()
    pay_method = df1[(df1['Actual paid'].isna()) & (df1['id'].isin(empty_offers))]['كيفية الدفع']
    reference_number = df1[(df1['Actual paid'].isna()) & (df1['id'].isin(empty_offers))]['الرقم المرجعي']
    urls_df = pd.DataFrame({"url":urls,
                            "row_index":row_indices,
                            'pay_method':pay_method,
                            "reference": reference_number})
    return urls_df
    
def get_cash_phones(row, url_list):
    global CORRECT_PHONE


    cash = []
    phones = []
    for url in url_list:
            print('url',url)
        # if row['pay_method'] == "فودافون كاش":
            CORRECT_PHONE = False
            phone, price = Main(url, row['pay_method']) 
            cash.append(float(price))
            phones.append(phone)

            if row['pay_method'] == 'انستا باي' or  row['pay_method'] == 'إنستا باي':
                if phone == row["reference"]:
                    CORRECT_PHONE = True
                else:
                    print("Reference code not match or not found")
                    CORRECT_PHONE = False
                    break
            elif row['pay_method'] == 'فودافون كاش':
                if phone in CORRECT_PHONE_NUMBERS:
                    CORRECT_PHONE = True
                else:
                    print("Phone number not match or not found")
                    CORRECT_PHONE = False
                    break
            elif row['pay_method'] == 'فيزا':
                    CORRECT_PHONE = True
    return cash, phones

def cash_report_df(cash_report):
    df_len = max([len(x) for x in cash_report.values()])
    for key in cash_report.keys():
        while len(cash_report[key]) != df_len:
            cash_report[key].append('')
    return cash_report

def highlight (service, start_row, end_row, start_col, end_col):
    request_body = {
    'requests':[
        {
            'repeatCell':{
                'range':{
                    'sheetId':CASH_REPORT_ID,
                    'startRowIndex':start_row,
                    'endRowIndex':end_row,

                    'startColumnIndex':start_col,
                    'endColumnIndex':end_col
                },
                'cell': {
                    'userEnteredFormat': {
                        'numberFormat':{
                            'type': "CURRENCY",
                            'pattern':'###0'
                        },
                        'backgroundColor':{
                            'red':30,
                            'green':161,
                            'blue':236,
                        },
                        'textFormat':{
                            'fontSize':16,
                             'bold':False
                        },
                        'horizontalAlignment':"CENTER"
                    }
                },
                'fields': 'userEnteredFormat(numberFormat,backgroundColor,textFormat,horizontalAlignment)'
            }
        }
    ]
}
    service = Create_Service(SECRET_FILE,API_NAME,API_VERSION,SCOPES)

    response = service.spreadsheets().batchUpdate(spreadsheetId = GOOGLE_SHEET_ID, body= request_body).execute()


def sheets_processing(service, df1, df2, df3):

    df3_columns = df3.columns.tolist()
    today_data = {x:[] for x in df3_columns}
    # print("today",today_data)
    today = datetime.today().strftime('%d-%m-%Y')
    today_data["Date"] = [today]
    
    df1, df2 = get_ids(df1, df2)
    empty_offers = get_emptyoffers(df1)

    df1.replace('', None, inplace=True)
    try:
        df1['Due'] = df1.Due.astype('float')
    except:
        raise Exception('Make sure that there is no empty rows!')
    min_dues = get_min_due(df1, df2, empty_offers)

    for phone, due in zip(min_dues.index, min_dues.values):
        df1.loc[(df1['offer'].isna()) & (df1['id']==phone), 'offer'] = due        # put min due in due column (for empty offers)

    urls_df = get_urls_df(df1, empty_offers)
    
    df1 = df1.drop('id',axis=1)                                                   # Drop id columns from df1, df2
    df2 = df2.drop('id',axis=1)
    
    for index,row in urls_df.iterrows():                                          # get phone and cash from vodafone cash reciets
        # print(type(index))
        # print(row['url'])
        urls = row['url'].replace(" ", "")
        url_list = urls.split(",")

        cash, phones = get_cash_phones(row, url_list)

        price = sum(cash)

        if CORRECT_PHONE and (price !=0):
            df1.loc[index,"Actual paid"] = price
            
            try:
                df1.loc[index,"Due"] = df1.loc[index,"offer"] - price
            except:
                # df1.loc[index,"offer"] = ""
                df1.loc[index,"Due"] = ""

            index = row['row_index'] - 1
            x = df1.iloc[index , :10]
            # print(x)
            # print('row data:',x.values.tolist())
            x['رقم الواتساب'] = "'" + x['رقم الواتساب']
            start_range = 'A'+str(index+2)
            update(x, service, start_range, INSTALLMENT_SHEET_TITLE )

            if row['pay_method'] == 'فودافون كاش':
                today_data[phones[0]].append(price)

            elif row['pay_method'] == 'فيزا' or row['pay_method'] == 'انستا باي' or row['pay_method'] == 'إنستا باي':
                today_data['Website Visa'].append(price)

            


        else:
            df1.loc[index,"Actual paid"] = ""

            index = row['row_index'] - 1
            x = df1.iloc[index , :8]
            # print(x)
            # print('row data:',x.values.tolist())
            start_range = 'A'+str(index+2)

            x['رقم الواتساب'] = "'" + x['رقم الواتساب']

            update(x, service, start_range, INSTALLMENT_SHEET_TITLE )

    df1.fillna('', inplace=True)
    df1['رقم الواتساب'] = "'"+df1['رقم الواتساب']
    # print("cash report data",cash_report_data)
    today_data = cash_report_df(today_data)
    today_dataframe = pd.DataFrame.from_dict(today_data)
    # print('cash report columns:',today_dataframe.columns)
    # print('df3 columns:',df3_columns)
    cash_report_dataframe = pd.concat([df3,today_dataframe])
    diffrence = len(cash_report_dataframe) - len(today_dataframe)
    # print(index)
    last_day_df = cash_report_dataframe.iloc[diffrence:,:]
    # print(last_day_df)
    for i, (index, row) in enumerate(last_day_df.iterrows()):
        # print(f"Row {i}, index: {index}")
        for j,item in enumerate(row):
            # print(f"Row {i+diffrence+1}, Column{j} ")
            # print(item)
            if item != "":
                highlight(service,i+diffrence+1, i+diffrence+2, j, j+1)
 

            
    #         print(row)
    # print("cash report dataframe",cash_report_dataframe)
    return df1, df2, cash_report_dataframe, urls_df, last_day_df, diffrence

def update(df1, service, start_range, sheet_title):
    l = []
    # l.append(df1.columns.tolist())
    l.extend(df1.values.tolist())

    for i,item in enumerate(l):
        if item == None :
            l[i] == ''
    print('L:',l)

    # cell_range = "اقساط ديسمبر!" + start_range
    cell_range = sheet_title + "!" + start_range

# Define the new value you want to set in the cell
    new_value = l

    # Create the value range object
    value_range_body = {
        "range": cell_range,
        "values": [new_value]
    }

    # Call the Sheets API to update the cell value
    result = service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=cell_range,
        valueInputOption='USER_ENTERED',
        body=value_range_body).execute()

    # Print the result to the console
    print(f"{result.get('updatedCells')} cells updated.")

def update_cash_report(df1, service, start_range, sheet_title):
    l = []
    # l.append(df1.columns.tolist())
    l.extend(df1.values.tolist())
    

    # cell_range = "اقساط ديسمبر!" + start_range
    cell_range = sheet_title + "!" + start_range

# Define the new value you want to set in the cell
    new_value = l

    # Create the value range object
    value_range_body = {
        "range": cell_range,
        "values": new_value
    }

    # Call the Sheets API to update the cell value
    result = service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=cell_range,
        valueInputOption='USER_ENTERED',
        body=value_range_body).execute()

    # Print the result to the console
    print(f"{result.get('updatedCells')} cells updated.")


    
def Audit(google_sheet_id):
    df1, df2, df3, service = read_sheets(google_sheet_id)
    df1, df2, cash_report_dataframe, indicies, last_day_df, diffrence = sheets_processing(service, df1, df2, df3)
    start_range = 'A' + str(diffrence +2)
    # today = cash_report_dataframe.iloc[-diffrence,:]
    # print(today)
    # update(df1, service, "A20",INSTALLMENT_SHEET_TITLE)
    # update_cash_report(cash_report_dataframe, service, 'A1', CASH_REPORT_SHEET_TITLE)
    print('start range:',start_range)
    print("diffrence: ",diffrence)
    update_cash_report(last_day_df, service, start_range, CASH_REPORT_SHEET_TITLE)


    print("Edited rows in installment sheet:\n",[x+1 for x in indicies['row_index']])





if __name__ == "__main__":
  
    while True:
        url = input("Enter the URL of cash report sheet:")
        if url == '0':
            break
        GOOGLE_SHEET_ID = re.findall('/d/(.*?)/', url)[0]
        CASH_REPORT_ID = re.findall('gid=(\d+)', url)[0]

        Audit(GOOGLE_SHEET_ID)

        get_due = input("Do you want to get Due ? (1/0)\n")
        if get_due == '1':
            url = input("Enter the URL of sheet:")
            calculate_due(url)




