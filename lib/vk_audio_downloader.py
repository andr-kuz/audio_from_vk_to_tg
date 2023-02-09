"""
Downloads track from VK
Thanks to
https://github.com/gpubiceps/vk_audio_downloader
"""
import os
import time
from asyncio.exceptions import TimeoutError as AioTimeoutError
from asyncio import Semaphore, run
from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ContentTypeError, ClientConnectorError
import m3u8
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

REQUEST_STATUS_CODE = 200
TEMP_AUDIO_FILE_NAME = "temp.ts"
MAX_TASKS = 10

class MusicDownloader:
    def __init__(self, vk_audio, save_dir: str = '.'):
        self._vk_audio = vk_audio
        self.save_dir = save_dir
        self.temp_file_path = f"{self.save_dir}/{TEMP_AUDIO_FILE_NAME}"
        self.semaphore = Semaphore(MAX_TASKS)

    def get_audio_by_id(self, owner_id: int, audio_id: int, verbose: bool = True) -> str:
        """Скачивает аудио по id трека

        Params
        ------
        owner_id: ID владельца (отрицательные значения для групп)
        audio_id: ID аудио
        verbose: Вывод времени выполнения
        """
        if verbose:
            start = time.time()

        os.makedirs(self.save_dir, exist_ok=True)

        m3u8_data = self._get_m3u8_by_id(owner_id, audio_id)
        if not m3u8_data:
            return None
        m3u8_data, m3u8_url, meta_info = m3u8_data
        parsed_m3u8 = self._parse_m3u8(m3u8_data)
        segments_binary_data = run(self._get_audio_from_m3u8(parsed_m3u8=parsed_m3u8, m3u8_url=m3u8_url))

        audio_name = f"{meta_info['artist']} - {meta_info['title']}"

        mp3_path = self._write_to_mp3(segments_binary_data)

        if verbose:
            print(f"{audio_name} saved in {time.time() - start} sec")
        return mp3_path


    def _get_m3u8_by_id(self, owner_id: int, audio_id: int) -> tuple:
        """
        Params
        ------
        owner_id: ID владельца (отрицательные значения для групп)
        audio_id: ID аудио

        Returns
        -------
        data: сожержимое m3u8 файла
        url: сылка на m3u8 файл
        meta_info: Dict['artist': str, 'title': str]
        """
        try:
            audio_info = self._vk_audio.get_audio_by_id(owner_id=owner_id, audio_id=audio_id)
        except StopIteration:
            return None
        url = audio_info.get("url")
        data = m3u8.load(uri=url)
        meta_info = {
                "artist": audio_info.get("artist"),
                "title": audio_info.get("title"),
                "duration": audio_info.get("duration"),
                }
        return data, url, meta_info

    @staticmethod
    def _parse_m3u8(m3u8_data) -> dict:
        """Возвращает информацию о сегментах"""
        parsed_data = []
        segments = m3u8_data.data.get("segments")
        for segment in segments:
            temp = {"name": segment.get("uri")}

            if segment["key"]["method"] == "AES-128":
                temp["key_uri"] = segment["key"]["uri"]
            else:
                temp["key_uri"] = None

            parsed_data.append(temp)
        return parsed_data

    async def _get_audio_from_m3u8(self, parsed_m3u8: list, m3u8_url: str) -> bytes:
        """Асинхронно скачивает сегменты и собирает их в одну байт-строку"""
        downloaded_chunks = [None] * len(parsed_m3u8) # to keep chunks in order
        progress_line_shorter_multiplier = 3
        whole_progress_line = ' ' * round(100 / progress_line_shorter_multiplier)
        async with ClientSession() as session:
            for index, segment in enumerate(parsed_m3u8):
                downloaded_chunks[index] = await self._handle_segment(m3u8_url, segment, session)
                downloading_progress = sum(x is not None for x in downloaded_chunks)
                downloading_progress_percent = round(downloading_progress / len(downloaded_chunks) * 100)
                block_spaces_counter = round(downloading_progress_percent / progress_line_shorter_multiplier)
                progress_line = whole_progress_line.replace(' ' * block_spaces_counter, '█' * block_spaces_counter, 1)
                print(f'Downloading chunks: {downloading_progress_percent}%|{progress_line}|{downloading_progress}/{len(downloaded_chunks)}',  end="\r")
        return b''.join(downloaded_chunks)

    async def _handle_segment(self, m3u8_url: str, segment: dict, session: ClientSession) -> bytes:
        segment_uri = m3u8_url.replace("index.m3u8", segment["name"])
        content = await self._download_chunk(segment_uri, session)
        if segment["key_uri"] is not None:
            key = await self._download_chunk(segment["key_uri"], session)
            content = await self._decode_aes_128(data=content, key=key)
        return content

    async def _download_chunk(self, url: str, session: ClientSession) -> bytes:
        async with self.semaphore:
            while True:
                try:
                    res = await session.get(url, timeout=5)
                    content = await res.read()
                    return content if res.status == REQUEST_STATUS_CODE else None
                except (ContentTypeError, AioTimeoutError, ClientConnectorError):
                    continue

    async def _decode_aes_128(self, data: bytes, key: bytes) -> bytes:
        """Декодирование из AES-128 по ключу"""
        try:
            iv = data[0:16]
        except TypeError:
            return bytearray()
        ciphered_data = data[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decoded = unpad(cipher.decrypt(ciphered_data), AES.block_size)
        return decoded

    @staticmethod
    def _write_to_file(data: bytes, path: str) -> None:
        with open(path, "wb+") as f:
            f.write(data)

    def _write_to_mp3(self, segments_binary_data: bytes) -> str:
        """Записывает бинарные данные в файл и конвертирует его в .mp3"""
        mp3_path = f"{self.save_dir}/{TEMP_AUDIO_FILE_NAME}.mp3"
        self._write_to_file(data=segments_binary_data, path=self.temp_file_path)
        os.system(f'ffmpeg -y -hide_banner -loglevel error -i "{self.temp_file_path}" -vn -acodec copy -y "{mp3_path}"')
        # finput = ffmpeg.input(self.temp_file_path, vn=None)
        # foutput = ffmpeg.output(finput.audio, filename=mp3_path)
        # foutput.run_async()
        os.remove(self.temp_file_path)
        return mp3_path
