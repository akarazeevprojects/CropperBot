#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater, MessageHandler, Filters
import telegram
import logging
import json
import os
import time

from PIL import Image
import math

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - \
                            %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_token():
    path = os.path.join('res', 'token.json')
    with open(path) as jsn:
        data = json.load(jsn)
    return data['token']


def text_handler(bot, update):
    update.message.reply_text("Better send me a file with .jpg or .png extension")


def letscrop(file_path, chat_dir, extension, squares=False, update=None, remove=True):
    img = Image.open(file_path)
    width, height = img.size

    slices = math.ceil(width / height)
    slice_width = math.floor(width / slices)
    if squares:
        slice_height = slice_width
    else:
        slice_height = math.floor(slice_width * (1350 / 1080))
        if slice_height > height:
            slice_height = height
    vert_shift = math.floor((height - slice_height) / 2)

    debug_text = []
    debug_text.append('W: {}, H: {}'.format(width, height))
    debug_text.append('Slice height: {} out of {} with shift {}'.format(slice_height, height, vert_shift))
    debug_text.append('{} * {} = {}'.format(slices, slice_width, slices * slice_width))
    debug_text = '\n'.join(debug_text)

    if update:
        if width < height:
            update.message.reply_text("Soryan, it's not a horizontal panorama")
            return

    right = slice_width
    left = 0

    for slice_num in range(slices):
        working_slice = img.crop((left, vert_shift, right, vert_shift + slice_height))

        slice_name = os.path.join(chat_dir, str(slice_num) + "_" + "slice" + extension)
        working_slice.save(slice_name)

        right += slice_width
        left += slice_width

        if update:
            with open(slice_name, "rb") as f:
                update.message.reply_photo(photo=f)
        time.sleep(1)

        if remove:
            os.remove(slice_name)

    if update:
        update.message.reply_text(debug_text)


def cropper(bot, update):
    file_path = None

    chat_dir = os.path.join("data", str(update.message.chat_id))
    if not os.path.exists(chat_dir):
        os.mkdir(chat_dir)

    extension = ".jpg"
    if update.message.document is None:
        # Photo case
        file_id = update.message.photo[-1].file_id
        file = bot.get_file(file_id)
        file_path = os.path.join(chat_dir, file_id + extension)
        file.download(file_path)
    elif update.message.photo == [] and update.message.document is not None:
        # Document case
        file_name = update.message.document.file_name

        extension = file_name[-4:].lower()
        if extension not in [".jpg", ".png"]:
            update.message.reply_text("Better send me a file with .jpg or .png extension")
            return

        file = bot.get_file(update.message.document.file_id)
        file_path = os.path.join(chat_dir, file_name)
        file.download(file_path)
    else:
        update.message.reply_text("Error")
        return

    update.message.reply_text("Cropping ...")
    letscrop(file_path, chat_dir, extension, update=update)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    token = get_token()
    print('-> USE PROXY')
    req = telegram.utils.request.Request(proxy_url='socks5h://127.0.0.1:9050',
            read_timeout=30, connect_timeout=20,
            con_pool_size=10)
    bot = telegram.Bot(token=token, request=req)
    
    updater = Updater(bot=bot)
    dp = updater.dispatcher
    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.photo | Filters.document, cropper))
    dp.add_handler(MessageHandler(Filters.text, text_handler))

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
