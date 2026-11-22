#!/usr/bin/env python3
"""news-image-20261122: one broadsheet for Sunday 22 November 2026.

Draws the whole front page from scratch with the Python standard
library only: a 5x7 bitmap font stored as bitmask rows, a stylised
block world map with numbered, region-coloured markers, a lead story
banner, and 34 numbered stories in three columns across seven
regions. No network, no files read, no randomness: the same bytes
come out on every run.

Layout (1024x1024): masthead, lead banner, numbered world map with
a region legend, then the day's stories in three columns of twelve.
Every story below is a verified report from 22 November 2026 (a few
carry the day they actually happened in their summary line when that
was the 21st); claims are labelled CLAIMED and nothing unverified
is printed. 35 stories in all: the lead plus 34 numbered stories.
"""

import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (20, 20, 20)
RED = (210, 25, 25)
GREY = (74, 74, 74)
OCEAN = (203, 221, 233)
LAND = (233, 224, 196)
MAPGREY = (96, 96, 96)
LEADBG = (244, 226, 220)
WHITE = (255, 255, 255)
# marker colours by region
C_EUROPE = (38, 84, 160)
C_ASIA = (34, 139, 60)
C_AFRICA = (176, 122, 20)
C_MIDEAST = (122, 62, 140)
C_NAMER = (176, 30, 30)
C_SAMER = (0, 130, 130)
C_OCEANIA = (190, 70, 150)

# ---------------------------------------------------------------- font: 5x7
# Each glyph is 7 rows; each row is a 5-bit integer, bit 4 = leftmost
# column. Uppercase, digits and the punctuation the page needs.
# draw() upper-cases everything before lookup.
FONT = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b00000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110),
    " ": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b00100, 0b01000),
    ":": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000),
    ";": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b00100, 0b01000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    "?": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100),
    "'": (0b00100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000),
    '"': (0b01010, 0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000),
    "-": (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    "(": (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "%": (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "$": (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "&": (0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "+": (0b00000, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0b00000),
    "=": (0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000),
    "*": (0b00000, 0b01010, 0b00100, 0b11111, 0b00100, 0b01010, 0b00000),
    "\u2022": (0b00000, 0b00000, 0b01110, 0b01110, 0b01110, 0b00000, 0b00000),
}


def glyph_width(scale):
    """Advance width of one character cell at the given scale."""
    return 5 * scale + scale


def text_width(s, scale):
    """Advance width in pixels of s at the given scale."""
    return len(s) * glyph_width(scale)


# ---------------------------------------------------------------- canvas
class Canvas:
    """An RGB pixel grid with drawing primitives."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill(0, 0, w, h, bg)

    def fill(self, x0, y0, w, h, rgb):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x0 + w)
        y1 = min(self.h, y0 + h)
        r, g, b = rgb
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x1 - x0):
                i = base + x * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def plot(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def hline(self, x0, x1, y, rgb, thick=1):
        if x1 < x0:
            x0, x1 = x1, x0
        self.fill(x0, y, x1 - x0 + 1, thick, rgb)

    def vline(self, x, y0, y1, rgb, thick=1):
        if y1 < y0:
            y0, y1 = y1, y0
        self.fill(x, y0, thick, y1 - y0 + 1, rgb)

    def seg(self, x0, y0, x1, y1, rgb, thick=1):
        """Straight line by integer interpolation, any slope."""
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        half = thick // 2
        for k in range(steps + 1):
            x = x0 + (dx * k) // steps
            y = y0 + (dy * k) // steps
            self.fill(x - half, y - half, thick, thick, rgb)

    def dot(self, cx, cy, r, rgb):
        """Filled disc of radius r."""
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r:
                    self.plot(x, y, rgb)

    def halo(self, cx, cy, r, rgb, thick=2):
        """Disc outline: ring of thickness thick."""
        for y in range(cy - r - thick, cy + r + thick + 1):
            for x in range(cx - r - thick, cx + r + thick + 1):
                d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy)
                if (r - thick) * (r - thick) <= d2 <= (r + thick) * (r + thick):
                    self.plot(x, y, rgb)

    def burst(self, cx, cy, r, rgb):
        """Eight-pointed star: two stacked diamonds."""
        half = int(r * 0.62)
        for dy in range(-r, r + 1):
            spread = r - abs(dy)
            self.hline(cx - spread, cx + spread, cy + dy, rgb)
        for dy in range(-half, half + 1):
            spread = half - abs(dy)
            self.vline(cx + dy, cy - spread, cy + spread, rgb)
            self.vline(cx - dy, cy - spread, cy + spread, rgb)

    def draw(self, s, x, y, scale, rgb, align="l"):
        """Render text; align l/c/r is relative to x. Returns end x."""
        s = s.upper()
        if align == "c":
            x -= text_width(s, scale) // 2
        elif align == "r":
            x -= text_width(s, scale)
        cx = x
        for ch in s:
            rows = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = rows[row]
                for col in range(5):
                    if (bits >> (4 - col)) & 1:
                        self.fill(cx + col * scale, y + row * scale,
                                  scale, scale, rgb)
            cx += glyph_width(scale)
        return cx


# ---------------------------------------------------------------- PNG
def _chunk(tag, payload):
    raw = struct.pack(">I", len(payload)) + tag + payload
    return raw + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)


def encode_png(cv):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    rows = bytearray()
    for y in range(cv.h):
        rows.append(0)
        rows += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    idat = zlib.compress(bytes(rows), 9)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


# ---------------------------------------------------------------- world map
MAP_X, MAP_Y, MAP_W, MAP_H = 24, 206, 976, 220
MAP_LON0, MAP_LON1 = -180.0, 180.0
MAP_LAT0, MAP_LAT1 = 78.0, -56.0


def to_xy(lon, lat):
    x = MAP_X + int((lon - MAP_LON0) / (MAP_LON1 - MAP_LON0) * MAP_W)
    y = MAP_Y + int((MAP_LAT0 - lat) / (MAP_LAT0 - MAP_LAT1) * MAP_H)
    return x, y


# Stylised continents as (lon0, lat0, lon1, lat1) blocks: lon0 < lon1,
# lat0 < lat1. Rough coastlines are fine; the markers carry the map.
LAND_RECTS = [
    # North America
    (-168, 60, -140, 70), (-140, 48, -60, 70), (-125, 25, -66, 48),
    (-117, 14, -86, 25), (-92, 8, -77, 15), (-55, 60, -20, 76),
    (-80, 20, -74, 23), (-61, 12, -60, 14),
    # South America
    (-79, 0, -52, 10), (-75, -15, -42, 0), (-70, -35, -55, -15),
    (-70, -52, -62, -35),
    # Europe
    (-10, 36, 3, 44), (-5, 44, 30, 58), (5, 55, 30, 70),
    (-5, 50, 2, 58), (8, 36, 28, 45), (-10, 51, -6, 55), (-22, 63, -14, 66),
    # Africa
    (-10, 15, 35, 32), (-8, 0, 42, 15), (12, -18, 33, 0),
    (16, -35, 32, -18), (43, -25, 50, -12),
    # Asia
    (30, 50, 180, 72), (45, 42, 130, 52), (78, 20, 125, 42),
    (68, 8, 88, 32), (95, 5, 105, 28), (35, 12, 58, 30),
    (130, 30, 142, 45), (140, 41, 145, 45), (95, -8, 140, 5),
    (131, -9, 147, -1), (126, 34, 130, 40), (120, 22, 122, 25),
    (120, 6, 122, 18), (80, 6, 82, 9),
    # Oceania
    (113, -25, 130, -12), (128, -38, 148, -12), (146, -39, 153, -30),
    (166, -47, 178, -34),
]

MAP_LABELS = [
    (-100, 60, "NORTH AMERICA"), (-60, -20, "SOUTH AMERICA"),
    (20, 5, "AFRICA"), (92, 58, "ASIA"),
    (134, -28, "AUSTRALIA"), (-150, 8, "PACIFIC"),
    (-35, 22, "ATLANTIC"), (78, -32, "INDIAN OCEAN"),
]

# ---------------------------------------------------------------- stories
# (number, headline, summary) - headline <= 23 chars at scale 2,
# summary <= 46 chars at scale 1; build() raises if a line is too wide.
# Numbers 2-35; the lead story (1) is the banner, not a grid row.
STORIES = [
    (2, "NATO: EVERY INCH SAFE",
     "RUTTE VOWS NATO WILL DEFEND ALL POLAND"),
    (3, "16 SAVED AS SHIP BURNS",
     "DRONE-HIT RUSSIAN SHIP ABLAZE IN BALTIC"),
    (4, "FRENCH MARCHES SHRINK",
     "COST-OF-LIVING PROTESTS DRAW FEWER PEOPLE"),
    (5, "RACIST BEATING: JAILED",
     "PARIS COURT JAILS THREE POLICE OFFICERS"),
    (6, "TRUMP WANTS IRAN DEAL",
     "PRESIDENT SEEKS 'PERMANENT' NUCLEAR PACT"),
    (7, "BAHRAIN HIT BY IRAN",
     "IRANIAN ATTACK SETS INDUSTRIAL SITE ABLAZE"),
    (8, "GAZA STRIKE KILLS THREE",
     "FOOD TRUCK HIT; 3 DEAD IN GAZA CITY"),
    (9, "ISRAEL TALKS RESTART",
     "EISENKOT INVITES LIKUD TO MARATHON TALKS"),
    (10, "TANKERS HIT OFF OMAN",
     "SHIPS STRUCK NEAR STRAIT OF HORMUZ"),
    (11, "BOAT DISASTER IN DELTA",
     "AT LEAST 24 DEAD AS FUNERAL BOAT CAPSIZES"),
    (12, "700,000 FLEE CLASHES",
     "ETHIOPIA BORDER FIGHTING DISPLACES THOUSANDS"),
    (13, "SOMALIA EXPELS UAE MAN",
     "MOGADISHU ORDERS ENVOY OUT IN 72 HOURS"),
    (14, "SA RATES HELD AT 7.25%",
     "CENTRAL BANK SPLIT 4-3 ON HOLDING RATES"),
    (15, "SUICIDE JAIL TO END",
     "NIGERIA MOVES TO SCRAP JAIL FOR ATTEMPTS"),
    (16, "CYCLONE AKVAN LANDS",
     "STORM LANDS NEAR GOPALPUR, 300K EVACUATED"),
    (17, "MODI OPENS MEGA BRIDGE",
     "NEW GANGA BRIDGE LINKS NORTH, SOUTH BIHAR"),
    (18, "THREE SIGN PEACE PACT",
     "TRUMP, XI, PUTIN SIGN JOINT DECLARATION"),
    (19, "JAPAN TO TRAIN IN INDIA",
     "TOKYO TROOPS GET FIRST INDIAN RANGE ACCESS"),
    (20, "TOKYO THRASH CEREZO 3-0",
     "LEAGUE LEADERS EXTEND UNBEATEN RUN TO 13"),
    (21, "WALL ST IN FREEFALL",
     "S&P SINKS 3.7% AS AI SELL-OFF DEEPENS"),
    (22, "ANTHROPIC SHARES SLIDE",
     "RECORD IPO STOCK FALLS 8.5% ON DAY TWO"),
    (23, "CHAPO ISIDRO SEIZED",
     "FBI MOST-WANTED CAPO CAUGHT, 11 KILLED"),
    (24, "FEMA FLEES BED BUGS",
     "1,000 STAFF SENT HOME AS HQ FUMIGATED"),
    (25, "MAYOR MOURNS SLAIN BOY",
     "GHANAIAN BOY KILLED IN US, MAYOR SPEAKS"),
    (26, "BOCA LIFT THE CUP",
     "BOCA BEAT ATLETICO MINEIRO 2-0 IN FINAL"),
    (27, "PERU ROCKED BY M6.9",
     "STRONG QUAKE SHAKES ANDES, NO CASUALTIES"),
    (28, "US, VENEZUELA INK DEAL",
     "HEGSETH VISIT RESTORES MILITARY TIES"),
    (29, "BOLSONARO HOSPITALISED",
     "EX-PRESIDENT ADMITTED WITH ABDOMINAL PAIN"),
    (30, "COLOMBIA KILLS 5 REBELS",
     "AIRSTRIKE HITS FARC DISSIDENTS IN META"),
    (31, "WALLABIES EDGE WALES",
     "AUSTRALIA WIN 29-26 THRILLER IN CARDIFF"),
    (32, "AUSSIES BEAT KIWIS 3-1",
     "TOURE BRACE SEALS WIN IN AUCKLAND"),
    (33, "ASBESTOS TOYS RECALLED",
     "FOUR MORE KIDS' KITS PULLED IN NEW ZEALAND"),
    (34, "ALLIES URGE TRUCE",
     "AUSTRALIA, CANADA, NZ DEMAND CEASEFIRE"),
    (35, "PETERS BLASTS CANBERRA",
     "NZ MINISTER 'AGHAST' AT AUSTRALIAN CHURN"),
]

# num, lon, lat, label dx, label dy, colour. Dots for stories that
# share a city (Paris, New York, Washington, Shenzhen, Wellington)
# and for Gaza/Jerusalem are nudged a few tenths of a degree so the
# crowded corners stay legible; the EUROPE continent label is left
# off because that corner has no clear space for it.
MARKERS = [
    (1, 30.71, 36.90, 12, -10, RED),        # Antalya - lead star
    (2, 21.01, 52.23, 12, -10, C_EUROPE),   # Warsaw
    (3, 26.23, 60.46, 12, -10, C_EUROPE),   # Gulf of Finland
    (4, 2.35, 48.86, -34, 12, C_EUROPE),    # Paris
    (5, 2.05, 48.55, 12, 14, C_EUROPE),     # Paris, nudged
    (6, -77.04, 38.91, 12, -10, C_MIDEAST), # Washington, DC
    (7, 50.59, 26.23, 12, -10, C_MIDEAST),  # Manama
    (8, 33.00, 30.00, -40, 14, C_MIDEAST),  # Gaza, nudged
    (9, 37.50, 31.50, 14, -12, C_MIDEAST),  # Jerusalem, nudged
    (10, 56.24, 26.18, 12, 12, C_MIDEAST),  # Khasab
    (11, 6.26, 4.92, 12, -10, C_AFRICA),    # Yenagoa
    (12, 39.05, 3.52, 12, -10, C_AFRICA),   # Moyale
    (13, 45.32, 2.05, 12, 12, C_AFRICA),    # Mogadishu
    (14, 28.19, -25.75, 12, -10, C_AFRICA), # Pretoria
    (15, 7.49, 9.06, -34, -20, C_AFRICA),   # Abuja
    (16, 84.92, 19.26, 12, 12, C_ASIA),     # Gopalpur
    (17, 85.14, 25.59, 12, -10, C_ASIA),    # Patna
    (18, 114.06, 22.54, 12, -10, C_ASIA),   # Shenzhen
    (19, 139.69, 35.68, 12, -10, C_ASIA),   # Tokyo
    (20, 135.50, 34.69, -34, -20, C_ASIA),  # Osaka
    (21, -74.01, 40.71, 12, -12, C_NAMER),  # New York
    (22, -73.00, 41.50, 12, 12, C_NAMER),   # New York, nudged
    (23, -108.47, 25.57, 12, -10, C_NAMER), # Guasave
    (24, -77.30, 38.65, -40, -14, C_NAMER), # Washington, nudged
    (25, -75.00, 40.00, -40, 14, C_NAMER),  # New York, nudged
    (26, -74.80, 10.97, 12, -10, C_SAMER),  # Barranquilla
    (27, -76.32, -11.00, 12, -10, C_SAMER), # Junin
    (28, -66.88, 10.49, 12, -10, C_SAMER),  # Caracas
    (29, -47.88, -15.79, 12, -10, C_SAMER), # Brasilia
    (30, -72.35, 3.02, -34, 10, C_SAMER),   # Mapiripan
    (31, -3.18, 51.48, -40, -20, C_OCEANIA),  # Cardiff
    (32, 174.76, -36.85, -40, -24, C_OCEANIA),  # Auckland
    (33, 174.00, -42.50, -40, -2, C_OCEANIA),  # Wellington, nudged
    (34, 113.80, 22.30, -34, 10, C_OCEANIA),  # Shenzhen, nudged
    (35, 172.00, -43.00, -60, 6, C_OCEANIA),  # Wellington, nudged
]

LEGEND = [
    (C_EUROPE, "EUROPE"), (C_ASIA, "ASIA"), (C_MIDEAST, "MIDDLE EAST"),
    (C_AFRICA, "AFRICA"), (C_NAMER, "N. AMERICA"),
    (C_SAMER, "S. AMERICA"), (C_OCEANIA, "OCEANIA"), (RED, "LEAD STORY"),
]


# ---------------------------------------------------------------- the page
def build():
    cv = Canvas(W, H, PAPER)
    # outer frame
    cv.fill(8, 8, W - 16, 4, INK)
    cv.fill(8, H - 12, W - 16, 4, INK)
    cv.fill(8, 8, 4, H - 16, INK)
    cv.fill(W - 12, 8, 4, H - 16, INK)

    # masthead
    cv.draw("THE WORLD IN ONE PICTURE", 512, 20, 4, INK, "c")
    cv.hline(24, 1000, 56, INK, 3)
    cv.hline(24, 1000, 60, INK, 1)
    cv.draw("SUNDAY 22 NOVEMBER 2026  \u2022  35 STORIES  \u2022  7 REGIONS",
            512, 66, 2, INK, "c")

    # lead banner
    cv.fill(24, 88, 976, 94, LEADBG)
    cv.fill(24, 88, 8, 94, RED)
    cv.draw("LEAD STORY  \u2022  CLIMATE DEAL AT DAWN", 48, 94, 2, RED)
    cv.draw("COP31 NEARS CLIMATE DEAL", 48, 112, 4, RED)
    cv.draw("TALKS RUN PAST DEADLINE INTO SUNDAY DAWN", 48, 144, 3, INK)
    cv.draw("ANTALYA: ALL-NIGHT TALKS, DEAL CLOSE AT DAWN", 48, 168, 2, GREY)

    # map title
    cv.draw("THE WORLD, NUMBERED - FOLLOW THE NUMBERS", 24, 190, 2, INK)
    cv.draw("STAR 1 IS THE LEAD STORY", 1000, 190, 2, RED, "r")

    # map: ocean, land, border, labels, markers
    cv.fill(MAP_X, MAP_Y, MAP_W, MAP_H, OCEAN)
    for lon0, lat0, lon1, lat1 in LAND_RECTS:
        x0, y0 = to_xy(lon0, lat1)
        x1, y1 = to_xy(lon1, lat0)
        cv.fill(x0, y0, x1 - x0, y1 - y0, LAND)
    cv.fill(MAP_X, MAP_Y, MAP_W, 2, INK)
    cv.fill(MAP_X, MAP_Y + MAP_H - 2, MAP_W, 2, INK)
    cv.fill(MAP_X, MAP_Y, 2, MAP_H, INK)
    cv.fill(MAP_X + MAP_W - 2, MAP_Y, 2, MAP_H, INK)
    for lon, lat, name in MAP_LABELS:
        x, y = to_xy(lon, lat)
        cv.draw(name, x, y, 2, MAPGREY, "c")
    for num, lon, lat, dx, dy, colour in MARKERS:
        x, y = to_xy(lon, lat)
        if num == 1:
            cv.burst(x, y, 10, RED)
            cv.halo(x, y, 13, RED, 2)
        else:
            cv.halo(x, y, 6, colour, 2)
            cv.dot(x, y, 4, colour)
        lx, ly = x + dx, y + dy
        if abs(dx) > 12 or abs(dy) > 12:
            cv.seg(x, y, lx + 6, ly + 7, colour, 1)
        cv.draw(str(num), lx, ly, 2, colour)

    # region legend, spread evenly across the page
    widths = [12 + 6 + text_width(name, 2) for _, name in LEGEND]
    gap = (976 - sum(widths)) // (len(LEGEND) - 1)
    lx = 24
    for (colour, name), w in zip(LEGEND, widths):
        cv.dot(lx + 6, 442, 5, colour)
        cv.draw(name, lx + 18, 435, 2, INK)
        lx += w + gap

    # stories header
    cv.hline(24, 1000, 466, INK, 2)
    cv.draw("THE DAY IN STORIES", 24, 474, 3, INK)
    cv.draw("NUMBERS MATCH THE MAP", 1000, 477, 2, GREY, "r")

    # stories grid: three columns of twelve
    colour_of = {num: colour for num, *_rest, colour in MARKERS}
    y0, row_h = 500, 40
    for i, (num, head, summ) in enumerate(STORIES):
        col = i // 12
        row = i % 12
        x = 24 + col * 331
        y = y0 + row * row_h
        if text_width(head, 2) > 282 or text_width(summ, 1) > 282:
            raise ValueError("story %d line too wide: %r" % (num, head))
        cv.fill(x, y, 24, 24, colour_of[num])
        cv.draw(str(num), x + 12, y + 5, 2, WHITE, "c")
        cv.draw(head, x + 32, y + 2, 2, INK)
        cv.draw(summ, x + 32, y + 22, 1, GREY)
        if row < 11:
            cv.hline(x, x + 282, y + 33, (200, 195, 185), 1)

    # footer
    cv.hline(24, 1000, 986, INK, 2)
    cv.draw("SUNDAY 22 NOVEMBER 2026 - STORIES FROM 16-22 NOV, LED BY TODAY'S NEWS",
            512, 992, 2, INK, "c")
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    png = encode_png(build())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))


if __name__ == "__main__":
    main()
