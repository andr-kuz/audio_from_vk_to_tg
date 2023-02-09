import os
from vk_handler import Vk_handler
from telegram import TelegramBot
from lib.mp3_info import get_info, update_from_vk

def get_env_data_as_dict(path: str) -> dict:
    with open(path, 'r') as f:
       return dict(tuple(line.replace('\n', '').split('=')) for line
                in f.readlines() if not line.startswith('#'))

if not os.environ.get('VK_USERNAME'):
    temp_env = get_env_data_as_dict('./vars.env')
    os.environ.update(temp_env)

VK_USERNAME = os.environ.get('VK_USERNAME')
VK_PASSWORD = os.getenv('VK_PASSWORD')
VK_APP_TOKEN = os.getenv('VK_APP_TOKEN')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_HOST = os.getenv('TELEGRAM_API_HOST')
TELEGRAM_API_PORT = os.getenv('TELEGRAM_API_PORT')

def main() -> None:
    telegram_bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_API_PORT, TELEGRAM_API_HOST)
    vk = Vk_handler(VK_USERNAME, VK_PASSWORD, VK_APP_TOKEN)
    two_factor = None
    while True:
        message, chat_id, update_id = telegram_bot.wait_for_updates()

        if not vk.auth(message if two_factor else None):
            two_factor = True
            resp = telegram_bot.send_message(chat_id, 'Введите код двухфакторной аутентификации ВК', update_id)
            continue
        if two_factor:
            telegram_bot.send_message(chat_id, 'Успешная авторизация в ВК', update_id)
            two_factor = False
            continue

        posts = vk.get_posts_by_id(message)
        if not posts:
            telegram_bot.send_message(chat_id, 'Таких постов не существует, либо сообщение в неправильном формате', update_id)
            continue

        if 'error' in posts:
            telegram_bot.send_message(chat_id, 'Ошибка ВК:\n' + posts['error']['error_msg'] + '\nВыключаю бота', update_id)
            break

        for post in posts['response']:
            music_files = []
            for attachment in post['attachments']:
                if attachment['type'] == 'audio':
                    vk_track = attachment['audio']
                    audio_path = vk.get_audio_by_id(vk_track['owner_id'], vk_track['id'])
                    if not audio_path:
                        telegram_bot.send_message(chat_id, 'Трек заблокирован', update_id)
                        continue

                    track_data = get_info(audio_path)
                    track_data = update_from_vk(vk_track, track_data)
                    track_data['path'] = audio_path
                    music_files.append(track_data)
            telegram_bot.send_message(chat_id, post['text'])
            for track in music_files:
                with open(track['path'], "rb") as file:
                    track['audio'] = file.read()
                    telegram_bot.send_audio(chat_id, track, update_id)

if __name__ == '__main__':
    main()
