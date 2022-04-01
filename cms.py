import sys
import numpy
from PIL import Image, ImageCms

HAS_GI = False

if sys.platform == 'win32':
    import win32gui  # type: ignore
else:
    # https://github.com/bvirxx/bLUe_PYSIDE/blob/486febf9a7cc0236fa6f6ef4a05864decfbc0375/bLUeTop/colorManagement.py
    try:
        from gi.repository import GLib, Gio, Colord

        HAS_GI = True
    except ImportError:
        pass


def get_display_profile(instance, screen):
    screen_name = screen.name()
    if sys.platform == 'win32':
        dc = win32gui.CreateDC(screen_name, None, None)
        icc_path = ImageCms.core.get_display_profile_win32(dc, 1)
        return icc_path
    elif HAS_GI:
        # not yet tested
        try:
            GIO_CANCELLABLE = Gio.Cancellable.new()
            client = Colord.Client.new()
            client.connect_sync(GIO_CANCELLABLE)
            device = client.find_device_sync('xrandr-' + screen_name,
                                             GIO_CANCELLABLE)
            device.connect_sync(GIO_CANCELLABLE)
            default_profile = device.get_default_profile()
            default_profile.connect_sync(GIO_CANCELLABLE)
            return default_profile.get_filename()
        except (NameError, ImportError, GLib.GError):
            pass

    return None


def generate_3dlut(res, out_profile_path):
    if out_profile_path is None:
        res = 2

    lut = Image.new('RGB', (res**3, 1))
    lut_data = lut.load()

    for i in range(res**3):
        r = (i // (res**2)) % res
        g = (i // res) % res
        b = i % res

        lut_data[i, 0] = (
          round(r / (res - 1) * 255),
          round(g / (res - 1) * 255),
          round(b / (res - 1) * 255),
        )

    if out_profile_path is not None:
        proof_profile = ImageCms.createProfile('sRGB')
        ImageCms.profileToProfile(lut,
                                  proof_profile,
                                  out_profile_path,
                                  3,
                                  'RGB',
                                  inPlace=True)

    return (res, numpy.array(lut))


def load_3dluts(instance, res):
    screens = instance.screens()
    iccs = [get_display_profile(instance, screen) for screen in screens]
    return [generate_3dlut(res, icc) for icc in iccs]
