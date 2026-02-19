from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

engine = create_engine(DATABASE_URL)

def debug_raw():
    print("=== RAW SQL DEBUG ===")
    with engine.connect() as conn:
        # Check Account 11 transactions > 9000
        result = conn.execute(text("SELECT id, amount, transaction_type, timestamp FROM transactions WHERE account_id = 11 AND amount > 9000"))
        rows = result.fetchall()
        print(f"SQL Query (Account 11, >9000) returned {len(rows)} rows:")
        for r in rows:
            print(f"  - ID: {r.id} | Amt: {r.amount} (Type: {type(r.amount)}) | Type: '{r.transaction_type}'")

if __name__ == "__main__":
    debug_raw()
