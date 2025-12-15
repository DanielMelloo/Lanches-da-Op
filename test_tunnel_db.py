from sqlalchemy import create_engine, text

def test_conn():
    # Tunnel is on 3307
    uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'
    print(f"Connecting to {uri}...")
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT DATABASE()"))
            print("Connected to:", res.fetchone())
            
            res2 = conn.execute(text("SELECT count(*) FROM subsites"))
            print("Subsites count:", res2.fetchone())
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    test_conn()
