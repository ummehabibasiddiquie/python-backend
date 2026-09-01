from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor(dictionary=True)
cur.execute(
    """
    SELECT roster_month_id, user_id, month_year, status, locked_by, locked_date
    FROM roster_month
    WHERE is_active = 1 AND status IN ('Locked', 'Approved', 'Pending Approval')
    ORDER BY roster_month_id DESC
    LIMIT 20
    """
)
print("Approved/Locked/Pending:")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
