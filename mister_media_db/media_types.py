"""ScreenScraper media type enum. Values match API 'type' strings directly."""

from enum import StrEnum


class MediaType(StrEnum):
    # sstitle          = Capture d'écran Titre         / Title Screen Screenshot
    SSTITLE = "sstitle"
    # ss               = Capture d'écran               / In-Game Screenshot
    SS = "ss"
    # fanart           = Fan Art                        / Fan Art Background
    FANART = "fanart"
    # video            = Vidéo                          / Gameplay Video
    VIDEO = "video"
    # video-normalized = Vidéo normalisée               / Normalized Video
    VIDEO_NORMALIZED = "video-normalized"
    # marquee          = Marquee                        / Arcade Marquee / Banner
    MARQUEE = "marquee"
    # screenmarquee    = Screen Marquee                 / Arcade Marquee / for leds?
    SCREENMARQUEE = "screenmarquee"
    # screenmarqueesmall = Petit Marquee                / Small Marquee
    SCREENMARQUEESMALL = "screenmarqueesmall"
    # manuel           = Manuel                         / Game Manual (PDF)
    MANUEL = "manuel"
    # steamgrid        = Steam Grid                     / Steam Grid Image
    STEAMGRID = "steamgrid"
    # wheel            = Wheel                          / Wheel / Logo Art
    WHEEL = "wheel"
    # wheel-carbon     = Wheel Carbone                  / Carbon Style Wheel Logo
    WHEEL_CARBON = "wheel-carbon"
    # wheel-steel      = Wheel Acier                    / Steel Style Wheel Logo
    WHEEL_STEEL = "wheel-steel"
    # box-2D           = Boîte 2D                       / 2D Box Front Cover
    BOX_2D = "box-2D"
    # box-2D-side      = Boîte 2D Côté                  / 2D Box Side
    BOX_2D_SIDE = "box-2D-side"
    # box-2D-back      = Boîte 2D Dos                   / 2D Box Back
    BOX_2D_BACK = "box-2D-back"
    # box-texture      = Texture Boîte                  / Box Texture Wrap
    BOX_TEXTURE = "box-texture"
    # box-3D           = Boîte 3D                       / 3D Rendered Box
    BOX_3D = "box-3D"
    # support-texture  = Texture Support                / Cartridge/Disc Texture
    SUPPORT_TEXTURE = "support-texture"
    # support-2D       = Support 2D                     / 2D Cartridge/Disc Image
    SUPPORT_2D = "support-2D"
    # bezel-16-9       = Bezel 16/9                     / Widescreen Bezel
    BEZEL_16_9 = "bezel-16-9"
    # mixrbv1          = Mix Recalbox v1                / Recalbox Composite Mix v1
    MIXRBV1 = "mixrbv1"
    # mixrbv2          = Mix Recalbox v2                / Recalbox Composite Mix v2
    MIXRBV2 = "mixrbv2"
    # pictoliste       = Pictogramme Liste              / List Pictogram / Icon
    PICTOLISTE = "pictoliste"
    # pictomonochrome  = Pictogramme Monochrome         / Monochrome Pictogram
    PICTOMONOCHROME = "pictomonochrome"
    # pictocouleur     = Pictogramme Couleur            / Color Pictogram
    PICTOCOULEUR = "pictocouleur"
    # flyer            = Flyer                          / Info flyer
    FLYER = "flyer"


# Maps raw API 'type' string → MediaType enum
MEDIA_TYPE_MAP: dict[str, MediaType] = {
    "sstitle": MediaType.SSTITLE,
    "ss": MediaType.SS,
    "fanart": MediaType.FANART,
    "video": MediaType.VIDEO,
    "video-normalized": MediaType.VIDEO_NORMALIZED,
    "screenmarquee": MediaType.SCREENMARQUEE,
    "screenmarqueesmall": MediaType.SCREENMARQUEESMALL,
    "manuel": MediaType.MANUEL,
    "steamgrid": MediaType.STEAMGRID,
    "wheel": MediaType.WHEEL,
    "wheel-carbon": MediaType.WHEEL_CARBON,
    "wheel-steel": MediaType.WHEEL_STEEL,
    "box-2D": MediaType.BOX_2D,
    "box-2D-side": MediaType.BOX_2D_SIDE,
    "box-2D-back": MediaType.BOX_2D_BACK,
    "box-texture": MediaType.BOX_TEXTURE,
    "box-3D": MediaType.BOX_3D,
    "support-texture": MediaType.SUPPORT_TEXTURE,
    "support-2D": MediaType.SUPPORT_2D,
    "bezel-16-9": MediaType.BEZEL_16_9,
    "mixrbv1": MediaType.MIXRBV1,
    "mixrbv2": MediaType.MIXRBV2,
    "pictoliste": MediaType.PICTOLISTE,
    "pictomonochrome": MediaType.PICTOMONOCHROME,
    "pictocouleur": MediaType.PICTOCOULEUR,
}
