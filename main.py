import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--ignore-ssl-errors")
chrome_options.add_argument("--headless")  # Enable headless mode

# Set up the Selenium driver with the specified options
driver = webdriver.Chrome(options=chrome_options)

# Open the login page
URL = 'https://my.quika.online/clientarea.php'
driver.get(URL)

# Find the username and password fields and enter your login credentials
username_field = driver.find_element(By.XPATH, '//input[@name="username"]')
password_field = driver.find_element(By.XPATH, '//input[@name="password"]')

username_field.send_keys('Technical@quika.af')
password_field.send_keys('TechQuika@765')

# Submit the login form
password_field.send_keys(Keys.RETURN)

# Wait for a while to ensure the login is complete
driver.implicitly_wait(5)


def login_again():
    URL = 'https://my.quika.online/clientarea.php'
    driver.get(URL)

    # Find the username and password fields and enter your login credentials
    username_field = driver.find_element(By.XPATH, '//input[@name="username"]')
    password_field = driver.find_element(By.XPATH, '//input[@name="password"]')

    username_field.send_keys('Technical@quika.af')
    password_field.send_keys('TechQuika@765')

    # Submit the login form
    password_field.send_keys(Keys.RETURN)

    # Wait for a while to ensure the login is complete
    driver.implicitly_wait(5)

    # Wait for a while to ensure the dropdown selection is complete
    driver.implicitly_wait(1)

    # Get the HTML content of the current page
    html_content = driver.page_source

    # Use BeautifulSoup to parse the HTML content
    return BeautifulSoup(html_content, 'html.parser')


def select_all_from_dropdown():
    try:
        select = Select(driver.find_element(By.NAME, 'tableServicesList_length'))
        select.select_by_visible_text('All')
    except NoSuchElementException:
        login_again()
        # Retry selecting the dropdown after login
        select = Select(driver.find_element(By.NAME, 'tableServicesList_length'))
        select.select_by_visible_text('All')


def htmlfile():
    desired_link = 'https://my.quika.online/clientarea.php?action=services'
    driver.get(desired_link)

    # Find and select the "All" option from the dropdown menu using explicit wait
    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.NAME, 'tableServicesList_length')))
        select_all_from_dropdown()
    except TimeoutException:
        print("Timeout waiting for the dropdown. Handling the exception.")
        login_again()
        select_all_from_dropdown()
        # Wait for a while to ensure the dropdown selection is complete
    driver.implicitly_wait(1)

    # Get the HTML content of the current page
    html_content = driver.page_source

    # Use BeautifulSoup to parse the HTML content
    return BeautifulSoup(html_content, 'html.parser')


# Telegram bot token
TOKEN = '6986837617:AAGAQB_LozNseY4IC34Dy3yxLEW6u8fszlg'

# Load the Excel file into a DataFrame
excel_file = 'recipients_data.xlsx'
df_recipients = pd.read_excel(excel_file)


def usage_extract(input_string):
    # Define a regex pattern to match numbers (floats or integers) in the string
    number_pattern = r'(\d+(\.\d+)?)'

    # Use re.findall to find all matches in the string
    matches = re.findall(number_pattern, input_string)

    # Extract the numbers from the matches
    current_usage = round(float(matches[0][0]) if matches and matches[0][0] else 0.0, 2)
    total_quota = round(float(matches[1][0]) if len(matches) > 1 and matches[1][0] else 0.0, 2)

    return current_usage, total_quota


def get_mac_from_code(code):
    # Search for the MAC address associated with the provided code
    try:
        mac_address = df_recipients.loc[df_recipients['Code'] == code, 'MAC'].values[0]
        return mac_address
    except IndexError:
        return None


def onemac(userinput):
    domain = 'https://my.quika.online/'
    mac_list = []
    link_list = []
    html = htmlfile()
    for tr in html('tr'):
        if tr.find_all('font') and tr.find_all('span', class_="label status status-active"):
            macs = tr.find_all('font')
            for m in macs:
                mac = m.string
                mac_list.append(mac)
            for link in tr.findAll('a', class_="btn btn-block btn-info"):
                link_list.append(domain + link.get('href'))

    macs_link = []
    macaddress = userinput
    if macaddress in mac_list:
        ind = mac_list.index(macaddress)
        macs_link.append(link_list[ind])

    mmac = []
    musage = []
    mexp = []

    for link in macs_link:
        url = link

        driver.get(url)
        time.sleep(4)
        client_html = driver.page_source
        soup = BeautifulSoup(client_html, 'html.parser')
        package = soup.find_all('span')[28].text
        div = soup.find('div', class_="col-md-6 text-center")
        expiredate = []
        for i in div:
            expiredate.append(i)
        mmac.append(macaddress)
        used, quota = usage_extract(package.strip('\n'))
        musage.append((used, quota))
        mexp.append(expiredate[8].get_text(strip=True))
    modem_data = dict(zip(mmac, zip(musage, mexp)))
    return modem_data


def get_modem_data(update: Update, context: CallbackContext) -> None:
    # Split the user's input to get the code
    user_input = update.message.text.split(' ')[1]
    user_code = user_input.strip()  # Assuming the code is directly provided by the user

    # Find the MAC address associated with the user's code
    mac_address = get_mac_from_code(user_code)

    if mac_address is not None:
        # Fetch and send modem data for the found MAC address
        modem_data = onemac(mac_address)

        for mac_address, (usage_quota, expiration_date) in modem_data.items():
            usage, quota = usage_quota
            if quota != 0:
                message = f'Dear valued customer, your modem with the MAC address {mac_address} has an activated data plan of {quota}GB. Your current usage is {usage}GB, leaving you with a remaining data balance of {round(quota - usage, 2)}GB, This package is valid until  {expiration_date}.'
                update.message.reply_text(message)
                if quota - usage < 10:
                    wmessage = f'Dear valued customer, you have less than 10GB of internet and need to renew, please contact with your sales channel for the renewal process.'
                    update.message.reply_text(wmessage)
                # welcome_message = f'Thank you for being with Quika Afghanisan.'
                # update.message.reply_text(welcome_message)

                persionmessage = f' مشتری گرامی شما در مودم با مک ادرس {str(mac_address)} که مربوط شما میباشد. {quota} جی بی فعال نموده اید. و شما تا این حال {usage}  جیبی استفاده نموده اید. و مقدار باقی مانده انترنت شما {round(quota - usage, 2)} جی بی است، که الا تاریخ {expiration_date} وقت دارد.'
                update.message.reply_text(persionmessage)
                alertpersionmessage = 'اطلاعیه\nمشتری گرامی!\nبرای جلوگیری از سوختن و خراب شدن دستگاه انترنت تان، لطفا در مواقع هوای بارانی و یا ابری با رعد و برق دستگاه خویش را خاموش نمایید و همچنان کیبل های شان را بکشید.\n تشکر از اعتماد شما!\nبا احترام\n شرکت کویکا افغانستان\n'
                update.message.reply_text(alertpersionmessage)
                if quota - usage < 10:
                    wpmessage = f'مشتری گرامی،شما کمتر از 10 جیبی  اینترنت دارید و نیاز به فعال سازی دوباره بسته انترنتی خود دارید، برای فعال سازی دوباره لطفا به بخش فروشات به تماس گردید.  '
                    update.message.reply_text(wpmessage)
                # pwelcome_message = f' تشکر از اینکه شما با Quika Afghanistan هستین.'
                # update.message.reply_text(pwelcome_message)
            else:
                welcome_message = f'Dear customer, Your package has been fully utilized (100%). please contact with your sales channel for the renewal process.'
                update.message.reply_text(welcome_message)
                pwelcome_message = f'مشتری محترم، بسته ای انترنیتی شما به صورت کامل (100%) به مصرف رسیده است. برای فعال سازی دوباره لطفا به بخش فروشات به تماس گردید  '
                update.message.reply_text(pwelcome_message)
    else:
        # If the code doesn't match any MAC address
        update.message.reply_text('مشتری محترم، رمز شما درست نمی باشد. لطفا رمز درست را وارد کنید.')


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'سلام مشتری محترم، این صفحه برای بررسی میزان مصرف اینترنت شما اختصاص داده شده است. برای اینکه شما بتوانید از این صفحه برای معلومات گرفتن از مقدار مصرف انترنت خود استفاده کنید باید از بخش تخنیک تقاضای رمز عبور نماید. تشکری میکنیم از شما که با ما همکار هستید.')
    """update.message.reply_text('سلام مشتری محترم، این صفحه فقط برای چک کردن مقدار مصرف انترنت شما میباشد.')
    update.message.reply_text('برای اینکه شما بتوانید از این صفحه استفاده کنید. باید از بخش تخنیک تقاضای رمز عبور نماید.')
    update.message.reply_text('تشکری میکنیم از شما که با ما همکار هستید.')
"""


def handle_message(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'مشتری محترم شما به صورت درست رمز عبور خود را وارد نکردید. شما باید به فارمت ذیل رمز عبور خود را وارد نماید. تشکر')
    update.message.reply_text('/code <رمز عبور>')


def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('code', get_modem_data))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

# Close the browser window
driver.quit()