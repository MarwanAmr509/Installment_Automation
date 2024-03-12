import pandas as pd
from Service import Create_Service
import regex as re


SECRET_FILE="secret.json"
API_NAME= "sheets"
API_VERSION = "v4"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GOOGLE_SHEET_ID = ""
INSTALLMENT_SHEET_TITLE = ""

def read_sheets(google_sheet_id):
    global INSTALLMENT_SHEET_TITLE, CASH_REPORT_SHEET_TITLE

    service = Create_Service(SECRET_FILE,API_NAME,API_VERSION,SCOPES)
    mySpreadSheets = service.spreadsheets().get(spreadsheetId=google_sheet_id).execute()

    sheets = mySpreadSheets["sheets"]

    for sheet in sheets:
        index = sheet['properties']['index']
        if index == 4:
            break
        # print(sheet["properties"]['title'])
        # print(index)
        if "أقساط" in sheet["properties"]['title']:
            INSTALLMENT_SHEET_TITLE = sheet['properties']['title']
            dataset = service.spreadsheets().values().get(spreadsheetId=google_sheet_id, range = sheet['properties']['title'], majorDimension = "ROWS").execute()
            # print(dataset['values'])
            df1 = pd.DataFrame(dataset['values'])
            df1.columns = df1.iloc[0]
            df1 = df1.iloc[1:]
            # df = df.replace("",np.nan)


    

    return df1,service

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
    print(cell_range)

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


def calculate_due(url):
    global GOOGLE_SHEET_ID, INSTALLMENT_SHEET_TITLE

    GOOGLE_SHEET_ID = re.findall('/d/(.*?)/', url)[0]

    df1, service = read_sheets(GOOGLE_SHEET_ID)
    filtered_df = df1[(df1['offer'] != "") & (df1['Actual paid'] != "") & (df1['Due'] == "")]

    for index, row in filtered_df.iterrows():
        df1.loc[index, "Due"] = float(df1.loc[index, "offer"]) - float(df1.loc[index, "Actual paid"])
        index = index - 1
        x = df1.iloc[index, 3:10]
        start_range = 'D' + str(index + 2)
        update(x, service, start_range, INSTALLMENT_SHEET_TITLE)


if __name__ == "__main__":
  
    while True:
        url = input("Enter the URL of sheet:")
        calculate_due(url)
        # if url == '0':
        #     break
        # GOOGLE_SHEET_ID = re.findall('/d/(.*?)/', url)[0]
        
        # df1, service = read_sheets(GOOGLE_SHEET_ID)
        # filtered_df = df1[(df1['offer'] != "") & (df1['Actual paid'] != "") & (df1['Due'] == '')]
        # # df1['رقم الواتساب'] = df1['رقم الواتساب'].apply(lambda x: "'" + x)




        # for index,row in filtered_df.iterrows():
        #     df1.loc[index,"Due"] = float(df1.loc[index,"offer"]) - float(df1.loc[index,"Actual paid"])
        #     index = index - 1
        #     x = df1.iloc[index , 3:10]
        #     start_range = 'D'+str(index+2)
        #     update(x, service, start_range, INSTALLMENT_SHEET_TITLE )
        # get_due()