from io import BytesIO
import eyed3

def get_info(path: str) -> dict:
    track = eyed3.load(path)
    attrs = {'thumb': None, 'duration': None, 'genre': None, 'title': None, 'performer': None}
    for k in list(attrs.keys()):
        try:
            if k == 'thumb':
                attrs[k] = BytesIO(track.tag.images[0].image_data)
            elif k == 'duration':
                attrs[k] = round(track.info.time_secs)
            elif k == 'genre':
                attrs[k] = track.tag.genre.name
            elif k == 'title':
                attrs[k] = track.tag.title
            elif k == 'performer':
                attrs[k] = track.tag.artist
        except (AttributeError, IndexError):
            continue
    return attrs

def update_from_vk(vk_attrs: dict, attrs: dict):
    for k in list(attrs.keys()):
        if not attrs[k]:
            if k == 'title':
                attrs[k] = vk_attrs['title']
            if k == 'performer':
                attrs[k] = vk_attrs['artist']
    return attrs
