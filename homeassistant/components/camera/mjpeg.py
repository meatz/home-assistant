"""
Support for IP Cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.mjpeg/
"""
import logging
from contextlib import closing

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from homeassistant.components.camera import DOMAIN, Camera
from homeassistant.helpers import validate_config

CONTENT_TYPE_HEADER = 'Content-Type'

_LOGGER = logging.getLogger(__name__)

BASIC_AUTHENTICATION = 'basic'
DIGEST_AUTHENTICATION = 'digest'


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup a MJPEG IP Camera."""
    if not validate_config({DOMAIN: config}, {DOMAIN: ['mjpeg_url']},
                           _LOGGER):
        return None

    add_devices_callback([MjpegCamera(config)])


# pylint: disable=too-many-instance-attributes
class MjpegCamera(Camera):
    """An implementation of an IP camera that is reachable over a URL."""

    def __init__(self, device_info):
        """Initialize a MJPEG camera."""
        super().__init__()
        self._name = device_info.get('name', 'Mjpeg Camera')
        self._authentication = device_info.get('authentication',
                                               BASIC_AUTHENTICATION)
        self._username = device_info.get('username')
        self._password = device_info.get('password')
        self._mjpeg_url = device_info['mjpeg_url']

    def camera_stream(self):
        """Return a MJPEG stream image response directly from the camera."""
        if self._username and self._password:
            if self._authentication == DIGEST_AUTHENTICATION:
                auth = HTTPDigestAuth(self._username, self._password)
            else:
                auth = HTTPBasicAuth(self._username, self._password)
            return requests.get(self._mjpeg_url,
                                auth=auth,
                                stream=True, timeout=10)
        else:
            return requests.get(self._mjpeg_url, stream=True, timeout=10)

    def camera_image(self):
        """Return a still image response from the camera."""
        def process_response(response):
            """Take in a response object, return the jpg from it."""
            data = b''
            for chunk in response.iter_content(1024):
                data += chunk
                jpg_start = data.find(b'\xff\xd8')
                jpg_end = data.find(b'\xff\xd9')
                if jpg_start != -1 and jpg_end != -1:
                    jpg = data[jpg_start:jpg_end + 2]
                    return jpg

        with closing(self.camera_stream()) as response:
            return process_response(response)

    def mjpeg_stream(self, response):
        """Generate an HTTP MJPEG stream from the camera."""
        stream = self.camera_stream()
        return response(
            stream.iter_content(chunk_size=1024),
            mimetype=stream.headers[CONTENT_TYPE_HEADER],
            direct_passthrough=True
        )

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name
