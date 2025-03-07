from __future__ import unicode_literals
import re
import base64

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    float_or_none,
    ExtractorError,
    unsmuggle_url,
)
from ..compat import compat_urllib_parse


class OoyalaBaseIE(InfoExtractor):

    def _extract(self, content_tree_url, video_id, domain='example.org'):
        content_tree = self._download_json(content_tree_url, video_id)['content_tree']
        metadata = content_tree[list(content_tree)[0]]
        embed_code = metadata['embed_code']
        pcode = metadata.get('asset_pcode') or embed_code
        video_info = {
            'id': embed_code,
            'title': metadata['title'],
            'description': metadata.get('description'),
            'thumbnail': metadata.get('thumbnail_image') or metadata.get('promo_image'),
            'duration': int_or_none(metadata.get('duration')),
        }

        formats = []
        for supported_format in ('mp4', 'm3u8', 'hds', 'rtmp'):
            auth_data = self._download_json(
                'http://player.ooyala.com/sas/player_api/v1/authorization/embed_code/%s/%s?' % (pcode, embed_code) + compat_urllib_parse.urlencode({'domain': domain, 'supportedFormats': supported_format}),
                video_id, 'Downloading %s JSON' % supported_format)

            cur_auth_data = auth_data['authorization_data'][embed_code]

            if cur_auth_data['authorized']:
                for stream in cur_auth_data['streams']:
                    url = base64.b64decode(stream['url']['data'].encode('ascii')).decode('utf-8')
                    delivery_type = stream['delivery_type']
                    if delivery_type == 'remote_asset':
                        video_info['url'] = url
                        return video_info
                    if delivery_type == 'hls':
                        formats.extend(self._extract_m3u8_formats(url, embed_code, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
                    elif delivery_type == 'hds':
                        formats.extend(self._extract_f4m_formats(url, embed_code, -1, 'hds', fatal=False))
                    else:
                        formats.append({
                            'url': url,
                            'ext': stream.get('delivery_type'),
                            'vcodec': stream.get('video_codec'),
                            'format_id': '%s-%s-%sp' % (stream.get('profile'), delivery_type, stream.get('height')),
                            'width': int_or_none(stream.get('width')),
                            'height': int_or_none(stream.get('height')),
                            'abr': int_or_none(stream.get('audio_bitrate')),
                            'vbr': int_or_none(stream.get('video_bitrate')),
                            'fps': float_or_none(stream.get('framerate')),
                        })
            else:
                raise ExtractorError('%s said: %s' % (self.IE_NAME, cur_auth_data['message']), expected=True)
        self._sort_formats(formats)

        video_info['formats'] = formats
        return video_info


class OoyalaIE(OoyalaBaseIE):
    _VALID_URL = r'(?:ooyala:|https?://.+?\.ooyala\.com/.*?(?:embedCode|ec)=)(?P<id>.+?)(&|$)'

    _TESTS = [
        {
            # From http://it.slashdot.org/story/13/04/25/178216/recovering-data-from-broken-hard-drives-and-ssds-video
            'url': 'http://player.ooyala.com/player.js?embedCode=pxczE2YjpfHfn1f3M-ykG_AmJRRn0PD8',
            'info_dict': {
                'id': 'pxczE2YjpfHfn1f3M-ykG_AmJRRn0PD8',
                'ext': 'mp4',
                'title': 'Explaining Data Recovery from Hard Drives and SSDs',
                'description': 'How badly damaged does a drive have to be to defeat Russell and his crew? Apparently, smashed to bits.',
                'duration': 853386,
            },
        }, {
            # Only available for ipad
            'url': 'http://player.ooyala.com/player.js?embedCode=x1b3lqZDq9y_7kMyC2Op5qo-p077tXD0',
            'info_dict': {
                'id': 'x1b3lqZDq9y_7kMyC2Op5qo-p077tXD0',
                'ext': 'mp4',
                'title': 'Simulation Overview - Levels of Simulation',
                'duration': 194948,
            },
        },
        {
            # Information available only through SAS api
            # From http://community.plm.automation.siemens.com/t5/News-NX-Manufacturing/Tool-Path-Divide/ba-p/4187
            'url': 'http://player.ooyala.com/player.js?embedCode=FiOG81ZTrvckcchQxmalf4aQj590qTEx',
            'md5': 'a84001441b35ea492bc03736e59e7935',
            'info_dict': {
                'id': 'FiOG81ZTrvckcchQxmalf4aQj590qTEx',
                'ext': 'mp4',
                'title': 'Divide Tool Path.mp4',
                'duration': 204405,
            }
        }
    ]

    @staticmethod
    def _url_for_embed_code(embed_code):
        return 'http://player.ooyala.com/player.js?embedCode=%s' % embed_code

    @classmethod
    def _build_url_result(cls, embed_code):
        return cls.url_result(cls._url_for_embed_code(embed_code),
                              ie=cls.ie_key())

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        embed_code = self._match_id(url)
        domain = smuggled_data.get('domain')
        content_tree_url = 'http://player.ooyala.com/player_api/v1/content_tree/embed_code/%s/%s' % (embed_code, embed_code)
        return self._extract(content_tree_url, embed_code, domain)


class OoyalaExternalIE(OoyalaBaseIE):
    _VALID_URL = r'''(?x)
                    (?:
                        ooyalaexternal:|
                        https?://.+?\.ooyala\.com/.*?\bexternalId=
                    )
                    (?P<partner_id>[^:]+)
                    :
                    (?P<id>.+)
                    (?:
                        :|
                        .*?&pcode=
                    )
                    (?P<pcode>.+?)
                    (?:&|$)
                    '''

    _TEST = {
        'url': 'https://player.ooyala.com/player.js?externalId=espn:10365079&pcode=1kNG061cgaoolOncv54OAO1ceO-I&adSetCode=91cDU6NuXTGKz3OdjOxFdAgJVtQcKJnI&callback=handleEvents&hasModuleParams=1&height=968&playerBrandingId=7af3bd04449c444c964f347f11873075&targetReplaceId=videoPlayer&width=1656&wmode=opaque&allowScriptAccess=always',
        'info_dict': {
            'id': 'FkYWtmazr6Ed8xmvILvKLWjd4QvYZpzG',
            'ext': 'mp4',
            'title': 'dm_140128_30for30Shorts___JudgingJewellv2',
            'duration': 1302000,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        partner_id, video_id, pcode = re.match(self._VALID_URL, url).groups()
        content_tree_url = 'http://player.ooyala.com/player_api/v1/content_tree/external_id/%s/%s:%s' % (pcode, partner_id, video_id)
        return self._extract(content_tree_url, video_id)
