"""Modèle financier — agence d'ouverture de véhicules et de clés auto, Casablanca.

Modèle mensuel sur 36 mois (démarrage le 1er mars 2027), montants en DH HT.
Il produit les chiffres du business plan : plan de financement, compte de résultat,
trésorerie, point mort, scénarios et sensibilités.

Usage : python3 modele_financier.py
"""

TVA = 1.20
START_MONTH = 3  # mars

# Saisonnalité par mois calendaire (Casablanca : pic d'été modéré)
SEASON = {1: 0.95, 2: 0.95, 3: 0.95, 4: 1.00, 5: 1.00, 6: 1.05,
          7: 1.15, 8: 1.10, 9: 1.00, 10: 1.00, 11: 0.95, 12: 1.00}

# Interventions par mois avant saisonnalité : (début an 1, fin an 1, début an 2, fin an 2, début an 3, fin an 3)
RAMP = (25, 90, 95, 125, 130, 150)

# Investissements : libellé, montant DH, durée d'amortissement (ans)
CAPEX = [
    ("Utilitaire d'occasion + aménagement atelier mobile", 125_000, 5),
    ("Programmateur d'immobiliseur principal", 30_000, 5),
    ("2e programmateur", 20_000, 5),
    ("Machine de taille électronique", 22_000, 5),
    ("Outils d'ouverture", 12_000, 5),
    ("Informatique et paiement", 14_000, 3),
    ("Aménagement du local", 12_000, 5),
    ("Formation technique", 20_000, 5),
    ("Identité visuelle", 8_000, 5),
    ("Site web et fiche Google", 6_000, 5),
    ("Constitution SARL AU", 6_000, 5),
]
STOCK_INIT = 25_000
DEPOSIT = 8_000
CONTINGENCY_RATE = 0.05
CASH_BUFFER = 140_000
EQUITY_SHARE = 0.30
LOAN_RATE = 0.02          # type Intelaka
LOAN_MONTHS = 84          # 7 ans
LOAN_GRACE = 6            # différé (intérêts seuls)

MIX = {1: dict(open=0.50, lost=0.20, dup=0.18, rep=0.12),
       2: dict(open=0.45, lost=0.20, dup=0.23, rep=0.12),
       3: dict(open=0.42, lost=0.20, dup=0.26, rep=0.12)}
PRICE_TTC = dict(open=350, lost=1700, dup=750, rep=400)
UNIT_COST = dict(open=55, lost=465, dup=245, rep=120)   # pièce + carburant + jetons
COMMISSION = 0.04                                        # apporteurs + frais de paiement
B2B_SHARE = {1: 0.12, 2: 0.25, 3: 0.35}
B2B_DISCOUNT = 0.20
B2B_DAYS = 60
PRICE_INDEX = {1: 1.00, 2: 1.03, 3: 1.06}
TAX_RATE = 0.20

capex_total = sum(c[1] for c in CAPEX)
contingency = round((capex_total + STOCK_INIT) * CONTINGENCY_RATE, -3)
invest_total = capex_total + STOCK_INIT + DEPOSIT + contingency + CASH_BUFFER


def fixed_costs(m, y):
    return {
        "Gérant-technicien": {1: 6000, 2: 8000, 3: 9000}[y],
        "Technicien n°2": 0 if m < 4 else {1: 6850, 2: 7200, 3: 7500}[y],
        "Assistant(e) mi-temps": 0 if y < 2 else {2: 3200, 3: 3400}[y],
        "Loyer local": {1: 4000, 2: 4100, 3: 4200}[y],
        "Véhicule": 1200,
        "Logiciels et jetons": {1: 900, 2: 1000, 3: 1300}[y],
        "Télécom et IT": {1: 500, 2: 600, 3: 800}[y],
        "Marketing": (7000 if m <= 3 else 5500) if y == 1 else {2: 5500, 3: 6500}[y],
        "Expert-comptable": {1: 800, 2: 900, 3: 1000}[y],
        "Assurance RC pro": 350,
        "Banque": 150,
        "Divers": {1: 500, 2: 600, 3: 700}[y],
    }


def base_jobs(m):
    r = RAMP
    if m <= 12:
        return r[0] + (r[1] - r[0]) * (m - 1) / 11
    if m <= 24:
        return r[2] + (r[3] - r[2]) * (m - 13) / 11
    return r[4] + (r[5] - r[4]) * (m - 25) / 11


def build(vol_mult=1.0, price_mult=1.0, cost_mult=1.0, b2b_shift=0.0):
    loan = round(invest_total * (1 - EQUITY_SHARE), -3)
    equity = invest_total - loan
    r = LOAN_RATE / 12
    annuity = loan * r / (1 - (1 + r) ** -(LOAN_MONTHS - LOAN_GRACE))
    balance = loan
    deps = [(amt / (yrs * 12), yrs * 12) for _, amt, yrs in CAPEX] + [(contingency / 60, 60)]

    months = []
    for m in range(1, 37):
        y = (m - 1) // 12 + 1
        cal = (START_MONTH - 1 + m - 1) % 12 + 1
        jobs = base_jobs(m) * SEASON[cal] * vol_mult
        b2b = min(0.6, B2B_SHARE[y] + b2b_shift)
        rev = var = 0.0
        for k, share in MIX[y].items():
            n = jobs * share
            price_ht = PRICE_TTC[k] * PRICE_INDEX[y] * price_mult / TVA
            rev += n * price_ht * (1 - b2b * B2B_DISCOUNT)
            var += n * UNIT_COST[k] * cost_mult
        var += rev * COMMISSION
        fixed = sum(fixed_costs(m, y).values()) * cost_mult
        ebitda = rev - var - fixed
        dep = sum(a for a, n in deps if m <= n)
        interest = balance * r
        principal = 0 if m <= LOAN_GRACE else annuity - interest
        balance -= principal
        b2b_rev = rev * b2b * (1 - B2B_DISCOUNT) / (1 - b2b * B2B_DISCOUNT)
        months.append(dict(m=m, y=y, jobs=jobs, rev=rev, var=var, fixed=fixed, ebitda=ebitda,
                           dep=dep, interest=interest, principal=principal,
                           ebt=ebitda - dep - interest, b2b_rev=b2b_rev))

    years, loss_cf = {}, 0.0
    for y in (1, 2, 3):
        ms = [x for x in months if x["y"] == y]
        a = {k: sum(x[k] for x in ms) for k in ("jobs", "rev", "var", "fixed", "ebitda", "dep", "interest", "ebt")}
        taxable = a["ebt"] + loss_cf
        a["tax"] = TAX_RATE * taxable if taxable > 0 else 0.0
        loss_cf = 0.0 if taxable > 0 else taxable
        a["net"] = a["ebt"] - a["tax"]
        years[y] = a

    # Trésorerie : créances B2B à 60 jours, stock qui suit le volume, IS payé en début d'année suivante
    cash, receivables, stock = CASH_BUFFER, 0.0, STOCK_INIT
    for x in months:
        new_receivables = x["b2b_rev"] * B2B_DAYS / 30
        target_stock = STOCK_INIT + 120 * max(0, x["jobs"] - 40)
        stock_in = max(0.0, target_stock - stock)
        stock += stock_in
        tax_paid = years[x["y"] - 1]["tax"] if x["m"] in (13, 25) else 0.0
        cash += (x["ebitda"] - x["interest"] - x["principal"]
                 - (new_receivables - receivables) - stock_in - tax_paid)
        receivables = new_receivables
        x["cash"] = cash

    breakeven = next((x["m"] for i, x in enumerate(months)
                      if all(months[j]["ebt"] >= 0 for j in range(i, min(i + 3, 36)))), None)
    low = min(months, key=lambda x: x["cash"])
    return dict(loan=loan, equity=equity, annuity=annuity, months=months, years=years,
                breakeven=breakeven, low_cash=low["cash"], low_month=low["m"])


def report(label, s):
    print(f"\n== {label} | point mort (résultat) : mois {s['breakeven']} | "
          f"trésorerie au plus bas : {s['low_cash']:,.0f} DH (mois {s['low_month']})")
    for y, a in s["years"].items():
        print(f"  An {y} : {a['jobs']:.0f} interventions | CA {a['rev']:,.0f} | EBITDA {a['ebitda']:,.0f} | "
              f"résultat net {a['net']:,.0f}")


if __name__ == "__main__":
    print(f"Besoin de financement : {invest_total:,.0f} DH")
    base = build()
    print(f"Apport : {base['equity']:,.0f} DH | Prêt : {base['loan']:,.0f} DH | "
          f"Mensualité après différé : {base['annuity']:,.0f} DH")
    report("Base", base)
    report("Pessimiste (volume -30 %, prix -10 %)", build(vol_mult=0.70, price_mult=0.90))
    report("Optimiste (volume +25 %)", build(vol_mult=1.25))

    y2 = base["years"][2]
    contrib = (y2["rev"] - y2["var"]) / y2["jobs"]
    print(f"\nPoint mort an 2 : {y2['fixed'] / 12 / contrib:.0f} interventions/mois (EBITDA), "
          f"{(y2['fixed'] + y2['dep'] + y2['interest']) / 12 / contrib:.0f} (résultat)")
    print("Sensibilité de l'EBITDA an 2 :")
    for label, kw in [("Prix -10 %", dict(price_mult=0.9)), ("Coûts +10 %", dict(cost_mult=1.1)),
                      ("Volume -10 %", dict(vol_mult=0.9)), ("Part B2B +15 pts", dict(b2b_shift=0.15))]:
        print(f"  {label} : {build(**kw)['years'][2]['ebitda'] - y2['ebitda']:+,.0f} DH")
