import requests
import re

class VkApp:
    def __init__(self, app_token: str, version: float = 5.131):
        self._params = dict(
                access_token = app_token,
                v = version,
        )

    def wall_get_by_id(self, posts_url: str) -> dict:
        pattern = r'(-?\d+_\d+)'
        matched = re.findall(pattern, posts_url)
        if matched:
            posts_id = ','.join(matched)
            params = self._params
            params['posts'] = posts_id
            url = 'https://api.vk.com/method/wall.getById'
            resp = requests.get(url = url, params = params)
            return resp.json()
