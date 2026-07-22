"""Generate fake but realistic French invoices as scanned-looking PDFs.

Outputs to the unprocessed/ folder.

Usage:
  uv run python generate_sample_invoices.py          # generates 10
  uv run python generate_sample_invoices.py 100      # generates 100
"""

import os
import random
from datetime import date, timedelta

import numpy as np
from fpdf import FPDF
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
QUALITY_DIRS = {
    "good": os.path.join(DATA_DIR, "unprocessed", "clean"),
    "bad": os.path.join(DATA_DIR, "unprocessed", "medium"),
    "ugly": os.path.join(DATA_DIR, "unprocessed", "ugly"),
}
for _d in QUALITY_DIRS.values():
    os.makedirs(_d, exist_ok=True)
OUTPUT_DIR = QUALITY_DIRS["good"]  # default, overridden per invoice in generate()

FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"

# ── Random data pools ──────────────────────────────────────────────────────────

FOURNISSEURS = [
    ("PLOMBERIE MARTIN & FILS", "14 rue des Artisans, 69003 Lyon", "04 72 11 22 33"),
    (
        "ELECTRICITE DUPONT SARL",
        "8 allée des Métiers, 31000 Toulouse",
        "05 61 44 55 66",
    ),
    ("MENUISERIE LEBLANC", "Zone Industrielle Nord, 59000 Lille", "03 20 12 34 56"),
    ("DATAFLOW SAS", "2 avenue de l'Innovation, 75008 Paris", "01 44 55 66 77"),
    (
        "MATERIAUX DU SUD SARL",
        "Zone Artisanale des Pins, 13300 Salon-de-Provence",
        "04 90 55 44 33",
    ),
    (
        "TRANSPORT GIRARD & CIE",
        "Route Nationale 7, 42000 Saint-Etienne",
        "04 77 33 22 11",
    ),
    ("AGENCE MEDIA CONCEPT", "17 rue de la Presse, 33000 Bordeaux", "05 56 78 90 12"),
    (
        "NETTOYAGE PRO SERVICES",
        "12 rue des Lilas, 69100 Villeurbanne",
        "04 78 66 55 44",
    ),
    ("SECURITE PLUS SA", "45 boulevard de la Sécurité, 06000 Nice", "04 93 22 33 44"),
    ("LOGISTIQUE EXPRESS", "Port de Commerce, 76600 Le Havre", "02 35 44 55 66"),
    ("IMPRIMERIE CENTRALE", "6 rue Gutenberg, 67000 Strasbourg", "03 88 77 66 55"),
    ("FOURNITURES BUREAU DELTA", "22 avenue Kléber, 75116 Paris", "01 47 23 45 67"),
    (
        "MAINTENANCE INDUSTRIELLE ROUX",
        "Parc Technologique, 38000 Grenoble",
        "04 76 88 99 00",
    ),
    ("CATERING & CO", "15 rue de la Gastronomie, 69001 Lyon", "04 72 33 44 55"),
    ("IT SOLUTIONS PRO", "Tour Défense, 92800 Puteaux", "01 49 88 77 66"),
]

CLIENTS = [
    ("SCI LES ACACIAS", "3 impasse des Lilas, 69007 Lyon"),
    ("GROUPE IMMOBILIER RENARD SA", "17 rue du Parc, 33000 Bordeaux"),
    ("BATISSEUR PROVENCAL SAS", "6 Lotissement les Oliviers, 13100 Aix-en-Provence"),
    ("DISTRIBUTION MARTIN & FILS", "ZAC des Portes, 31670 Labège"),
    ("HOTEL RESTAURANT DU LAC", "Bord du Lac, 74290 Talloires"),
    ("CABINET LEGAL MOREAU", "8 place du Palais, 75001 Paris"),
    ("CLINIQUE DES ALPES", "Route des Alpes, 38700 La Tronche"),
    ("BOULANGERIE ARTISANALE SIMON", "4 rue du Pain, 44000 Nantes"),
    ("AUTO-ECOLE DUPUIS", "23 avenue de la Gare, 54000 Nancy"),
    ("ASSOCIATION SPORT LOISIRS", "Complexe Sportif, 59300 Valenciennes"),
]

IBANS = [
    "FR76 3000 4028 3700 0100 7890 143",
    "FR76 1420 6600 0120 0336 7890 071",
    "FR76 3005 7190 0005 0017 6420 085",
    "FR76 1027 8060 0001 0290 5412 086",
    "FR76 3000 6000 0112 3456 7890 189",
    "FR76 2004 1010 0505 0013 4567 089",
]

BICS = ["BNPAFRPPXXX", "AGRIFRPP882", "CMCIFRPP", "CEPAFRPP751", "SOGEFRPP"]

PRODUITS_SERVICES = [
    [
        ("Fourniture et pose robinetterie", 1, 180),
        ("Joint et pièces diverses", 1, 35),
        ("Main d'oeuvre (3h)", 3, 65),
    ],
    [
        ("Câblage tableau électrique", 1, 450),
        ("Disjoncteurs et matériel", 1, 120),
        ("Main d'oeuvre (4h)", 4, 75),
    ],
    [
        ("Pose fenêtres double vitrage (x3)", 3, 380),
        ("Joints d'étanchéité", 1, 45),
        ("Main d'oeuvre", 1, 240),
    ],
    [
        ("Abonnement logiciel Pro (12 mois)", 1, 990),
        ("Support technique prioritaire", 1, 200),
    ],
    [
        ("Livraison matériaux chantier", 1, 85),
        ("Ciment sac 25kg (x20)", 20, 8.20),
        ("Parpaings palette", 2, 89),
    ],
    [
        ("Transport marchandises 500km", 1, 320),
        ("Frais de péage", 1, 45),
        ("Assurance transport", 1, 35),
    ],
    [
        ("Création site internet", 1, 1200),
        ("Référencement SEO (6 mois)", 1, 480),
        ("Hébergement annuel", 1, 120),
    ],
    [("Nettoyage locaux (mensuel)", 1, 480), ("Produits d'entretien", 1, 65)],
    [
        ("Surveillance alarme (trimestre)", 1, 290),
        ("Maintenance système", 1, 150),
        ("Badge accès (x5)", 5, 25),
    ],
    [("Location entrepôt 200m2 (mois)", 1, 1800), ("Charges et taxes", 1, 320)],
    [
        ("Impression brochures A4 (1000ex)", 1, 340),
        ("Plastification couverture", 1, 80),
    ],
    [
        ("Fournitures bureau (commande)", 1, 245),
        ("Cartouches imprimante (x4)", 4, 28),
        ("Ramettes papier (x10)", 10, 5.50),
    ],
    [
        ("Révision machine CNC", 1, 580),
        ("Pièces de rechange", 1, 195),
        ("Main d'oeuvre technicien", 4, 95),
    ],
    [
        ("Buffet réunion (30 pers)", 1, 450),
        ("Location matériel (verres, etc.)", 1, 120),
    ],
    [("Audit sécurité informatique", 1, 1500), ("Rapport et recommandations", 1, 350)],
]

TVA_RATES = [0.20, 0.10, 0.055]


def _random_date(year: int = 2024) -> tuple[str, str]:
    start = date(year, 1, 1)
    d = start + timedelta(days=random.randint(0, 364))
    echeance = d + timedelta(days=random.choice([30, 45, 60]))
    return d.strftime("%d/%m/%Y"), echeance.strftime("%d/%m/%Y")


def _invoice_number(i: int) -> str:
    prefixes = ["FA", "FC", "INV", "F", "FAC"]
    return f"{random.choice(prefixes)}-2024-{i:04d}"


def _siret() -> str:
    return f"{random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(10000, 99999)}"


def _scan_effect(img: Image.Image, quality: str = "mixed") -> Image.Image:
    """quality: "good" | "bad" | "ugly" | "mixed" (random pick)."""
    if quality == "mixed":
        quality = random.choices(["good", "bad", "ugly"], weights=[0.3, 0.4, 0.3])[0]

    w, h = img.size

    if quality == "good":
        angle = random.uniform(-0.8, 0.8)
        noise_std = random.uniform(2, 6)
        blur_r = random.uniform(0.2, 0.5)
        contrast = random.uniform(0.92, 1.05)
        brightness = random.uniform(0.95, 1.03)
    elif quality == "bad":
        angle = random.uniform(-2.5, 2.5)
        noise_std = random.uniform(8, 18)
        blur_r = random.uniform(0.6, 1.2)
        contrast = random.uniform(0.75, 0.95)
        brightness = random.uniform(0.82, 1.15)
    else:  # ugly
        angle = random.uniform(-4.0, 4.0)
        noise_std = random.uniform(15, 30)
        blur_r = random.uniform(1.0, 2.2)
        contrast = random.uniform(0.55, 0.80)
        brightness = random.uniform(0.70, 1.30)

    # Rotation
    fill_color = (
        random.randint(235, 255),
        random.randint(232, 252),
        random.randint(225, 248),
    )
    img = img.rotate(angle, fillcolor=fill_color, expand=False)

    # Noise
    arr = np.array(img).astype(np.float32)
    noise = np.random.normal(0, noise_std, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # Blur
    img = img.filter(ImageFilter.GaussianBlur(radius=blur_r))

    # Contrast & brightness
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)

    # Vignette (dark edges) — surtout sur bad/ugly
    if quality in ("bad", "ugly") and random.random() < 0.6:
        arr = np.array(img).astype(np.float32)
        strength = (
            random.uniform(0.25, 0.55)
            if quality == "ugly"
            else random.uniform(0.1, 0.3)
        )
        xs = np.linspace(-1, 1, w)
        ys = np.linspace(-1, 1, h)
        xv, yv = np.meshgrid(xs, ys)
        vignette = 1 - strength * (xv**2 + yv**2)
        vignette = np.clip(vignette, 0, 1)
        arr *= vignette[:, :, np.newaxis]
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # Tache aléatoire (café / doigt) — ugly seulement
    if quality == "ugly" and random.random() < 0.4:
        ImageDraw.Draw(img)
        cx = random.randint(w // 4, 3 * w // 4)
        cy = random.randint(h // 4, 3 * h // 4)
        rx, ry = random.randint(15, 40), random.randint(10, 25)
        alpha = random.randint(60, 130)
        color = (
            random.randint(150, 200),
            random.randint(120, 170),
            random.randint(80, 130),
            alpha,
        )
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry], fill=color
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    return img


def _pdf_to_scanned_pdf(pdf_bytes: bytes, filename: str) -> None:
    pages = convert_from_bytes(pdf_bytes, dpi=150)
    scanned = [_scan_effect(p.convert("RGB")) for p in pages]
    out_path = os.path.join(OUTPUT_DIR, filename)
    scanned[0].save(out_path, "PDF", save_all=True, append_images=scanned[1:])


def _setup_fonts(pdf: FPDF) -> None:
    pdf.add_font("Sans", "", FONT_REGULAR)
    pdf.add_font("Sans", "B", FONT_BOLD)


# ── Layout variants ────────────────────────────────────────────────────────────


def _layout_classic(i: int) -> bytes:
    """Classic French invoice: header top-left, table, totals."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    bic = random.choice(BICS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    pdf.set_font("Sans", "B", 15)
    pdf.cell(0, 8, fourn_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 5, f"Tél : {fourn_tel}   SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, f"FACTURE N° {inv_num}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(
        0,
        5,
        f"Date : {date_str}     Echéance : {echeance_str}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    pdf.set_font("Sans", "B", 9)
    pdf.cell(0, 5, "Facturé à :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_fill_color(225, 225, 225)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(90, 7, "Désignation", border=1, fill=True)
    pdf.cell(20, 7, "Qté", border=1, fill=True, align="C")
    pdf.cell(35, 7, "Prix U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 7, "Total HT", border=1, fill=True, align="R")
    pdf.ln()

    total_ht = 0
    pdf.set_font("Sans", "", 9)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(90, 6, desc, border=1)
        pdf.cell(20, 6, str(qty), border=1, align="C")
        pdf.cell(35, 6, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 6, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)

    pdf.ln(3)
    pdf.set_font("Sans", "", 9)
    for label, val in [
        ("Total HT :", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}% :", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.cell(145, 5, label, align="R")
        pdf.cell(25, 5, val, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.cell(145, 6, "TOTAL TTC :", align="R")
    pdf.cell(25, 6, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, f"Virement : {iban}   BIC : {bic}", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _layout_modern(i: int) -> bytes:
    """Modern invoice: colored header band, right-aligned invoice info."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, _fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    bic = random.choice(BICS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    r, g, b = random.choice([(30, 80, 160), (0, 120, 80), (140, 30, 30), (80, 40, 120)])

    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Sans", "B", 14)
    pdf.cell(0, 10, f"  {fourn_name}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 4, f"SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Sans", "B", 10)
    pdf.cell(0, 7, f"  FACTURE N° {inv_num}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Sans", "", 9)
    pdf.ln(3)
    pdf.cell(95, 5, f"Date : {date_str}")
    pdf.cell(0, 5, f"Echéance : {echeance_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Sans", "B", 9)
    pdf.cell(0, 5, "Destinataire :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_fill_color(230, 235, 245)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(95, 7, "Prestation / Produit", border=1, fill=True)
    pdf.cell(20, 7, "Qté", border=1, fill=True, align="C")
    pdf.cell(30, 7, "P.U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 7, "Total HT", border=1, fill=True, align="R")
    pdf.ln()

    total_ht = 0
    pdf.set_font("Sans", "", 9)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(95, 6, desc, border=1)
        pdf.cell(20, 6, str(qty), border=1, align="C")
        pdf.cell(30, 6, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 6, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)

    pdf.ln(3)
    pdf.set_font("Sans", "", 9)
    for label, val in [
        ("Sous-total HT", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.cell(145, 5, label, align="R")
        pdf.cell(25, 5, val, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 10)
    pdf.cell(145, 6, "TOTAL TTC", align="R")
    pdf.cell(25, 6, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, f"IBAN : {iban}   BIC : {bic}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 4, f"Référence à rappeler : {inv_num}", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _layout_two_col(i: int) -> bytes:
    """Two-column header (fournisseur left, invoice info right)."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    bic = random.choice(BICS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    pdf.set_font("Sans", "B", 13)
    pdf.cell(95, 7, fourn_name)
    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, "FACTURE", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(95, 4, fourn_addr)
    pdf.cell(0, 4, f"N° : {inv_num}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 4, f"SIRET : {_siret()}")
    pdf.cell(0, 4, f"Date : {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 4, f"Tél : {fourn_tel}")
    pdf.cell(
        0, 4, f"Echéance : {echeance_str}", align="R", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(3)
    pdf.set_draw_color(160, 160, 160)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Sans", "B", 8)
    pdf.cell(0, 4, "CLIENT :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, f"{client_name} — {client_addr}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    widths = [15, 73, 15, 28, 28, 11]
    headers = ["Réf.", "Désignation", "Qté", "Prix U. HT", "Total HT", "TVA"]
    pdf.set_fill_color(215, 215, 215)
    pdf.set_font("Sans", "B", 8)
    for w, h in zip(widths, headers, strict=False):
        pdf.cell(w, 6, h, border=1, fill=True, align="C")
    pdf.ln()

    total_ht = 0
    pdf.set_font("Sans", "", 8)
    for j, (desc, qty, pu) in enumerate(produits):
        t = round(qty * pu, 2)
        total_ht += t
        ref = f"ART-{j + 1:03d}"
        for w, val in zip(
            widths,
            [
                ref,
                desc,
                str(qty),
                f"{pu:.2f} EUR",
                f"{t:.2f} EUR",
                f"{int(tva_rate * 100)}%",
            ],
            strict=False,
        ):
            pdf.cell(w, 5, val, border=1, align="C" if w <= 15 else "L")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)

    pdf.ln(3)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        (f"Base HT {int(tva_rate * 100)}%", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
        ("Total HT", f"{total_ht:.2f} EUR"),
        ("TOTAL TTC", f"{ttc:.2f} EUR"),
    ]:
        pdf.cell(150, 4, label, align="R")
        pdf.cell(20, 4, val, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Sans", "", 7)
    pdf.cell(
        0, 4, f"Virement : IBAN {iban}   BIC : {bic}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.cell(
        0,
        4,
        "Pénalités de retard : 3x taux légal. Indemnité forfaitaire : 40 EUR.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


def _layout_minimal(i: int) -> bytes:
    """Freelance / auto-entrepreneur : pas de bordures, tout en texte."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, _ = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    pdf.set_font("Sans", "B", 11)
    pdf.cell(0, 7, fourn_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 4, f"SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Sans", "B", 9)
    pdf.cell(0, 5, f"Facture n° {inv_num}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(
        0,
        4,
        f"Emise le {date_str} — Echéance {echeance_str}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    pdf.set_font("Sans", "", 8)
    pdf.cell(
        0, 4, f"Client : {client_name}, {client_addr}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(6)

    total_ht = 0
    pdf.set_font("Sans", "B", 8)
    pdf.cell(110, 5, "Prestation")
    pdf.cell(20, 5, "Qté", align="R")
    pdf.cell(30, 5, "Total HT", align="R")
    pdf.ln()
    pdf.set_draw_color(180, 180, 180)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(1)

    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(110, 5, desc)
        pdf.cell(20, 5, str(qty), align="R")
        pdf.cell(30, 5, f"{t:.2f} EUR", align="R")
        pdf.ln()

    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(3)

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.set_font("Sans", "", 8)
    pdf.cell(130, 4, "Total HT", align="R")
    pdf.cell(30, 4, f"{total_ht:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(130, 4, f"TVA {int(tva_rate * 100)}%", align="R")
    pdf.cell(30, 4, f"{tva_amt:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.cell(130, 5, "Net à payer", align="R")
    pdf.cell(30, 5, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Sans", "", 7)
    pdf.cell(0, 4, f"Virement : {iban}", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _layout_sidebar(i: int) -> bytes:
    """Colonne de gauche colorée avec infos fournisseur, corps à droite."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    r, g, b = random.choice([(45, 85, 140), (30, 110, 70), (120, 40, 40)])

    # Sidebar
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 55, 297, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(5, 20)
    pdf.set_font("Sans", "B", 10)
    pdf.multi_cell(45, 6, fourn_name)
    pdf.set_font("Sans", "", 7)
    pdf.set_x(5)
    pdf.multi_cell(45, 4, fourn_addr)
    pdf.set_x(5)
    pdf.cell(45, 4, fourn_tel, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_x(5)
    pdf.cell(45, 4, "SIRET:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(5)
    pdf.cell(45, 4, _siret(), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_x(5)
    pdf.set_font("Sans", "B", 7)
    pdf.cell(45, 4, "IBAN:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 6)
    pdf.set_x(5)
    pdf.multi_cell(45, 4, iban)

    # Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(62, 18)
    pdf.set_font("Sans", "B", 13)
    pdf.cell(0, 8, "FACTURE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(62)
    pdf.set_font("Sans", "", 8)
    pdf.cell(
        0,
        4,
        f"N° {inv_num}  |  {date_str}  |  Echéance : {echeance_str}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)
    pdf.set_x(62)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(0, 4, "Facturé à :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(62)
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(62)
    pdf.cell(0, 4, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    total_ht = 0
    col_w = [80, 15, 25, 25]
    pdf.set_x(62)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Sans", "B", 8)
    for w, h in zip(col_w, ["Désignation", "Qté", "P.U. HT", "Total HT"], strict=False):
        pdf.cell(w, 6, h, fill=True, align="C" if w < 40 else "L")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.set_x(62)
        pdf.cell(col_w[0], 5, desc, border="B")
        pdf.cell(col_w[1], 5, str(qty), border="B", align="C")
        pdf.cell(col_w[2], 5, f"{pu:.2f}", border="B", align="R")
        pdf.cell(col_w[3], 5, f"{t:.2f}", border="B", align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        ("Total HT", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.set_x(62)
        pdf.cell(120, 4, label, align="R")
        pdf.cell(25, 4, val, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.set_x(62)
    pdf.cell(120, 5, "TOTAL TTC", align="R")
    pdf.cell(25, 5, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _layout_centered(i: int) -> bytes:
    """En-tête centré, style cabinet ou profession libérale."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    pdf.set_font("Sans", "B", 16)
    pdf.cell(0, 9, fourn_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, fourn_addr, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        4,
        f"Tél : {fourn_tel}   SIRET : {_siret()}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)
    pdf.set_draw_color(100, 100, 100)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(6)

    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, f"FACTURE N° {inv_num}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(
        0,
        4,
        f"Date : {date_str}   —   Echéance : {echeance_str}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    # Client bloc à droite
    pdf.set_font("Sans", "B", 8)
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, "Destinataire :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    total_ht = 0
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(95, 6, "Désignation", border=1, fill=True)
    pdf.cell(15, 6, "Qté", border=1, fill=True, align="C")
    pdf.cell(35, 6, "Prix U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 6, "Total HT", border=1, fill=True, align="R")
    pdf.ln()
    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(95, 5, desc, border=1)
        pdf.cell(15, 5, str(qty), border=1, align="C")
        pdf.cell(35, 5, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 5, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        ("Total HT", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.cell(0, 4, f"{label} : {val}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.cell(
        0, 5, f"TOTAL TTC : {ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(6)
    pdf.set_font("Sans", "", 7)
    pdf.cell(
        0,
        4,
        f"Règlement par virement — IBAN : {iban}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


def _layout_oldschool(i: int) -> bytes:
    """Double bordure extérieure, style tampon, très années 90."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    # Double bordure
    pdf.set_draw_color(80, 80, 80)
    pdf.set_line_width(1.2)
    pdf.rect(10, 10, 190, 277)
    pdf.set_line_width(0.3)
    pdf.rect(12, 12, 186, 273)

    pdf.set_font("Sans", "B", 14)
    pdf.set_xy(18, 20)
    pdf.cell(0, 8, fourn_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.set_x(18)
    pdf.cell(0, 4, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.cell(
        0, 4, f"Tél : {fourn_tel}  —  SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(3)

    pdf.set_line_width(0.6)
    pdf.set_x(18)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Sans", "B", 11)
    pdf.set_x(18)
    pdf.cell(80, 7, f"FACTURE N° {inv_num}")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 7, f"Date : {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Sans", "", 8)
    pdf.cell(80, 5, f"Echéance de paiement : {echeance_str}")
    pdf.ln(6)

    pdf.set_x(18)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(
        0, 5, f"CLIENT : {client_name}  /  {client_addr}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(4)

    total_ht = 0
    pdf.set_x(18)
    pdf.set_font("Sans", "B", 8)
    for w, h in zip(
        [85, 20, 30, 30, 9],
        ["DESIGNATION", "QTE", "PU HT", "MONTANT HT", "TVA"],
        strict=False,
    ):
        pdf.cell(w, 6, h, border=1, align="C")
    pdf.ln()
    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.set_x(18)
        for w, v in zip(
            [85, 20, 30, 30, 9],
            [desc, str(qty), f"{pu:.2f}", f"{t:.2f}", f"{int(tva_rate * 100)}%"],
            strict=False,
        ):
            pdf.cell(w, 5, v, border=1, align="C" if w <= 30 else "L")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_x(18)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        ("TOTAL HT", f"{total_ht:.2f}"),
        (f"T.V.A. {int(tva_rate * 100)}%", f"{tva_amt:.2f}"),
    ]:
        pdf.cell(155, 4, label, align="R")
        pdf.cell(19, 4, val, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(18)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(155, 6, "TOTAL T.T.C.", align="R")
    pdf.cell(19, 6, f"{ttc:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_x(18)
    pdf.set_font("Sans", "", 7)
    pdf.cell(0, 4, f"Virement bancaire — IBAN : {iban}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.cell(
        0,
        4,
        "Tout retard de paiement entraine des penalites de 3x le taux legal.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


def _layout_condensed(i: int) -> bytes:
    """Dense, petite police, beaucoup d'info, style fournisseur industriel."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    bic = random.choice(BICS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = random.choice(TVA_RATES)

    # Two-column header block
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(15, 15, 85, 35, "FD")
    pdf.rect(110, 15, 85, 35, "FD")

    pdf.set_xy(17, 17)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(81, 5, "EMETTEUR", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 7)
    pdf.set_x(17)
    pdf.multi_cell(
        81, 3.5, f"{fourn_name}\n{fourn_addr}\nTel: {fourn_tel}\nSIRET: {_siret()}"
    )

    pdf.set_xy(112, 17)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(81, 5, "DESTINATAIRE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 7)
    pdf.set_xy(112, 22)
    pdf.multi_cell(81, 3.5, f"{client_name}\n{client_addr}")

    pdf.set_y(53)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(45, 5, f"FACTURE N° {inv_num}")
    pdf.cell(45, 5, f"Date : {date_str}")
    pdf.cell(0, 5, f"Echeance : {echeance_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(100, 100, 100)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    total_ht = 0
    pdf.set_font("Sans", "B", 7)
    col_w = [10, 78, 12, 22, 22, 22, 14]
    col_h = ["#", "Désignation", "Qté", "P.U. HT", "Total HT", "Total TTC", "TVA"]
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(col_w, col_h, strict=False):
        pdf.cell(w, 5, h, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Sans", "", 7)
    for j, (desc, qty, pu) in enumerate(produits):
        t_ht = round(qty * pu, 2)
        t_ttc = round(t_ht * (1 + tva_rate), 2)
        total_ht += t_ht
        vals = [
            str(j + 1),
            desc,
            str(qty),
            f"{pu:.2f}",
            f"{t_ht:.2f}",
            f"{t_ttc:.2f}",
            f"{int(tva_rate * 100)}%",
        ]
        for w, v in zip(col_w, vals, strict=False):
            pdf.cell(w, 4.5, v, border="B", align="L" if w > 20 else "C")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(2)
    pdf.set_font("Sans", "", 7)
    for label, val in [
        ("Total HT", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
        ("NET A PAYER TTC", f"{ttc:.2f} EUR"),
    ]:
        bold = label.startswith("NET")
        pdf.set_font("Sans", "B" if bold else "", 7 if not bold else 8)
        pdf.cell(162, 4, label, align="R")
        pdf.cell(18, 4, val, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Sans", "", 6)
    pdf.cell(
        0,
        3.5,
        f"Reglement : virement IBAN {iban}  BIC {bic}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


LAYOUTS = [
    _layout_classic,
    _layout_modern,
    _layout_two_col,
    _layout_minimal,
    _layout_sidebar,
    _layout_centered,
    _layout_oldschool,
    _layout_condensed,
]


# ── Trap invoices ──────────────────────────────────────────────────────────────
# Clean scans but with deliberate data problems to test AI flagging.


def _trap_iban_ambiguous(i: int) -> bytes:
    """IBAN avec O/0 ambigus : FR76 3OO0 4028 37O0 0l00 789O 143 (lettres O et l mélangées)."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    # IBAN with O/0 and l/1 confusion (looks clean but ambiguous chars)
    iban_trap = "FR76 3OO0 4028 37O0 0l00 789O 143"
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = 0.20

    pdf.set_font("Sans", "B", 15)
    pdf.cell(0, 8, fourn_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 5, f"Tél : {fourn_tel}   SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, f"FACTURE N° {inv_num}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(
        0,
        5,
        f"Date : {date_str}     Echéance : {echeance_str}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(0, 5, "Facturé à :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    total_ht = 0
    pdf.set_fill_color(225, 225, 225)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(90, 7, "Désignation", border=1, fill=True)
    pdf.cell(20, 7, "Qté", border=1, fill=True, align="C")
    pdf.cell(35, 7, "Prix U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 7, "Total HT", border=1, fill=True, align="R")
    pdf.ln()
    pdf.set_font("Sans", "", 9)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(90, 6, desc, border=1)
        pdf.cell(20, 6, str(qty), border=1, align="C")
        pdf.cell(35, 6, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 6, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_font("Sans", "", 9)
    for label, val in [
        ("Total HT :", f"{total_ht:.2f} EUR"),
        ("TVA 20% :", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.cell(145, 5, label, align="R")
        pdf.cell(25, 5, val, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.cell(145, 6, "TOTAL TTC :", align="R")
    pdf.cell(25, 6, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Sans", "", 8)
    # Trap: ambiguous IBAN printed clearly but with wrong chars
    pdf.cell(0, 4, f"Virement : {iban_trap}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 7)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 4, "(IBAN à vérifier avant virement)", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _trap_math_error(i: int) -> bytes:
    """Facture où HT + TVA ≠ TTC affiché (erreur de calcul volontaire)."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = 0.20

    pdf.set_font("Sans", "B", 13)
    pdf.cell(95, 7, fourn_name)
    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, "FACTURE", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(95, 4, fourn_addr)
    pdf.cell(0, 4, f"N° : {inv_num}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 4, f"SIRET : {_siret()}")
    pdf.cell(0, 4, f"Date : {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 4, f"Tél : {fourn_tel}")
    pdf.cell(
        0, 4, f"Echéance : {echeance_str}", align="R", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(3)
    pdf.set_draw_color(160, 160, 160)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(0, 4, "CLIENT :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, f"{client_name} — {client_addr}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    widths = [15, 73, 15, 28, 28, 11]
    headers = ["Réf.", "Désignation", "Qté", "Prix U. HT", "Total HT", "TVA"]
    pdf.set_fill_color(215, 215, 215)
    pdf.set_font("Sans", "B", 8)
    for w, h in zip(widths, headers, strict=False):
        pdf.cell(w, 6, h, border=1, fill=True, align="C")
    pdf.ln()

    total_ht = 0
    pdf.set_font("Sans", "", 8)
    for j, (desc, qty, pu) in enumerate(produits):
        t = round(qty * pu, 2)
        total_ht += t
        ref = f"ART-{j + 1:03d}"
        for w, val in zip(
            widths,
            [
                ref,
                desc,
                str(qty),
                f"{pu:.2f} EUR",
                f"{t:.2f} EUR",
                f"{int(tva_rate * 100)}%",
            ],
            strict=False,
        ):
            pdf.cell(w, 5, val, border=1, align="C" if w <= 15 else "L")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    correct_ttc = round(total_ht + tva_amt, 2)
    # Trap: TTC has a deliberate error (+10 EUR discrepancy)
    wrong_ttc = correct_ttc + 10.00

    pdf.ln(3)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        (f"Base HT {int(tva_rate * 100)}%", f"{total_ht:.2f} EUR"),
        (f"TVA {int(tva_rate * 100)}%", f"{tva_amt:.2f} EUR"),
        ("Total HT", f"{total_ht:.2f} EUR"),
        ("TOTAL TTC", f"{wrong_ttc:.2f} EUR"),
    ]:
        pdf.cell(150, 4, label, align="R")
        pdf.cell(20, 4, val, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Sans", "", 7)
    pdf.cell(0, 4, f"Virement : IBAN {iban}", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _trap_date_paradox(i: int) -> bytes:
    """Echéance antérieure à la date de facture (incohérence temporelle)."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = 0.20

    # Trap: échéance is 30 days BEFORE the invoice date
    invoice_date = date(2024, 9, 15)
    echeance_date = date(2024, 8, 14)  # 32 days before invoice
    date_str = invoice_date.strftime("%d/%m/%Y")
    echeance_str = echeance_date.strftime("%d/%m/%Y")

    pdf.set_font("Sans", "B", 16)
    pdf.cell(0, 9, fourn_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, fourn_addr, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        4,
        f"Tél : {fourn_tel}   SIRET : {_siret()}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)
    pdf.set_draw_color(100, 100, 100)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(6)

    pdf.set_font("Sans", "B", 12)
    pdf.cell(0, 7, f"FACTURE N° {inv_num}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    # Trap: these two dates will appear contradictory
    pdf.cell(
        0,
        4,
        f"Date : {date_str}   —   Echéance : {echeance_str}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    pdf.set_font("Sans", "B", 8)
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, "Destinataire :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(100, 4, "")
    pdf.cell(0, 4, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    total_ht = 0
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(95, 6, "Désignation", border=1, fill=True)
    pdf.cell(15, 6, "Qté", border=1, fill=True, align="C")
    pdf.cell(35, 6, "Prix U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 6, "Total HT", border=1, fill=True, align="R")
    pdf.ln()
    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(95, 5, desc, border=1)
        pdf.cell(15, 5, str(qty), border=1, align="C")
        pdf.cell(35, 5, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 5, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_font("Sans", "", 8)
    for label, val in [
        ("Total HT", f"{total_ht:.2f} EUR"),
        ("TVA 20%", f"{tva_amt:.2f} EUR"),
    ]:
        pdf.cell(0, 4, f"{label} : {val}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 9)
    pdf.cell(
        0, 5, f"TOTAL TTC : {ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(6)
    pdf.set_font("Sans", "", 7)
    pdf.cell(
        0,
        4,
        f"Règlement par virement — IBAN : {iban}",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


def _trap_tva_mismatch(i: int) -> bytes:
    """TVA indiquée à 20% mais montant calculé à 10% (incohérence taux/montant)."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, _fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    inv_num = _invoice_number(i)
    date_str, echeance_str = _random_date()
    iban = random.choice(IBANS)
    produits = random.choice(PRODUITS_SERVICES)

    pdf.set_font("Sans", "B", 14)
    pdf.cell(0, 10, f"  {fourn_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 4, f"SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Sans", "B", 10)
    pdf.cell(0, 7, f"  FACTURE N° {inv_num}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.ln(3)
    pdf.cell(95, 5, f"Date : {date_str}")
    pdf.cell(0, 5, f"Echéance : {echeance_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(0, 5, "Destinataire :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 5, client_name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, client_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_fill_color(230, 235, 245)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(95, 7, "Prestation / Produit", border=1, fill=True)
    pdf.cell(20, 7, "Qté", border=1, fill=True, align="C")
    pdf.cell(30, 7, "P.U. HT", border=1, fill=True, align="R")
    pdf.cell(25, 7, "Total HT", border=1, fill=True, align="R")
    pdf.ln()

    total_ht = 0
    pdf.set_font("Sans", "", 9)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.cell(95, 6, desc, border=1)
        pdf.cell(20, 6, str(qty), border=1, align="C")
        pdf.cell(30, 6, f"{pu:.2f} EUR", border=1, align="R")
        pdf.cell(25, 6, f"{t:.2f} EUR", border=1, align="R")
        pdf.ln()

    # Trap: label says 20% but amount is calculated at 10%
    tva_label_rate = 0.20
    tva_actual_rate = 0.10
    tva_amt = round(total_ht * tva_actual_rate, 2)  # calculated at 10%
    ttc = round(total_ht + tva_amt, 2)

    pdf.ln(3)
    pdf.set_font("Sans", "", 9)
    pdf.cell(145, 5, "Sous-total HT", align="R")
    pdf.cell(25, 5, f"{total_ht:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    # Label says 20%, amount is 10% of HT
    pdf.cell(145, 5, f"TVA {int(tva_label_rate * 100)}%", align="R")
    pdf.cell(25, 5, f"{tva_amt:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "B", 10)
    pdf.cell(145, 6, "TOTAL TTC", align="R")
    pdf.cell(25, 6, f"{ttc:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Sans", "", 8)
    pdf.cell(0, 4, f"IBAN : {iban}", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def _trap_missing_fields(i: int) -> bytes:
    """Facture incomplète : pas de numéro, pas d'IBAN, montant HT absent."""
    pdf = FPDF()
    _setup_fonts(pdf)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(False)

    fourn_name, fourn_addr, fourn_tel = random.choice(FOURNISSEURS)
    client_name, client_addr = random.choice(CLIENTS)
    date_str, echeance_str = _random_date()
    produits = random.choice(PRODUITS_SERVICES)
    tva_rate = 0.20

    pdf.set_draw_color(80, 80, 80)
    pdf.set_line_width(1.2)
    pdf.rect(10, 10, 190, 277)
    pdf.set_line_width(0.3)
    pdf.rect(12, 12, 186, 273)

    pdf.set_font("Sans", "B", 14)
    pdf.set_xy(18, 20)
    pdf.cell(0, 8, fourn_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Sans", "", 8)
    pdf.set_x(18)
    pdf.cell(0, 4, fourn_addr, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.cell(
        0, 4, f"Tél : {fourn_tel}  —  SIRET : {_siret()}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(3)

    pdf.set_line_width(0.6)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Sans", "B", 11)
    pdf.set_x(18)
    # Trap: no invoice number (left blank intentionally)
    pdf.cell(80, 7, "FACTURE N° ___________")
    pdf.set_font("Sans", "", 9)
    pdf.cell(0, 7, f"Date : {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Sans", "", 8)
    pdf.cell(80, 5, f"Echéance de paiement : {echeance_str}")
    pdf.ln(6)

    pdf.set_x(18)
    pdf.set_font("Sans", "B", 8)
    pdf.cell(
        0, 5, f"CLIENT : {client_name}  /  {client_addr}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(4)

    total_ht = 0
    pdf.set_x(18)
    pdf.set_font("Sans", "B", 8)
    for w, h in zip(
        [85, 20, 30, 30, 9],
        ["DESIGNATION", "QTE", "PU HT", "MONTANT HT", "TVA"],
        strict=False,
    ):
        pdf.cell(w, 6, h, border=1, align="C")
    pdf.ln()
    pdf.set_font("Sans", "", 8)
    for desc, qty, pu in produits:
        t = round(qty * pu, 2)
        total_ht += t
        pdf.set_x(18)
        for w, v in zip(
            [85, 20, 30, 30, 9],
            [desc, str(qty), f"{pu:.2f}", f"{t:.2f}", f"{int(tva_rate * 100)}%"],
            strict=False,
        ):
            pdf.cell(w, 5, v, border=1, align="C" if w <= 30 else "L")
        pdf.ln()

    tva_amt = round(total_ht * tva_rate, 2)
    ttc = round(total_ht + tva_amt, 2)
    pdf.ln(3)
    pdf.set_x(18)
    pdf.set_font("Sans", "", 8)
    # Trap: no HT subtotal line, jump straight to TTC
    pdf.cell(155, 4, f"T.V.A. {int(tva_rate * 100)}%", align="R")
    pdf.cell(19, 4, f"{tva_amt:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(155, 6, "TOTAL T.T.C.", align="R")
    pdf.cell(19, 6, f"{ttc:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_x(18)
    pdf.set_font("Sans", "", 7)
    # Trap: no IBAN, just "à communiquer"
    pdf.cell(
        0,
        4,
        "Coordonnées bancaires : à communiquer sur demande",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    return pdf.output()


TRAP_LAYOUTS = [
    _trap_iban_ambiguous,
    _trap_math_error,
    _trap_date_paradox,
    _trap_tva_mismatch,
    _trap_missing_fields,
]


def generate() -> None:
    """Génère un exemplaire de chaque layout pour chaque qualité + factures pièges."""
    qualities = ["good", "bad", "ugly"]
    total = len(LAYOUTS) * len(qualities)
    print(
        f"Generating {total} invoices ({len(LAYOUTS)} layouts x {len(qualities)} qualities)\n"
    )

    counter = 1
    for q in qualities:
        out_dir = QUALITY_DIRS[q]
        for layout in LAYOUTS:
            layout_name = layout.__name__.replace("_layout_", "")
            filename = f"{q}-{layout_name}.pdf"
            pdf_bytes = bytes(layout(counter))
            pages = convert_from_bytes(pdf_bytes, dpi=150)
            scanned = [_scan_effect(p.convert("RGB"), quality=q) for p in pages]
            out_path = os.path.join(out_dir, filename)
            scanned[0].save(out_path, "PDF", save_all=True, append_images=scanned[1:])
            print(f"  [{counter:2d}/{total}] [{q:6s}] {filename}")
            counter += 1

    # Trap invoices: clean quality scan, problematic content
    print(f"\nGenerating {len(TRAP_LAYOUTS)} trap invoices (clean scan, bad data)\n")
    trap_dir = QUALITY_DIRS["good"]
    for layout in TRAP_LAYOUTS:
        trap_name = layout.__name__.replace("_trap_", "")
        filename = f"trap-{trap_name}.pdf"
        pdf_bytes = bytes(layout(counter))
        pages = convert_from_bytes(pdf_bytes, dpi=150)
        scanned = [_scan_effect(p.convert("RGB"), quality="good") for p in pages]
        out_path = os.path.join(trap_dir, filename)
        scanned[0].save(out_path, "PDF", save_all=True, append_images=scanned[1:])
        print(f"  [trap] {filename}")
        counter += 1

    print(f"\nDone. {total} normal + {len(TRAP_LAYOUTS)} trap invoices.")
    print("Trap invoices in: data/unprocessed/clean/ (prefix 'trap-')")


if __name__ == "__main__":
    generate()
