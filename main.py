#!/usr/bin/env python3
"""news-image-20261122: one broadsheet for Sunday 22 November 2026.

Renders the whole front page from scratch using only the Python
standard library: a 5x7 pixel font stored as rows of '#' and '.',
a blocky world map with numbered, region-coloured pins, a lead
story (COP31 climate talks at dawn in Antalya), and 34 numbered
stories in three columns across seven regions. No network access,
no files read, no randomness: every run writes identical bytes.

Layout (1024x1024): masthead, lead banner, numbered world map with
a region key, then the day's stories in three columns. Every story
below is a verified report from 16-22 November 2026, led by today's
news; nothing unverified is printed. 35 stories in all: the lead
plus 34 numbered stories.
"""

import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (20, 20, 20)
CRIMSON = (176, 30, 30)
MUTED = (74, 74, 74)
SEA = (203, 221, 233)
SAND = (233, 224, 196)
MAPGREY = (96, 96, 96)
LEADPINK = (244, 226, 220)
SNOW = (255, 255, 255)
DIVIDER = (200, 195, 185)

# Region colours, keyed by the short region code used in the data.
REGION_COLOURS = {
    "EU": (38, 84, 160),
    "AS": (34, 139, 60),
    "ME": (122, 62, 140),
    "AF": (176, 122, 20),
    "NA": (176, 30, 30),
    "SA": (13, 148, 136),
    "OC": (196, 30, 140),
    "LEAD": (176, 30, 30),
}

# ---------------------------------------------------------------- font: 5x7
# Each glyph is 7 rows of 5 characters; '#' paints, '.' stays empty.
# Uppercase letters, digits and the punctuation the page needs.
# Sheet.text() upper-cases everything before lookup.
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "\u2022": (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
}


# ---------------------------------------------------------------- canvas
class Sheet:
    """A plain RGB pixel grid with a few drawing helpers."""

    def __init__(self, width, height, paper):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.paint(0, 0, width, height, paper)

    def paint(self, x, y, w, h, colour):
        """Fill a rectangle, clipped to the sheet."""
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        r, g, b = colour
        for yy in range(y0, y1):
            base = (yy * self.width + x0) * 3
            for xx in range(x1 - x0):
                i = base + xx * 3
                self.pixels[i] = r
                self.pixels[i + 1] = g
                self.pixels[i + 2] = b

    def point(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i], self.pixels[i + 1], self.pixels[i + 2] = colour

    def hbar(self, x0, x1, y, colour, thick=1):
        if x1 < x0:
            x0, x1 = x1, x0
        self.paint(x0, y, x1 - x0 + 1, thick, colour)

    def vbar(self, x, y0, y1, colour, thick=1):
        if y1 < y0:
            y0, y1 = y1, y0
        self.paint(x, y0, thick, y1 - y0 + 1, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Straight line by integer interpolation, any slope."""
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        half = thick // 2
        for k in range(steps + 1):
            x = x0 + (dx * k) // steps
            y = y0 + (dy * k) // steps
            self.paint(x - half, y - half, thick, thick, colour)

    def disc(self, cx, cy, r, colour):
        """Filled disc of radius r."""
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.point(xx, yy, colour)

    def ring(self, cx, cy, r, colour, thick=2):
        """Disc outline: a ring of thickness thick."""
        for yy in range(cy - r - thick, cy + r + thick + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if (r - thick) * (r - thick) <= d2 <= (r + thick) * (r + thick):
                    self.point(xx, yy, colour)

    def star(self, cx, cy, r, colour):
        """Eight-pointed star made from two diamonds."""
        half = int(r * 0.62)
        for dy in range(-r, r + 1):
            spread = r - abs(dy)
            self.hbar(cx - spread, cx + spread, cy + dy, colour)
        for dy in range(-half, half + 1):
            spread = half - abs(dy)
            self.vbar(cx + dy, cy - spread, cy + spread, colour)
            self.vbar(cx - dy, cy - spread, cy + spread, colour)

    def glyph(self, ch, x, y, zoom, colour):
        rows = GLYPHS.get(ch, GLYPHS[" "])
        for row in range(7):
            for col in range(5):
                if rows[row][col] == "#":
                    self.paint(x + col * zoom, y + row * zoom,
                               zoom, zoom, colour)

    def span(self, s, zoom):
        """Advance width in pixels of s at the given zoom."""
        return len(s) * 6 * zoom

    def text(self, s, x, y, zoom, colour, align="left"):
        """Render text; align left/center/right is relative to x."""
        s = s.upper()
        if align == "center":
            x -= self.span(s, zoom) // 2
        elif align == "right":
            x -= self.span(s, zoom)
        cx = x
        for ch in s:
            self.glyph(ch, cx, y, zoom, colour)
            cx += 6 * zoom
        return cx


# ---------------------------------------------------------------- PNG
def _pack_chunk(kind, payload):
    raw = struct.pack(">I", len(payload)) + kind + payload
    return raw + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def to_png(sheet):
    """Encode a Sheet as a PNG byte string."""
    header = struct.pack(">IIBBBBB", sheet.width, sheet.height, 8, 2, 0, 0, 0)
    rows = bytearray()
    for y in range(sheet.height):
        rows.append(0)
        rows += sheet.pixels[y * sheet.width * 3:(y + 1) * sheet.width * 3]
    body = zlib.compress(bytes(rows), 9)
    return (b"\x89PNG\r\n\x1a\n"
            + _pack_chunk(b"IHDR", header)
            + _pack_chunk(b"IDAT", body)
            + _pack_chunk(b"IEND", b""))

# ---------------------------------------------------------------- world map
MAP_LEFT, MAP_TOP = 24, 226
MAP_RIGHT, MAP_BOTTOM = 1000, 466
LON_WEST, LON_EAST = -180.0, 180.0
LAT_NORTH, LAT_SOUTH = 78.0, -56.0


def project(lon, lat):
    """Equirectangular projection into the map box."""
    x = MAP_LEFT + int((lon - LON_WEST) / (LON_EAST - LON_WEST)
                       * (MAP_RIGHT - MAP_LEFT))
    y = MAP_TOP + int((LAT_NORTH - lat) / (LAT_NORTH - LAT_SOUTH)
                      * (MAP_BOTTOM - MAP_TOP))
    return x, y


# Rough continent blocks: (west lon, south lat, east lon, north lat).
# Blocky on purpose; the numbered pins carry the map.
CONTINENTS = [
    # North America
    (-168, 60, -140, 70),
    (-140, 50, -60, 70),
    (-125, 30, -66, 48),
    (-117, 15, -86, 30),
    (-92, 8, -77, 16),
    (-55, 60, -20, 76),
    (-85, 18, -74, 23),
    # South America
    (-80, 0, -52, 12),
    (-80, -18, -42, 0),
    (-70, -35, -55, -15),
    (-70, -52, -62, -35),
    # Europe
    (-10, 36, 3, 44),
    (-5, 44, 30, 58),
    (5, 55, 30, 70),
    (-5, 50, 2, 58),
    (8, 36, 28, 45),
    (-10, 51, -6, 55),
    (-22, 63, -14, 66),
    # Africa
    (-10, 15, 35, 32),
    (-17, 4, 42, 15),
    (12, -18, 33, 4),
    (16, -35, 32, -18),
    (33, -2, 51, 12),
    (43, -25, 50, -12),
    # Asia
    (30, 50, 180, 72),
    (45, 42, 130, 52),
    (78, 20, 125, 42),
    (68, 8, 88, 32),
    (95, 5, 105, 28),
    (34, 12, 58, 30),
    (30, 29, 44, 37),
    (44, 25, 63, 42),
    (130, 30, 142, 45),
    (140, 41, 145, 45),
    (95, -8, 140, 5),
    (131, -9, 147, -1),
    (126, 34, 130, 40),
    # Oceania
    (113, -25, 130, -12),
    (128, -38, 148, -12),
    (146, -39, 153, -30),
    (166, -47, 178, -34),
]

# Ocean and continent names printed on the map: (lon, lat, name).
OCEAN_NAMES = [
    (-100, 60, "NORTH AMERICA"),
    (-55, -28, "SOUTH AMERICA"),
    (20, 5, "AFRICA"),
    (92, 58, "ASIA"),
    (128, -30, "AUSTRALIA"),
    (-150, 8, "PACIFIC"),
    (-35, 22, "ATLANTIC"),
    (78, -32, "INDIAN OCEAN"),
]

# Map pins: (number, lon, lat, label dx, label dy, region).
# A few event spots are nudged a few degrees so crowded corners stay
# legible; the label offsets keep the numbers off the pins.
PINS = [
    (1, 30.7, 36.9, 12, -8, "LEAD"),       # Antalya - lead star
    (2, 21.0, 52.2, 10, -8, "EU"),        # Warsaw
    (3, 23.5, 59.8, 12, -14, "EU"),       # Gulf of Finland
    (4, 2.3, 48.9, -32, 6, "EU"),         # Paris
    (5, 7.0, 47.2, 12, 14, "EU"),         # Paris, nudged east
    (6, 51.4, 35.7, 10, -8, "ME"),        # Tehran
    (7, 50.6, 26.2, 10, 10, "ME"),        # Bahrain
    (8, 28.5, 21.0, -34, 8, "ME"),        # Gaza City, nudged south
    (9, 41.0, 30.0, 12, -10, "ME"),       # Jerusalem, nudged east
    (10, 56.5, 26.5, 10, 12, "ME"),       # Strait of Hormuz
    (11, 6.3, 4.9, -34, 8, "AF"),         # Bayelsa, Nigeria
    (12, 39.0, 3.5, 10, -8, "AF"),        # Moyale
    (13, 45.3, 2.0, 10, 10, "AF"),        # Mogadishu
    (14, 28.0, -26.2, 10, -8, "AF"),      # Johannesburg
    (15, 7.5, 9.1, 10, -8, "AF"),         # Abuja
    (16, 83.0, 18.5, 10, 10, "AS"),       # Gopalpur, Odisha
    (17, 85.1, 25.6, 10, -8, "AS"),       # Patna
    (18, 114.1, 22.5, -34, 10, "AS"),     # Shenzhen
    (19, 139.7, 35.7, 10, -8, "AS"),      # Tokyo
    (20, 141.5, 37.5, 10, 12, "AS"),      # Tokyo, nudged north
    (21, -74.0, 40.7, 10, -14, "NA"),     # New York
    (22, -122.4, 37.8, -34, -8, "NA"),    # San Francisco
    (23, -108.5, 25.6, -34, 8, "NA"),     # Guasave, Sinaloa
    (24, -79.0, 37.8, -36, -8, "NA"),     # Washington DC, nudged west
    (25, -69.5, 39.2, 12, 6, "NA"),       # New York, nudged east
    (26, -74.8, 11.0, -34, -20, "SA"),    # Barranquilla
    (27, -76.0, -11.0, 10, 10, "SA"),     # Junin, Peru
    (28, -66.9, 10.5, 10, -8, "SA"),      # Caracas
    (29, -47.9, -15.8, 10, -8, "SA"),     # Brasilia
    (30, -72.5, 2.9, -44, 14, "SA"),      # Mapiripan, Meta
    (31, -5.5, 52.0, -36, -10, "OC"),     # Cardiff, nudged west
    (32, 174.8, -36.9, -34, -8, "OC"),    # Auckland
    (33, 172.5, -41.5, -34, 8, "OC"),     # New Zealand
    (34, 119.0, 26.5, 10, 10, "OC"),      # Shenzhen, nudged north
    (35, 149.1, -35.3, 10, -12, "OC"),    # Canberra
]

# Region key under the map: (region code, label).
KEY = [
    ("EU", "EUROPE"), ("AS", "ASIA"), ("ME", "MIDDLE EAST"),
    ("AF", "AFRICA"), ("NA", "N. AMERICA"), ("SA", "S. AMERICA"),
    ("OC", "OCEANIA"), ("LEAD", "LEAD STORY"),
]

# ---------------------------------------------------------------- stories
# (number, headline, summary, region). Headlines fit 22 chars at
# zoom 2; summaries fit 45 chars at zoom 1. Every line below is a
# verified report from 16-22 November 2026.
ITEMS = [
    (2, "NATO: EVERY INCH SAFE", "RUTTE VOWS NATO WILL DEFEND ALL POLAND", "EU"),
    (3, "16 SAVED AS SHIP BURNS", "DRONE-HIT RUSSIAN SHIP ABLAZE IN BALTIC", "EU"),
    (4, "FRENCH MARCHES SHRINK", "COST-OF-LIVING PROTESTS DRAW FEWER PEOPLE", "EU"),
    (5, "RACIST BEATING: JAILED", "PARIS COURT JAILS THREE POLICE OFFICERS", "EU"),
    (6, "TRUMP WANTS IRAN DEAL", "PRESIDENT SEEKS 'PERMANENT' NUCLEAR PACT", "ME"),
    (7, "BAHRAIN HIT BY IRAN", "IRANIAN ATTACK SETS INDUSTRIAL SITE ABLAZE", "ME"),
    (8, "GAZA STRIKE KILLS 3", "FOOD TRUCK HIT; 3 DEAD IN GAZA CITY", "ME"),
    (9, "ISRAEL TALKS RESTART", "EISENKOT INVITES LIKUD TO MARATHON TALKS", "ME"),
    (10, "TANKERS HIT OFF OMAN", "SHIPS STRUCK NEAR STRAIT OF HORMUZ", "ME"),
    (11, "BOAT DISASTER IN DELTA", "AT LEAST 24 DEAD AS FUNERAL BOAT CAPSIZES", "AF"),
    (12, "700,000 FLEE CLASHES", "ETHIOPIA BORDER FIGHTING DISPLACES THOUSANDS", "AF"),
    (13, "SOMALIA EXPELS UAE MAN", "MOGADISHU ORDERS ENVOY OUT IN 72 HOURS", "AF"),
    (14, "SA RATES HELD AT 7.25%", "CENTRAL BANK SPLIT 4-3 ON HOLDING RATES", "AF"),
    (15, "SUICIDE JAIL TO END", "NIGERIA MOVES TO SCRAP JAIL FOR ATTEMPTS", "AF"),
    (16, "CYCLONE AKVAN LANDS", "STORM LANDS NEAR GOPALPUR; 300K EVACUATED", "AS"),
    (17, "MODI OPENS MEGA BRIDGE", "NEW GANGA BRIDGE LINKS NORTH, SOUTH BIHAR", "AS"),
    (18, "THREE SIGN PEACE PACT", "TRUMP, XI, PUTIN SIGN JOINT DECLARATION", "AS"),
    (19, "JAPAN TRAINS IN INDIA", "TOKYO TROOPS GET FIRST INDIAN RANGE ACCESS", "AS"),
    (20, "TOKYO BEAT CEREZO 3-0", "LEAGUE LEADERS EXTEND UNBEATEN RUN TO 13", "AS"),
    (21, "WALL ST IN FREEFALL", "S&P SINKS 3.7% AS AI SELL-OFF DEEPENS", "NA"),
    (22, "ANTHROPIC SHARES SLIDE", "RECORD IPO STOCK FALLS 8.5% ON DAY TWO", "NA"),
    (23, "CHAPO ISIDRO SEIZED", "FBI MOST-WANTED CAPO CAUGHT; 11 KILLED", "NA"),
    (24, "FEMA FLEES BED BUGS", "1,000 STAFF SENT HOME AS HQ FUMIGATED", "NA"),
    (25, "MAYOR MOURNS SLAIN BOY", "GHANAIAN BOY KILLED IN US; MAYOR SPEAKS", "NA"),
    (26, "BOCA LIFT THE CUP", "BOCA BEAT ATLETICO MINEIRO 2-0 IN FINAL", "SA"),
    (27, "PERU ROCKED BY M6.9", "STRONG QUAKE SHAKES ANDES; NO CASUALTIES", "SA"),
    (28, "US, VENEZUELA INK DEAL", "HEGSETH VISIT RESTORES MILITARY TIES", "SA"),
    (29, "BOLSONARO HOSPITALISED", "EX-PRESIDENT ADMITTED WITH ABDOMINAL PAIN", "SA"),
    (30, "COLOMBIA KILLS REBELS", "AIRSTRIKE HITS FARC DISSIDENTS IN META", "SA"),
    (31, "WALLABIES EDGE WALES", "AUSTRALIA WIN 29-26 THRILLER IN CARDIFF", "OC"),
    (32, "AUSSIES BEAT KIWIS 3-1", "TOURE BRACE SEALS WIN IN AUCKLAND", "OC"),
    (33, "ASBESTOS TOYS RECALLED", "FOUR MORE KIDS' KITS PULLED IN NEW ZEALAND", "OC"),
    (34, "ALLIES URGE TRUCE", "AUSTRALIA, CANADA, NZ DEMAND CEASEFIRE", "OC"),
    (35, "PETERS BLASTS CANBERRA", "NZ MINISTER 'AGHAST' AT AUSTRALIAN CHURN", "OC"),
]


# ---------------------------------------------------------------- the page
def compose():
    page = Sheet(W, H, PAPER)
    # outer frame
    page.paint(8, 8, W - 16, 4, INK)
    page.paint(8, H - 12, W - 16, 4, INK)
    page.paint(8, 8, 4, H - 16, INK)
    page.paint(W - 12, 8, 4, H - 16, INK)

    # masthead
    page.text("THE WORLD IN ONE PICTURE", 512, 22, 5, INK, "center")
    page.hbar(24, 1000, 64, INK, 3)
    page.hbar(24, 1000, 67, INK, 1)
    page.text("SUNDAY 22 NOVEMBER 2026  \u2022  35 STORIES  \u2022  7 REGIONS",
              512, 74, 2, INK, "center")

    # lead banner
    page.paint(24, 100, 976, 104, LEADPINK)
    page.paint(24, 100, 8, 104, CRIMSON)
    page.text("LEAD STORY  \u2022  CLIMATE DEAL AT DAWN", 48, 106, 2, CRIMSON)
    page.text("COP31 NEARS CLIMATE DEAL", 48, 124, 5, CRIMSON)
    page.text("TALKS RUN PAST DEADLINE INTO SUNDAY DAWN", 48, 162, 3, INK)
    page.text("ANTALYA: ALL-NIGHT TALKS, DEAL CLOSE AT DAWN", 48, 186, 2, MUTED)

    # map title
    page.text("THE WORLD, NUMBERED - FOLLOW THE NUMBERS", 24, 210, 2, INK)
    page.text("STAR 1 IS THE LEAD STORY", 1000, 210, 2, CRIMSON, "right")

    # map: ocean, land, border, names, pins
    page.paint(MAP_LEFT, MAP_TOP, MAP_RIGHT - MAP_LEFT,
               MAP_BOTTOM - MAP_TOP, SEA)
    for west, south, east, north in CONTINENTS:
        x0, y0 = project(west, north)
        x1, y1 = project(east, south)
        page.paint(x0, y0, x1 - x0, y1 - y0, SAND)
    page.hbar(MAP_LEFT, MAP_RIGHT, MAP_TOP, INK, 2)
    page.hbar(MAP_LEFT, MAP_RIGHT, MAP_BOTTOM - 2, INK, 2)
    page.vbar(MAP_LEFT, MAP_TOP, MAP_BOTTOM, INK, 2)
    page.vbar(MAP_RIGHT - 2, MAP_TOP, MAP_BOTTOM, INK, 2)
    for lon, lat, name in OCEAN_NAMES:
        x, y = project(lon, lat)
        page.text(name, x, y, 2, MAPGREY, "center")
    for num, lon, lat, dx, dy, region in PINS:
        x, y = project(lon, lat)
        colour = REGION_COLOURS[region]
        if num == 1:
            page.star(x, y, 13, CRIMSON)
            page.ring(x, y, 17, CRIMSON, 2)
        else:
            page.ring(x, y, 6, colour, 2)
            page.disc(x, y, 4, colour)
        lx, ly = x + dx, y + dy
        if abs(dx) > 12 or abs(dy) > 12:
            page.line(x, y, lx + 6, ly + 7, colour, 1)
        page.text(str(num), lx, ly, 2, colour)

    # region key, spread evenly across the page
    widths = [18 + page.span(name, 2) for _, name in KEY]
    gap = (976 - sum(widths)) // (len(KEY) - 1)
    lx = 24
    for (region, name), w in zip(KEY, widths):
        page.disc(lx + 6, 481, 5, REGION_COLOURS[region])
        page.text(name, lx + 18, 474, 2, INK)
        lx += w + gap

    # stories header
    page.hbar(24, 1000, 496, INK, 2)
    page.text("THE DAY IN STORIES", 24, 504, 3, INK)
    page.text("NUMBERS MATCH THE MAP", 1000, 507, 2, MUTED, "right")

    # stories grid: three columns of twelve, twelve, ten
    for idx, (num, head, summ, region) in enumerate(ITEMS):
        col = idx // 12
        row = idx % 12
        x = 24 + col * 336
        y = 530 + row * 38
        if len(head) * 12 > 272 or len(summ) * 6 > 272:
            raise ValueError("story %d line too wide: %r" % (num, head))
        page.paint(x, y, 24, 24, REGION_COLOURS[region])
        page.text(str(num), x + 12, y + 5, 2, SNOW, "center")
        page.text(head, x + 32, y + 2, 2, INK)
        page.text(summ, x + 32, y + 20, 1, MUTED)
        if row < 11:
            page.hbar(x, x + 304, y + 32, DIVIDER, 1)

    # footer
    page.hbar(24, 1000, 990, INK, 2)
    page.text("SUNDAY 22 NOVEMBER 2026 - STORIES FROM 16-22 NOV, "
              "LED BY TODAY'S NEWS", 512, 996, 2, INK, "center")
    return page


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    data = to_png(compose())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
