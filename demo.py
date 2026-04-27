#!/usr/bin/env python3
"""
ULTRA-DETAILED QUANTUM ATTACK EXPLAINER
Kurzgesagt-style visual journey through ECDH, Shor's Algorithm, and Post-Quantum Security
Each concept explained visually step-by-step
"""

import os
import math
import random
import hashlib
import colorsys
from typing import Tuple, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon, Arc, FancyArrowPatch, Wedge
import numpy as np
from PIL import Image

# =========================
# Configuration
# =========================
OUTPUT_DIR = "quantum_explainer_frames"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Beautiful color palette
BG = "#0a0a2e"
BG_LIGHT = "#0f0f3a"
PANEL = "#151545"
BOX = "#1a1a50"
WHITE = "#e8e8ff"
SILVER = "#a0a0c0"
RED = "#ff3355"
RED_DARK = "#cc0033"
GREEN = "#00ff88"
GREEN_DARK = "#00cc66"
BLUE = "#4488ff"
BLUE_DARK = "#2266cc"
YELLOW = "#ffdd00"
ORANGE = "#ff8800"
PURPLE = "#bb44ff"
CYAN = "#00ddff"
PINK = "#ff44aa"

class UltraDetailedExplainer:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.ec_p = 11
        self.ec_a = 1
        self.ec_b = 6
        self.ec_G = (2, 7)
        self.ec_n = 13
        self.frame_counter = 0
        self.all_frames = []

    def _create_fig(self, title="", subtitle=""):
        """Create a professional figure"""
        fig = plt.figure(figsize=(18, 10), facecolor=BG, dpi=120)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(BG)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        
        # Top decorative bar
        top_bar = FancyBboxPatch((0, 94), 100, 6, boxstyle="round,pad=0.1",
                                facecolor=PANEL, edgecolor=BLUE, linewidth=2)
        ax.add_patch(top_bar)
        
        if title:
            ax.text(50, 97.5, title, color=WHITE, fontsize=20, ha='center', va='center', 
                   fontweight='bold', fontfamily='serif')
        if subtitle:
            ax.text(50, 94, subtitle, color=SILVER, fontsize=12, ha='center', va='center',
                   fontstyle='italic', fontfamily='serif')
        
        return fig, ax

    def _save_frame(self, fig):
        """Save frame and return path"""
        frame_path = os.path.join(self.output_dir, f"frame_{self.frame_counter:05d}.png")
        fig.savefig(frame_path, dpi=120, facecolor=BG, edgecolor='none', bbox_inches='tight')
        plt.close(fig)
        self.all_frames.append(frame_path)
        self.frame_counter += 1
        return frame_path

    def _add_box(self, ax, x, y, w, h, title, content, edge_color=BLUE, title_color=None, fontsize=10):
        """Add a styled box with content"""
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5", 
                            facecolor=BOX, edgecolor=edge_color, linewidth=1.5)
        ax.add_patch(box)
        
        if title_color is None:
            title_color = edge_color
        
        if title:
            ax.text(x + w/2, y + h - 3, title, color=title_color, fontsize=fontsize+2, 
                   ha='center', va='center', fontweight='bold', fontfamily='serif')
        
        if isinstance(content, list):
            current_y = y + h - 8
            for line in content:
                ax.text(x + 2, current_y, line, color=SILVER, fontsize=fontsize, 
                       ha='left', va='top', fontfamily='serif')
                current_y -= 4
        else:
            ax.text(x + w/2, y + h/2 - 2, content, color=SILVER, fontsize=fontsize,
                   ha='center', va='center', fontfamily='serif')

    def _add_glow_text(self, ax, x, y, text, color, size=14, align='center'):
        """Add text with glow effect"""
        for offset in [(0.3, -0.3), (0.2, -0.2)]:
            ax.text(x + offset[0], y + offset[1], text, color=color, fontsize=size,
                   ha=align, va='center', alpha=0.3, fontfamily='serif')
        ax.text(x, y, text, color=color, fontsize=size, ha=align, va='center',
               fontweight='bold', fontfamily='serif')

    def _add_arrow(self, ax, x1, y1, x2, y2, color=WHITE, style='->', lw=1.5):
        """Add an arrow"""
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle=style, color=color, lw=lw))

    def create_intro_sequence(self):
        """Chapter 0: Introduction - What are we trying to protect?"""
        print("Creating Introduction Sequence...")
        
        # Frame 0: Title card
        fig, ax = self._create_fig("HOW QUANTUM COMPUTERS BREAK ENCRYPTION", "")
        self._add_glow_text(ax, 50, 80, "A Visual Journey Through Cryptography", CYAN, 16)
        
        # Visual: Lock turning into broken pieces
        lock_center = (50, 50)
        # Draw a lock
        lock_body = FancyBboxPatch((lock_center[0]-8, lock_center[1]-6), 16, 12, 
                                   boxstyle="round,pad=0.3", facecolor=PANEL, 
                                   edgecolor=GREEN, linewidth=3)
        ax.add_patch(lock_body)
        # Shackle
        theta = np.linspace(0, np.pi, 30)
        r = 7
        shackle_x = lock_center[0] + r * np.cos(theta)
        shackle_y = lock_center[1] + 6 + r * np.sin(theta)
        ax.plot(shackle_x, shackle_y, color=GREEN, linewidth=4)
        
        ax.text(50, 30, "Session Key: 45efb1008f87ae125d45f4b488fabd6a...", 
               color=GREEN, fontsize=8, ha='center', fontfamily='monospace')
        
        self._add_glow_text(ax, 50, 15, "What happens when quantum computers arrive?", YELLOW, 13)
        self._save_frame(fig)
        
        # Frame 1: The Problem
        fig, ax = self._create_fig("THE PROBLEM", "Why your private messages are at risk")
        
        self._add_box(ax, 5, 70, 42, 25, "Classical Encryption", [
            "RSA, ECDH, ECDSA...",
            "Security based on:",
            "• Factoring large numbers",
            "• Discrete logarithm problem",
            "These are HARD for classical computers"
        ], BLUE)
        
        self._add_box(ax, 53, 70, 42, 25, "Quantum Threat", [
            "Shor's Algorithm (1994)",
            "Quantum computer can:",
            "• Factor numbers in polynomial time",
            "• Solve discrete log efficiently",
            "These become EASY for quantum computers"
        ], RED)
        
        # Visual: Classical vs Quantum
        # Classical computer (slow)
        rect_cl = FancyBboxPatch((10, 40), 30, 20, boxstyle="round,pad=0.3",
                                facecolor=BOX, edgecolor=BLUE, linewidth=1)
        ax.add_patch(rect_cl)
        ax.text(25, 55, "Classical Computer", color=BLUE, fontsize=10, ha='center', fontweight='bold')
        ax.text(25, 48, "2^128 operations", color=SILVER, fontsize=9, ha='center')
        ax.text(25, 43, "= Lifetime of universe", color=SILVER, fontsize=9, ha='center')
        
        # Quantum computer (fast)
        rect_q = FancyBboxPatch((60, 40), 30, 20, boxstyle="round,pad=0.3",
                               facecolor=BOX, edgecolor=RED, linewidth=1)
        ax.add_patch(rect_q)
        ax.text(75, 55, "Quantum Computer", color=RED, fontsize=10, ha='center', fontweight='bold')
        ax.text(75, 48, "~1000 operations", color=SILVER, fontsize=9, ha='center')
        ax.text(75, 43, "= Seconds", color=SILVER, fontsize=9, ha='center')
        
        # Arrow showing transition
        self._add_arrow(ax, 42, 50, 58, 50, RED, '-|>', 3)
        ax.text(50, 55, "BREAKS", color=RED, fontsize=8, ha='center', fontweight='bold')
        
        self._add_glow_text(ax, 50, 15, "Question: Can we protect against quantum attacks?", YELLOW, 13)
        self._save_frame(fig)

    def create_ecdh_explanation(self):
        """Chapter 1: ECDH Explained Simply"""
        print("Creating ECDH Explanation...")
        
        # Frame: What is ECDH?
        fig, ax = self._create_fig("ELLIPTIC CURVE DIFFIE-HELLMAN", "The foundation of secure messaging")
        
        self._add_box(ax, 5, 65, 42, 30, "The Problem ECDH Solves", [
            "Alice and Bob want to agree on a",
            "secret key over a PUBLIC channel.",
            "",
            "Anyone can see their messages!",
            "",
            "Solution: Mathematics that is",
            "easy to compute but HARD to reverse.",
            "",
            "Like mixing paint colors:",
            "Easy to mix, impossible to separate!"
        ], BLUE)
        
        # Visual: Paint mixing analogy
        # Paint can 1
        circle1 = Circle((65, 80), 5, facecolor=RED, edgecolor=WHITE, linewidth=1)
        ax.add_patch(circle1)
        ax.text(65, 87, "Alice's\nSecret", color=SILVER, fontsize=7, ha='center')
        
        # Paint can 2
        circle2 = Circle((85, 80), 5, facecolor=BLUE, edgecolor=WHITE, linewidth=1)
        ax.add_patch(circle2)
        ax.text(85, 87, "Bob's\nSecret", color=SILVER, fontsize=7, ha='center')
        
        # Mixed paint
        circle3 = Circle((75, 68), 5, facecolor=PURPLE, edgecolor=WHITE, linewidth=1)
        ax.add_patch(circle3)
        ax.text(75, 64, "Shared\nSecret", color=SILVER, fontsize=7, ha='center')
        
        # Arrows
        self._add_arrow(ax, 67, 78, 73, 72, PURPLE)
        self._add_arrow(ax, 83, 78, 77, 72, PURPLE)
        
        self._add_box(ax, 5, 30, 90, 25, "The Mathematics", [
            "1. Choose a public starting point G (like a base color)",
            "2. Alice picks secret number a, computes a·G (her color mix)",
            "3. Bob picks secret number b, computes b·G (his color mix)",
            "4. They exchange a·G and b·G publicly",
            "5. Alice computes a·(b·G) = ab·G",
            "6. Bob computes b·(a·G) = ab·G",
            "Both arrive at the SAME secret point!"
        ], GREEN)
        
        ax.text(50, 15, "The magic: From G and a·G, you cannot find a (Discrete Log Problem)", 
               color=YELLOW, fontsize=10, ha='center', fontstyle='italic')
        
        self._save_frame(fig)
        
        # Frame: Visual ECDH on actual curve
        fig, ax = self._create_fig("ECDH IN ACTION", "Visualizing on a toy elliptic curve")
        
        # Draw the elliptic curve
        ec_points = []
        for x in range(self.ec_p):
            rhs = (x**3 + self.ec_a * x + self.ec_b) % self.ec_p
            for y in range(self.ec_p):
                if (y * y) % self.ec_p == rhs:
                    ec_points.append((x, y))
        
        # Plot curve
        for point in ec_points:
            ax.plot(point[0] * 6 + 5, point[1] * 6 + 5, 'o', color=BLUE, markersize=8, alpha=0.4)
        
        # Plot generator
        G_vis = (self.ec_G[0] * 6 + 5, self.ec_G[1] * 6 + 5)
        ax.plot(G_vis[0], G_vis[1], '*', color=GREEN, markersize=25, markeredgecolor=WHITE, markeredgewidth=2)
        ax.text(G_vis[0], G_vis[1] + 3, 'G (Starting Point)', color=GREEN, fontsize=10, ha='center', fontweight='bold')
        
        # Show the operation
        # Compute some multiples for visualization
        k_c = random.randint(2, self.ec_n-1)
        
        current = (0, 0)
        points_to_show = [(0, 0)]
        for i in range(k_c):
            # Manual EC addition
            if current == (0, 0):
                current = self.ec_G
            else:
                # Simplified addition for visualization
                current = ((current[0] + self.ec_G[0]) % self.ec_p, 
                          (current[1] + self.ec_G[1] + current[0]) % self.ec_p)
            points_to_show.append(current)
        
        # Show the path
        for i, point in enumerate(points_to_show[:5]):  # Show first 5 steps
            if i > 0:
                x_vis = point[0] * 6 + 5
                y_vis = point[1] * 6 + 5
                prev_x = points_to_show[i-1][0] * 6 + 5
                prev_y = points_to_show[i-1][1] * 6 + 5
                
                ax.plot(x_vis, y_vis, 'o', color=YELLOW, markersize=10, markeredgecolor=WHITE)
                ax.annotate('', xy=(x_vis, y_vis), xytext=(prev_x, prev_y),
                           arrowprops=dict(arrowstyle='->', color=YELLOW, lw=2, alpha=0.7))
                ax.text(x_vis + 1, y_vis + 1, f'{i}G', color=YELLOW, fontsize=7)
        
        ax.plot(points_to_show[-1][0] * 6 + 5, points_to_show[-1][1] * 6 + 5, 
               's', color=RED, markersize=15, markeredgecolor=WHITE)
        ax.text(points_to_show[-1][0] * 6 + 5, points_to_show[-1][1] * 6 + 8,
               f'Public Key = {k_c}·G', color=RED, fontsize=12, ha='center', fontweight='bold')
        
        self._add_box(ax, 5, 70, 40, 20, "What's Happening", [
            f"Starting from G (green star)",
            f"Jump to 1G, 2G, 3G... (yellow dots)",
            f"After {k_c} jumps, reach {k_c}G",
            f"This is the PUBLIC KEY",
            f"Knowing G and {k_c}G, can you find {k_c}?",
            "That's the DISCRETE LOG PROBLEM!"
        ], YELLOW)
        
        ax.text(5, 65, "The security: Finding the number of jumps is HARD", 
               color=RED, fontsize=8, fontweight='bold')
        
        self._save_frame(fig)

    def create_shors_explanation(self):
        """Chapter 2: Shor's Algorithm Explained"""
        print("Creating Shor's Algorithm Explanation...")
        
        # Frame: How Shor's works
        fig, ax = self._create_fig("SHOR'S ALGORITHM", "How quantum computers break ECDH")
        
        self._add_box(ax, 2, 75, 96, 20, "The Core Idea", [
            "Shor's algorithm finds the PRIVATE KEY (k) from the PUBLIC KEY (k·G)",
            "It converts the discrete log problem into a PERIOD-FINDING problem",
            "Period finding is HARD for classical computers, EASY for quantum computers",
            "Quantum computers use SUPERPOSITION to check ALL possibilities simultaneously"
        ], RED)
        
        # Visual: Period finding concept
        # Draw a wave
        x_wave = np.linspace(10, 90, 200)
        y_wave = 25 + 5 * np.sin(x_wave / 3)
        ax.plot(x_wave, y_wave, color=PURPLE, linewidth=2)
        
        # Mark period
        ax.axvline(x=10 + 18.85, color=YELLOW, linestyle='--', alpha=0.5)
        ax.axvline(x=10 + 2*18.85, color=YELLOW, linestyle='--', alpha=0.5)
        ax.annotate('Period r', xy=(10 + 18.85, 32), xytext=(10 + 9, 35),
                   arrowprops=dict(arrowstyle='->', color=YELLOW), color=YELLOW, fontsize=10)
        
        self._add_glow_text(ax, 50, 15, "Once you find the period, you can compute the private key!", YELLOW, 12)
        
        self._save_frame(fig)
        
        # Frame: BSGS Visualization
        fig, ax = self._create_fig("BABY-STEP GIANT-STEP ALGORITHM", "Classical implementation of Shor's idea")
        
        self._add_box(ax, 2, 80, 45, 15, "Baby Steps", [
            "Compute: 0G, 1G, 2G, 3G, ...",
            f"Store all results in a table",
            f"m = ceil(√n) = {math.isqrt(self.ec_n)+1} steps"
        ], BLUE)
        
        self._add_box(ax, 53, 80, 45, 15, "Giant Steps", [
            "Start from target P_c",
            "Jump backward by mG each time",
            "Check if result is in baby step table",
            "If YES → Collision found!"
        ], ORANGE)
        
        # Visual: Show baby steps vs giant steps
        # Baby steps going up
        baby_x = 15
        for i in range(8):
            y_baby = 50 + i * 3
            circle = Circle((baby_x, y_baby), 1.2, facecolor=BLUE, edgecolor=WHITE, linewidth=1)
            ax.add_patch(circle)
            ax.text(baby_x, y_baby, f'{i}G', color=SILVER, fontsize=7, ha='center', va='center')
            
            if i > 0:
                self._add_arrow(ax, baby_x, y_baby - 2, baby_x, y_baby - 0.8, BLUE)
        
        # Giant steps coming down
        giant_x = 85
        for i in range(8):
            y_giant = 50 + i * 3
            circle = Circle((giant_x, y_giant), 1.2, facecolor=ORANGE, edgecolor=WHITE, linewidth=1)
            ax.add_patch(circle)
            ax.text(giant_x, y_giant, f'P-{i}mG', color=SILVER, fontsize=6, ha='center', va='center')
            
            if i > 0:
                self._add_arrow(ax, giant_x, y_giant - 2, giant_x, y_giant - 0.8, ORANGE)
        
        # Collision point
        ax.text(50, 45, "When they meet:", color=WHITE, fontsize=12, ha='center')
        ax.text(50, 40, "Collision = Private Key Found!", color=RED, fontsize=14, ha='center', fontweight='bold')
        
        # Show the math
        self._add_box(ax, 20, 5, 60, 30, "The Mathematics", [
            "If j·G = P_c - i·mG",
            "Then P_c = (i·m + j)·G",
            "Therefore: k_c = i·m + j !",
            "",
            "Time required: O(√n) instead of O(n)",
            "For n=13: 4 steps instead of 13",
            "For real ECDH (n≈2^256): 2^128 instead of 2^256",
            "That's IMPRACTICALLY LARGE for classical computers",
            "But polynomial for QUANTUM COMPUTERS!"
        ], WHITE, RED)
        
        self._save_frame(fig)

    def create_attack_sequence(self):
        """Chapter 3: The Attack in Action"""
        print("Creating Attack Sequence...")
        
        # Frame: Attack begins
        fig, ax = self._create_fig("THE ATTACK BEGINS", "Attacker intercepts public keys")
        
        # Network visualization
        # Client
        client_box = FancyBboxPatch((5, 70), 25, 20, boxstyle="round,pad=0.3",
                                   facecolor=BOX, edgecolor=GREEN, linewidth=2)
        ax.add_patch(client_box)
        ax.text(17.5, 85, "ALICE", color=GREEN, fontsize=12, ha='center', fontweight='bold')
        ax.text(17.5, 78, "Private: k_c = 7", color=SILVER, fontsize=8, ha='center')
        ax.text(17.5, 73, "Public: P_c = 7·G", color=YELLOW, fontsize=8, ha='center')
        
        # Server
        server_box = FancyBboxPatch((70, 70), 25, 20, boxstyle="round,pad=0.3",
                                   facecolor=BOX, edgecolor=GREEN, linewidth=2)
        ax.add_patch(server_box)
        ax.text(82.5, 85, "BOB", color=GREEN, fontsize=12, ha='center', fontweight='bold')
        ax.text(82.5, 78, "Private: k_s = 3", color=SILVER, fontsize=8, ha='center')
        ax.text(82.5, 73, "Public: P_s = 3·G", color=YELLOW, fontsize=8, ha='center')
        
        # Attack interception
        self._add_arrow(ax, 32, 80, 68, 80, YELLOW, '-', 2)
        ax.text(50, 83, "P_c → Network → P_s", color=YELLOW, fontsize=8, ha='center')
        
        # Attacker (eavesdropper)
        attacker_box = FancyBboxPatch((30, 40), 40, 20, boxstyle="round,pad=0.3",
                                     facecolor=BOX, edgecolor=RED, linewidth=2)
        ax.add_patch(attacker_box)
        ax.text(50, 55, "👁 EVE THE ATTACKER", color=RED, fontsize=12, ha='center', fontweight='bold')
        ax.text(50, 48, "Intercepted: G, P_c, P_s", color=RED, fontsize=9, ha='center')
        ax.text(50, 43, "Goal: Find k_c from P_c = k_c·G", color=RED, fontsize=9, ha='center')
        
        self._add_glow_text(ax, 50, 20, "With QUANTUM computer, Eve can find k_c!", RED, 14)
        self._save_frame(fig)
        
        # Frame: BSGS solving
        for step in range(5):
            fig, ax = self._create_fig(f"QUANTUM ATTACK - STEP {step+1}/5", "Baby-Step Giant-Step in action")
            
            m = math.isqrt(self.ec_n) + 1
            
            if step == 0:
                self._add_box(ax, 5, 80, 90, 15, "Phase 1: Baby Steps", 
                            ["Compute and store all baby steps: 0G, 1G, 2G, ..., (m-1)G",
                             "This is like filling a dictionary with possible positions"], BLUE)
            elif step == 1:
                self._add_box(ax, 5, 80, 90, 15, "Phase 2: Giant Steps",
                            ["Compute P_c - 0·mG, P_c - 1·mG, P_c - 2·mG, ...",
                             "After each computation, check if result is in baby step table"], ORANGE)
            elif step == 2:
                self._add_box(ax, 5, 80, 90, 15, "COLLISION FOUND!",
                            ["Found: P_c - 2·mG = 3G (from baby steps)",
                             "This means: P_c = (2·m + 3)·G"], GREEN)
            elif step == 3:
                self._add_box(ax, 5, 80, 90, 15, "PRIVATE KEY RECOVERED",
                            ["k_c = 2·m + 3 = 7",
                             "Verification: 7·G = P_c ✓"], RED)
            else:  # step == 4
                self._add_box(ax, 5, 80, 90, 15, "SESSION KEY COMPROMISED",
                            ["Eve computes: S = k_c·P_s = 7·P_s",
                             "This is the SAME shared secret as Alice and Bob!",
                             "ALL encrypted messages can now be decrypted"], RED, RED)
            
            # Visual progress
            if step < 2:
                progress_text = f"Searching... ({step+1}/5)"
                progress_color = YELLOW
            elif step < 4:
                progress_text = "KEY FOUND!"
                progress_color = RED
            else:
                progress_text = "SYSTEM BROKEN"
                progress_color = RED
            
            self._add_glow_text(ax, 50, 50, progress_text, progress_color, 24)
            
            # Add mathematical details based on step
            if step == 2:
                ax.text(50, 30, "j·G = P_c - i·mG", color=WHITE, fontsize=14, ha='center', fontfamily='monospace')
                ax.text(50, 25, "j=3, i=2 → k_c = 2·4 + 3 = 7", color=GREEN, fontsize=14, ha='center', fontfamily='monospace')
            
            self._save_frame(fig)
        
        # Frame: Final result
        fig, ax = self._create_fig("❌ CLASSICAL ECDH: COMPLETELY BROKEN", "")
        
        # Big broken lock
        lock_center = (50, 50)
        # Broken pieces
        pieces = []
        for i in range(8):
            angle = i * np.pi * 2 / 8
            piece_x = lock_center[0] + np.cos(angle) * 15
            piece_y = lock_center[1] + np.sin(angle) * 15
            pieces.append((piece_x, piece_y))
            ax.plot(piece_x, piece_y, 'X', color=RED, markersize=12, alpha=0.6)
        
        ax.text(50, 70, "Session Key Exposed", color=RED, fontsize=20, ha='center', fontweight='bold')
        ax.text(50, 60, "K = HKDF(k_c · P_s)", color=SILVER, fontsize=14, ha='center', fontfamily='monospace')
        ax.text(50, 50, "Eve computes IDENTICAL key", color=RED, fontsize=12, ha='center')
        
        self._add_glow_text(ax, 50, 20, "One mathematical breakthrough = TOTAL COMPROMISE", RED, 16)
        self._save_frame(fig)

    def create_hybrid_solution(self):
        """Chapter 4: The Hybrid Solution"""
        print("Creating Hybrid Solution Explanation...")
        
        # Frame: Introducing hybrid
        fig, ax = self._create_fig("THE SOLUTION: HYBRID KEY EXCHANGE", "Defense in depth against quantum attacks")
        
        # Two layers
        self._add_box(ax, 5, 55, 42, 35, "Layer 1: Classical ECDH", [
            "Same as before",
            "Provides classical security",
            "Vulnerable to Shor's algorithm",
            "If broken: ecdh_secret exposed",
            "But ALONE this is dangerous!",
            "",
            "Status: ⚠️ QUANTUM-VULNERABLE"
        ], ORANGE)
        
        self._add_box(ax, 53, 55, 42, 35, "Layer 2: Post-Quantum KEM", [
            "CRYSTALS-Kyber (NIST FIPS 203)",
            "Security based on: Module-LWE",
            "Lattice-based cryptography",
            "NO known quantum attacks!",
            "Even Shor's algorithm cannot help",
            "",
            "Status: ✅ QUANTUM-RESISTANT"
        ], GREEN)
        
        # Combined key
        self._add_box(ax, 20, 15, 60, 25, "Final Session Key", [
            "K = HKDF(ecdh_secret || kyber_secret)",
            "",
            "🎯 Both components needed!",
            "If ECDH broken → only ecdh_secret known",
            "Kyber_secret remains UNKNOWN",
            "Attacker CANNOT compute final key!"
        ], BLUE)
        
        self._save_frame(fig)
        
        # Frame: Kyber lattice visualization
        fig, ax = self._create_fig("KYBER'S SECRET: THE MODULE-LWE PROBLEM", "Why quantum computers can't break it")
        
        self._add_box(ax, 5, 70, 90, 25, "The Module-LWE Problem", [
            "LWE = Learning With Errors",
            "Given: A (public matrix) and b = A·s + e (where e is small error)",
            "Problem: Find the secret vector s",
            "Classical hardness: Finding s requires solving hard lattice problems",
            "Quantum: Even Grover's algorithm gives only √ speedup (insufficient)",
            "Security level: Kyber-512 provides 128-bit post-quantum security"
        ], GREEN)
        
        # Lattice visualization
        for i in range(-5, 6):
            for j in range(-5, 6):
                x = 50 + i*5 + j*2
                y = 30 + i*3 - j*4
                ax.plot(x, y, 'o', color=GREEN, markersize=3, alpha=0.5)
        
        # Highlight the secret
        ax.plot(50, 30, 'o', color=RED, markersize=8, markeredgecolor=WHITE)
        ax.text(50, 27, 'Secret s', color=RED, fontsize=8, ha='center')
        
        ax.text(50, 15, "Finding the right lattice point among billions is IMPOSSIBLE without the key", 
               color=YELLOW, fontsize=10, ha='center')
        
        self._save_frame(fig)
        
        # Frame: Attack on hybrid
        for attack_step in range(4):
            fig, ax = self._create_fig(f"QUANTUM ATTACK ON HYBRID - PHASE {attack_step+1}", 
                                      "Trying to break both layers")
            
            if attack_step == 0:
                self._add_box(ax, 5, 70, 90, 25, "Phase 1: Attack ECDH Layer", [
                    "Eve runs Shor's algorithm on the ECDH component",
                    "Finds k_c from P_c = k_c·G",
                    "Recovers ecdh_secret successfully",
                    "ECDH layer: BROKEN"
                ], ORANGE)
                
                # Show ECDH breaking
                lock1 = FancyBboxPatch((30, 35), 15, 10, boxstyle="round,pad=0.3",
                                      facecolor=RED, edgecolor=RED, alpha=0.3)
                ax.add_patch(lock1)
                ax.text(37.5, 40, "ECDH\nBROKEN", color=RED, fontsize=10, ha='center', fontweight='bold')
                
                # Show Kyber still standing
                lock2 = FancyBboxPatch((55, 35), 15, 10, boxstyle="round,pad=0.3",
                                      facecolor=GREEN, edgecolor=GREEN, linewidth=2)
                ax.add_patch(lock2)
                ax.text(62.5, 40, "KYBER\nSECURE", color=GREEN, fontsize=10, ha='center', fontweight='bold')
                
            elif attack_step == 1:
                self._add_box(ax, 5, 70, 90, 25, "Phase 2: Attack Kyber Layer (M-LWE)", [
                    "Eve attempts to solve Module-LWE from public key + ciphertext",
                    "Best known quantum attack: lattice sieving ≈ 2^178 operations",
                    "That's still IMPRACTICALLY LARGE!",
                    "Even quantum computers need billions of years",
                    "Kyber layer: STILL SECURE"
                ], GREEN)
                
                # Show quantum computer failing
                ax.text(50, 45, "???", color=RED, fontsize=40, ha='center')
                ax.text(50, 35, "Unknown kyber_secret", color=RED, fontsize=12, ha='center')
                
            elif attack_step == 2:
                self._add_box(ax, 5, 70, 90, 25, "Phase 3: Attempt Session Key Recovery", [
                    "Eve has: ecdh_secret (from broken ECDH)",
                    "Eve lacks: kyber_secret (protected by M-LWE)",
                    "Session Key = HKDF(known || UNKNOWN)",
                    "Without kyber_secret: CANNOT compute final key!"
                ], RED)
                
                # Visual representation
                ax.text(30, 50, "ecdh_secret", color=RED, fontsize=12, ha='center')
                ax.text(50, 50, "‖", color=WHITE, fontsize=20, ha='center')
                ax.text(70, 50, "???????????", color=GREEN, fontsize=12, ha='center')
                
                self._add_glow_text(ax, 50, 30, "Result: UNKNOWN = Secure", YELLOW, 14)
                
            else:  # attack_step == 3
                self._add_box(ax, 5, 70, 90, 25, "RESULT: HYBRID WITHSTANDS QUANTUM ATTACK", [
                    "ECDH layer compromised (partial win for attacker)",
                    "Kyber layer holds strong against quantum attacks",
                    "Final session key remains SECURE",
                    "Defense in depth WORKS!"
                ], GREEN, GREEN)
                
                # Secure lock
                lock_center = (50, 35)
                lock = FancyBboxPatch((lock_center[0]-10, lock_center[1]-8), 20, 16,
                                     boxstyle="round,pad=0.5", facecolor=GREEN, 
                                     edgecolor=GREEN, alpha=0.3, linewidth=3)
                ax.add_patch(lock)
                ax.text(50, 35, "🔒 SECURE", color=GREEN, fontsize=16, ha='center', fontweight='bold')
            
            self._save_frame(fig)

    def create_final_comparison(self):
        """Chapter 5: Side-by-side comparison"""
        print("Creating Final Comparison...")
        
        # Frame: Comparison table
        fig, ax = self._create_fig("FINAL COMPARISON", "Classical ECDH vs Hybrid ECDH+Kyber")
        
        # Two columns
        # Classical
        self._add_box(ax, 5, 40, 42, 55, "CLASSICAL ECDH", [
            "Security: Discrete Log Problem",
            "Quantum attack: Shor's Algorithm",
            "Attack complexity: Polynomial O((log n)³)",
            "Result after quantum:",
            "  ✗ PRIVATE KEY RECOVERED",
            "  ✗ SESSION KEY EXPOSED",
            "  ✗ ALL TRAFFIC DECRYPTABLE",
            "",
            "Verdict: COMPLETELY BROKEN"
        ], RED)
        
        # Hybrid
        self._add_box(ax, 53, 40, 42, 55, "HYBRID ECDH+KYBER", [
            "Security: DLP AND Module-LWE",
            "Quantum attack on ECDH: Succeeds",
            "Quantum attack on Kyber: No known alg",
            "Result after quantum:",
            "  ✗ ECDH layer broken (partial)",
            "  ✓ Kyber layer secure",
            "  ✓ Session key remains SAFE",
            "  ✓ Traffic still encrypted",
            "",
            "Verdict: DEFENSE IN DEPTH"
        ], GREEN)
        
        # Arrows showing outcomes
        self._add_arrow(ax, 47, 30, 47, 15, RED, '-|>', 3)
        self._add_arrow(ax, 53, 30, 53, 15, GREEN, '-|>', 3)
        
        ax.text(26, 12, "TOTAL\nCOMPROMISE", color=RED, fontsize=14, ha='center', fontweight='bold')
        ax.text(74, 12, "SECURE\nSYSTEM", color=GREEN, fontsize=14, ha='center', fontweight='bold')
        
        self._save_frame(fig)
        
        # Frame: Final conclusion
        fig, ax = self._create_fig("CONCLUSION", "The path forward for post-quantum security")
        
        self._add_box(ax, 10, 60, 80, 30, "Key Insights", [
            "1. Classical ECDH relies on ONE mathematical problem (DLP)",
            "   → Quantum computers can break this efficiently → TOTAL FAILURE",
            "",
            "2. Hybrid ECDH+Kyber requires breaking TWO independent problems",
            "   → Breaking ECDH alone is NOT sufficient → PARTIAL SUCCESS for attacker",
            "",
            "3. Module-LWE (Kyber) remains hard even for quantum computers",
            "   → Provides long-term security in the post-quantum era"
        ], BLUE)
        
        self._add_box(ax, 10, 10, 80, 25, "For Your Thesis", [
            "Theorem: If M-LWE is quantum-hard, the hybrid scheme provides",
            "post-quantum confidentiality even when classical ECDH is broken.",
            "",
            "This is the dual-hardness argument:",
            "Security = min(security_of_layer1, security_of_layer2)",
            "Even if layer1 = 0, layer2 > 0 → overall security > 0"
        ], GREEN)
        
        self._save_frame(fig)

    def build_gif(self, output_name="quantum_explainer.gif", duration=150):
        """Build the final GIF"""
        print(f"\nBuilding final GIF: {output_name}")
        print(f"Total frames: {len(self.all_frames)}")
        
        images = []
        for frame_path in self.all_frames:
            img = Image.open(frame_path)
            images.append(img)
        
        gif_path = os.path.join(self.output_dir, output_name)
        images[0].save(gif_path, save_all=True, append_images=images[1:], 
                      duration=duration*8, loop=0, optimize=True)
        
        # Clean up individual frames
        for frame_path in self.all_frames:
            os.remove(frame_path)
        
        print(f"✅ GIF created: {gif_path}")
        print(f"📊 Size: {os.path.getsize(gif_path) / 1024 / 1024:.1f} MB")
        
        return gif_path

def main():
    print("🎬 ULTRA-DETAILED QUANTUM ATTACK EXPLAINER")
    print("=" * 60)
    print("Creating Kurzgesagt-style educational animation...")
    print("This will take a few minutes to render all frames...\n")
    
    explainer = UltraDetailedExplainer()
    
    print("📖 Chapter 0: Introduction")
    explainer.create_intro_sequence()
    print(f"   ✓ {explainer.frame_counter} frames created")
    
    print("\n📖 Chapter 1: Understanding ECDH")
    explainer.create_ecdh_explanation()
    print(f"   ✓ {explainer.frame_counter} frames total")
    
    print("\n📖 Chapter 2: Shor's Algorithm Explained")
    explainer.create_shors_explanation()
    print(f"   ✓ {explainer.frame_counter} frames total")
    
    print("\n📖 Chapter 3: The Attack in Action")
    explainer.create_attack_sequence()
    print(f"   ✓ {explainer.frame_counter} frames total")
    
    print("\n📖 Chapter 4: The Hybrid Solution")
    explainer.create_hybrid_solution()
    print(f"   ✓ {explainer.frame_counter} frames total")
    
    print("\n📖 Chapter 5: Final Comparison")
    explainer.create_final_comparison()
    print(f"   ✓ {explainer.frame_counter} frames total")
    
    print("\n🎬 Building final animation...")
    gif_path = explainer.build_gif()
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print(f"\n📁 Your animation is ready: {gif_path}")
    print("\n🎯 This animation covers:")
    print("  1. What ECDH is and how it works (with visual math)")
    print("  2. How Shor's algorithm breaks it (period finding → BSGS)")
    print("  3. The attack in real-time (step by step)")
    print("  4. Why hybrid ECDH+Kyber survives (dual-layer defense)")
    print("  5. Side-by-side comparison (broken vs secure)")
    print("\n💡 Perfect for thesis defense and research presentations!")

if __name__ == "__main__":
    main()