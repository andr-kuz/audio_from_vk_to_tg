"""
Обработчик информации для связи VK с остальным приложением
"""
import vk_api
from vk_api import audio
from lib.vk_app import VkApp
from lib.vk_audio_downloader import MusicDownloader

class Vk_handler():
    def __init__(self, vk_username, vk_password, vk_app_token):
        self.username = vk_username
        self.password = vk_password
        self.token = vk_app_token
        self.vk_session = None
        self.vk_app = None
        self.vk_audio = None
        self.downloader = None

    def auth(self, two_factor_code: str = None) -> bool:
        """
        Auths in VK
        If there's demand of two-factor authentication, returns False
        """
        def tf_auth_handler():
            remember_device = True
            return two_factor_code, remember_device
        
        handler = tf_auth_handler if two_factor_code else None
        self.vk_session = vk_api.VkApi(self.username, self.password, auth_handler=handler)
        try:
            self.vk_session.auth(token_only=True)
            return True
        except vk_api.exceptions.AuthError:
            return False

    def get_posts_by_id(self, posts: str) -> list:
        """
        Receives VK posts string formatted like `-12345678_12345 123456_123` with any separator
        """
        if not self.vk_app:
            self.vk_app = VkApp(self.token)
        posts = self.vk_app.wall_get_by_id(posts)
        return posts

    def get_audio_by_id(self, owner_id: str, track_id: str):
        """
        Downloads audio by track id
        Params
        ------
        owner_id: id who owns the track (groups owner id always starts with -)
        audio_id: audio id
        """
        if not self.vk_audio:
            self.vk_audio = audio.VkAudio(self.vk_session)
            self.downloader = MusicDownloader(self.vk_audio)
        return self.downloader.get_audio_by_id(owner_id, track_id)

if __name__ == '__main__':
    VK_USERNAME = 'USERNAME'
    VK_PASSWORD = 'PASSWORD'
    vk = Vk_handler(VK_USERNAME, VK_PASSWORD, None)
    if not vk.auth():
        message = input('Введите код двухфакторной аутентификации: ')
        res = vk.auth(message)
