"""Modèle financier — agence d'ouverture de véhicules et de clés auto, Casablanca.

Modèle mensuel sur 60 mois (démarrage le 1er mars 2027), montants en DH HT.
Il produit les chiffres du business plan et du dossier de prêt Intelaka : plan de
financement, comptes de résultat, plan de trésorerie, bilans, ratios bancaires,
point mort, scénarios (dont le plan de repli) et sensibilités.

Usage : python3 modele_financier.py [chemin_export.json]
"""
import json
import sys

TVA = 1.20
START_MONTH = 3  # mars
HORIZON = 60

# Saisonnalité par mois calendaire (Casablanca : pic d'été modéré)
SEASON = {1: 0.95, 2: 0.95, 3: 0.95, 4: 1.00, 5: 1.00, 6: 1.05,
          7: 1.15, 8: 1.10, 9: 1.00, 10: 1.00, 11: 0.95, 12: 1.00}

# Interventions par mois avant saisonnalité : (début, fin) de chaque année
RAMP = {1: (25, 90), 2: (95, 125), 3: (130, 150), 4: (150, 158), 5: (158, 165)}

# Investissements : libellé, montant HT, durée d'amortissement (ans), TVA récupérable
CAPEX = [
    ("Utilitaire d'occasion + aménagement atelier mobile", 125_000, 5, False),
    ("Programmateur d'immobiliseur principal", 30_000, 5, True),
    ("2e programmateur", 20_000, 5, True),
    ("Machine de taille électronique", 22_000, 5, True),
    ("Outils d'ouverture", 12_000, 5, True),
    ("Informatique et paiement", 14_000, 3, True),
    ("Aménagement du local", 12_000, 5, True),
    ("Formation technique", 20_000, 5, False),
    ("Identité visuelle", 8_000, 5, True),
    ("Site web et fiche Google", 6_000, 5, True),
    ("Constitution SARL AU", 6_000, 5, False),
]
STOCK_INIT = 25_000
DEPOSIT = 8_000
CONTINGENCY_RATE = 0.05
CASH_BUFFER = 140_000
EQUITY_SHARE = 0.30
LOAN_RATE = 0.02          # Intelaka, zone urbaine
LOAN_MONTHS = 84          # 7 ans, différé compris
TAX_RATE = 0.20

MIX_BY_YEAR = {1: dict(open=0.50, lost=0.20, dup=0.18, rep=0.12),
               2: dict(open=0.45, lost=0.20, dup=0.23, rep=0.12),
               3: dict(open=0.42, lost=0.20, dup=0.26, rep=0.12)}
PRICE_TTC = dict(open=350, lost=1700, dup=750, rep=400)
UNIT_COST = dict(open=55, lost=465, dup=245, rep=120)   # pièce + carburant + jetons
COMMISSION = 0.04                                        # apporteurs + frais de paiement
B2B_SHARE = {1: 0.12, 2: 0.25, 3: 0.35}
B2B_DISCOUNT = 0.20
B2B_DAYS = 60
PRICE_INDEX = {1: 1.00, 2: 1.03, 3: 1.06}   # puis +3 % par an
COST_GROWTH = 0.04          # charges fixes à partir de l'an 4
TVA_FIXED_PURCHASES = 4_000  # achats fixes mensuels soumis à TVA déductible
# Renouvellements : mois d'achat, libellé, montant HT, durée d'amortissement (ans)
RENEWALS = [(37, "Renouvellement informatique", 14_000, 3),
            (49, "Renouvellement du programmateur principal", 30_000, 5)]

capex_total = sum(c[1] for c in CAPEX)
contingency = round((capex_total + STOCK_INIT) * CONTINGENCY_RATE, -3)
invest_total = capex_total + STOCK_INIT + DEPOSIT + contingency + CASH_BUFFER
tva_on_assets = 0.20 * (sum(c[1] for c in CAPEX if c[3]) + STOCK_INIT)


def price_index(y):
    return PRICE_INDEX[y] if y <= 3 else PRICE_INDEX[3] * 1.03 ** (y - 3)


def mix(y):
    return MIX_BY_YEAR[min(y, 3)]


def b2b_share(y):
    return B2B_SHARE[min(y, 3)]


CAPACITY_2_TECHS = 170   # interventions par mois en pointe avec deux techniciens


def fixed_costs(m, y, lean=False, extra_capacity=False):
    if y <= 3:
        c = {
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
    else:
        g = (1 + COST_GROWTH) ** (y - 3)
        c = {k: round(v * g, -1) for k, v in fixed_costs(25, 3).items()}
    if extra_capacity:
        # Au-delà de la capacité de deux techniciens : un troisième et un second véhicule loué
        c["Technicien n°3"] = round(6000 * (1 + COST_GROWTH) ** max(0, y - 4), -1)
        c["Véhicule n°2 (location longue durée)"] = 2500
    if lean:
        c["Technicien n°2"] = 0          # payé à la commission (voir variable)
        c["Assistant(e) mi-temps"] = 0
        c["Loyer local"] = 500           # domiciliation + box de stockage
        c["Marketing"] = 4000
        c["Gérant-technicien"] = 6000
    return c


def base_jobs(m):
    y = (m - 1) // 12 + 1
    a, b = RAMP[y]
    return a + (b - a) * ((m - 1) % 12) / 11


def build(vol_mult=1.0, price_mult=1.0, cost_mult=1.0, b2b_shift=0.0, grace=6, lean_from=None):
    loan = round(invest_total * (1 - EQUITY_SHARE), -3)
    equity = invest_total - loan
    r = LOAN_RATE / 12
    annuity = loan * r / (1 - (1 + r) ** -(LOAN_MONTHS - grace))
    balance = loan
    deps = [(amt / (yrs * 12), 1, yrs * 12) for _, amt, yrs, _ in CAPEX] + [(contingency / 60, 1, 60)]
    deps += [(amt / (yrs * 12), m0, m0 + yrs * 12 - 1) for m0, _, amt, yrs in RENEWALS]
    renewals = {m0: amt for m0, _, amt, _ in RENEWALS}

    def demand(m):
        cal = (START_MONTH - 1 + m - 1) % 12 + 1
        return base_jobs(m) * SEASON[cal] * vol_mult

    peak = {y: max(demand(m) for m in range(12 * y - 11, 12 * y + 1)) for y in range(1, HORIZON // 12 + 1)}

    months = []
    for m in range(1, HORIZON + 1):
        y = (m - 1) // 12 + 1
        cal = (START_MONTH - 1 + m - 1) % 12 + 1
        lean = lean_from is not None and m >= lean_from
        jobs = base_jobs(m) * SEASON[cal] * vol_mult
        b2b = min(0.6, b2b_share(y) + b2b_shift)
        rev = var = 0.0
        for k, share in mix(y).items():
            n = jobs * share
            price_ht = PRICE_TTC[k] * price_index(y) * price_mult / TVA
            rev += n * price_ht * (1 - b2b * B2B_DISCOUNT)
            var += n * UNIT_COST[k] * cost_mult
        var += rev * COMMISSION
        if lean and m >= 4:
            var += rev * 0.12            # technicien n°2 à la commission
        fixed = sum(fixed_costs(m, y, lean, peak[y] > CAPACITY_2_TECHS).values()) * cost_mult
        ebitda = rev - var - fixed
        dep = sum(a for a, s, e in deps if s <= m <= e)
        interest = balance * r
        principal = 0.0 if m <= grace else min(balance, annuity - interest)
        balance -= principal
        b2b_rev = rev * b2b * (1 - B2B_DISCOUNT) / (1 - b2b * B2B_DISCOUNT)
        months.append(dict(m=m, y=y, cal=cal, jobs=jobs, rev=rev, var=var, fixed=fixed, ebitda=ebitda,
                           dep=dep, interest=interest, principal=principal, balance=balance,
                           ebt=ebitda - dep - interest, b2b_rev=b2b_rev, capex=renewals.get(m, 0.0)))

    years, loss_cf = {}, 0.0
    for y in range(1, HORIZON // 12 + 1):
        ms = [x for x in months if x["y"] == y]
        a = {k: sum(x[k] for x in ms)
             for k in ("jobs", "rev", "var", "fixed", "ebitda", "dep", "interest", "principal", "ebt", "capex")}
        taxable = a["ebt"] + loss_cf
        a["tax"] = TAX_RATE * taxable if taxable > 0 else 0.0
        loss_cf = 0.0 if taxable > 0 else taxable
        a["net"] = a["ebt"] - a["tax"]
        a["caf"] = a["net"] + a["dep"]
        a["debt_service"] = a["interest"] + a["principal"]
        a["dscr"] = a["caf"] / a["debt_service"] if a["debt_service"] else None
        a["margin_rate"] = (a["rev"] - a["var"]) / a["rev"]
        a["breakeven_rev"] = (a["fixed"] + a["dep"] + a["interest"]) / a["margin_rate"]
        years[y] = a

    # Trésorerie : TVA sur équipements avancée puis imputée, créances B2B à 60 jours,
    # stock qui suit le volume, IS payé au début de l'année suivante
    cash = CASH_BUFFER - tva_on_assets
    tva_credit, receivables, stock = tva_on_assets, 0.0, float(STOCK_INIT)
    for x in months:
        new_receivables = x["b2b_rev"] * B2B_DAYS / 30
        target_stock = STOCK_INIT + 120 * max(0, x["jobs"] - 40)
        stock_in = max(0.0, target_stock - stock)
        stock += stock_in
        tva_credit += 0.20 * x["capex"]
        tva_due = max(0.0, 0.20 * (x["rev"] - x["var"] - TVA_FIXED_PURCHASES))
        tva_recovered = min(tva_credit, tva_due)
        tva_credit -= tva_recovered
        tax_paid = years[x["y"] - 1]["tax"] if (x["m"] - 1) % 12 == 0 and x["y"] > 1 else 0.0
        cash_in = x["rev"] - (new_receivables - receivables)
        x.update(cash_in=cash_in, opex_out=x["var"] + x["fixed"], debt_out=x["interest"] + x["principal"],
                 other_out=stock_in + tax_paid - tva_recovered + x["capex"] * 1.2)
        cash += cash_in - x["opex_out"] - x["debt_out"] - x["other_out"]
        receivables = new_receivables
        x.update(cash=cash, receivables=receivables, stock=stock, tva_credit=tva_credit)

    # Bilans de fin d'année et contrôle d'équilibre
    gross_assets = capex_total + contingency
    cum_dep = cum_net = 0.0
    for y, a in years.items():
        gross_assets += a["capex"]
        cum_dep += a["dep"]
        cum_net += a["net"]
        end = months[12 * y - 1]
        assets = dict(fixed=gross_assets - cum_dep, deposit=DEPOSIT, stock=end["stock"],
                      receivables=end["receivables"], tva_credit=end["tva_credit"], cash=end["cash"])
        liabilities = dict(equity=equity, retained=cum_net, loan=end["balance"], tax_payable=a["tax"])
        a["assets"], a["liabilities"] = assets, liabilities
        bfr = end["stock"] + end["receivables"] + end["tva_credit"] - a["tax"]
        a["bfr"] = bfr
        gap = sum(assets.values()) - sum(liabilities.values())
        assert abs(gap) < 1, f"Bilan déséquilibré an {y} : {gap:.2f}"

    first36 = months[:36]
    breakeven = next((x["m"] for i, x in enumerate(first36)
                      if all(first36[j]["ebt"] >= 0 for j in range(i, min(i + 3, 36)))), None)
    low = min(months, key=lambda x: x["cash"])
    return dict(loan=loan, equity=equity, annuity=annuity, grace=grace, months=months, years=years,
                breakeven=breakeven, low_cash=low["cash"], low_month=low["m"])


def report(label, s, n_years=5):
    print(f"\n== {label} | point mort (résultat) : mois {s['breakeven']} | "
          f"trésorerie au plus bas : {s['low_cash']:,.0f} DH (mois {s['low_month']})")
    for y in range(1, n_years + 1):
        a = s["years"][y]
        dscr = f"{a['dscr']:.2f}" if a["dscr"] is not None else "-"
        print(f"  An {y} : {a['jobs']:.0f} interv. | CA {a['rev']:,.0f} | EBITDA {a['ebitda']:,.0f} | "
              f"net {a['net']:,.0f} | CAF {a['caf']:,.0f} | DSCR {dscr} | tréso fin {s['months'][12*y-1]['cash']:,.0f}")


if __name__ == "__main__":
    print(f"Besoin de financement : {invest_total:,.0f} DH | TVA avancée sur équipements : {tva_on_assets:,.0f} DH")
    base = build()
    print(f"Apport : {base['equity']:,.0f} DH | Prêt : {base['loan']:,.0f} DH | "
          f"Mensualité après différé : {base['annuity']:,.0f} DH")
    report("Base", base)
    report("Base, différé de 12 mois", build(grace=12))
    report("Pessimiste (volume -30 %, prix -10 %)", build(vol_mult=0.70, price_mult=0.90))
    report("Pessimiste + plan de repli dès le mois 7", build(vol_mult=0.70, price_mult=0.90, lean_from=7))
    report("Optimiste (volume +25 %)", build(vol_mult=1.25))

    y2 = base["years"][2]
    contrib = (y2["rev"] - y2["var"]) / y2["jobs"]
    print(f"\nPoint mort an 2 : {y2['fixed'] / 12 / contrib:.0f} interventions/mois (EBITDA), "
          f"{(y2['fixed'] + y2['dep'] + y2['interest']) / 12 / contrib:.0f} (résultat)")
    print("Sensibilité de l'EBITDA an 2 :")
    for label, kw in [("Prix -10 %", dict(price_mult=0.9)), ("Coûts +10 %", dict(cost_mult=1.1)),
                      ("Volume -10 %", dict(vol_mult=0.9)), ("Part B2B +15 pts", dict(b2b_shift=0.15))]:
        print(f"  {label} : {build(**kw)['years'][2]['ebitda'] - y2['ebitda']:+,.0f} DH")

    if len(sys.argv) > 1:
        json.dump(dict(invest_total=invest_total, tva_on_assets=tva_on_assets, base=base,
                       grace12=build(grace=12),
                       pess=build(vol_mult=0.70, price_mult=0.90),
                       pess_lean=build(vol_mult=0.70, price_mult=0.90, lean_from=7)),
                  open(sys.argv[1], "w"), default=float, indent=1)
