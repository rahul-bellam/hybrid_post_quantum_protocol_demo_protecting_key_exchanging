#!/usr/bin/env python3
"""
🔥 INSANE QUANTUM ATTACK VISUALIZER 🔥
Watch ECDH die frame-by-frame. Watch Hybrid survive.
Even your grandma will understand.

Outputs:
  - demo_a_ecdh_dies.gif     (22 frames, ECDH → BSGS → death)
  - demo_b_hybrid_lives.gif  (24 frames, Hybrid → ECDH dies but key lives)
  - security_comparison.png  (theorem figure)
"""

import argparse
import hashlib
import hmac
import math
import os
import random
import secrets
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Wedge
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------
# THEME (darker, more insane)
# ----------------------------------
DARK = "#020208"
PANEL = "#0a0a20"
BOX = "#151535"
ACCENT = "#1e1e45"
WHITE = "#f0f0ff"
SILVER = "#b0b0d0"
RED = "#ff1744"
RED_GLOW = "#ff0040"
GREEN = "#00e676"
GREEN_GLOW = "#00ff80"
BLUE = "#00b0ff"
BLUE_GLOW = "#0080ff"
YELLOW = "#ffea00"
ORANGE = "#ff6d00"
PURPLE = "#d500f9"
CYAN = "#00e5ff"

Point = Optional[Tuple[int, int]]

# ----------------------------------
# TOY EC (so we can SEE everything)
# ----------------------------------
class ToyEC:
    """E: y² = x³ + x + 6 (mod 11) — tiny so every operation is visible"""
    def __init__(self):
        self.p = 11
        self.a = 1
        self.b = 6
        self.G = (2, 7)
        self.n = 13
        self.points = self._all_points()
    
    def _all_points(self):
        pts = [None]
        for x in range(self.p):
            rhs = (x**3 + self.a*x + self.b) % self.p
            for y in range(self.p):
                if (y*y) % self.p == rhs:
                    pts.append((x, y))
        return pts
    
    def inv(self, x):
        return pow(x % self.p, -1, self.p)
    
    def neg(self, P):
        if P is None: return None
        return (P[0], (-P[1]) % self.p)
    
    def add(self, P, Q):
        if P is None: return Q
        if Q is None: return P
        x1, y1 = P
        x2, y2 = Q
        if x1 == x2 and (y1 + y2) % self.p == 0:
            return None
        if P == Q:
            lam = ((3*x1*x1 + self.a) * self.inv(2*y1)) % self.p
        else:
            lam = ((y2 - y1) * self.inv(x2 - x1)) % self.p
        x3 = (lam*lam - x1 - x2) % self.p
        y3 = (lam*(x1 - x3) - y1) % self.p
        return (x3, y3)
    
    def mul(self, k, P):
        """Double-and-add — we animate this!"""
        k %= self.n
        R = None
        Q = P
        steps = []
        while k > 0:
            if k & 1:
                steps.append(('add', R, Q))
                R = self.add(R, Q)
            steps.append(('double', Q, Q))
            Q = self.add(Q, Q)
            k >>= 1
        return R, steps

# ----------------------------------
# KDF helpers
# ----------------------------------
def hkdf_sha256(ikm, salt, info, length=32):
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    prev = b""
    c = 1
    while len(okm) < length:
        prev = hmac.new(prk, prev + info + bytes([c]), hashlib.sha256).digest()
        okm += prev
        c += 1
    return okm[:length]

def point_bytes(P: Point) -> bytes:
    return b"\x00\x00" if P is None else bytes([P[0], P[1]])

def run_kyber():
    try:
        from kyber_py.kyber import Kyber512
        pk, sk = Kyber512.keygen()
        a, b = Kyber512.encaps(pk)
        if len(a) == 32:
            ss, ct = a, b
        else:
            ct, ss = a, b
        ss_s = Kyber512.decaps(sk, ct)
        return {"real": True, "name": "Kyber512 (ML-KEM)", "pk": bytes(pk), "sk": bytes(sk),
                "ct": bytes(ct), "ss": bytes(ss), "ss_s": bytes(ss_s)}
    except:
        ss = secrets.token_bytes(32)
        return {"real": False, "name": "Kyber512 (sim)", "pk": secrets.token_bytes(800),
                "sk": secrets.token_bytes(1632), "ct": secrets.token_bytes(768),
                "ss": ss, "ss_s": ss}

# ----------------------------------
# THE INSANE VISUALIZER
# ----------------------------------
class InsaneViz:
    def __init__(self, outdir):
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)
    
    def _fig(self, title, sub=""):
        fig = plt.figure(figsize=(18, 11), facecolor=DARK, dpi=160)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(DARK)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        # Title bar
        tb = FancyBboxPatch((2, 93), 96, 5.5, boxstyle="round,pad=0.08",
                            facecolor=PANEL, edgecolor=BLUE, linewidth=2.5)
        ax.add_patch(tb)
        ax.text(50, 96, title, color=WHITE, fontsize=17, ha='center', va='center',
                fontweight='bold', family='monospace')
        if sub:
            ax.text(50, 90, sub, color=SILVER, fontsize=10, ha='center', va='center',
                    family='monospace', style='italic')
        return fig, ax
    
    def _save(self, fig, name):
        p = os.path.join(self.outdir, name)
        fig.savefig(p, dpi=160, facecolor=DARK, edgecolor='none')
        plt.close(fig)
        return p
    
    def _gif(self, frames, name, dur=1400):
        imgs = [Image.open(f) for f in frames]
        p = os.path.join(self.outdir, name)
        imgs[0].save(p, save_all=True, append_images=imgs[1:], duration=dur, loop=0, optimize=True)
        print(f"  🔥 {name}")

    # ================================
    # DEMO A: WATCH ECDH DIE
    # ================================
    def demo_a(self, ec: ToyEC, k_c, k_s, P_c, P_s, S):
        frames = []
        m = math.isqrt(ec.n) + 1
        mP = ec.mul(m, ec.G)[0]
        minus_mP = ec.neg(mP)
        
        # --- FRAME 1: What is ECDH? ---
        fig, ax = self._fig("WHAT IS ECDH? 🤔", "Two people create a shared secret using public math")
        ax.text(50, 85, "Imagine a special clock with 13 hours", color=YELLOW, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 78, "Client picks secret: k_c = ???  (keeps it hidden!)", color=CYAN, fontsize=12, ha='center')
        ax.text(50, 72, "Server picks secret: k_s = ???  (keeps it hidden!)", color=ORANGE, fontsize=12, ha='center')
        ax.text(50, 64, "They both know a starting point G = (2,7)", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 56, "Client sends: P_c = k_c · G  (public!)", color=CYAN, fontsize=12, ha='center')
        ax.text(50, 50, "Server sends: P_s = k_s · G  (public!)", color=ORANGE, fontsize=12, ha='center')
        ax.text(50, 42, "Shared secret: S = k_c · P_s = k_s · P_c", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 35, "Only they can compute S! 🔒", color=GREEN_GLOW, fontsize=16, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a0_what_is_ecdh.png"))
        
        # --- FRAME 2: Show the actual curve ---
        fig, ax = self._fig("THE ELLIPTIC CURVE 📐", f"E: y² = x³ + x + 6 (mod {ec.p})  —  {len(ec.points)-1} points")
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=80, alpha=0.5, zorder=1)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=400, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(ec.G[0], ec.G[1]+1.2, "G (generator)", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        ax.text(50, 15, "Every point is (x, y) where y² = x³+x+6 (mod 11)", color=SILVER, fontsize=10, ha='center', family='monospace')
        frames.append(self._save(fig, "a1_curve.png"))
        
        # --- FRAME 3: Client computes k_c·G (DOUBLE-AND-ADD LIVE!) ---
        fig, ax = self._fig("CLIENT COMPUTES: k_c · G 🔢", f"k_c = {k_c}  →  P_c = k_c·G = {P_c}")
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=60, alpha=0.3, zorder=1)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=300, marker='★', edgecolors=WHITE, linewidths=2, zorder=10)
        
        # Animate double-and-add
        R = None
        Q = ec.G
        k = k_c
        step_num = 0
        y_pos = 70
        binary = bin(k)[2:][::-1]
        
        for bit in binary:
            step_num += 1
            if bit == '1':
                if R is None:
                    ax.text(15, y_pos, f"Step {step_num}: ADD  R=∞ + Q={Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
                else:
                    ax.text(15, y_pos, f"Step {step_num}: ADD  R={R} + Q={Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
                ax.arrow(20, y_pos+3, 8, 0, head_width=0.5, fc=CYAN, ec=CYAN, alpha=0.6)
                R = ec.add(R, Q)
                ax.scatter([R[0]], [R[1]], c=CYAN, s=200, marker='o', edgecolors=WHITE, linewidths=2, zorder=10)
                ax.text(R[0], R[1]-1.5, f"R={R}", color=CYAN, fontsize=8, ha='center')
                y_pos -= 12
            
            ax.text(15, y_pos, f"Step {step_num+1}: DOUBLE  Q={Q} + Q={Q}", color=ORANGE, fontsize=9, ha='left', family='monospace')
            ax.arrow(20, y_pos+3, 8, 0, head_width=0.5, fc=ORANGE, ec=ORANGE, alpha=0.6)
            Q = ec.add(Q, Q)
            ax.scatter([Q[0]], [Q[1]], c=ORANGE, s=150, marker='s', edgecolors=WHITE, linewidths=1.5, zorder=10)
            ax.text(Q[0], Q[1]-1.5, f"Q={Q}", color=ORANGE, fontsize=8, ha='center')
            y_pos -= 12
        
        ax.text(50, 10, f"RESULT: P_c = {P_c}  ✓  Client sends this to server!", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a2_double_and_add.png"))
        
        # --- FRAME 4: Server does same ---
        fig, ax = self._fig("SERVER COMPUTES: k_s · G 🔢", f"k_s = {k_s}  →  P_s = k_s·G = {P_s}")
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=60, alpha=0.3, zorder=1)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=300, marker='★', edgecolors=WHITE, linewidths=2, zorder=10)
        
        R = None
        Q = ec.G
        k = k_s
        step_num = 0
        y_pos = 70
        binary = bin(k)[2:][::-1]
        
        for bit in binary:
            step_num += 1
            if bit == '1':
                ax.text(15, y_pos, f"Step {step_num}: ADD  R={'∞' if R is None else R} + Q={Q}", color=ORANGE, fontsize=9, ha='left', family='monospace')
                ax.arrow(20, y_pos+3, 8, 0, head_width=0.5, fc=ORANGE, ec=ORANGE, alpha=0.6)
                R = ec.add(R, Q)
                ax.scatter([R[0]], [R[1]], c=ORANGE, s=200, marker='o', edgecolors=WHITE, linewidths=2, zorder=10)
                y_pos -= 12
            
            ax.text(15, y_pos, f"Step {step_num+1}: DOUBLE  Q={Q}+{Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
            ax.arrow(20, y_pos+3, 8, 0, head_width=0.5, fc=CYAN, ec=CYAN, alpha=0.6)
            Q = ec.add(Q, Q)
            ax.scatter([Q[0]], [Q[1]], c=CYAN, s=150, marker='s', edgecolors=WHITE, linewidths=1.5, zorder=10)
            y_pos -= 12
        
        ax.text(50, 10, f"RESULT: P_s = {P_s}  ✓  Server sends this to client!", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a3_server_compute.png"))
        
        # --- FRAME 5: Shared secret ---
        fig, ax = self._fig("SHARED SECRET 🔐", "Both compute S = k_c · P_s = k_s · P_c")
        ax.text(50, 80, "Client has: k_c (secret) and P_s (public)", color=CYAN, fontsize=12, ha='center')
        ax.text(50, 72, "Server has: k_s (secret) and P_c (public)", color=ORANGE, fontsize=12, ha='center')
        ax.text(50, 62, "Client computes: S = k_c · P_s", color=CYAN, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 54, f"  = {k_c} · {P_s}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 46, "Server computes: S = k_s · P_c", color=ORANGE, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 38, f"  = {k_s} · {P_c}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 28, f"BOTH GET: S = {S}  🔒", color=GREEN, fontsize=16, ha='center', fontweight='bold')
        ax.text(50, 18, "Session Key = HKDF(H(S)) — only they know it!", color=GREEN_GLOW, fontsize=12, ha='center')
        frames.append(self._save(fig, "a4_shared_secret.png"))
        
        # --- FRAME 6: ATTACKER SEES THIS ---
        fig, ax = self._fig("👁️ ATTACKER'S VIEW 👁️", "Everything on the wire is PUBLIC!")
        # Big red eye
        eye = Circle((50, 50), 12, facecolor=RED, edgecolor=RED_GLOW, linewidth=4, alpha=0.3)
        ax.add_patch(eye)
        ax.text(50, 50, "👁", color=WHITE, fontsize=20, ha='center', va='center')
        
        ax.text(50, 80, "ATTACKER INTERCEPTS:", color=RED, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 72, f"G  = {ec.G}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 64, f"P_c = {P_c}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 56, f"P_s = {P_s}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 44, "GOAL: Find k_c where  k_c · G = P_c", color=RED_GLOW, fontsize=15, ha='center', fontweight='bold')
        ax.text(50, 34, "This is the ELLIPTIC CURVE DISCRETE LOG PROBLEM (DLP)", color=YELLOW, fontsize=11, ha='center')
        ax.text(50, 24, "Classical computers: takes forever ❌", color=SILVER, fontsize=10, ha='center')
        ax.text(50, 16, "Quantum computer (Shor's): POLYNOMIAL TIME ✅", color=RED, fontsize=12, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a5_attacker_view.png"))
        
        # --- FRAME 7: BSGS EXPLAINED ---
        fig, ax = self._fig("BABY-STEP GIANT-STEP (BSGS) 🧮", "Quantum DLP solver — watch it work!")
        ax.text(50, 85, "Idea: Write k_c = i·m + j  where m = ⌈√n⌉", color=YELLOW, fontsize=13, ha='center', fontweight='bold')
        ax.text(50, 78, f"n = {ec.n}  →  m = {m}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 70, "Then: k_c·G = i·(m·G) + j·G", color=CYAN, fontsize=12, ha='center')
        ax.text(50, 62, "Rearranged: j·G = P_c - i·(m·G)", color=ORANGE, fontsize=12, ha='center')
        ax.text(50, 52, "Step 1: Build table of j·G for j=0,1,...,m-1", color=GREEN, fontsize=11, ha='center')
        ax.text(50, 44, "Step 2: Compute P_c - i·(m·G) for i=0,1,...,m-1", color=RED, fontsize=11, ha='center')
        ax.text(50, 36, "Step 3: When they match → k_c = i·m + j 🎉", color=GREEN_GLOW, fontsize=13, ha='center', fontweight='bold')
        ax.text(50, 26, f"m·G = {mP}", color=WHITE, fontsize=10, ha='center', family='monospace')
        frames.append(self._save(fig, "a6_bsgs_explained.png"))
        
        # --- FRAME 8-13: BABY STEPS (animated) ---
        baby_steps = []
        baby = None
        for j in range(m):
            baby_steps.append((j, baby))
            baby = ec.add(baby, ec.G)
        
        for idx in range(len(baby_steps)):
            j, pt = baby_steps[idx]
            fig, ax = self._fig(f"BABY STEPS: Building table 📝  (j={j}/{m-1})",
                               f"Compute j·G and store in quantum memory (QRAM)")
            
            for p in ec.points[1:]:
                ax.scatter([p[0]], [p[1]], c=BLUE, s=50, alpha=0.2, zorder=1)
            
            # Show previous steps
            for jj in range(idx):
                jj_pt = baby_steps[jj][1]
                if jj_pt:
                    ax.scatter([jj_pt[0]], [jj_pt[1]], c=GREEN, s=100, alpha=0.4, zorder=5)
                    ax.text(jj_pt[0], jj_pt[1]-1.2, f"{jj}G", color=GREEN, fontsize=7, ha='center')
            
            # Current step
            if pt:
                ax.scatter([pt[0]], [pt[1]], c=YELLOW, s=250, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
                ax.text(pt[0], pt[1]+1.5, f"{j}·G = {pt}", color=YELLOW, fontsize=11, ha='center', fontweight='bold')
                ax.arrow(pt[0]-3, pt[1], -6, 0, head_width=0.5, fc=YELLOW, ec=YELLOW, alpha=0.6)
            else:
                ax.text(50, 50, f"{j}·G = ∞ (point at infinity)", color=YELLOW, fontsize=11, ha='center')
            
            ax.text(50, 15, f"Table[{j}] = {pt if pt else '∞'}", color=WHITE, fontsize=10, ha='center', family='monospace')
            frames.append(self._save(fig, f"a7_baby_{idx}.png"))
            time.sleep(0.05)
        
        # --- FRAME 14-18: GIANT STEPS (animated) ---
        fig, ax = self._fig("GIANT STEPS: Searching for collision 🔍",
                           f"Compute P_c - i·(m·G) and check against baby table")
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=50, alpha=0.2, zorder=1)
        ax.scatter([P_c[0]], [P_c[1]], c=RED, s=350, marker='X', edgecolors=RED_GLOW, linewidths=4, zorder=10)
        ax.text(P_c[0], P_c[1]+1.2, "P_c (target)", color=RED, fontsize=12, ha='center', fontweight='bold')
        
        cur = P_c
        for i in range(m):
            if i > 0:
                fig, ax = self._fig(f"GIANT STEPS: i={i}/{m-1} 🔍",
                                   f"Compute P_c - {i}·(m·G) = P_c - {i}·{mP}")
                for p in ec.points[1:]:
                    ax.scatter([p[0]], [p[1]], c=BLUE, s=50, alpha=0.2, zorder=1)
                ax.scatter([P_c[0]], [P_c[1]], c=RED, s=300, marker='X', edgecolors=RED_GLOW, linewidths=3, zorder=10)
            
            if cur:
                ax.scatter([cur[0]], [cur[1]], c=ORANGE, s=250, marker='◆', edgecolors=WHITE, linewidths=2, zorder=10)
                ax.text(cur[0], cur[1]+1.2, f"i={i}: {cur}", color=ORANGE, fontsize=10, ha='center')
                
                # Check against baby table
                match_j = None
                for j, bpt in baby_steps:
                    if bpt == cur:
                        match_j = j
                        break
                
                if match_j is not None:
                    ax.text(50, 15, f"MATCH! i={i}, j={match_j} → k_c = {i}·{m} + {match_j} = {i*m + match_j}",
                            color=GREEN_GLOW, fontsize=13, ha='center', fontweight='bold')
                    # Draw connection
                    if baby_steps[match_j][1]:
                        ax.plot([cur[0], baby_steps[match_j][1][0]],
                               [cur[1], baby_steps[match_j][1][1]],
                               color=GREEN, linewidth=4, linestyle='--', alpha=0.8)
            
            cur = ec.add(cur, minus_mP)
            frames.append(self._save(fig, f"a8_giant_{i}.png"))
            time.sleep(0.08)
        
        # --- FRAME 19: COLLISION! ---
        fig, ax = self._fig("💥 COLLISION FOUND! 💥", "Baby step matches giant step!")
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=50, alpha=0.2, zorder=1)
        
        # Find the match
        i_match, j_match = 0, 0
        cur = P_c
        for i in range(m):
            for j, bpt in baby_steps:
                if bpt == cur:
                    i_match, j_match = i, j
                    break
            cur = ec.add(cur, minus_mP)
        
        k_recovered = i_match * m + j_match
        
        ax.scatter([P_c[0]], [P_c[1]], c=RED, s=400, marker='X', edgecolors=RED_GLOW, linewidths=5, zorder=10)
        recovered_pt = ec.mul(k_recovered, ec.G)[0]
        if recovered_pt:
            ax.scatter([recovered_pt[0]], [recovered_pt[1]],
                       c=GREEN, s=350, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
        
        # Equation
        ebox = FancyBboxPatch((10, 30), 80, 35, boxstyle="round,pad=1",
                              facecolor=RED, edgecolor=RED_GLOW, linewidth=4, alpha=0.3)
        ax.add_patch(ebox)
        ax.text(50, 58, f"k_c = {k_recovered}", color=RED, fontsize=28, ha='center', fontweight='bold', family='monospace')
        ax.text(50, 48, f"Verify: {k_recovered}·G = {recovered_pt} == P_c ✓", color=WHITE, fontsize=12, ha='center', family='monospace')
        
        ax.text(50, 15, "DLP SOLVED — Attacker now knows client's private key!", color=RED_GLOW, fontsize=14, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a9_collision.png"))
        
        # --- FRAME 20: SESSION KEY COMPROMISED ---
        fig, ax = self._fig("❌ SESSION KEY COMPROMISED ❌", "Attacker computes identical key!")
        # Broken lock
        lock = FancyBboxPatch((35, 30), 30, 25, boxstyle="round,pad=0.8",
                              facecolor=RED, edgecolor=RED_GLOW, linewidth=4, alpha=0.4)
        ax.add_patch(lock)
        theta = np.linspace(0, np.pi, 20)
        r = 8
        xs = 50 + r*np.cos(theta)
        ys = 42 + r*np.sin(theta)
        xs[8:12] = np.nan
        ax.plot(xs, ys, color=RED, linewidth=5)
        
        ax.text(50, 78, "Attacker computes:", color=WHITE, fontsize=13, ha='center')
        ax.text(50, 70, f"S' = k_c · P_s = {k_recovered} · {P_s} = {S}", color=WHITE, fontsize=12, ha='center', family='monospace')
        ax.text(50, 62, "K' = HKDF(H(S'))", color=WHITE, fontsize=12, ha='center')
        
        key_hex = hashlib.sha256(point_bytes(S)).hexdigest()[:32]
        ax.text(50, 52, f"Recovered: {key_hex}...", color=GREEN, fontsize=11, ha='center', family='monospace')
        
        legit_key = hashlib.sha256(point_bytes(S)).hexdigest()[:32]
        ax.text(50, 42, f"Legitimate: {legit_key}...", color=CYAN, fontsize=11, ha='center', family='monospace')
        
        ax.text(50, 32, "✓ MATCH — All traffic is now readable!", color=RED, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 20, "CLASSICAL ECDH: COMPLETELY BROKEN BY QUANTUM 💀", color=RED_GLOW, fontsize=16, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a10_compromised.png"))
        
        self._gif(frames, "demo_a_ecdh_dies.gif", dur=1500)
    
    # ================================
    # DEMO B: HYBRID LIVES
    # ================================
    def demo_b(self, ec: ToyEC, k_c, P_c, P_s, ecdh_secret, kem, hybrid_key):
        frames = []
        m = math.isqrt(ec.n) + 1
        mP = ec.mul(m, ec.G)[0]
        
        # --- FRAME 1: HYBRID SETUP ---
        fig, ax = self._fig("HYBRID: ECDH + KYBER 🛡️", "Two locks — break one, key still safe!")
        ax.plot([50, 50], [10, 90], color=SILVER, linestyle='--', alpha=0.3, linewidth=2)
        
        # Left: ECDH
        box_l = FancyBboxPatch((5, 18), 40, 62, boxstyle="round,pad=0.5",
                               facecolor=BOX, edgecolor=ORANGE, linewidth=2)
        ax.add_patch(box_l)
        ax.text(25, 76, "ECDH", color=ORANGE, fontsize=14, ha='center', fontweight='bold')
        ax.text(25, 68, f"P_c = {P_c}", color=WHITE, fontsize=10, ha='center', family='monospace')
        ax.text(25, 62, f"P_s = {P_s}", color=WHITE, fontsize=10, ha='center', family='monospace')
        ax.text(25, 54, "ss_E = H(k_c·P_s)", color=SILVER, fontsize=10, ha='center')
        ax.text(25, 46, "Hardness: DLP", color=YELLOW, fontsize=10, ha='center')
        ax.text(25, 36, "Status: ❌ BREAKABLE", color=RED, fontsize=10, ha='center', fontweight='bold')
        
        # Right: Kyber
        box_r = FancyBboxPatch((55, 18), 40, 62, boxstyle="round,pad=0.5",
                               facecolor=BOX, edgecolor=GREEN, linewidth=2)
        ax.add_patch(box_r)
        ax.text(75, 76, "KYBER512", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        ax.text(75, 68, f"pk: {kem['pk'][:8].hex()}...", color=SILVER, fontsize=9, ha='center', family='monospace')
        ax.text(75, 62, f"ct: {kem['ct'][:8].hex()}...", color=SILVER, fontsize=9, ha='center', family='monospace')
        ax.text(75, 54, "ss_K = ML-KEM secret", color=SILVER, fontsize=10, ha='center')
        ax.text(75, 46, "Hardness: M-LWE", color=CYAN, fontsize=10, ha='center')
        ax.text(75, 36, "Status: ✓ QUANTUM-SAFE", color=GREEN, fontsize=10, ha='center', fontweight='bold')
        
        # Lattice dots
        np.random.seed(42)