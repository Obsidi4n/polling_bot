import time
import math
import logging
import telegram
import sqlite3
from telegram.ext import Updater

from telegram.utils.request import Request

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .config import CONFIG

logger = logging.getLogger(__name__)

SUMMARY_CYCLE = 15
CHECK_INTERVALS_SECONDS = 30
EXCHANGE_FEE_PERC = 0.001

SUMMARY_GAP = math.floor((SUMMARY_CYCLE * CHECK_INTERVALS_SECONDS)/60)



conn = sqlite3.connect('persist.db')
conn.row_factory = sqlite3.Row

cursor = conn.cursor()
cursor.execute("select * from users")

for row in cursor:
    user = row['user']
    if user in CONFIG:
        prev_mapping = CONFIG[user]
        for key in row.keys():
            prev_mapping[key] = row[key]

        CONFIG[user] = prev_mapping

token = cursor.execute("select token from bots where bot_name='eragon'").fetchone()['token']

print(CONFIG)
bot = telegram.Bot(token=token,
                   request=Request(con_pool_size=4, connect_timeout=30,read_timeout=30))
# updater = Updater(token=token)


driver = webdriver.Chrome()
driver.implicitly_wait(30)
driver.get("https://www.binance.com/trade.html")

wait = WebDriverWait(driver, 120)
element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'main-aside')))

print('Starting to monitor')
i = 0

while True:
    summary_iteration = (i%SUMMARY_CYCLE)==0
    alertDict = {}
    total_profit = {}

    # market_link = driver.find_element_by_xpath("//div[@class='main-aside']//li[text()='BTC']")
    market_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='main-aside']//li[text()='BTC']")))

    market_link.click()

    print(market_link.get_attribute("class"))

    #market_box = divContainer.find_element_by_xpath("//div[@class='market-box']")
    for element in driver.find_elements_by_xpath("//div[@class='market-con scrollStyle']/child::ul"):
        print(element.text)
        currency,value,market_change = element.text.split()

        coin,base = currency.split('/')
        for user in CONFIG:
            kitty = CONFIG[user]['kitty']
            if coin in kitty:
                print('Comparing %s' % coin)

                coin_config = kitty.get(coin)
                if isinstance(coin_config, list):
                    coin_count = sum([j for i,j in coin_config])
                    buy_value = sum([i*j for i,j in coin_config])/coin_count
                else:
                    buy_value, coin_count = coin_config
                
                buy_amount = coin_count*buy_value
                effective_coin_count = math.floor(coin_count * (1 - EXCHANGE_FEE_PERC))

                print('Bought at %s for bulk amount %s' % (str(buy_value),str(buy_amount)))
                print('Right now at %s' % value)
                curr_value = float(value)
                diff = curr_value - buy_value
                price_change_perc = 100 * diff/buy_value

                sell_amount = effective_coin_count*curr_value*(1-EXCHANGE_FEE_PERC)
                profit =  sell_amount - buy_amount
                total_profit[user] = total_profit.get(user,0.0)+profit
                profit_perc = 100*profit/buy_amount

                break_even_price = buy_amount/(effective_coin_count *(1-EXCHANGE_FEE_PERC))

                print('Perc diff at %s' % str(price_change_perc))
                if summary_iteration or profit_perc>5:
                    alertItems = alertDict.get(user,[])
                    alertItems.append((coin,price_change_perc,buy_value,break_even_price,curr_value,profit,profit_perc))
                    alertDict[user] = alertItems

    if alertDict:
        for user in alertDict:
            alertItems = alertDict[user]
            print('Alerts for %s' % user)
            print(alertItems)
            if summary_iteration:
                message_text = "Summary (Next one in %d min)\nTotal Profit/Loss: %0.8f" % (SUMMARY_GAP,total_profit[user])
            else:
                message_text = "Something's cooking!"

            message_text = "%s\n\n%s" % (message_text,
                                 '\n'.join(["%s is at %0.2f%%\nBuy price at %0.8f\nBreakeven at %0.8f\nPresently at %0.8f\nProfit/loss calculated %0.8f (%0.2f%%)\n" % item for item in alertItems]))

            chat_id = CONFIG[user]['chat_id']
            message_id = None
            fetch_message_id = 'summary_message' if summary_iteration else 'alert_message'
            message_id = CONFIG[user].get(fetch_message_id)
            try:
                if not message_id or message_id==-1:
                    print('No previous message. Sending anew to %s' % user)
                    sent_message = bot.sendMessage(chat_id,message_text)
                    # send_message

                    print('Saving message id: %s' % sent_message)
                    print("update users set %s=%d where user='%s'" % (fetch_message_id,sent_message,user))
                    cursor.execute("update users set %s=%d where user='%s'" % (fetch_message_id,sent_message,user))
                    conn.commit()
                    CONFIG[user][fetch_message_id] = sent_message
                else:

                    print('Found old message id for %s: %s' % (user,message_id))
                    # bot.editMessageText(chat_id = chat_id, message_id = message_id, text = message_text, timeout=10)
                    sent_message.edit_text(text = message_text)
            except:
                logger.exception('Error',exc_info=True)
                print('Something went wrong. But let\'s keep quiet about it for now')
    i+=1
    if i==SUMMARY_CYCLE:
        driver.refresh()
        i=0
        element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'main-aside')))
    print('Resting')
    time.sleep(CHECK_INTERVALS_SECONDS)
driver.close()