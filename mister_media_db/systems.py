"""System definitions for MiSTer Media DB ETL."""

from dataclasses import dataclass, field


@dataclass
class System:
    zaparoo_id: str
    mister_media_dirname: str  # canonical folder (first item of mister_folders)
    mister_folders: list[str]
    mister_core_name: str
    screenscraper_id: int  # 0 = no known SS match


# ─── OBVIOUS MATCHES ──────────────────────────────────────────────────────────
# Clear 1:1 mapping between MiSTer system and ScreenScraper entry.

SYSTEMS: list[System] = [
    # Consoles
    System(
        zaparoo_id="3DO",
        mister_media_dirname="3DO",
        mister_folders=["3DO"],
        mister_core_name="3DO",
        screenscraper_id=29,
    ),
    System(
        zaparoo_id="AdventureVision",
        mister_media_dirname="AVision",
        mister_folders=["AVision"],
        mister_core_name="AdventureVision",
        screenscraper_id=78,
    ),
    System(
        zaparoo_id="AmigaCD32",
        mister_media_dirname="AmigaCD32",
        mister_folders=["AmigaCD32"],
        mister_core_name="AmigaCD32",
        screenscraper_id=130,
    ),
    System(
        zaparoo_id="Arcadia",
        mister_media_dirname="Arcadia",
        mister_folders=["Arcadia"],
        mister_core_name="Arcadia",
        screenscraper_id=94,
    ),
    System(
        zaparoo_id="Astrocade",
        mister_media_dirname="Astrocade",
        mister_folders=["Astrocade"],
        mister_core_name="Astrocade",
        screenscraper_id=44,
    ),
    System(
        zaparoo_id="Atari2600",
        mister_media_dirname="ATARI7800",
        mister_folders=["ATARI7800", "Atari2600"],
        mister_core_name="Atari2600",
        screenscraper_id=26,
    ),
    System(
        zaparoo_id="Atari5200",
        mister_media_dirname="ATARI5200",
        mister_folders=["ATARI5200"],
        mister_core_name="Atari5200",
        screenscraper_id=40,
    ),
    System(
        zaparoo_id="Atari7800",
        mister_media_dirname="ATARI7800",
        mister_folders=["ATARI7800"],
        mister_core_name="Atari7800",
        screenscraper_id=41,
    ),
    System(
        zaparoo_id="AtariLynx",
        mister_media_dirname="AtariLynx",
        mister_folders=["AtariLynx"],
        mister_core_name="AtariLynx",
        screenscraper_id=28,
    ),
    System(
        zaparoo_id="CasioPV1000",
        mister_media_dirname="Casio_PV-1000",
        mister_folders=["Casio_PV-1000"],
        mister_core_name="CasioPV1000",
        screenscraper_id=74,
    ),
    System(
        zaparoo_id="CDI",
        mister_media_dirname="CD-i",
        mister_folders=["CD-i"],
        mister_core_name="CDI",
        screenscraper_id=133,
    ),
    System(
        zaparoo_id="ChannelF",
        mister_media_dirname="ChannelF",
        mister_folders=["ChannelF"],
        mister_core_name="ChannelF",
        screenscraper_id=80,
    ),
    System(
        zaparoo_id="ColecoVision",
        mister_media_dirname="Coleco",
        mister_folders=["Coleco"],
        mister_core_name="ColecoVision",
        screenscraper_id=48,
    ),
    System(
        zaparoo_id="CreatiVision",
        mister_media_dirname="CreatiVision",
        mister_folders=["CreatiVision"],
        mister_core_name="CreatiVision",
        screenscraper_id=241,
    ),
    System(
        zaparoo_id="FDS",
        mister_media_dirname="NES",
        mister_folders=["NES", "FDS"],
        mister_core_name="NES",
        screenscraper_id=106,
    ),
    System(
        zaparoo_id="Gamate",
        mister_media_dirname="Gamate",
        mister_folders=["Gamate"],
        mister_core_name="Gamate",
        screenscraper_id=266,
    ),
    System(
        zaparoo_id="Gameboy",
        mister_media_dirname="GAMEBOY",
        mister_folders=["GAMEBOY"],
        mister_core_name="Gameboy",
        screenscraper_id=9,
    ),
    System(
        zaparoo_id="GameboyColor",
        mister_media_dirname="GAMEBOY",
        mister_folders=["GAMEBOY", "GBC"],
        mister_core_name="Gameboy",
        screenscraper_id=10,
    ),
    System(
        zaparoo_id="GameGear",
        mister_media_dirname="SMS",
        mister_folders=["SMS", "GameGear"],
        mister_core_name="GameGear",
        screenscraper_id=21,
    ),
    System(
        zaparoo_id="GameNWatch",
        mister_media_dirname="GameNWatch",
        mister_folders=["GameNWatch", "Game and Watch"],
        mister_core_name="GameNWatch",
        screenscraper_id=52,
    ),
    System(
        zaparoo_id="GBA",
        mister_media_dirname="GBA",
        mister_folders=["GBA"],
        mister_core_name="GBA",
        screenscraper_id=12,
    ),
    System(
        zaparoo_id="Genesis",
        mister_media_dirname="MegaDrive",
        mister_folders=["MegaDrive", "Genesis"],
        mister_core_name="Genesis",
        screenscraper_id=1,
    ),
    System(
        zaparoo_id="Intellivision",
        mister_media_dirname="Intellivision",
        mister_folders=["Intellivision"],
        mister_core_name="Intellivision",
        screenscraper_id=115,
    ),
    System(
        zaparoo_id="Jaguar",
        mister_media_dirname="Jaguar",
        mister_folders=["Jaguar"],
        mister_core_name="Jaguar",
        screenscraper_id=27,
    ),
    System(
        zaparoo_id="JaguarCD",
        mister_media_dirname="Jaguar",
        mister_folders=["Jaguar"],
        mister_core_name="JaguarCD",
        screenscraper_id=171,
    ),
    System(
        zaparoo_id="MasterSystem",
        mister_media_dirname="SMS",
        mister_folders=["SMS"],
        mister_core_name="SMS",
        screenscraper_id=2,
    ),
    System(
        zaparoo_id="MegaCD",
        mister_media_dirname="MegaCD",
        mister_folders=["MegaCD"],
        mister_core_name="MegaCD",
        screenscraper_id=20,
    ),
    System(
        zaparoo_id="MegaDuck",
        mister_media_dirname="MegaDuck",
        mister_folders=["GAMEBOY", "MegaDuck"],
        mister_core_name="MegaDuck",
        screenscraper_id=90,
    ),
    System(
        zaparoo_id="NeoGeoCD",
        mister_media_dirname="NeoGeo-CD",
        mister_folders=["NeoGeo-CD", "NEOGEO"],
        mister_core_name="NeoGeoCD",
        screenscraper_id=70,
    ),
    System(
        zaparoo_id="NeoGeoPocket",
        mister_media_dirname="NGP",
        mister_folders=["NGP"],
        mister_core_name="NeoGeoPocket",
        screenscraper_id=25,
    ),
    System(
        zaparoo_id="NeoGeoPocketColor",
        mister_media_dirname="NGPC",
        mister_folders=["NGPC"],
        mister_core_name="NeoGeoPocketColor",
        screenscraper_id=82,
    ),
    System(
        zaparoo_id="NES",
        mister_media_dirname="NES",
        mister_folders=["NES"],
        mister_core_name="NES",
        screenscraper_id=3,
    ),
    System(
        zaparoo_id="Nintendo64",
        mister_media_dirname="N64",
        mister_folders=["N64"],
        mister_core_name="N64",
        screenscraper_id=14,
    ),
    System(
        zaparoo_id="Odyssey2",
        mister_media_dirname="ODYSSEY2",
        mister_folders=["ODYSSEY2"],
        mister_core_name="Odyssey2",
        screenscraper_id=104,
    ),
    System(
        zaparoo_id="PocketChallengeV2",
        mister_media_dirname="WonderSwan",
        mister_folders=["WonderSwan", "PocketChallengeV2"],
        mister_core_name="PocketChallengeV2",
        screenscraper_id=237,
    ),
    System(
        zaparoo_id="PokemonMini",
        mister_media_dirname="PokemonMini",
        mister_folders=["PokemonMini"],
        mister_core_name="PokemonMini",
        screenscraper_id=211,
    ),
    System(
        zaparoo_id="PSX",
        mister_media_dirname="PSX",
        mister_folders=["PSX"],
        mister_core_name="PSX",
        screenscraper_id=57,
    ),
    System(
        zaparoo_id="Sega32X",
        mister_media_dirname="S32X",
        mister_folders=["S32X"],
        mister_core_name="S32X",
        screenscraper_id=19,
    ),
    System(
        zaparoo_id="SG1000",
        mister_media_dirname="SG1000",
        mister_folders=["SG1000", "Coleco", "SMS"],
        mister_core_name="SG1000",
        screenscraper_id=109,
    ),
    System(
        zaparoo_id="SuperGameboy",
        mister_media_dirname="SGB",
        mister_folders=["SGB"],
        mister_core_name="SGB",
        screenscraper_id=127,
    ),
    System(
        zaparoo_id="SuperVision",
        mister_media_dirname="SuperVision",
        mister_folders=["SuperVision"],
        mister_core_name="SuperVision",
        screenscraper_id=207,
    ),
    System(
        zaparoo_id="Saturn",
        mister_media_dirname="Saturn",
        mister_folders=["Saturn"],
        mister_core_name="Saturn",
        screenscraper_id=22,
    ),
    System(
        zaparoo_id="SNES",
        mister_media_dirname="SNES",
        mister_folders=["SNES"],
        mister_core_name="SNES",
        screenscraper_id=4,
    ),
    System(
        zaparoo_id="SuperGrafx",
        mister_media_dirname="TGFX16",
        mister_folders=["TGFX16"],
        mister_core_name="SuperGrafx",
        screenscraper_id=105,
    ),
    System(
        zaparoo_id="TurboGrafx16",
        mister_media_dirname="TGFX16",
        mister_folders=["TGFX16"],
        mister_core_name="TurboGrafx16",
        screenscraper_id=31,
    ),
    System(
        zaparoo_id="TurboGrafx16CD",
        mister_media_dirname="TGFX16-CD",
        mister_folders=["TGFX16-CD"],
        mister_core_name="TurboGrafx16CD",
        screenscraper_id=114,
    ),
    System(
        zaparoo_id="VC4000",
        mister_media_dirname="VC4000",
        mister_folders=["VC4000"],
        mister_core_name="VC4000",
        screenscraper_id=281,
    ),
    System(
        zaparoo_id="Vectrex",
        mister_media_dirname="VECTREX",
        mister_folders=["VECTREX"],
        mister_core_name="Vectrex",
        screenscraper_id=102,
    ),
    System(
        zaparoo_id="VirtualBoy",
        mister_media_dirname="VirtualBoy",
        mister_folders=["VirtualBoy"],
        mister_core_name="VirtualBoy",
        screenscraper_id=11,
    ),
    System(
        zaparoo_id="WonderSwan",
        mister_media_dirname="WonderSwan",
        mister_folders=["WonderSwan"],
        mister_core_name="WonderSwan",
        screenscraper_id=45,
    ),
    System(
        zaparoo_id="WonderSwanColor",
        mister_media_dirname="WonderSwan",
        mister_folders=["WonderSwan", "WonderSwanColor"],
        mister_core_name="WonderSwanColor",
        screenscraper_id=46,
    ),
    # Computers
    System(
        zaparoo_id="AcornAtom",
        mister_media_dirname="AcornAtom",
        mister_folders=["AcornAtom"],
        mister_core_name="AcornAtom",
        screenscraper_id=36,
    ),
    System(
        zaparoo_id="AcornElectron",
        mister_media_dirname="AcornElectron",
        mister_folders=["AcornElectron"],
        mister_core_name="AcornElectron",
        screenscraper_id=85,
    ),
    System(
        zaparoo_id="Amstrad",
        mister_media_dirname="Amstrad",
        mister_folders=["Amstrad"],
        mister_core_name="Amstrad",
        screenscraper_id=65,
    ),
    System(
        zaparoo_id="AppleII",
        mister_media_dirname="Apple-II",
        mister_folders=["Apple-II"],
        mister_core_name="AppleII",
        screenscraper_id=86,
    ),
    System(
        zaparoo_id="Atari800",
        mister_media_dirname="ATARI800",
        mister_folders=["ATARI800"],
        mister_core_name="Atari800",
        screenscraper_id=43,
    ),
    System(
        zaparoo_id="BBCMicro",
        mister_media_dirname="BBCMicro",
        mister_folders=["BBCMicro"],
        mister_core_name="BBCMicro",
        screenscraper_id=37,
    ),
    System(
        zaparoo_id="BK0011M",
        mister_media_dirname="BK0011M",
        mister_folders=["BK0011M"],
        mister_core_name="BK0011M",
        screenscraper_id=93,
    ),
    System(
        zaparoo_id="C16",
        mister_media_dirname="C16",
        mister_folders=["C16"],
        mister_core_name="C16",
        screenscraper_id=99,
    ),
    System(
        zaparoo_id="C64",
        mister_media_dirname="C64",
        mister_folders=["C64"],
        mister_core_name="C64",
        screenscraper_id=66,
    ),
    System(
        zaparoo_id="CoCo2",
        mister_media_dirname="CoCo2",
        mister_folders=["CoCo2"],
        mister_core_name="CoCo2",
        screenscraper_id=144,
    ),
    System(
        zaparoo_id="DOS",
        mister_media_dirname="AO486",
        mister_folders=["AO486", "_DOS Games"],
        mister_core_name="ao486",
        screenscraper_id=135,
    ),
    System(
        zaparoo_id="Jupiter",
        mister_media_dirname="Jupiter",
        mister_folders=["Jupiter"],
        mister_core_name="Jupiter",
        screenscraper_id=126,
    ),
    System(
        zaparoo_id="Lynx48",
        mister_media_dirname="Lynx48",
        mister_folders=["Lynx48"],
        mister_core_name="Lynx48",
        screenscraper_id=88,
    ),
    System(
        zaparoo_id="MSX",
        mister_media_dirname="MSX",
        mister_folders=["MSX"],
        mister_core_name="MSX",
        screenscraper_id=113,
    ),
    System(
        zaparoo_id="Oric",
        mister_media_dirname="Oric",
        mister_folders=["Oric"],
        mister_core_name="Oric",
        screenscraper_id=131,
    ),
    System(
        zaparoo_id="PET2001",
        mister_media_dirname="PET2001",
        mister_folders=["PET2001"],
        mister_core_name="PET2001",
        screenscraper_id=240,
    ),
    System(
        zaparoo_id="SAMCoupe",
        mister_media_dirname="SAMCOUPE",
        mister_folders=["SAMCOUPE"],
        mister_core_name="SAMCoupe",
        screenscraper_id=213,
    ),
    System(
        zaparoo_id="SVI328",
        mister_media_dirname="SVI328",
        mister_folders=["SVI328"],
        mister_core_name="SVI328",
        screenscraper_id=218,
    ),
    System(
        zaparoo_id="TI994A",
        mister_media_dirname="TI-99_4A",
        mister_folders=["TI-99_4A"],
        mister_core_name="TI994A",
        screenscraper_id=205,
    ),
    System(
        zaparoo_id="VIC20",
        mister_media_dirname="VIC20",
        mister_folders=["VIC20"],
        mister_core_name="VIC20",
        screenscraper_id=73,
    ),
    System(
        zaparoo_id="X68000",
        mister_media_dirname="X68000",
        mister_folders=["X68000"],
        mister_core_name="X68000",
        screenscraper_id=79,
    ),
    System(
        zaparoo_id="ZX81",
        mister_media_dirname="ZX81",
        mister_folders=["ZX81"],
        mister_core_name="ZX81",
        screenscraper_id=77,
    ),
    System(
        zaparoo_id="ZXSpectrum",
        mister_media_dirname="Spectrum",
        mister_folders=["Spectrum"],
        mister_core_name="ZXSpectrum",
        screenscraper_id=76,
    ),
    # Other
    # Arcade must be run custom for MRA matching from arcade.py
    # System(
    #     zaparoo_id="Arcade",
    #     mister_media_dirname="_Arcade",
    #     mister_folders=["_Arcade"],
    #     mister_core_name="Arcade",
    #     screenscraper_id=75,
    # ),
    System(
        zaparoo_id="Arduboy",
        mister_media_dirname="Arduboy",
        mister_folders=["Arduboy"],
        mister_core_name="Arduboy",
        screenscraper_id=263,
    ),
    System(
        zaparoo_id="ScummVM",
        mister_media_dirname="ScummVM",
        mister_folders=["ScummVM"],
        mister_core_name="ScummVM",
        screenscraper_id=123,
    ),

    # ─── PROBABLE MATCHES ─────────────────────────────────────────────────────
    # Likely correct SS mapping but less certain; verify before treating as ground truth.

    # Gameboy2P: MiSTer dual-player GB core. SS 9 = same as Gameboy; Gameboy is champion.
    # System(
    #     zaparoo_id="Gameboy2P",
    #     mister_media_dirname="GAMEBOY2P",
    #     mister_folders=["GAMEBOY2P"],
    #     mister_core_name="Gameboy2P",
    #     screenscraper_id=9,  # same as Game Boy
    # ),
    # GBA2P: MiSTer dual-player GBA core. SS 12 = same as GBA; GBA is champion.
    # System(
    #     zaparoo_id="GBA2P",
    #     mister_media_dirname="GBA2P",
    #     mister_folders=["GBA2P"],
    #     mister_core_name="GBA2P",
    #     screenscraper_id=12,  # same as GBA
    # ),
    # AppleI: SS 86 (Apple II) includes Apple I in noms_commun; no dedicated SS entry. SS 86 = same as AppleII; AppleII is champion.
    # System(
    #     zaparoo_id="AppleI",
    #     mister_media_dirname="Apple-I",
    #     mister_folders=["Apple-I"],
    #     mister_core_name="AppleI",
    #     screenscraper_id=86,  # Apple II entry (includes Apple I)
    # ),
    # # MacPlus: SS 146 is general "Mac OS"; no MiSTer-specific Mac Plus SS entry.
    # System(
    #     zaparoo_id="MacPlus",
    #     mister_media_dirname="MACPLUS",
    #     mister_folders=["MACPLUS"],
    #     mister_core_name="MacPlus",
    #     screenscraper_id=146,  # Mac OS (general)
    # ),
    # MSX1: separate MiSTer core (MSX1 folder, .dsk/.rom). SS 113 = same as MSX; MSX is champion.
    # System(
    #     zaparoo_id="MSX1",
    #     mister_media_dirname="MSX1",
    #     mister_folders=["MSX1"],
    #     mister_core_name="MSX1",
    #     screenscraper_id=113,  # same as MSX
    # ),
    # PCXT: IBM PC XT era. SS 135 (PC Dos) = same as DOS; DOS is champion.
    # System(
    #     zaparoo_id="PCXT",
    #     mister_media_dirname="PCXT",
    #     mister_folders=["PCXT"],
    #     mister_core_name="PCXT",
    #     screenscraper_id=135,  # PC Dos
    # ),
    # ZXNext: ZX Spectrum Next, no dedicated SS entry. SS 76 = same as ZXSpectrum; ZXSpectrum is champion.
    # System(
    #     zaparoo_id="ZXNext",
    #     mister_media_dirname="ZXNext",
    #     mister_folders=["ZXNext"],
    #     mister_core_name="ZXNext",
    #     screenscraper_id=76,  # ZX Spectrum
    # ),

    # ─── UNSURE / NO SS MATCH ─────────────────────────────────────────────────
    # No clear ScreenScraper entry found; screenscraper_id=0 until resolved.

    # # AliceMC10: Tandy/Radio Shack MC-10; not in SS system list.
    # System(
    #     zaparoo_id="AliceMC10",
    #     mister_media_dirname="AliceMC10",
    #     mister_folders=["AliceMC10"],
    #     mister_core_name="AliceMC10",
    #     screenscraper_id=0,
    # ),
    # # AmstradPCW: PCW word processor series; distinct from CPC (SS 65), not in SS.
    # System(
    #     zaparoo_id="AmstradPCW",
    #     mister_media_dirname="Amstrad PCW",
    #     mister_folders=["Amstrad PCW"],
    #     mister_core_name="AmstradPCW",
    #     screenscraper_id=0,
    # ),
    # # Apogee: Soviet BK-based home computer; not in SS.
    # System(
    #     zaparoo_id="Apogee",
    #     mister_media_dirname="APOGEE",
    #     mister_folders=["APOGEE"],
    #     mister_core_name="Apogee",
    #     screenscraper_id=0,
    # ),
    # # Aquarius: Mattel Aquarius; not in SS system list.
    # System(
    #     zaparoo_id="Aquarius",
    #     mister_media_dirname="AQUARIUS",
    #     mister_folders=["AQUARIUS"],
    #     mister_core_name="Aquarius",
    #     screenscraper_id=0,
    # ),
    # # CasioPV2000: Casio PV-2000; SS has PV-1000 (74) but not PV-2000.
    # System(
    #     zaparoo_id="CasioPV2000",
    #     mister_media_dirname="Casio_PV-2000",
    #     mister_folders=["Casio_PV-2000"],
    #     mister_core_name="CasioPV2000",
    #     screenscraper_id=0,
    # ),
    # # Chip8: CHIP-8 interpreted language; not in SS.
    # System(
    #     zaparoo_id="Chip8",
    #     mister_media_dirname="Chip8",
    #     mister_folders=["Chip8"],
    #     mister_core_name="Chip8",
    #     screenscraper_id=0,
    # ),
    # # EDSAC: 1940s Cambridge mainframe reproduction; not in SS.
    # System(
    #     zaparoo_id="EDSAC",
    #     mister_media_dirname="EDSAC",
    #     mister_folders=["EDSAC"],
    #     mister_core_name="EDSAC",
    #     screenscraper_id=0,
    # ),
    # # Galaksija: Yugoslav hobbyist computer; not in SS.
    # System(
    #     zaparoo_id="Galaksija",
    #     mister_media_dirname="Galaksija",
    #     mister_folders=["Galaksija"],
    #     mister_core_name="Galaksija",
    #     screenscraper_id=0,
    # ),
    # # Groovy: GroovyMAME integration core; not in SS.
    # System(
    #     zaparoo_id="Groovy",
    #     mister_media_dirname="Groovy",
    #     mister_folders=["Groovy"],
    #     mister_core_name="Groovy",
    #     screenscraper_id=0,
    # ),
    # # Interact: Interact Model 1 / Victor computer; not in SS.
    # System(
    #     zaparoo_id="Interact",
    #     mister_media_dirname="Interact",
    #     mister_folders=["Interact"],
    #     mister_core_name="Interact",
    #     screenscraper_id=0,
    # ),
    # # Laser: VTech Laser 310 / Dick Smith VZ-200; not in SS.
    # System(
    #     zaparoo_id="Laser",
    #     mister_media_dirname="Laser",
    #     mister_folders=["Laser"],
    #     mister_core_name="Laser",
    #     screenscraper_id=0,
    # ),
    # # MultiComp: Grant Searle MultiComp FPGA kit; not in SS.
    # System(
    #     zaparoo_id="MultiComp",
    #     mister_media_dirname="MultiComp",
    #     mister_folders=["MultiComp"],
    #     mister_core_name="MultiComp",
    #     screenscraper_id=0,
    # ),
    # # NESMusic: NSF chiptune player (not a game system); no SS entry.
    # System(
    #     zaparoo_id="NESMusic",
    #     mister_media_dirname="NES",
    #     mister_folders=["NES"],
    #     mister_core_name="NES",
    #     screenscraper_id=0,
    # ),
    # # SNESMusic: SPC chiptune player (not a game system); no SS entry.
    # System(
    #     zaparoo_id="SNESMusic",
    #     mister_media_dirname="SNES",
    #     mister_folders=["SNES"],
    #     mister_core_name="SNES",
    #     screenscraper_id=0,
    # ),
    # # Orao: Croatian Orao (Eagle) microcomputer; not in SS.
    # System(
    #     zaparoo_id="Orao",
    #     mister_media_dirname="ORAO",
    #     mister_folders=["ORAO"],
    #     mister_core_name="Orao",
    #     screenscraper_id=0,
    # ),
    # # PDP1: DEC PDP-1 mainframe; not in SS.
    # System(
    #     zaparoo_id="PDP1",
    #     mister_media_dirname="PDP1",
    #     mister_folders=["PDP1"],
    #     mister_core_name="PDP1",
    #     screenscraper_id=0,
    # ),
    # # PMD85: Czechoslovak Tesla PMD 85 microcomputer; not in SS.
    # System(
    #     zaparoo_id="PMD85",
    #     mister_media_dirname="PMD85",
    #     mister_folders=["PMD85"],
    #     mister_core_name="PMD85",
    #     screenscraper_id=0,
    # ),
    # # QL: Sinclair QL; not in SS system list.
    # System(
    #     zaparoo_id="QL",
    #     mister_media_dirname="QL",
    #     mister_folders=["QL"],
    #     mister_core_name="QL",
    #     screenscraper_id=0,
    # ),
    # # RX78: Bandai RX-78; not in SS.
    # System(
    #     zaparoo_id="RX78",
    #     mister_media_dirname="RX78",
    #     mister_folders=["RX78"],
    #     mister_core_name="RX78",
    #     screenscraper_id=0,
    # ),
    # # SordM5: Sord M5 (also Grundy NewBrain-adjacent); not in SS.
    # System(
    #     zaparoo_id="SordM5",
    #     mister_media_dirname="Sord M5",
    #     mister_folders=["Sord M5"],
    #     mister_core_name="SordM5",
    #     screenscraper_id=0,
    # ),
    # # Specialist: Soviet Specialist MX computer; not in SS.
    # System(
    #     zaparoo_id="Specialist",
    #     mister_media_dirname="SPMX",
    #     mister_folders=["SPMX"],
    #     mister_core_name="Specialist",
    #     screenscraper_id=0,
    # ),
    # # TatungEinstein: Tatung Einstein TC-01; not in SS.
    # System(
    #     zaparoo_id="TatungEinstein",
    #     mister_media_dirname="TatungEinstein",
    #     mister_folders=["TatungEinstein"],
    #     mister_core_name="TatungEinstein",
    #     screenscraper_id=0,
    # ),
    # # TomyTutor: Tomy Tutor / Pyuuta; not in SS.
    # System(
    #     zaparoo_id="TomyTutor",
    #     mister_media_dirname="TomyTutor",
    #     mister_folders=["TomyTutor"],
    #     mister_core_name="TomyTutor",
    #     screenscraper_id=0,
    # ),
    # # TRS80: Tandy TRS-80 Model I/III (not Color Computer). SS 144 is specifically
    # # "TRS-80 Color Computer" (CoCo), which is a different platform. CoCo2 → SS 144.
    # System(
    #     zaparoo_id="TRS80",
    #     mister_media_dirname="TRS-80",
    #     mister_folders=["TRS-80"],
    #     mister_core_name="TRS80",
    #     screenscraper_id=0,
    # ),
    # # TSConf: ZX Evolution / TS Configuration board (Russian ZX Spectrum variant); not in SS.
    # System(
    #     zaparoo_id="TSConf",
    #     mister_media_dirname="TSConf",
    #     mister_folders=["TSConf"],
    #     mister_core_name="TSConf",
    #     screenscraper_id=0,
    # ),
    # # UK101: Compukit UK101 (Ohio Scientific clone); not in SS.
    # System(
    #     zaparoo_id="UK101",
    #     mister_media_dirname="UK101",
    #     mister_folders=["UK101"],
    #     mister_core_name="UK101",
    #     screenscraper_id=0,
    # ),
    # # Vector06C: Soviet Vector-06C computer; not in SS.
    # System(
    #     zaparoo_id="Vector06C",
    #     mister_media_dirname="VECTOR06",
    #     mister_folders=["VECTOR06"],
    #     mister_core_name="Vector06C",
    #     screenscraper_id=0,
    # ),
]
