#!/usr/bin/env python3
"""news-image-20261125: one-page broadsheet summing up Wednesday 25 November 2026.

Pure Python 3 stdlib. Draws a 1024x1024 PNG with a built-in 5x7 bitmap font,
a pure-stdlib PNG encoder (zlib/struct), vector motifs, a dotted world map
with numbered pins, and a dense numbered briefs list. Deterministic: no time,
no randomness, no network, no files read. Writes /output/entry.png.
"""
import binascii
import os
import struct
import zlib
from collections import Counter

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 14 hex chars = 7 rows of 5 bits (bit 4 = leftmost pixel).
FONT = {
    'A': '0E11111F111111', 'B': '1E11111E11111E', 'C': '0F10101010100F',
    'D': '1E11111111111E', 'E': '1F10101E10101F', 'F': '1F10101E101010',
    'G': '0F10101711110E', 'H': '1111111F111111', 'I': '0E04040404040E',
    'J': '0702020202120C', 'K': '11121418141211', 'L': '1010101010101F',
    'M': '111B1515111111', 'N': '11191915131311', 'O': '0E11111111110E',
    'P': '1E11111E101010', 'Q': '0E11111115120D', 'R': '1E11111E141211',
    'S': '0F10100E01011E', 'T': '1F040404040404', 'U': '1111111111110E',
    'V': '11111111110A04', 'W': '11111115151B11', 'X': '11110A040A1111',
    'Y': '11110A04040404', 'Z': '1F01020408101F',
    '0': '0E13151911110E', '1': '040C040404040E', '2': '0E11010204081F',
    '3': '1E01010E01011E', '4': '02060A121F0202', '5': '1F101E0101110E',
    '6': '0E10101E11110E', '7': '1F010204040404', '8': '0E11110E11110E',
    '9': '0E11110F01010E',
    ' ': '00000000000000', '.': '00000000000606', ',': '00000000000604',
    ':': '00060000060000', ';': '00060000060400', '-': '0000001F000000',
    "'": '04040000000000', '!': '04040404040004', '?': '0E110102040004',
    '/': '01020204080810', '+': '0004041F040400', '%': '11120204080911',
    '$': '040F150E051E04', '&': '0C12140815120D', '(': '02040808080402',
    ')': '08040202020408', '=': '00001F001F0000', '"': '0A0A0000000000',
    '*': '000A041F040A00', '#': '0A0A1F0A1F0A0A', '@': '0E11171517100E',
    '_': '0000000000001F', '<': '02040810080402', '>': '08040201020408',
    '[': '0E08080808080E', ']': '0E02020202020E', '^': '040A0000000000',
    '~': '00000B15000000', '`': '04080000000000', '\\': '10100804020101',
    '|': '04040404040404', '{': '0604040C040406', '}': '0C04040604040C',
}

# ---------------------------------------------------------------- canvas
PAPER = (246, 241, 227)
BOX = (255, 253, 245)
INK = (20, 20, 20)
RED = (180, 35, 24)
BLUE = (29, 78, 216)
GOLD = (180, 83, 9)
GREY = (107, 114, 128)
LINE = (214, 208, 188)
MAPDOT = (88, 98, 110)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill(x, y, w, t, c)
        self.fill(x, y + h - t, w, t, c)
        self.fill(x, y, t, h, c)
        self.fill(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        if r < 1:
            self.set(cx, cy, c)
            return
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            if fill:
                self.fill(cx - dx, cy + dy, 2 * dx + 1, 1, c)
            else:
                self.set(cx - dx, cy + dy, c)
                self.set(cx + dx, cy + dy, c)

    def fill_poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            if len(xs) >= 2:
                xs.sort()
                self.fill(int(xs[0]), y, int(xs[-1]) - int(xs[0]) + 1, 1, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            g = FONT.get(ch)
            if g is None:
                g = FONT['?']
            rows = bytes.fromhex(g)
            for r in range(7):
                b = rows[r]
                for col in range(5):
                    if b >> (4 - col) & 1:
                        self.fill(cx + col * scale, y + r * scale,
                                  scale, scale, c)
            cx += 6 * scale
        return cx

    def twidth(self, s, scale):
        return len(s) * 6 * scale


def wrap(s, maxw, scale):
    lines = []
    cur = ''
    for w in s.split(' '):
        t = (cur + ' ' + w) if cur else w
        if len(t) * 6 * scale <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def centre_text(cv, cx, y, s, scale, c):
    cv.text(cx - cv.twidth(s, scale) // 2, y, s, scale, c)


# ---------------------------------------------------------------- data
# 40 stories: 3 large + 10 medium drawn features, 27 briefs.
# num, size, title, deck/brief, src, region, field, sure, icon, lon, lat.
STORIES = [
    dict(num=1, size='L', title="HORMUZ TRAFFIC COLLAPSES",
         deck="TANKER CROSSINGS DOWN OVER 40% IN NOVEMBER. ABOUT 25 TANKERS HIT "
              "BY MINES. 28 CROSSINGS A DAY, FROM 125-140 BEFORE THE WAR.",
         src="NEWS18, 25 NOV", region="Middle East", field="War",
         sure="CONFIRMED", icon="tanker", lon=58, lat=27),
    dict(num=2, size='L', title="FIRST PAKISTANI ON TIANGONG",
         deck="SHENZHOU-24 LAUNCHED 08:18 BEIJING TIME AND DOCKED 11:56. CREW: "
              "TANG HONGBO, WU YI AND MUHAMMAD ZEESHAN ALI. 90+ EXPERIMENTS PLANNED.",
         src="CHINA MANNED SPACE AGENCY", region="Asia", field="Space",
         sure="OFFICIAL", icon="rocket", lon=100, lat=41),
    dict(num=3, size='L', title="15-YEAR-OLD HITS 204 OFF 53",
         deck="VAIBHAV SOORYAVANSHI HITS THE FASTEST LIST A DOUBLE CENTURY, IN 52 "
              "BALLS, AND THE FASTEST LIST A HUNDRED, IN 28 BALLS. INDIA A VS UAE, DOHA.",
         src="INDIAN EXPRESS", region="Asia", field="Sport",
         sure="CONFIRMED", icon="cricket", lon=49, lat=20),
    dict(num=4, size='M', title="203 BATTLES IN A DAY",
         deck="203 CLASHES ON 24 NOV. POKROVSK: 28 REPELLED. 1,863 DRONES.",
         src="UKRAINE GENERAL STAFF", region="Europe", field="War",
         sure="OFFICIAL", icon="burst", lon=32, lat=50),
    dict(num=5, size='M', title="7 KILLED IN GAZA STRIKES",
         deck="7 KILLED, INCL. HAMAS SECURITY CHIEF. 1,650+ DEAD SINCE TRUCE.",
         src="AFP", region="Middle East", field="War",
         sure="CONFIRMED", icon="city", lon=36, lat=28),
    dict(num=6, size='M', title="TRUMP PARDONS 'FREEDOM'",
         deck="TRUMP RUES MIDTERM DEFEAT; CLAIMS US WOULD BE $6TN RICHER.",
         src="AP", region="North America", field="Politics",
         sure="CONFIRMED", icon="flag", lon=-80, lat=36),
    dict(num=7, size='M', title="USA TO HOST 2031 WOMEN'S CUP",
         deck="USA-LED BID WITH MEXICO, COSTA RICA, JAMAICA. FIRST 48-TEAM.",
         src="FIFA", region="North America", field="Sport",
         sure="CONFIRMED", icon="ball", lon=-100, lat=39),
    dict(num=8, size='M', title="HUAWEI GUILTY ON 10 COUNTS",
         deck="CONVICTED ON TRADE-SECRET THEFT, FRAUD, SANCTIONS EVASION.",
         src="REUTERS", region="North America", field="Law",
         sure="CONFIRMED", icon="court", lon=-72, lat=45),
    dict(num=9, size='M', title="ASIAN STOCKS PLUNGE",
         deck="KOSPI -5.3%, TAIWAN -5.1%, NIKKEI -2.9%. AI SELL-OFF SPREADS.",
         src="REUTERS", region="Asia", field="Markets",
         sure="CONFIRMED", icon="chart", lon=139, lat=36),
    dict(num=10, size='M', title="M5.1 QUAKE SHAKES PANAY",
         deck="07:29 IN ANTIQUE. INTENSITY V FELT. DAMAGE EXPECTED.",
         src="PHIVOLCS", region="Asia", field="Disaster",
         sure="OFFICIAL", icon="quake", lon=122, lat=11),
    dict(num=11, size='M', title="GUKESH DRAWS GAME 1",
         deck="DRAWS WITH SINDAROV IN 38 MOVES, BLACK. BOTH AGED 20.",
         src="FIDE", region="Europe", field="Sport",
         sure="CONFIRMED", icon="chess", lon=6, lat=46),
    dict(num=12, size='M', title="SENEGAL GET AFCON TITLE BACK",
         deck="CAS OVERTURNS CAF'S 3-0 AWARD TO MOROCCO. WON 1-0 IN JANUARY.",
         src="CAS", region="Africa", field="Sport",
         sure="CONFIRMED", icon="trophy", lon=-17, lat=15),
    dict(num=13, size='M', title="HASINA SEEKS DEC 16 RETURN",
         deck="EX-PM ASKS DHAKA FOR AIR TRANSPORT. DHAKA WANTS EXTRADITION.",
         src="INDIAN EXPRESS", region="Asia", field="Politics",
         sure="REPORTED", icon="plane", lon=90, lat=24),
    dict(num=14, size='B', brief="TRUMP: IRAN WAR FUNDS SECURE TO END-JAN (NY POST)",
         region="North America", field="Politics", sure="REPORTED"),
    dict(num=15, size='B', brief="ZAPORIZHZHIA STRIKE KILLS 2, WOUNDS 44 (AP)",
         region="Europe", field="War", sure="CONFIRMED"),
    dict(num=16, size='B', brief="ODESA STRIKE KILLS 2, INCLUDING BOY, 17 (AP)",
         region="Europe", field="War", sure="CONFIRMED"),
    dict(num=17, size='B', brief="RUSSIA DEFENCE UP 27% TO 17.1TN RBL (REUTERS)",
         region="Europe", field="Economy", sure="CONFIRMED"),
    dict(num=18, size='B', brief="HAMAS TO RETURN 4 HOSTAGE BODIES; RAFAH SHUT (AP)",
         region="Middle East", field="War", sure="CONFIRMED"),
    dict(num=19, size='B', brief="HOUTHI THREAT TO JEDDAH; HODEIDAH EMPTIES (AP)",
         region="Middle East", field="War", sure="CONFIRMED"),
    dict(num=20, size='B', brief="RUSSIAN DRONE ENTERS POLISH AIRSPACE (REUTERS)",
         region="Europe", field="War", sure="CONFIRMED"),
    dict(num=21, size='B', brief="MAGYAR MEETS ZELENSKY IN UZHHOROD (AP)",
         region="Europe", field="Diplomacy", sure="CONFIRMED"),
    dict(num=22, size='B', brief="EU PROPOSES 22ND RUSSIA SANCTIONS (REUTERS)",
         region="Europe", field="Diplomacy", sure="CONFIRMED"),
    dict(num=23, size='B', brief="EU TO LEND KYIV EUR45BN IN 2027 (REUTERS)",
         region="Europe", field="Economy", sure="CONFIRMED"),
    dict(num=24, size='B', brief="UK-UKRAINE SIGN ATTACK-DRONE DEAL (REUTERS)",
         region="Europe", field="Defence", sure="CONFIRMED"),
    dict(num=25, size='B', brief="GERMANY TO SPEND EUR4BN+ ON PATRIOTS (REUTERS)",
         region="Europe", field="Defence", sure="REPORTED"),
    dict(num=26, size='B', brief="NORWAY PLEDGES AT LEAST $7BN TO UKRAINE (REUTERS)",
         region="Europe", field="Diplomacy", sure="REPORTED"),
    dict(num=27, size='B', brief="DALAI LAMA OFFICE GETS DELHI BUNGALOW (EXPRESS)",
         region="Asia", field="Politics", sure="CONFIRMED"),
    dict(num=28, size='B', brief="INDIA: HUMAN OVERSIGHT FOR AI WARFARE (PTI)",
         region="Asia", field="Defence", sure="REPORTED"),
    dict(num=29, size='B', brief="TRUMP: US MAY STILL BUY NVIDIA STAKE (REUTERS)",
         region="North America", field="Business", sure="REPORTED"),
    dict(num=30, size='B', brief="HUANG REINSTATED AS NVIDIA CEO (REUTERS)",
         region="North America", field="Business", sure="CONFIRMED"),
    dict(num=31, size='B', brief="MEDAL OF FREEDOM FOR GIULIANI, CARSON (AP)",
         region="North America", field="Politics", sure="CONFIRMED"),
    dict(num=32, size='B', brief="TRUMP WEIGHS TARIFFS ON INDIA, CHINA +14 (WSJ)",
         region="North America", field="Trade", sure="REPORTED"),
    dict(num=33, size='B', brief="CIA AND ODNI HIT BY CYBER BREACH (NYT)",
         region="North America", field="Security", sure="REPORTED"),
    dict(num=34, size='B', brief="ABREGO GARCIA LEAVES US FOR SPAIN (AP)",
         region="North America", field="Immigration", sure="CONFIRMED"),
    dict(num=35, size='B', brief="TOP EU COURT BACKS MIGRANT PUSHBACKS (REUTERS)",
         region="Europe", field="Law", sure="CONFIRMED"),
    dict(num=36, size='B', brief="HANOI HOT POT BLAST KILLS 7, INJURES 9 (AP)",
         region="Asia", field="Disaster", sure="CONFIRMED"),
    dict(num=37, size='B', brief="BUS CRASH IN RAK KILLS 13 (GULF NEWS)",
         region="Middle East", field="Disaster", sure="REPORTED"),
    dict(num=38, size='B', brief="SENEGAL NAVY RESCUES 974 MIGRANTS (UNHCR)",
         region="Africa", field="Migration", sure="CONFIRMED"),
    dict(num=39, size='B', brief="NVIDIA -5.9% AFTER +31.5% SURGE (REUTERS)",
         region="North America", field="Markets", sure="CONFIRMED"),
    dict(num=40, size='B', brief="DOW 50,018.70; S&P -0.5%; NASDAQ -1.5% (REUTERS)",
         region="North America", field="Markets", sure="CONFIRMED"),
]

NUMBERS = [
    ("203", "COMBAT CLASHES IN UKRAINE IN ONE DAY"),
    ("~25", "TANKERS HIT IN THE STRAIT OF HORMUZ"),
    ("974", "MIGRANTS RESCUED OFF SENEGAL"),
    ("204", "RUNS OFF 53 BALLS, AGE 15"),
    ("17.1TN", "ROUBLES: RUSSIA'S 2027 DEFENCE BUDGET"),
    ("90+", "SCIENCE EXPERIMENTS ON SHENZHOU-24"),
]

DATE_CHECK = [
    "INDIA-NEPAL RS 15,000 CR PACKAGE: 23 NOV",
    "CHEN JINING PROBE: ANNOUNCED 24 NOV",
    "EU SUMMIT ON UKRAINE: 26-27 NOV, NOT YET HELD",
    "US OCT PCE + Q3 GDP: NOT YET RELEASED",
    "IPL 2027 AUCTION: 16 DEC, STOKES SIGNS UP",
    "G20 SUMMIT: DECEMBER, NOT TODAY",
]

# Rough continent ellipses (lon centre, lat centre, lon radius, lat radius).
LAND = [
    (-100, 48, 28, 14), (-88, 30, 18, 10), (-155, 63, 12, 6),
    (-95, 18, 8, 5), (-42, 74, 10, 6),
    (-60, -10, 12, 14), (-65, -30, 8, 12),
    (18, 5, 18, 14), (25, -18, 10, 12), (45, 10, 6, 6),
    (12, 52, 14, 8), (22, 60, 8, 6), (-2, 40, 6, 5),
    (60, 55, 30, 12), (90, 45, 20, 12), (105, 25, 12, 10),
    (78, 21, 8, 8), (122, 30, 10, 8), (140, 36, 5, 8),
    (100, 12, 6, 7), (115, -2, 10, 6), (138, -25, 12, 8),
    (172, -41, 4, 5),
]


def on_land(lon, lat):
    for cx, cy, rx, ry in LAND:
        if ((lon - cx) / rx) ** 2 + ((lat - cy) / ry) ** 2 <= 1.0:
            return True
    return False


# ---------------------------------------------------------------- motifs
def draw_motif(cv, kind, x, y, w, h, c, acc):
    """Vector pictogram in the box (x, y, w, h); coords are fractions."""
    def X(f):
        return x + int(f * w)

    def Y(f):
        return y + int(f * h)

    def R(fx, fy, fw, fh):
        cv.fill(X(fx), Y(fy), max(1, int(fw * w)), max(1, int(fh * h)), c)

    def Ln(p, q, col=None):
        cv.line(X(p[0]), Y(p[1]), X(q[0]), Y(q[1]), col or c)

    def Poly(pts, col=None):
        cv.fill_poly([(X(a), Y(b)) for a, b in pts], col or c)

    def Circ(fx, fy, fr, col=None, fill=True):
        cv.circle(X(fx), Y(fy), max(1, int(fr * min(w, h))), col or c, fill)

    if kind == 'tanker':
        Poly([(0.10, 0.45), (0.90, 0.45), (0.82, 0.75), (0.18, 0.75)])
        R(0.20, 0.28, 0.45, 0.17)
        R(0.68, 0.20, 0.10, 0.25, )
        cv.fill(X(0.68), Y(0.20), max(1, int(0.10 * w)), max(1, int(0.08 * h)), acc)
        Ln((0.30, 0.08), (0.30, 0.28))
        Ln((0.05, 0.86), (0.95, 0.86))
        Ln((0.10, 0.94), (0.90, 0.94))
    elif kind == 'rocket':
        R(0.30, 0.35, 0.45, 0.30)
        Poly([(0.75, 0.35), (0.75, 0.65), (0.96, 0.50)])
        Poly([(0.30, 0.38), (0.30, 0.62), (0.06, 0.50)], acc)
        Poly([(0.35, 0.65), (0.45, 0.65), (0.38, 0.86)])
        Poly([(0.35, 0.35), (0.45, 0.35), (0.38, 0.14)])
        Circ(0.55, 0.50, 0.09, BOX)
        Ln((0.12, 0.12), (0.18, 0.12))
        Ln((0.15, 0.09), (0.15, 0.15))
        Ln((0.86, 0.10), (0.92, 0.10))
        Ln((0.89, 0.07), (0.89, 0.13))
    elif kind == 'cricket':
        Poly([(0.22, 0.88), (0.30, 0.82), (0.58, 0.12), (0.52, 0.08)])
        Circ(0.80, 0.25, 0.09, acc)
        for fx in (0.10, 0.15, 0.20):
            cv.fill(X(fx), Y(0.55), 2, Y(0.92) - Y(0.55), c)
        Ln((0.10, 0.53), (0.22, 0.53))
    elif kind == 'burst':
        import math
        cx, cy = X(0.50), Y(0.50)
        for k in range(10):
            a = math.radians(k * 36)
            r = 0.44 if k % 2 == 0 else 0.28
            cv.line(cx, cy, cx + int(math.cos(a) * r * w),
                    cy + int(math.sin(a) * r * h), c)
        Circ(0.50, 0.50, 0.09, acc)
        Circ(0.50, 0.50, 0.04, BOX)
    elif kind == 'city':
        for fx, fy, fw, fh in [(0.05, 0.45, 0.14, 0.45), (0.22, 0.30, 0.14, 0.60),
                               (0.39, 0.50, 0.14, 0.40), (0.56, 0.35, 0.14, 0.55),
                               (0.73, 0.48, 0.14, 0.42), (0.88, 0.60, 0.08, 0.30)]:
            R(fx, fy, fw, fh)
        Circ(0.85, 0.15, 0.08, GOLD)
        Ln((0.02, 0.92), (0.98, 0.92))
    elif kind == 'flag':
        Ln((0.25, 0.05), (0.25, 0.85))
        R(0.25, 0.08, 0.42, 0.24)
        cv.fill(X(0.25), Y(0.08), max(1, int(0.42 * w)), max(1, int(0.24 * h)), acc)
        Ln((0.38, 0.14), (0.54, 0.14))
        Ln((0.46, 0.10), (0.46, 0.18))
        Ln((0.10, 0.90), (0.90, 0.90))
    elif kind == 'ball':
        r = int(min(w, h) * 0.34)
        cv.circle(X(0.50), Y(0.50), r, c, fill=False)
        cv.circle(X(0.50), Y(0.50), r - 1, c, fill=False)
        import math
        for k in range(5):
            a = math.radians(90 + k * 72)
            ex = X(0.50) + int(math.cos(a) * r * 0.95)
            ey = Y(0.50) + int(math.sin(a) * r * 0.95)
            cv.line(X(0.50), Y(0.50), ex, ey, c)
        Circ(0.50, 0.50, 0.10, c)
    elif kind == 'court':
        Poly([(0.08, 0.35), (0.92, 0.35), (0.50, 0.06)])
        for fx in (0.18, 0.46, 0.74):
            R(fx, 0.40, 0.08, 0.46)
        R(0.08, 0.88, 0.84, 0.08)
        R(0.46, 0.60, 0.08, 0.26)
        cv.fill(X(0.46), Y(0.60), max(1, int(0.08 * w)), max(1, int(0.26 * h)), BOX)
    elif kind == 'chart':
        Ln((0.10, 0.90), (0.10, 0.08))
        Ln((0.10, 0.90), (0.94, 0.90))
        pts = [(0.15, 0.28), (0.32, 0.42), (0.50, 0.36), (0.68, 0.62), (0.88, 0.80)]
        for a, b in zip(pts, pts[1:]):
            Ln(a, b, acc)
            cv.line(X(a[0]), Y(a[1]) + 1, X(b[0]), Y(b[1]) + 1, acc)
        Poly([(0.88, 0.80), (0.80, 0.78), (0.86, 0.68)], acc)
    elif kind == 'quake':
        pts = [(0.02, 0.55), (0.18, 0.55), (0.28, 0.12), (0.38, 0.90),
               (0.48, 0.30), (0.58, 0.70), (0.68, 0.55), (0.98, 0.55)]
        for a, b in zip(pts, pts[1:]):
            Ln(a, b)
    elif kind == 'chess':
        # Board and pawn sized from box height so they cannot spill
        # into the headline below the motif strip.
        sq = max(2, int(0.30 * h))
        for r in range(2):
            for col in range(4):
                if (r + col) % 2 == 0:
                    cv.fill(X(0.06) + col * sq, Y(0.15) + r * sq, sq, sq, c)
        cv.rect(X(0.06), Y(0.15), 4 * sq, 2 * sq, c)
        Circ(0.74, 0.30, 0.13, c)
        R(0.67, 0.48, 0.14, 0.34)
        R(0.63, 0.82, 0.22, 0.08)
    elif kind == 'trophy':
        Poly([(0.38, 0.14), (0.62, 0.14), (0.58, 0.50), (0.42, 0.50)])
        Ln((0.38, 0.20), (0.28, 0.34))
        Ln((0.28, 0.34), (0.38, 0.44))
        Ln((0.62, 0.20), (0.72, 0.34))
        Ln((0.72, 0.34), (0.62, 0.44))
        R(0.47, 0.50, 0.06, 0.18)
        R(0.38, 0.68, 0.24, 0.10)
        Ln((0.47, 0.04), (0.53, 0.04))
        Ln((0.50, 0.01), (0.50, 0.07))
    elif kind == 'plane':
        R(0.15, 0.42, 0.55, 0.14)
        Poly([(0.70, 0.42), (0.70, 0.56), (0.92, 0.49)])
        Poly([(0.38, 0.42), (0.52, 0.42), (0.44, 0.10)])
        Poly([(0.38, 0.56), (0.52, 0.56), (0.44, 0.88)])
        Poly([(0.15, 0.42), (0.24, 0.42), (0.16, 0.20)])
        for fx in (0.30, 0.40, 0.50, 0.60):
            Circ(fx, 0.49, 0.03, BOX)


# ---------------------------------------------------------------- png
def png_bytes(w, h, px):
    raw = b''.join(b'\x00' + bytes(px[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))
    comp = zlib.compress(raw, 9)

    def chunk(t, data):
        c = struct.pack('>I', len(data)) + t + data
        return c + struct.pack('>I', binascii.crc32(t + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', comp) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- build
def badge(cv, x, y, size, num, scale):
    cv.fill(x, y, size, size, RED)
    s = str(num)
    cv.text(x + (size - cv.twidth(s, scale)) // 2,
            y + (size - 7 * scale) // 2, s, scale, BOX)


def main():
    W = H = 1024
    cv = Canvas(W, H, PAPER)
    drawn = [s for s in STORIES if s['size'] in ('L', 'M')]
    briefs = [s for s in STORIES if s['size'] == 'B']
    regions = Counter(s['region'] for s in STORIES)
    fields = Counter(s['field'] for s in STORIES)

    # ---- masthead
    cv.fill(8, 8, 1008, 88, INK)
    centre_text(cv, 512, 16, "THE WORLD IN ONE DAY", 5, BOX)
    centre_text(cv, 512, 58, "WEDNESDAY 25 NOVEMBER 2026", 2, BOX)
    spec = ("%d STORIES - %d REGIONS - %d FIELDS - %d DRAWN SCENES - VERIFIED"
            % (len(STORIES), len(regions), len(fields), len(drawn)))
    centre_text(cv, 512, 82, spec, 1, GOLD)
    cv.fill(16, 102, 992, 2, INK)

    # ---- by the numbers
    for i, (big, label) in enumerate(NUMBERS):
        x = 16 + i * 165
        centre_text(cv, x + 82, 112, big, 3, RED)
        for j, ln in enumerate(wrap(label, 158, 1)):
            centre_text(cv, x + 82, 138 + j * 9, ln, 1, INK)
        if i:
            cv.fill(x, 112, 1, 46, LINE)
    cv.fill(16, 164, 992, 1, LINE)

    # ---- by field / by region strips
    fparts = ["%s %d" % (f.upper(), n)
              for f, n in sorted(fields.items(), key=lambda kv: (-kv[1], kv[0]))]
    flines = wrap("BY FIELD: " + " - ".join(fparts), 992, 1)
    for j, ln in enumerate(flines):
        cv.text(16, 172 + j * 9, ln, 1, INK)
    rparts = ["%s %d" % (r.upper(), n)
              for r, n in sorted(regions.items(), key=lambda kv: (-kv[1], kv[0]))]
    cv.text(16, 172 + len(flines) * 9 + 2,
            "BY REGION: " + " - ".join(rparts), 1, BLUE)
    cv.fill(16, 204, 992, 1, LINE)

    # ---- lead story (large 1)
    s = drawn[0]
    cv.fill(16, 212, 992, 112, BOX)
    cv.rect(16, 212, 992, 112, INK, 2)
    draw_motif(cv, s['icon'], 30, 224, 160, 88, INK, RED)
    badge(cv, 208, 220, 26, 1, 2)
    cv.text(242, 223, "WAR IN THE GULF - THE OIL ROUTE CHOKED", 1, RED)
    cv.text(242, 234, s['title'], 3, INK)
    cv.fill(242, 260, cv.twidth(s['title'], 3), 3, RED)
    for j, ln in enumerate(wrap(s['deck'], 748, 1)):
        cv.text(242, 268 + j * 9, ln, 1, INK)
    cv.text(242, 296, "SOURCE: %s - %s" % (s['src'], s['sure']), 1, GREY)
    cv.text(242, 308, "%s - %s" % (s['region'].upper(), s['field'].upper()), 1, INK)

    # ---- large 2 and 3
    for k, s in enumerate(drawn[1:3]):
        bx = 16 + k * 504
        cv.fill(bx, 332, 488, 108, BOX)
        cv.rect(bx, 332, 488, 108, INK, 2)
        draw_motif(cv, s['icon'], bx + 8, 362, 108, 68, INK, RED)
        badge(cv, bx + 8, 340, 18, s['num'], 1)
        cv.text(bx + 126, 344, s['title'], 2, INK)
        cv.fill(bx + 126, 362, cv.twidth(s['title'], 2), 2, RED)
        for j, ln in enumerate(wrap(s['deck'], 350, 1)):
            cv.text(bx + 126, 370 + j * 9, ln, 1, INK)
        cv.text(bx + 126, 424, "SOURCE: %s - %s" % (s['src'], s['sure']), 1, GREY)

    # ---- medium features, 5 x 2
    for i, s in enumerate(drawn[3:]):
        col, row = i % 5, i // 5
        x = 16 + col * 199
        y = 448 + row * 112
        cv.fill(x, y, 195, 108, BOX)
        cv.rect(x, y, 195, 108, INK)
        draw_motif(cv, s['icon'], x + 8, y + 5, 179, 30, INK, RED)
        badge(cv, x + 8, y + 5, 16, s['num'], 1)
        hl = wrap(s['title'], 183, 2)
        for j, ln in enumerate(hl[:2]):
            cv.text(x + 6, y + 40 + j * 15, ln, 2, INK)
        for j, ln in enumerate(wrap(s['deck'], 183, 1)[:3]):
            cv.text(x + 6, y + 74 + j * 8, ln, 1, INK)
        cv.text(x + 6, y + 100, "SOURCE: %s" % s['src'], 1, GREY)

    # ---- world map + date check
    cv.text(16, 676, "WHERE IT HAPPENED - 13 DRAWN STORIES PINNED", 1, INK)
    cv.rect(16, 686, 624, 120, INK)
    mx0, my0, mw, mh = 16, 686, 624, 120
    for lon in range(-180, 178, 3):
        for lat in range(78, -58, -3):
            if on_land(lon, lat):
                px = mx0 + int((lon + 180) * mw / 360)
                py = my0 + int((78 - lat) * mh / 135)
                cv.fill(px, py, 2, 2, MAPDOT)
    for s in drawn:
        px = mx0 + int((s['lon'] + 180) * mw / 360)
        py = my0 + int((78 - s['lat']) * mh / 135)
        cv.circle(px, py, 7, RED)
        cv.circle(px, py, 7, BOX, fill=False)
        num = str(s['num'])
        cv.text(px - cv.twidth(num, 1) // 2, py - 3, num, 1, BOX)
    cv.fill(656, 686, 352, 120, BOX)
    cv.rect(656, 686, 352, 120, RED, 2)
    cv.text(668, 694, "DATE CHECK - LEFT OUT ON PURPOSE", 1, RED)
    for j, ln in enumerate(DATE_CHECK):
        cv.text(668, 708 + j * 14, "- " + ln, 1, INK)
    cv.text(668, 796, "ALL OTHER STORIES ARE 25 NOV 2026.", 1, GREY)

    # ---- briefs
    cv.text(16, 814, "THE DAY IN BRIEF - %d MORE STORIES" % len(briefs), 1, INK)
    cv.fill(16, 824, 992, 1, INK)
    for i, s in enumerate(briefs):
        col, row = i // 9, i % 9
        x = 16 + col * 328
        y = 832 + row * 16
        num = str(s['num'])
        cv.text(x, y, num, 1, RED)
        cv.text(x + cv.twidth(num + " ", 1), y, s['brief'], 1, INK)

    # ---- footer
    cv.fill(16, 972, 992, 2, INK)
    cv.text(16, 980, "HOW SURE: CONFIRMED = 2+ OUTLETS - OFFICIAL = THE BODY ITSELF "
                     "- REPORTED = ONE OUTLET - CLAIM = ONE SIDE - FORECAST = EXPECTED",
            1, INK)
    cv.text(16, 994, "SOURCES: NEWS18 - REUTERS - AP - AFP - NYT - WSJ - XINHUA - "
                     "PHIVOLCS - USGS - UKRAINE GENERAL STAFF - FIFA - CAS - FIDE - "
                     "INDIAN EXPRESS - PTI - UNHCR - GULF NEWS", 1, GREY)
    cv.text(16, 1008, "COMPILED ON WEDNESDAY 25 NOVEMBER 2026 FROM THE SOURCES ABOVE. "
                      "EVERY STORY IS DATED 25 NOVEMBER 2026 UNLESS MARKED IN DATE CHECK.",
            1, GREY)

    out = os.environ.get('MAKEFUN_OUT', '/output/entry.png')
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    data = png_bytes(W, H, cv.px)
    with open(out, 'wb') as f:
        f.write(data)
    print("wrote %s %d bytes %dx%d" % (out, len(data), W, H))


if __name__ == '__main__':
    main()
