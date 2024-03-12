# Installment_Automation

- This is a CLI Application that automate courses installment revesion
- Using Python, Google Sheets API, Image Processing, OCR
- The task was to check if the student had paid the monthly installment of the course he registerd through Vodafone Cash or Instapay receipt
- Then update the cash report google sheet which has the total income from installments
- I had made a module 'OCR.py' that extract the needed data from the recipts
- The main code in 'Main.py' which read the google sheets and iterate over each installment then OCR module check if he paid the installment or not then update the cash report. 
