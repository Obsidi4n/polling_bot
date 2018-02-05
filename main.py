import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def echo(bot, update):
    logging.info('Echoing back to %d' % update.message.chat_id)
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def start(bot, update):
    logging.info('Start chat with %d' % update.message.chat_id)
    bot.send_message(chat_id=update.message.chat_id, text="Hello! ")

updater = Updater(token='477217407:AAFFh8bwTuNcMoNbWy8PKcFtX4nhJAHVCbU')
start_handler = CommandHandler('start', start)
echo_handler = MessageHandler(Filters.text, echo)

dispatcher = updater.dispatcher
dispatcher.add_handler(echo_handler)
dispatcher.add_handler(start_handler)

updater.start_polling()