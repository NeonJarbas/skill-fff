import random
from os.path import join, dirname

import requests
from json_database import JsonStorageXDG

from ovos_utils.ocp import MediaType, PlaybackType
from ovos_workshop.decorators.ocp import ocp_search, ocp_featured_media
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill


class FullFreeFilmsSkill(OVOSCommonPlaybackSkill):
    def __init__(self, *args, **kwargs):
        self.supported_media = [MediaType.MOVIE]
        self.skill_icon = self.default_bg = join(dirname(__file__), "ui", "fff_logo.png")
        self.archive = JsonStorageXDG("FullFreeFilms", subfolder="OCP")
        self.media_type_exceptions = {}
        super().__init__(*args, **kwargs)

    def initialize(self):
        self._sync_db()
        self.load_ocp_keywords()

    def load_ocp_keywords(self):
        genre = ["horror", "scifi", "sci-fi", "action", "fantasy"]
        title = []
        docus = []

        for url, data in self.archive.items():
            t = data["title"].split("|")[0].split("(")[0].strip().strip("¿?.!").rstrip("¿")
            if "documentary" in data["title"].lower():
                docus.append(t)
                if ":" in t:
                    t1, t2 = t.split(":", 1)
                    docus.append(t1.strip())
                    docus.append(t2.strip())
                # signal this entry as DOCUMENTARY media type
                # in case it gets selected later
                self.media_type_exceptions[data["url"]] = MediaType.DOCUMENTARY
            else:
                title.append(t)
                if ":" in t:
                    t1, t2 = t.split(":", 1)
                    title.append(t1.strip())
                    title.append(t2.strip())

        self.register_ocp_keyword(MediaType.MOVIE,
                                  "movie_name", title)
        self.register_ocp_keyword(MediaType.DOCUMENTARY,
                                  "documentary_name", docus)
        self.register_ocp_keyword(MediaType.MOVIE,
                                  "film_genre", genre)
        self.register_ocp_keyword(MediaType.MOVIE,
                                  "movie_streaming_provider",
                                  ["Full Free Films",
                                   "FFF",
                                   "FullFreeFilms"])

    def _sync_db(self):
        bootstrap = "https://github.com/JarbasSkills/skill-fff/raw/dev/bootstrap.json"
        data = requests.get(bootstrap).json()
        self.archive.merge(data)
        self.schedule_event(self._sync_db, random.randint(3600, 24 * 3600))

    def get_playlist(self, score=50, num_entries=250):
        pl = self.featured_media()[:num_entries]
        return {
            "match_confidence": score,
            "media_type": MediaType.MOVIE,
            "playlist": pl,
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "image": self.skill_icon,
            "bg_image": self.default_bg,
            "title": "Full Free Films (Movie Playlist)",
            "author": "Full Free Films"
        }

    @ocp_search()
    def search_db(self, phrase, media_type):
        base_score = 15 if media_type == MediaType.MOVIE else 0
        entities = self.ocp_voc_match(phrase)

        skill = "movie_streaming_provider" in entities  # skill matched

        base_score += 30 * len(entities)
        title = entities.get("movie_name")
        dtitle = entities.get("documentary_name")

        if media_type == MediaType.DOCUMENTARY:
            candidates = [video for video in self.archive.values()
                          if self.media_type_exceptions.get(video["url"], MediaType.MOVIE) ==
                          MediaType.DOCUMENTARY]

        else:
            candidates = [video for video in self.archive.values()
                          if video["url"] not in self.media_type_exceptions]

        if title:
            base_score += 30
            candidates = [video for video in candidates
                          if title.lower() in video["title"].lower()]
            for video in candidates:
                yield {
                    "title": video["title"],
                    "author": video["author"],
                    "match_confidence": min(100, base_score),
                    "media_type": MediaType.MOVIE,
                    "uri": "youtube//" + video["url"],
                    "playback": PlaybackType.VIDEO,
                    "skill_icon": self.skill_icon,
                    "skill_id": self.skill_id,
                    "image": video["thumbnail"],
                    "bg_image": video["thumbnail"]
                }

        if dtitle:
            base_score += 20
            candidates = [video for video in candidates
                          if dtitle.lower() in video["title"].lower()]
            for video in candidates:
                yield {
                    "title": video["title"],
                    "author": video["author"],
                    "match_confidence": min(100, base_score),
                    "media_type": MediaType.DOCUMENTARY,
                    "uri": "youtube//" + video["url"],
                    "playback": PlaybackType.VIDEO,
                    "skill_icon": self.skill_icon,
                    "skill_id": self.skill_id,
                    "image": video["thumbnail"],
                    "bg_image": video["thumbnail"]
                }

        if skill:
            yield self.get_playlist()

    @ocp_featured_media()
    def featured_media(self):
        return [{
            "title": video["title"],
            "image": video["thumbnail"],
            "match_confidence": 70,
            "media_type": MediaType.MOVIE,
            "uri": "youtube//" + video["url"],
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "bg_image": video["thumbnail"],
            "skill_id": self.skill_id
        } for video in self.archive.values()]


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus

    s = FullFreeFilmsSkill(bus=FakeBus(), skill_id="t.fake")
    for r in s.search_db("play THE BODY TREE", MediaType.MOVIE):
        print(r)
        # {'title': 'THE BODY TREE | Full HORROR Movie | MURDER MYSTERY', 'author': 'FFF Full Free Films', 'match_confidence': 75, 'media_type': <MediaType.MOVIE: 10>, 'uri': 'youtube//https://youtube.com/watch?v=uqJDLazlrPg', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/uqJDLazlrPg/sddefault.jpg', 'bg_image': 'https://i.ytimg.com/vi/uqJDLazlrPg/sddefault.jpg'}

    for r in s.search_db("play ZEITGEIST", MediaType.DOCUMENTARY):
        print(r)
        # {'title': 'ZEITGEIST: MOVING FORWARD | Full Documentary Movie | The Monetary-Market Economics Explained', 'author': 'FFF Full Free Films', 'match_confidence': 50, 'media_type': <MediaType.DOCUMENTARY: 15>, 'uri': 'youtube//https://youtube.com/watch?v=BOQtgMpSEFM', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/BOQtgMpSEFM/sddefault.jpg?v=605a6f05', 'bg_image': 'https://i.ytimg.com/vi/BOQtgMpSEFM/sddefault.jpg?v=605a6f05'}
        # {'title': 'ZEITGEIST THE MOVIE: ADDENDUM | The Economic Corruption Explained | Full Documentary', 'author': 'FFF Full Free Films', 'match_confidence': 50, 'media_type': <MediaType.DOCUMENTARY: 15>, 'uri': 'youtube//https://youtube.com/watch?v=AttPOn1ZOfk', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/AttPOn1ZOfk/sddefault.jpg?v=60662369', 'bg_image': 'https://i.ytimg.com/vi/AttPOn1ZOfk/sddefault.jpg?v=60662369'}
