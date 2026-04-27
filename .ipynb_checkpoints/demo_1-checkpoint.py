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
    
    def bsgs_solve(self, P):
        """Solve k where k·G = P using BSGS"""
        m = math.isqrt(self.n) + 1
        baby_steps = []
        baby = None
        for j in range(m):
            baby_steps.append((j, baby))
            baby = self.add(baby, self.G)
        
        mP = self.mul(m, self.G)[0]
        minus_mP = self.neg(mP)
        cur = P
        for i in range(m + 1):
            for j, bpt in baby_steps:
                if bpt == cur:
                    return i * m + j, baby_steps, i, j
            cur = self.add(cur, minus_mP)
        return None, baby_steps, -1, -1

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

def hybrid_kdf(ecdh_secret, kem_ss, transcript):
    return hkdf_sha256(ecdh_secret + kem_ss, 
                       hashlib.sha256(transcript).digest(), 
                       b"OPAQUE-HYBRID-DEMO-v3", 32)

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
        # Clean up frames
        for f in frames:
            try:
                os.remove(f)
            except:
                pass
        print(f"  🔥 {name} - {len(frames)} frames")
        return p
    
    def _glow_box(self, ax, x, y, w, h, text, color, fontsize=14, alpha=0.3):
        """Add a glowing box with text"""
        box = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.8",
                             facecolor=color, edgecolor=color, linewidth=3, alpha=alpha)
        ax.add_patch(box)
        ax.text(x, y, text, color=WHITE, fontsize=fontsize, ha='center', va='center',
                fontweight='bold', family='monospace')
    
    def _curve_bg(self, ax, ec, alpha=0.3):
        """Draw all curve points as background"""
        for p in ec.points[1:]:
            ax.scatter([p[0]], [p[1]], c=BLUE, s=80, alpha=alpha, zorder=1)

    # ================================
    # DEMO A: WATCH ECDH DIE
    # ================================
    def demo_a(self, ec: ToyEC, k_c, k_s, P_c, P_s, S):
        frames = []
        m = math.isqrt(ec.n) + 1
        mP = ec.mul(m, ec.G)[0]
        minus_mP = ec.neg(mP)
        
        # Solve BSGS for the animation
        k_recovered, baby_steps, i_match, j_match = ec.bsgs_solve(P_c)
        
        # --- FRAME 1: What is ECDH? (THE BIG PICTURE) ---
        fig, ax = self._fig("WHAT IS ECDH? 🤔", "The mathematical magic behind secure messaging")
        
        # Story mode
        self._glow_box(ax, 50, 85, 80, 12, "Alice and Bob want to share a secret", BLUE, 14, 0.2)
        
        # Show the three actors
        # Alice
        alice_box = FancyBboxPatch((8, 55), 24, 20, boxstyle="round,pad=0.5",
                                   facecolor=BOX, edgecolor=CYAN, linewidth=2)
        ax.add_patch(alice_box)
        ax.text(20, 70, "👩 ALICE", color=CYAN, fontsize=12, ha='center', fontweight='bold')
        ax.text(20, 63, f"Secret: k_c = {k_c}", color=WHITE, fontsize=9, ha='center')
        ax.text(20, 57, f"Sends: P_c = {P_c}", color=YELLOW, fontsize=9, ha='center')
        
        # Bob
        bob_box = FancyBboxPatch((68, 55), 24, 20, boxstyle="round,pad=0.5",
                                 facecolor=BOX, edgecolor=ORANGE, linewidth=2)
        ax.add_patch(bob_box)
        ax.text(80, 70, "👨 BOB", color=ORANGE, fontsize=12, ha='center', fontweight='bold')
        ax.text(80, 63, f"Secret: k_s = {k_s}", color=WHITE, fontsize=9, ha='center')
        ax.text(80, 57, f"Sends: P_s = {P_s}", color=YELLOW, fontsize=9, ha='center')
        
        # Arrows showing exchange
        self._add_arrow(ax, 34, 65, 66, 65, YELLOW, '-', 2)
        ax.text(50, 68, "P_c →", color=YELLOW, fontsize=9, ha='center')
        self._add_arrow(ax, 66, 62, 34, 62, YELLOW, '-', 2)
        ax.text(50, 58, "← P_s", color=YELLOW, fontsize=9, ha='center')
        
        # Shared secret
        self._glow_box(ax, 50, 40, 70, 12, f"BOTH compute S = {S}  →  Session Key!", GREEN, 12, 0.2)
        
        ax.text(50, 28, "The math: S = k_c·P_s = k_s·P_c = (k_c·k_s)·G", color=SILVER, fontsize=10, ha='center', family='monospace')
        ax.text(50, 20, "Even though P_c and P_s are PUBLIC, only Alice & Bob know S!", color=GREEN_GLOW, fontsize=11, ha='center')
        ax.text(50, 12, "This is the ELLIPTIC CURVE DISCRETE LOG problem (DLP) — HARD for classical computers!", color=YELLOW, fontsize=9, ha='center')
        
        frames.append(self._save(fig, "a0_what_is_ecdh.png"))
        
        # --- FRAME 2: Show the actual curve ---
        fig, ax = self._fig("THE ELLIPTIC CURVE 📐", f"E: y² = x³ + x + 6 (mod {ec.p})  —  {len(ec.points)-1} points + point at infinity")
        self._curve_bg(ax, ec, 0.5)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=500, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(ec.G[0], ec.G[1]+1.5, "G (generator)", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        
        # Explain what the curve is
        self._add_box(ax, 60, 60, 35, 30, "Curve Facts:", [
            f"y² = x³ + x + 6 (mod {ec.p})",
            f"Field: GF({ec.p})",
            f"Points: {len(ec.points)-1} + ∞",
            f"Order of G: {ec.n}",
            "",
            "Adding points follows",
            "geometric rules!"
        ], BLUE)
        
        ax.text(50, 15, "Every cryptographic operation happens on THIS curve!", color=YELLOW, fontsize=11, ha='center')
        frames.append(self._save(fig, "a1_curve.png"))
        
        # --- FRAME 3: Point Addition Demo ---
        fig, ax = self._fig("POINT ADDITION GEOMETRY 🔍", "Adding P+Q on the curve (visual)")
        self._curve_bg(ax, ec, 0.4)
        
        # Pick two points to add
        P1 = ec.points[2]  # some point
        P2 = ec.points[5]  # another
        P3 = ec.add(P1, P2)
        
        ax.scatter([P1[0]], [P1[1]], c=CYAN, s=300, marker='o', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(P1[0], P1[1]+1.2, f"P={P1}", color=CYAN, fontsize=12, ha='center', fontweight='bold')
        
        ax.scatter([P2[0]], [P2[1]], c=ORANGE, s=300, marker='o', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(P2[0], P2[1]+1.2, f"Q={P2}", color=ORANGE, fontsize=12, ha='center', fontweight='bold')
        
        # Draw line between them
        ax.plot([P1[0], P2[0]], [P1[1], P2[1]], color=PURPLE, linewidth=2, linestyle='--', alpha=0.7)
        
        if P3:
            ax.scatter([P3[0]], [P3[1]], c=GREEN, s=400, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
            ax.text(P3[0], P3[1]+1.2, f"P+Q={P3}", color=GREEN, fontsize=12, ha='center', fontweight='bold')
        
        self._add_box(ax, 5, 60, 35, 30, "Point Addition Rule:", [
            f"P={P1}, Q={P2}",
            f"P+Q={P3}",
            "",
            "1. Draw line through P, Q",
            "2. Find 3rd intersection",
            "3. Reflect across x-axis",
            "",
            "Doubling uses tangent!"
        ], BLUE)
        
        ax.text(50, 15, "Scalar multiplication = ADD a point to itself k times (using double-and-add)", color=YELLOW, fontsize=10, ha='center')
        frames.append(self._save(fig, "a1b_point_add.png"))
        
        # --- FRAME 4: Client computes k_c·G (DOUBLE-AND-ADD LIVE!) ---
        fig, ax = self._fig("CLIENT COMPUTES: k_c · G 🔢", f"k_c = {k_c}  (binary: {bin(k_c)[2:]})  →  P_c = k_c·G = {P_c}")
        self._curve_bg(ax, ec, 0.3)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=300, marker='★', edgecolors=WHITE, linewidths=2, zorder=10)
        ax.text(ec.G[0], ec.G[1]+1.2, "G", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        
        # Animate double-and-add
        _, steps = ec.mul(k_c, ec.G)
        y_pos = 75
        step_num = 0
        
        for step_type, R, Q in steps[:8]:  # Show first 8 steps
            step_num += 1
            if step_type == 'add':
                if R is None:
                    ax.text(65, y_pos, f"Step {step_num}: ADD  R=∞ + Q={Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
                else:
                    ax.text(65, y_pos, f"Step {step_num}: ADD  R={R} + Q={Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
                    if R:
                        ax.scatter([R[0]], [R[1]], c=CYAN, s=150, marker='o', edgecolors=WHITE, linewidths=2, zorder=10, alpha=0.7)
                y_pos -= 10
            else:
                ax.text(65, y_pos, f"Step {step_num}: DOUBLE  Q={Q}+{Q}", color=ORANGE, fontsize=9, ha='left', family='monospace')
                if Q:
                    ax.scatter([Q[0]], [Q[1]], c=ORANGE, s=120, marker='s', edgecolors=WHITE, linewidths=1.5, zorder=10, alpha=0.6)
                y_pos -= 10
        
        ax.scatter([P_c[0]], [P_c[1]], c=YELLOW, s=400, marker='★', edgecolors=WHITE, linewidths=4, zorder=10)
        ax.text(P_c[0], P_c[1]+1.5, f"P_c = {P_c}", color=YELLOW, fontsize=13, ha='center', fontweight='bold')
        
        self._add_box(ax, 5, 55, 35, 35, "Double-and-Add 🔢", [
            "Efficient method:",
            f"k_c = {k_c} = 0b{bin(k_c)[2:]}",
            "",
            "For each bit:",
            "  ALWAYS double Q",
            "  If bit=1: ADD R+Q",
            "",
            f"{math.ceil(math.log2(k_c))} ops vs {k_c} ops!"
        ], CYAN)
        
        ax.text(50, 10, f"RESULT: P_c = {P_c}  ✓  Client SENDS this to server!", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a2_double_and_add.png"))
        
        # --- FRAME 5: Server computes k_s·G ---
        fig, ax = self._fig("SERVER COMPUTES: k_s · G 🔢", f"k_s = {k_s}  →  P_s = k_s·G = {P_s}")
        self._curve_bg(ax, ec, 0.3)
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=300, marker='★', edgecolors=WHITE, linewidths=2, zorder=10)
        
        _, steps = ec.mul(k_s, ec.G)
        y_pos = 75
        
        for step_type, R, Q in steps[:8]:
            if step_type == 'add':
                if R is None:
                    ax.text(65, y_pos, f"ADD: R=∞ + Q={Q}", color=ORANGE, fontsize=9, ha='left', family='monospace')
                else:
                    ax.text(65, y_pos, f"ADD: R={R} + Q={Q}", color=ORANGE, fontsize=9, ha='left', family='monospace')
                    if R:
                        ax.scatter([R[0]], [R[1]], c=ORANGE, s=150, marker='o', edgecolors=WHITE, linewidths=2, zorder=10, alpha=0.7)
                y_pos -= 10
            else:
                ax.text(65, y_pos, f"DOUBLE: Q={Q}", color=CYAN, fontsize=9, ha='left', family='monospace')
                if Q:
                    ax.scatter([Q[0]], [Q[1]], c=CYAN, s=120, marker='s', edgecolors=WHITE, linewidths=1.5, zorder=10, alpha=0.6)
                y_pos -= 10
        
        ax.scatter([P_s[0]], [P_s[1]], c=ORANGE, s=400, marker='★', edgecolors=WHITE, linewidths=4, zorder=10)
        ax.text(P_s[0], P_s[1]+1.5, f"P_s = {P_s}", color=ORANGE, fontsize=13, ha='center', fontweight='bold')
        
        ax.text(50, 10, f"RESULT: P_s = {P_s}  ✓  Server SENDS this to client!", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a3_server_compute.png"))
        
        # --- FRAME 6: Shared Secret Computation ---
        fig, ax = self._fig("SHARED SECRET COMPUTATION 🔐", "The magic moment — both compute the SAME point!")
        self._curve_bg(ax, ec, 0.35)
        
        # Show both public keys
        ax.scatter([P_c[0]], [P_c[1]], c=CYAN, s=350, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(P_c[0], P_c[1]+1.3, f"P_c = {P_c}", color=CYAN, fontsize=12, ha='center')
        
        ax.scatter([P_s[0]], [P_s[1]], c=ORANGE, s=350, marker='★', edgecolors=WHITE, linewidths=3, zorder=10)
        ax.text(P_s[0], P_s[1]+1.3, f"P_s = {P_s}", color=ORANGE, fontsize=12, ha='center')
        
        # Show shared secret
        ax.scatter([S[0]], [S[1]], c=GREEN, s=600, marker='★', edgecolors=WHITE, linewidths=5, zorder=10)
        ax.text(S[0], S[1]+1.8, f"S = {S}", color=GREEN_GLOW, fontsize=15, ha='center', fontweight='bold')
        
        # Computation boxes
        self._add_box(ax, 5, 55, 40, 18, "👩 Alice (Client):", [
            f"S = k_c · P_s",
            f"  = {k_c} · {P_s}",
            f"  = {S}"
        ], CYAN)
        
        self._add_box(ax, 55, 55, 40, 18, "👨 Bob (Server):", [
            f"S = k_s · P_c",
            f"  = {k_s} · {P_c}",
            f"  = {S}"
        ], ORANGE)
        
        ax.text(50, 45, "Both arrive at S = k_c·k_s·G  ✓  Session key = HKDF(H(S))", color=GREEN, fontsize=12, ha='center', fontweight='bold')
        ax.text(50, 35, "🔒 ECDH COMPLETE — Only Alice & Bob know S", color=GREEN_GLOW, fontsize=14, ha='center', fontweight='bold')
        frames.append(self._save(fig, "a4_shared_secret.png"))
        
        # --- FRAME 7: ATTACKER'S VIEW ---
        fig, ax = self._fig("👁️ EVE THE EAVESDROPPER 👁️", "Everything on the network is PUBLIC!")
        
        # Big eye
        eye_bg = Circle((25, 50), 18, facecolor=RED, edgecolor=RED_GLOW, linewidth=5, alpha=0.25, zorder=1)
        ax.add_patch(eye_bg)
        ax.text(25, 50, "👁", color=WHITE, fontsize=30, ha='center', va='center', zorder=2)
        
        self._add_box(ax, 42, 55, 50, 35, "WHAT EVE SEES (Public Info):", [
            f"G  = {ec.G}     ← The generator",
            f"P_c = {P_c}   ← Alice's public key",
            f"P_s = {P_s}   ← Bob's public key",
            "",
            "❓ Eve's Goal:",
            f"Find k_c such that {k_c}·G = {P_c}",
            "",
            "This is the DISCRETE LOG PROBLEM (DLP)",
            "HARD for classical computers",
            "BUT quantum computers can SOLVE it!"
        ], RED)
        
        ax.text(50, 20, "Shor's Algorithm (1994): Quantum DLP solver in POLYNOMIAL TIME ⚡", color=RED_GLOW, fontsize=13, ha='center', fontweight='bold')
        ax.text(50, 12, "Let's watch Shor's algorithm BREAK this in REAL TIME...", color=YELLOW, fontsize=12, ha='center')
        frames.append(self._save(fig, "a5_attacker_view.png"))
        
        # --- FRAME 8: BSGS INTRO ---
        fig, ax = self._fig("BABY-STEP GIANT-STEP (BSGS) 🧮", "Shor's algorithm — classical version for visualization")
        
        self._glow_box(ax, 50, 82, 90, 10, f"Problem: Find k_c where k_c·G = {P_c}", RED, 13, 0.2)
        
        self._add_box(ax, 5, 10, 90, 62, "How BSGS Works:", [
            f"1. Set m = ⌈√n⌉ = ⌈√{ec.n}⌉ = {m}     (split the search space)",
            f"2. Write k_c = i·m + j     where i,j ∈ [0, {m-1}]",
            "",
            "3. Then: k_c·G = (i·m + j)·G = i·(m·G) + j·G",
            "   Rearranged: j·G = P_c - i·(m·G)",
            "",
            "🎯 BABY STEPS: Compute and STORE j·G for j=0,1,...,m-1",
            "🎯 GIANT STEPS: Compute P_c - i·(m·G) for i=0,1,...",
            "   CHECK if result is in baby step table",
            "",
            "💥 When they match: k_c = i·m + j   ← PRIVATE KEY RECOVERED!",
            "",
            f"m·G = {m}·G = {mP}"
        ], BLUE, BLUE, 10)
        
        ax.text(50, 5, f"Time: O(√n) = O({m}) instead of O(n) = O({ec.n})", color=GREEN, fontsize=10, ha='center', family='monospace')
        frames.append(self._save(fig, "a6_bsgs_explained.png"))
        
        # --- FRAME 9-12: BABY STEPS ANIMATION ---
        for idx in range(0, len(baby_steps)):
            j, pt = baby_steps[idx]
            fig, ax = self._fig(f"BABY STEPS: Building the table 📝  (j={j}/{m-1})",
                               "Computing j·G and storing in quantum memory (QRAM)")
            self._curve_bg(ax, ec, 0.25)
            
            # Show target
            ax.scatter([P_c[0]], [P_c[1]], c=RED, s=350, marker='X', edgecolors=RED_GLOW, linewidths=3, zorder=10)
            ax.text(P_c[0], P_c[1]+1.2, "TARGET", color=RED, fontsize=11, ha='center', fontweight='bold')
            
            # Show all computed baby steps
            for jj in range(idx + 1):
                jj_pt = baby_steps[jj][1]
                if jj_pt:
                    alpha = 0.8 if jj == idx else 0.4
                    size = 180 if jj == idx else 80
                    ax.scatter([jj_pt[0]], [jj_pt[1]], c=GREEN, s=size, alpha=alpha, 
                              marker='o' if jj < idx else '★', edgecolors=WHITE, linewidths=2, zorder=10)
                    ax.text(jj_pt[0], jj_pt[1]-1.3, f"{jj}G", color=GREEN, fontsize=7, ha='center', alpha=alpha)
            
            # Progress bar
            progress = (idx + 1) / m
            bar = FancyBboxPatch((20, 8), 60 * progress, 3, boxstyle="round,pad=0.1",
                                 facecolor=GREEN, edgecolor=GREEN_GLOW, linewidth=1)
            ax.add_patch(bar)
            ax.text(50, 5, f"Table[{j}] = j·G = {pt if pt else '∞'}", color=WHITE, fontsize=10, ha='center', family='monospace')
            
            if idx % 3 == 0 or idx == len(baby_steps) - 1:
                frames.append(self._save(fig, f"a7_baby_{idx}.png"))
                plt.close(fig)
            else:
                plt.close(fig)
        
        # --- FRAME 13-16: GIANT STEPS with COLLISION ---
        cur = P_c
        for i in range(m):
            fig, ax = self._fig(f"GIANT STEPS: Searching for match 🔍  (i={i}/{m-1})",
                               f"Compute P_c - {i}·(m·G) and CHECK against baby table")
            self._curve_bg(ax, ec, 0.25)
            
            # Target
            ax.scatter([P_c[0]], [P_c[1]], c=RED, s=350, marker='X', edgecolors=RED_GLOW, linewidths=3, zorder=10)
            ax.text(P_c[0], P_c[1]+1.2, "P_c", color=RED, fontsize=12, ha='center', fontweight='bold')
            
            # Current giant step
            if cur:
                ax.scatter([cur[0]], [cur[1]], c=ORANGE, s=300, marker='◆', edgecolors=WHITE, linewidths=3, zorder=10)
                ax.text(cur[0], cur[1]+1.2, f"i={i}: {cur}", color=ORANGE, fontsize=11, ha='center', fontweight='bold')
            
            # Check match
            match_j = None
            for j, bpt in baby_steps:
                if bpt == cur:
                    match_j = j
                    break
            
            if match_j is not None:
                # COLLISION!
                self._glow_box(ax, 50, 15, 80, 12, 
                             f"💥 MATCH! i={i}, j={match_j} → k_c = {i}·{m} + {match_j} = {i*m + match_j}",
                             GREEN_GLOW, 12, 0.3)
                
                # Draw the matching baby step
                matched_pt = baby_steps[match_j][1]
                if matched_pt and cur:
                    ax.scatter([matched_pt[0]], [matched_pt[1]], c=GREEN, s=300, marker='★', 
                              edgecolors=WHITE, linewidths=3, zorder=10)
                    ax.plot([cur[0], matched_pt[0]], [cur[1], matched_pt[1]], 
                           color=GREEN, linewidth=3, linestyle='--', alpha=0.8)
                    ax.text((cur[0]+matched_pt[0])/2, (cur[1]+matched_pt[1])/2 + 1, 
                           "MATCH!", color=GREEN_GLOW, fontsize=14, ha='center', fontweight='bold')
                
                frames.append(self._save(fig, f"a8_giant_{i}_collision.png"))
                break
            
            if i % 3 == 0 or i == m - 1:
                ax.text(50, 5, f"Checking P_c - {i}·(m·G) = {cur}  ... No match yet", color=SILVER, fontsize=9, ha='center')
                frames.append(self._save(fig, f"a8_giant_{i}.png"))
            
            cur = ec.add(cur, minus_mP)
            plt.close(fig)
        
        # --- FRAME 17: PRIVATE KEY RECOVERED ---
        fig, ax = self._fig("🔓 PRIVATE KEY RECOVERED! 🔓", f"k_c = {k_recovered}  (verified)")
        self._curve_bg(ax, ec, 0.3)
        
        # Dramatic reveal
        self._glow_box(ax, 50, 75, 90, 25, f"k_c = {k_recovered}", RED, 28, 0.4)
        
        # Verification
        ax.scatter([ec.G[0]], [ec.G[1]], c=GREEN, s=300, marker='★', edgecolors=WHITE, linewidths=2, zorder=10)
        ax.text(ec.G[0], ec.G[1]+1.2, "G", color=GREEN, fontsize=14, ha='center')
        
        ax.scatter([P_c[0]], [P_c[1]], c=RED, s=350, marker='X', edgecolors=RED_GLOW, linewidths=4, zorder=10)
        ax.text(P_c[0], P_c[1]+1.2, f"P_c={P_c}", color=RED, fontsize=14, ha='center')
        
        verified = ec.mul(k_recovered, ec.G)[0]
        ax.text(50, 55, f"Verify: {k_recovered}·G = {verified} == {P_c}  ✓", color=GREEN, fontsize=14, ha='center', fontweight='bold', family='monospace')
        
        ax.text(50, 42, "Attacker now has Alice's private key!", color=RED, fontsize=14, ha='center', fontweight='bold')
        ax.text(50, 32, f"⌛ BSGS completed in O(√{ec.n}) = {m} steps", color=YELLOW, fontsize=11, ha='center')
        ax.text(50, 22, "On real curves (256-bit): 2^128 steps with quantum = POLYNOMIAL", color=RED_GLOW, fontsize=10, ha='center')
        
        frames.append(self._save(fig, "a9_key_recovered.png"))
        
        # --- FRAME 18: SESSION KEY COMPROMISED ---
        fig, ax = self._fig("💀 SESSION KEY COMPROMISED 💀", "Attacker derives identical session key")
        
        # Big X
        ax.plot([30, 70], [30, 70], color=RED, linewidth=5, alpha=0.5)
        ax.plot([70, 30], [30, 70], color=RED, linewidth=5, alpha=0.5)
        
        session_key = hashlib.sha256(point_bytes(S)).hexdigest()[:40]
        
        self._glow_box(ax, 50, 82, 85, 10, "ATTACKER RECOVERS SESSION KEY", RED, 13, 0.3)
        
        self._add_box(ax, 10, 50, 80, 25, "Attacker's Computation:", [
            f"S' = k_c · P_s = {k_recovered} · {P_s} = {S}",
            f"K' = HKDF(H(S')) = HKDF(H({S}))",
            f"K' = {session_key}..."
        ], RED)
        
        self._add_box(ax, 10, 15, 80, 25, "Legitimate Session Key:", [
            f"S = k_c · P_s = {S}",
            f"K = HKDF(H(S))",
            f"K = {session_key}..."
        ], GREEN, GREEN)
        
        ax.text(50, 8, "✗ KEYS MATCH — All encrypted traffic is READABLE by attacker!", color=RED_GLOW, fontsize=12, ha='center', fontweight='bold')
        
        frames.append(self._save(fig, "a10_compromised.png"))
        
        # --- FRAME 19: DEATH OF ECDH ---
        fig, ax = self._fig("⚰️ CLASSICAL ECDH: COMPLETELY BROKEN ⚰️", "One mathematical breakthrough = Total compromise")
        
        # Death effects
        for _ in range(30):
            x = random.uniform(5, 95)
            y = random.uniform(5, 90)
            ax.scatter(x, y, color=RED, s=random.randint(10, 50), alpha=random.uniform(0.2, 0.6))
        
        self._glow_box(ax, 50, 70, 90, 20, "THE PROBLEM WITH CLASSICAL ECDH", RED, 14, 0.3)
        
        ax.text(50, 50, "✓ Security depends on ONE assumption: DLP is hard", color=WHITE, fontsize=12, ha='center')
        ax.text(50, 42, "✗ Quantum computers (Shor's) BREAK this assumption", color=RED, fontsize=12, ha='center')
        ax.text(50, 34, "✗ Single point of failure = TOTAL COMPROMISE", color=RED, fontsize=12, ha='center')
        ax.text(50, 24, "✓ Solution: ADD POST-QUANTUM LAYER (Kyber)", color=GREEN_GLOW, fontsize=13, ha='center', fontweight='bold')
        ax.text(50, 14, "→ Watch DEMO B to see how hybrid survives the same attack!", color=YELLOW, fontsize=12, ha='center')
        
        frames.append(self._save(fig, "a11_death.png"))
        
        self._gif(frames, "demo_a_ecdh_dies.gif", dur=1200)
        return k_recovered
    
    # ================================
    # DEMO B: HYBRID LIVES
    # ================================
    def demo_b(self, ec: ToyEC, k_c, P_c, P_s, ecdh_secret, kem, hybrid_key):
        frames = []
        m = math.isqrt(ec.n) + 1
        mP = ec.mul(m, ec.G)[0]
        
        # BSGS results for the ECDH layer
        k_recovered, baby_steps, i_match, j_match = ec.bsgs_solve(P_c)
        
        # --- FRAME 1: HYBRID ARCHITECTURE ---
        fig, ax = self._fig("HYBRID KEY EXCHANGE: ECDH + KYBER 🛡️", "Two independent locks — break one, key stays SAFE!")
        ax.plot([50, 50], [10, 90], color=SILVER, linestyle='--', alpha=0.3, linewidth=2)
        
        # Left: ECDH (vulnerable but fast)
        left_box = FancyBboxPatch((5, 15), 40, 65, boxstyle="round,pad=0.5",
                                  facecolor=BOX, edgecolor=ORANGE, linewidth=2.5)
        ax.add_patch(left_box)
        ax.text(25, 76, "LAYER 1: ECDH", color=ORANGE, fontsize=14, ha='center', fontweight='bold')
        ax.text(25, 68, f"P_c = {P_c}", color=WHITE, fontsize=10, ha='center', family='monospace')
        ax.text(25, 62, f"P_s = {P_s}", color=WHITE, fontsize=10, ha='center', family='monospace')
        ax.text(25, 54, "ss_ECDH = H(k_c·P_s)", color=SILVER, fontsize=10, ha='center')
        ax.text(25, 46, "Security: DLP", color=YELLOW, fontsize=11, ha='center')
        ax.text(25, 38, "Quantum: ❌ BREAKABLE", color=RED, fontsize=10, ha='center', fontweight='bold')
        ax.text(25, 28, "Status: ⚠️ WEAK LINK", color=ORANGE, fontsize=10, ha='center')
        
        # Right: Kyber (quantum-safe)
        right_box = FancyBboxPatch((55, 15), 40, 65, boxstyle="round,pad=0.5",
                                   facecolor=BOX, edgecolor=GREEN, linewidth=2.5)
        ax.add_patch(right_box)
        ax.text(75, 76, "LAYER 2: KYBER512", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        ax.text(75, 68, f"pk: {kem['pk'][:8].hex()}...", color=SILVER, fontsize=9, ha='center', family='monospace')
        ax.text(75, 62, f"ct: {kem['ct'][:8].hex()}...", color=SILVER, fontsize=9, ha='center', family='monospace')
        ax.text(75, 54, "ss_Kyber = 256-bit", color=SILVER, fontsize=10, ha='center')
        ax.text(75, 46, "Security: M-LWE", color=CYAN, fontsize=11, ha='center')
        ax.text(75, 38, "Quantum: ✅ SAFE", color=GREEN, fontsize=10, ha='center', fontweight='bold')
        ax.text(75, 28, "Status: 💪 STRONG", color=GREEN, fontsize=10, ha='center')
        
        # Lattice visualization on right side
        np.random.seed(42)
        for _ in range(80):
            x = np.random.normal(75, 9)
            y = np.random.normal(25, 9)
            ax.plot(x, y, 'o', color=GREEN, markersize=2.5, alpha=0.45)
        
        # Bottom: Combined
        combo = FancyBboxPatch((8, 3), 84, 10, boxstyle="round,pad=0.3",
                               facecolor=ACCENT, edgecolor=BLUE, linewidth=2.5)
        ax.add_patch(combo)
        ax.text(50, 9, "HYBRID KEY = HKDF( ss_ECDH ‖ ss_Kyber ‖ H(transcript) )", color=WHITE, 
               fontsize=10, ha='center', fontweight='bold', family='monospace')
        ax.text(50, 5, "Need BOTH secrets to compute final key!", color=YELLOW, fontsize=9, ha='center')
        
        frames.append(self._save(fig, "b0_hybrid_setup.png"))
        
        # --- FRAME 2-5: QUANTUM ATTACK ON ECDH (QUICK VERSION) ---
        attack_msgs = [
            ("⚡ QUANTUM ATTACK BEGINS ⚡", "Shor's algorithm targets ECDH layer..."),
            ("ECDH UNDER ATTACK 🔍", f"BSGS running... m={m}"),
            ("ECDH LAYER: FOUND MATCH 💥", f"k_c = {k_recovered} recovered"),
            ("ECDH LAYER: DESTROYED 💀", f"ss_ECDH = {ecdh_secret[:12].hex()}... NOW KNOWN")
        ]
        
        for frame_idx, (title, sub) in enumerate(attack_msgs):
            fig, ax = self._fig(title, sub)
            ax.plot([50, 50], [10, 90], color=SILVER, linestyle='--', alpha=0.3, linewidth=2)
            
            # LEFT: ECDH falling apart
            if frame_idx < 3:
                for offset in [(0,0), (0.2,0.2), (-0.1,-0.15)]:
                    crack = FancyBboxPatch((5+offset[0], 15+offset[1]), 40, 65, boxstyle="round,pad=0.5",
                                          facecolor=BOX, edgecolor=RED, linewidth=2, alpha=0.2)
                    ax.add_patch(crack)
            
            if frame_idx == 3:
                # Fully broken
                broken = FancyBboxPatch((5, 15), 40, 65, boxstyle="round,pad=0.5",
                                       facecolor=RED, edgecolor=RED_GLOW, linewidth=3, alpha=0.3)
                ax.add_patch(broken)
                ax.text(25, 55, "❌ BROKEN ❌", color=RED, fontsize=18, ha='center', fontweight='bold')
                ax.text(25, 42, f"k_c = {k_recovered}", color=RED_GLOW, fontsize=14, ha='center')
                ax.text(25, 32, "ss_ECDH EXPOSED", color=RED, fontsize=11, ha='center')
            else:
                ax.text(25, 55, f"Step {frame_idx+1}/4...", color=YELLOW, fontsize=14, ha='center', fontweight='bold')
            
            # RIGHT: Kyber untouched
            right_box = FancyBboxPatch((55, 15), 40, 65, boxstyle="round,pad=0.5",
                                      facecolor=BOX, edgecolor=GREEN, linewidth=3)
            ax.add_patch(right_box)
            ax.text(75, 55, "✅ KYBER SECURE ✅", color=GREEN, fontsize=14, ha='center', fontweight='bold')
            
            # Lattice stays strong
            np.random.seed(42)
            for _ in range(80):
                x = np.random.normal(75, 9)
                y = np.random.normal(25, 9)
                ax.plot(x, y, 'o', color=GREEN, markersize=3, alpha=0.5)
            
            ax.text(75, 35, "M-LWE problem:", color=CYAN, fontsize=10, ha='center')
            ax.text(75, 28, "Still HARD for", color=CYAN, fontsize=10, ha='center')
            ax.text(75, 21, "quantum computers", color=CYAN, fontsize=10, ha='center')
            
            # Quantum particles on ECDH side
            if frame_idx < 3:
                for _ in range(20):
                    x = np.random.uniform(7, 43)
                    y = np.random.uniform(17, 78)
                    ax.scatter(x, y, color=RED, s=15, alpha=0.4)
            
            frames.append(self._save(fig, f"b1_attack_{frame_idx}.png"))
            time.sleep(0.03)
        
        # --- FRAME 6: KYBER WALL ---
        fig, ax = self._fig("🧱 THE KYBER WALL 🧱", "Attacker hits the Module-LWE problem")
        
        self._glow_box(ax, 50, 82, 85, 10, "KYBER512 SECURITY PARAMETERS", GREEN, 13, 0.2)
        
        self._add_box(ax, 5, 15, 90, 58, "Module-LWE Problem (Kyber's Hardness):", [
            "Ring: Z_q[X]/(X^256+1)    where q = 3329",
            "Module rank k = 2    (Kyber512)",
            "",
            "Problem: Given A (k×k matrix), b = A·s + e",
            "         Find s (the secret vector)",
            "         where e is a small random error",
            "",
            "Classical hardness: ≈ 2^118 bit operations",
            "",
            "⚡ QUANTUM ATTACKS:",
            "  • Lattice sieving: ≈ 2^178 operations",
            "  • Grover's: ONLY √ speedup → 2^59 (STILL huge!)",
            "  • NO known polynomial-time quantum algorithm!",
            "",
            "Security level: NIST Level 1 (≈ AES-128 post-quantum)"
        ], GREEN, GREEN, 10)
        
        ax.text(50, 8, "Even with quantum computer: 2^178 ops > universe lifespan! 🕐", color=GREEN_GLOW, fontsize=11, ha='center')
        frames.append(self._save(fig, "b2_kyber_wall.png"))
        
        # --- FRAME 7-10: ATTACKER SEARCHES LATTICE (FUTILE) ---
        np.random.seed(123)
        lattice_pts = [(np.random.normal(50, 20), np.random.normal(40, 18)) for _ in range(300)]
        
        for attempt in range(4):
            fig, ax = self._fig(f"SEARCHING LATTICE... {2**(attempt*40)}/{2**178} checked 🔍",
                               f"That's {2**(attempt*40)/2**178*100:.20f}% of the search space")
            
            # Draw massive lattice
            for x, y in lattice_pts:
                ax.plot(x, y, 'o', color=GREEN, markersize=2.5, alpha=0.4)
            
            # Unknown target
            self._glow_box(ax, 50, 75, 40, 8, "ss_Kyber = ?????????", RED, 12, 0.3)
            
            # Random guesses (all wrong)
            guesses = np.random.choice(len(lattice_pts), 10, replace=False)
            for g in guesses:
                ax.plot(lattice_pts[g][0], lattice_pts[g][1], 'x', color=YELLOW, markersize=12, linewidths=2)
                ax.text(lattice_pts[g][0], lattice_pts[g][1], '✗', color=RED, fontsize=8, ha='center', va='center')
            
            ax.text(50, 55, f"Attempts: {2**(attempt*40)}", color=SILVER, fontsize=12, ha='center', family='monospace')
            ax.text(50, 47, "Correct key: STILL HIDDEN", color=RED, fontsize=14, ha='center', fontweight='bold')
            ax.text(50, 39, "This is IMPOSSIBLE", color=RED_GLOW, fontsize=16, ha='center', fontweight='bold')
            
            progress_pct = 2**(attempt*40) / 2**178 * 100
            ax.text(50, 25, f"Progress: {progress_pct:.20f}%", color=YELLOW, fontsize=11, ha='center', family='monospace')
            
            frames.append(self._save(fig, f"b3_lattice_{attempt}.png"))
            time.sleep(0.04)
        
        # --- FRAME 11: ATTACKER GIVES UP ---
        fig, ax = self._fig("😩 ATTACKER ADMITS DEFEAT 😩", "Cannot break Kyber's M-LWE problem")
        
        self._glow_box(ax, 50, 75, 85, 12, "ATTACK RESULT: PARTIAL SUCCESS (ECDH) — TOTAL FAILURE (SESSION KEY)", ORANGE, 12, 0.3)
        
        self._add_box(ax, 10, 45, 80, 22, "What Attacker HAS:", [
            f"✓ ss_ECDH = {ecdh_secret[:12].hex()}...     (from broken ECDH)",
            "✗ ss_Kyber = ????????????????????     (UNKNOWN)",
            "✗ H(transcript) is known but useless without ss_Kyber"
        ], ORANGE)
        
        self._add_box(ax, 10, 12, 80, 25, "Session Key Derivation:", [
            "K = HKDF( ss_ECDH  ‖  ss_Kyber  ‖  H(T) )",
            "   = HKDF( KNOWN   ‖  UNKNOWN   ‖  KNOWN )",
            "   = UNKNOWN",
            "",
            "Without ss_Kyber: Session key remains SECURE! 🔒"
        ], GREEN, GREEN)
        
        frames.append(self._save(fig, "b4_give_up.png"))
        
        # --- FRAME 12-13: KEY DERIVATION VISUAL ---
        for step in range(2):
            fig, ax = self._fig("🔐 KEY DERIVATION ANALYSIS 🔐" if step == 0 else "⚠️ ATTACKER'S ATTEMPT ⚠️",
                               "What the attacker knows vs what they need")
            
            if step == 0:
                # Show the correct derivation
                self._add_box(ax, 10, 65, 80, 25, "Legitimate Key Derivation:", [
                    f"ss_ECDH  = {ecdh_secret[:16].hex()}...",
                    f"ss_Kyber = {kem['ss'][:16].hex()}...",
                    f"K = HKDF({ecdh_secret[:8].hex()}... ‖ {kem['ss'][:8].hex()}... ‖ H(T))",
                    f"K = {hybrid_key.hex()[:40]}..."
                ], GREEN)
            else:
                # Show attacker's wrong attempt
                guessed = secrets.token_bytes(32)
                wrong_key = hybrid_kdf(ecdh_secret, guessed, b"transcript")
                self._add_box(ax, 10, 65, 80, 25, "Attacker's Failed Attempt:", [
                    f"ss_ECDH  = {ecdh_secret[:16].hex()}...  ✓ (CORRECT)",
                    f"ss_Kyber = {guessed[:16].hex()}...  ✗ (WRONG GUESS)",
                    f"K' = HKDF({ecdh_secret[:8].hex()}... ‖ {guessed[:8].hex()}... ‖ H(T))",
                    f"K' = {wrong_key.hex()[:40]}..."
                ], RED)
            
            # Visual comparison
            ax.text(50, 55, "‖", color=WHITE, fontsize=24, ha='center')
            
            if step == 0:
                self._glow_box(ax, 25, 50, 30, 8, "ss_ECDH ✓", GREEN, 11, 0.2)
                self._glow_box(ax, 75, 50, 30, 8, "ss_Kyber ✓", GREEN, 11, 0.2)
                self._glow_box(ax, 50, 35, 60, 10, "CORRECT KEY = SECURE 🔒", GREEN, 13, 0.3)
            else:
                self._glow_box(ax, 25, 50, 30, 8, "ss_ECDH ✓", GREEN, 11, 0.2)
                self._glow_box(ax, 75, 50, 30, 8, "WRONG GUESS ✗", RED, 11, 0.2)
                self._glow_box(ax, 50, 35, 60, 10, "K' ≠ K → CANNOT DECRYPT ANYTHING!", RED, 13, 0.3)
            
            ax.text(50, 15, "Hybrid key exchange: Defense in depth WORKS!", color=GREEN_GLOW, fontsize=13, ha='center', fontweight='bold')
            frames.append(self._save(fig, f"b5_key_derivation_{step}.png"))
        
        # --- FRAME 14: HYBRID WINS ---
        fig, ax = self._fig("🏆 HYBRID ECDH+KYBER: QUANTUM-RESISTANT 🏆", "The hybrid approach defeats quantum attacks")
        
        # Split screen recap
        ax.plot([50, 50], [10, 90], color=SILVER, linestyle='--', alpha=0.3, linewidth=2)
        
        # Left: What the attacker got
        left_box = FancyBboxPatch((5, 45), 40, 40, boxstyle="round,pad=0.5",
                                  facecolor=BOX, edgecolor=RED, linewidth=2)
        ax.add_patch(left_box)
        ax.text(25, 80, "ATTACKER WINS:", color=RED, fontsize=13, ha='center', fontweight='bold')
        ax.text(25, 72, "✓ ECDH broken", color=ORANGE, fontsize=11, ha='center')
        ax.text(25, 65, "✓ ss_ECDH recovered", color=ORANGE, fontsize=11, ha='center')
        ax.text(25, 56, "PARTIAL VICTORY", color=YELLOW, fontsize=12, ha='center', fontweight='bold')
        
        # Right: What stays safe
        right_box = FancyBboxPatch((55, 45), 40, 40, boxstyle="round,pad=0.5",
                                   facecolor=BOX, edgecolor=GREEN, linewidth=2)
        ax.add_patch(right_box)
        ax.text(75, 80, "ATTACKER LOSES:", color=GREEN, fontsize=13, ha='center', fontweight='bold')
        ax.text(75, 72, "✗ Kyber survives", color=GREEN, fontsize=11, ha='center')
        ax.text(75, 65, "✗ ss_Kyber unknown", color=GREEN, fontsize=11, ha='center')
        ax.text(75, 56, "SESSION KEY SAFE", color=GREEN, fontsize=12, ha='center', fontweight='bold')
        
        # Final verdict
        self._glow_box(ax, 50, 30, 90, 18, "VERDICT: HYBRID SESSION KEY REMAINS SECURE 🔒", GREEN_GLOW, 15, 0.3)
        
        ax.text(50, 15, "Theorem: If M-LWE is quantum-hard, hybrid provides post-quantum security", 
               color=WHITE, fontsize=10, ha='center', style='italic')
        
        frames.append(self._save(fig, "b6_hybrid_wins.png"))
        
        self._gif(frames, "demo_b_hybrid_lives.gif", dur=1400)

    def _add_box(self, ax, x, y, w, h, title, lines, edge_color=BLUE, title_color=None, fontsize=10):
        """Helper to add a text box"""
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4",
                            facecolor=BOX, edgecolor=edge_color, linewidth=1.5)
        ax.add_patch(box)
        
        if title_color is None:
            title_color = edge_color
        
        if title:
            ax.text(x + w/2, y + h - 3, title, color=title_color, fontsize=fontsize+2,
                   ha='center', va='center', fontweight='bold', family='monospace')
        
        current_y = y + h - 8
        for line in lines:
            ax.text(x + 2, current_y, line, color=SILVER, fontsize=fontsize,
                   ha='left', va='top', family='monospace')
            current_y -= 4
    
    def _add_arrow(self, ax, x1, y1, x2, y2, color=WHITE, style='->', lw=1.5):
        """Helper to add an arrow"""
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle=style, color=color, lw=lw))
    
    def create_comparison(self, ec, k_c, P_c, P_s, ecdh_secret, kem, hybrid_key):
        """Create static comparison theorem figure"""
        fig, ax = self._fig("SECURITY THEOREM: Classical vs Hybrid", "Post-Quantum Key Exchange Analysis")
        
        # Two columns
        # Classical
        classical_box = FancyBboxPatch((5, 15), 42, 70, boxstyle="round,pad=0.5",
                                       facecolor=BOX, edgecolor=RED, linewidth=2.5)
        ax.add_patch(classical_box)
        ax.text(26, 80, "CLASSICAL ECDH", color=RED, fontsize=15, ha='center', fontweight='bold')
        
        items_classical = [
            "Hardness assumption: DLP",
            "Quantum attack: Shor's",
            "QL complexity: Poly O((log n)³)",
            "Result: PRIVATE KEY RECOVERED",
            "Session key: COMPROMISED ✗",
            "Quantum security: 0 bits",
            "HNDL resistant: NO",
            "",
            "Verdict: BROKEN 💀"
        ]
        
        y = 72
        for item in items_classical:
            if "COMPROMISED" in item or "BROKEN" in item or "0 bits" in item:
                ax.text(26, y, item, color=RED, fontsize=9, ha='center', fontweight='bold')
            else:
                ax.text(26, y, item, color=SILVER, fontsize=9, ha='center')
            y -= 5
        
        # Hybrid
        hybrid_box = FancyBboxPatch((53, 15), 42, 70, boxstyle="round,pad=0.5",
                                    facecolor=BOX, edgecolor=GREEN, linewidth=2.5)
        ax.add_patch(hybrid_box)
        ax.text(74, 80, "HYBRID ECDH+KYBER", color=GREEN, fontsize=15, ha='center', fontweight='bold')
        
        items_hybrid = [
            "Hardness: DLP ∧ M-LWE",
            "ECDH attack: Succeeds",
            "Kyber attack: NO known algorithm",
            "Kyber best attack: 2^178 ops",
            "ECDH result: PARTIAL break",
            "Session key: SECURE ✓",
            "Quantum security: 128 bits",
            "HNDL resistant: YES",
            "",
            "Verdict: DEFENSE IN DEPTH 🛡️"
        ]
        
        y = 72
        for item in items_hybrid:
            if "SECURE" in item or "DEFENSE" in item or "128 bits" in item or "YES" in item:
                ax.text(74, y, item, color=GREEN, fontsize=9, ha='center', fontweight='bold')
            elif "NO known" in item:
                ax.text(74, y, item, color=GREEN, fontsize=9, ha='center')
            else:
                ax.text(74, y, item, color=SILVER, fontsize=9, ha='center')
            y -= 5
        
        # Theorem at bottom
        theorem = FancyBboxPatch((5, 3), 90, 10, boxstyle="round,pad=0.3",
                                 facecolor=ACCENT, edgecolor=BLUE, linewidth=2)
        ax.add_patch(theorem)
        ax.text(50, 9, "Theorem: If M-LWE is quantum-hard, hybrid ECDH+Kyber provides post-quantum",
               color=WHITE, fontsize=8, ha='center', style='italic')
        ax.text(50, 5, "confidentiality even when ECDH is broken — defense in depth works.",
               color=WHITE, fontsize=8, ha='center', style='italic')
        
        p = self._save(fig, "security_comparison.png")
        print(f"  📊 Comparison: security_comparison.png")
        return p


def main():
    parser = argparse.ArgumentParser(description="INSANE Quantum Attack Visualizer")
    parser.add_argument("--outdir", default="quantum_demo_outputs", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    print("\n" + "🔥" * 30)
    print("    INSANE QUANTUM ATTACK VISUALIZER")
    print("    Watch ECDH die. Watch Hybrid survive.")
    print("🔥" * 30 + "\n")
    
    random.seed(args.seed)
    
    # Initialize
    ec = ToyEC()
    viz = InsaneViz(args.outdir)
    
    # Demo A: Classical ECDH
    print("🎬 DEMO A: CLASSICAL ECDH (watch it die)...\n")
    k_c = random.randint(2, ec.n - 2)
    k_s = random.randint(2, ec.n - 2)
    P_c = ec.mul(k_c, ec.G)[0]
    P_s = ec.mul(k_s, ec.G)[0]
    S = ec.mul(k_c, P_s)[0]
    
    ecdh_secret_a = hashlib.sha256(point_bytes(S)).digest()
    session_key_a = hkdf_sha256(ecdh_secret_a, b"classical-salt", b"classical-demo")
    
    print(f"  Client: k_c={k_c}, P_c={P_c}")
    print(f"  Server: k_s={k_s}, P_s={P_s}")
    print(f"  Shared: S={S}")
    print(f"  Session key: {session_key_a.hex()[:32]}...")
    print(f"  Attacker will recover: k_c = {k_c}\n")
    
    recovered_k = viz.demo_a(ec, k_c, k_s, P_c, P_s, S)
    print(f"  ✓ Recovered: k_c = {recovered_k}\n")
    
    # Demo B: Hybrid
    print("🎬 DEMO B: HYBRID ECDH + KYBER (watch it survive)...\n")
    k_c2 = random.randint(2, ec.n - 2)
    k_s2 = random.randint(2, ec.n - 2)
    P_c2 = ec.mul(k_c2, ec.G)[0]
    P_s2 = ec.mul(k_s2, ec.G)[0]
    S2 = ec.mul(k_c2, P_s2)[0]
    ecdh_secret_b = hashlib.sha256(point_bytes(S2)).digest()
    
    kem = run_kyber()
    transcript = hashlib.sha256(f"{P_c2}{P_s2}{kem['pk']}{kem['ct']}".encode()).digest()
    hybrid_key = hybrid_kdf(ecdh_secret_b, kem['ss'], transcript)
    
    print(f"  ECDH: k_c={k_c2}, P_c={P_c2}")
    print(f"  Kyber: {kem['name']}")
    print(f"  Hybrid key: {hybrid_key.hex()[:40]}...")
    print(f"  Attacker breaks ECDH (gets ss_ECDH) but cannot get ss_Kyber\n")
    
    viz.demo_b(ec, k_c2, P_c2, P_s2, ecdh_secret_b, kem, hybrid_key)
    
    # Comparison
    print("📊 Creating comparison theorem...\n")
    viz.create_comparison(ec, k_c2, P_c2, P_s2, ecdh_secret_b, kem, hybrid_key)
    
    print("\n" + "=" * 60)
    print("✅ ALL DONE!")
    print(f"\n📁 Output directory: {args.outdir}/")
    print(f"  🔥 demo_a_ecdh_dies.gif     — Watch ECDH get destroyed")
    print(f"  🔥 demo_b_hybrid_lives.gif  — Watch hybrid survive quantum attack")
    print(f"  📊 security_comparison.png   — Theorem figure")
    
    print("\n🎯 For your thesis defense:")
    print("  1. Start with demo_a_ecdh_dies.gif — shows the threat")
    print("  2. Explain how Shor's/BSGS works (frames 8-16)")
    print("  3. Show demo_b_hybrid_lives.gif — shows the solution")
    print("  4. Point to Kyber wall (frame 6-10) and lattice search failure")
    print("  5. End with security_comparison.png — the theorem")
    print("\n💡 Dual Hardness Argument: Need BOTH DLP AND M-LWE broken!")
    print("   Even quantum can't break M-LWE = Session key stays SAFE 🔒\n")

if __name__ == "__main__":
    main()