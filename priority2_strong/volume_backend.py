"""Version-tolerant pycaw wrapper. pycaw's internal API has changed across releases;
this tries the two call shapes seen in the wild and gives one clear error if neither works."""
from core.logger import get_logger

log = get_logger()


def _get_endpoint_volume():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    speakers = AudioUtilities.GetSpeakers()

    try:
        iface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(iface, POINTER(IAudioEndpointVolume))
    except AttributeError:
        pass

    try:
        return speakers.EndpointVolume
    except AttributeError:
        pass

    try:
        return AudioUtilities.GetSpeakers().Activate()
    except Exception as e:
        raise RuntimeError(
            "This pycaw version's API doesn't match either call shape this project knows. "
            f"Run 'pip show pycaw' and 'pip install pycaw==20240210' to pin a known-good version. ({e})"
        )


def get_volume_scalar():
    return _get_endpoint_volume().GetMasterVolumeLevelScalar()


def set_volume_scalar(value):
    _get_endpoint_volume().SetMasterVolumeLevelScalar(max(0.0, min(1.0, value)), None)


def set_mute(muted):
    _get_endpoint_volume().SetMute(1 if muted else 0, None)
