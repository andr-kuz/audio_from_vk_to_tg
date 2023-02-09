import os
import time
import requests
import time

def sent_timer(func):
    def wrapper(*args,**kwargs):
        tg_limitations_timeout = 1.5
        timers = args[0].sent_timers
        recipient = args[1]
        if recipient in timers:
            while timers[recipient] + tg_limitations_timeout > time.time():
                time.sleep(tg_limitations_timeout)
        func(*args,**kwargs)
        timers[recipient] = time.time()
    return wrapper

class TelegramBot:
    def __init__(self, token: str, api_port: str, api_host: str=None):
        self._prefix = f'https://api.telegram.org/bot{token}'
        self.port = api_port
        self.host = api_host
        if self.host:
            self._prefix = f'http://{self.host}:{self.port}/bot{token}'
        self.offset = 0
        self.sent_timers = {}

    def wait_for_updates(self, timeout: int = 60) -> tuple:
        while True:
            dt = dict(offset=self.offset, timeout=timeout)
            resp = requests.get(f"{self._prefix}/getUpdates", params=dt).json()
            if not resp['ok']:
                print(resp)
                return False

            if not 'result' in resp:
                time.sleep(3)
                continue
            for result in resp['result']:
                if 'message' in result and 'text' in result['message']:
                    return (
                            result['message']['text'],
                            result['message']['chat']['id'],
                            result['update_id']
                           )

    @sent_timer
    def send_message(self, chat_id: int, text: str, update_id: int = 0) -> object:
        resp = requests.get(
                f"{self._prefix}/sendMessage",
                params = {
                    'chat_id': chat_id,
                    'text': text
                    }
                )
        if update_id:
            self.update_confirmed(update_id)
        return resp.json()

    @sent_timer
    def send_audio(self, chat_id: int, audio_data: dict, update_id: int) -> object:
        audio_data['chat_id'] = chat_id
        audio_bytes = audio_data['audio']
        del audio_data['audio']
        resp = requests.post(f'{self._prefix}/sendAudio', data = audio_data, files={'audio': audio_bytes}).json()
        if resp['ok']:
            self.update_confirmed(update_id)
        return resp

    def update_confirmed(self, update_id: int) -> None:
        self.offset = update_id + 1

    def delete_webhook(self, delete_pending_updates: bool) -> object:
        resp = requests.post(
                f"{self._prefix}/deleteWebhook",
                data = {'delete_pending_updates': delete_pending_updates},
                )
        return resp.json()
