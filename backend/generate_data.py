import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Customer, Account, Transaction, Base

# ─── TYPOLOGY DEFINITIONS ───────────────────────────────────────────
# Each customer is assigned a primary typology so detection is deterministic.

TYPOLOGIES = {
    "SMURFING": "Multiple small deposits from many unique sources, each below CTR threshold ($10k)",
    "LAYERING": "Rapid layering: large deposit immediately split into many smaller outbound transfers",
    "ROUND_TRIPPING": "Funds leave to Party-A, return from linked Party-B within days at similar amount",
    "RAPID_MOVEMENT": "Large deposit followed by same-amount withdrawal within 24 hours (pass-through)",
    "SHELL_FAN_OUT": "Single large wire fanned out to 10+ shell company entities same day",
}

LEGITIMATE_DESCRIPTIONS = [
    "Payroll deposit", "Utility payment", "Rent payment", "Grocery purchase",
    "Insurance premium", "Subscription service", "Loan repayment", "Salary credit",
    "ATM withdrawal", "Online purchase", "Restaurant bill", "Fuel purchase",
]

SHELL_NAMES = [
    "Apex Holdings Ltd", "BlueStar Ventures LLC", "CrestPoint Capital Inc",
    "Delta Maritime Services", "EverGreen Trading Co", "FrontLine Logistics LLC",
    "GoldBridge Exports Ltd", "HorizonWave Solutions", "IronClad Industries",
    "JadeStone Mining Corp", "KingsGate Properties", "LionHeart Consulting",
]

OFFSHORE_ENTITIES = [
    "HIGH-RISK-ENTITY-OFFSHORE", "CaymanBridge Financial", "PanamaLink Holdings",
    "BVI-Capital-Trust", "LuxInvest-SA", "CyprusShell-Ltd",
]

def generate_synthetic_data():
    """Generate synthetic AML test data with 5 money laundering typologies"""

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ── Clear old data ──
        db.query(Transaction).delete()
        db.query(Account).delete()
        db.query(Customer).delete()
        db.commit()
        print("🗑️  Cleared old data.")

        # ── Create 10 customers ──
        # Customers 1-5: assigned specific typologies
        # Customers 6-10: clean/legitimate activity
        typology_assignments = {
            1: "SMURFING",
            2: "LAYERING",
            3: "ROUND_TRIPPING",
            4: "RAPID_MOVEMENT",
            5: "SHELL_FAN_OUT",
        }

        customers = []
        for i in range(1, 11):
            typology = typology_assignments.get(i)
            risk = "HIGH" if typology else random.choice(["LOW", "MEDIUM"])
            name_suffix = random.choice(["LLC", "Inc", "Ltd", "Corp", "Partners"])
            customer = Customer(
                name=f"Customer {i} ({name_suffix})",
                account_number=f"ACC{1000 + i}",
                risk_profile=risk
            )
            db.add(customer)
            customers.append(customer)

        db.commit()

        # ── Create accounts ──
        accounts_map = {}  # customer_id → list of accounts
        all_accounts = []
        for customer in customers:
            num_accounts = random.randint(1, 3)
            accs = []
            for j in range(num_accounts):
                account = Account(
                    customer_id=customer.id,
                    account_type=random.choice(["CHECKING", "SAVINGS", "BUSINESS"]),
                    balance=random.uniform(5000, 200000)
                )
                db.add(account)
                accs.append(account)
                all_accounts.append(account)
            accounts_map[customer.id] = accs

        db.commit()

        # ── Generate baseline legitimate transactions for ALL customers ──
        start_date = datetime.now() - timedelta(days=90)

        for account in all_accounts:
            for _ in range(random.randint(25, 60)):
                transaction = Transaction(
                    account_id=account.id,
                    amount=round(random.uniform(50, 4500), 2),
                    transaction_type=random.choice(["DEPOSIT", "WITHDRAWAL", "TRANSFER"]),
                    timestamp=start_date + timedelta(
                        days=random.randint(0, 85),
                        hours=random.randint(8, 18),
                        minutes=random.randint(0, 59)
                    ),
                    counterparty=f"Party-{random.randint(1, 200)}",
                    description=random.choice(LEGITIMATE_DESCRIPTIONS)
                )
                db.add(transaction)

        db.commit()
        print(f"✅ Created {len(customers)} customers, {len(all_accounts)} accounts, legitimate transactions seeded.")

        # ══════════════════════════════════════════════════════════════
        # TYPOLOGY 1: SMURFING (Customer 1)
        # Multiple small deposits from many unique sources below $10k
        # ══════════════════════════════════════════════════════════════
        smurf_account = accounts_map[customers[0].id][0]
        smurf_start = datetime.now() - timedelta(days=4)
        print(f"\n🕵️ SMURFING → Customer {customers[0].id}, Account {smurf_account.id}")

        smurf_parties = [f"Individual-{random.randint(1000, 9999)}" for _ in range(18)]
        for i, party in enumerate(smurf_parties):
            transaction = Transaction(
                account_id=smurf_account.id,
                amount=round(random.uniform(5000, 9400), 2),
                transaction_type="DEPOSIT",
                timestamp=smurf_start + timedelta(hours=random.randint(0, 72)),
                counterparty=party,
                description="Cash deposit"
            )
            db.add(transaction)

        # ══════════════════════════════════════════════════════════════
        # TYPOLOGY 2: LAYERING (Customer 2)
        # Large deposit → immediate split into many smaller transfers
        # ══════════════════════════════════════════════════════════════
        layer_account = accounts_map[customers[1].id][0]
        layer_date = datetime.now() - timedelta(days=3)
        print(f"🕵️ LAYERING → Customer {customers[1].id}, Account {layer_account.id}")

        # Large inbound
        big_amount = round(random.uniform(150000, 300000), 2)
        db.add(Transaction(
            account_id=layer_account.id,
            amount=big_amount,
            transaction_type="DEPOSIT",
            timestamp=layer_date,
            counterparty=random.choice(OFFSHORE_ENTITIES),
            description="Wire transfer received"
        ))

        # Immediate outbound fan-out (within 6 hours)
        remaining = big_amount
        split_count = random.randint(8, 14)
        for i in range(split_count):
            split_amount = round(remaining / (split_count - i) * random.uniform(0.5, 1.5), 2)
            split_amount = min(split_amount, remaining)
            remaining -= split_amount
            db.add(Transaction(
                account_id=layer_account.id,
                amount=split_amount,
                transaction_type="TRANSFER",
                timestamp=layer_date + timedelta(hours=random.uniform(1, 6)),
                counterparty=random.choice(SHELL_NAMES),
                description="Outbound wire transfer"
            ))

        # ══════════════════════════════════════════════════════════════
        # TYPOLOGY 3: ROUND-TRIPPING (Customer 3)
        # Money leaves to Party-A, returns from Party-B at similar amount
        # ══════════════════════════════════════════════════════════════
        rt_account = accounts_map[customers[2].id][0]
        rt_date = datetime.now() - timedelta(days=10)
        print(f"🕵️ ROUND-TRIPPING → Customer {customers[2].id}, Account {rt_account.id}")

        linked_pairs = [
            ("Outbound-Corp-Alpha", "Return-Corp-Alpha-Sub"),
            ("Outbound-Corp-Beta", "Return-Corp-Beta-Sub"),
            ("Outbound-Corp-Gamma", "Return-Corp-Gamma-Sub"),
        ]

        for out_party, in_party in linked_pairs:
            rt_amount = round(random.uniform(40000, 90000), 2)
            # Outbound
            db.add(Transaction(
                account_id=rt_account.id,
                amount=rt_amount,
                transaction_type="TRANSFER",
                timestamp=rt_date,
                counterparty=out_party,
                description="Outbound wire"
            ))
            # Return (3-5 days later, amount ±10%)
            return_amount = round(rt_amount * random.uniform(0.90, 1.10), 2)
            db.add(Transaction(
                account_id=rt_account.id,
                amount=return_amount,
                transaction_type="DEPOSIT",
                timestamp=rt_date + timedelta(days=random.randint(3, 5)),
                counterparty=in_party,
                description="Inbound wire"
            ))
            rt_date += timedelta(days=7)

        # ══════════════════════════════════════════════════════════════
        # TYPOLOGY 4: RAPID MOVEMENT / PASS-THROUGH (Customer 4)
        # Large deposit → same-amount withdrawal within 24 hours
        # ══════════════════════════════════════════════════════════════
        rapid_account = accounts_map[customers[3].id][0]
        rapid_date = datetime.now() - timedelta(days=6)
        print(f"🕵️ RAPID MOVEMENT → Customer {customers[3].id}, Account {rapid_account.id}")

        for i in range(4):
            pass_amount = round(random.uniform(50000, 120000), 2)
            # Deposit
            db.add(Transaction(
                account_id=rapid_account.id,
                amount=pass_amount,
                transaction_type="DEPOSIT",
                timestamp=rapid_date + timedelta(days=i * 2, hours=9),
                counterparty=f"Source-Entity-{random.randint(100, 999)}",
                description="Wire deposit"
            ))
            # Same-day withdrawal
            db.add(Transaction(
                account_id=rapid_account.id,
                amount=round(pass_amount * random.uniform(0.95, 1.0), 2),
                transaction_type="WITHDRAWAL",
                timestamp=rapid_date + timedelta(days=i * 2, hours=random.randint(14, 20)),
                counterparty=random.choice(OFFSHORE_ENTITIES),
                description="Outbound wire same day"
            ))

        # ══════════════════════════════════════════════════════════════
        # TYPOLOGY 5: SHELL COMPANY FAN-OUT (Customer 5)
        # One large wire → 10+ transfers to shell entities same day
        # ══════════════════════════════════════════════════════════════
        shell_account = accounts_map[customers[4].id][0]
        shell_date = datetime.now() - timedelta(days=2)
        print(f"🕵️ SHELL FAN-OUT → Customer {customers[4].id}, Account {shell_account.id}")

        # Large inbound wire
        shell_amount = round(random.uniform(500000, 1000000), 2)
        db.add(Transaction(
            account_id=shell_account.id,
            amount=shell_amount,
            transaction_type="DEPOSIT",
            timestamp=shell_date + timedelta(hours=8),
            counterparty="MegaCorp-International",
            description="Large inbound wire"
        ))

        # Fan-out to shell companies
        remaining = shell_amount
        for i, shell in enumerate(SHELL_NAMES):
            fan_amount = round(remaining / (len(SHELL_NAMES) - i) * random.uniform(0.6, 1.4), 2)
            fan_amount = min(fan_amount, remaining)
            remaining -= fan_amount
            db.add(Transaction(
                account_id=shell_account.id,
                amount=fan_amount,
                transaction_type="TRANSFER",
                timestamp=shell_date + timedelta(hours=random.uniform(9, 17)),
                counterparty=shell,
                description=f"Wire to {shell}"
            ))

        db.commit()

        # ── Summary ──
        total_txns = db.query(Transaction).count()
        print(f"\n{'='*60}")
        print(f"✅ DATA GENERATION COMPLETE")
        print(f"   Customers: {len(customers)}")
        print(f"   Accounts:  {len(all_accounts)}")
        print(f"   Transactions: {total_txns}")
        print(f"{'='*60}")
        print(f"\n📋 TYPOLOGY MAP:")
        for cid, typ in typology_assignments.items():
            c = customers[cid - 1]
            acc = accounts_map[c.id][0]
            print(f"   Customer {c.id} (Account {acc.id}) → {typ}")
        print(f"   Customers 6-10 → CLEAN (legitimate activity only)")
        print(f"{'='*60}")

    finally:
        db.close()

if __name__ == "__main__":
    generate_synthetic_data()
