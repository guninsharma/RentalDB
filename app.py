from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'rentaldb_secret_key')

# ── DB connection ──────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'Custom#JamBun#69'),
        database=os.getenv('DB_NAME', 'RentalDB')
    )

# ── Home ───────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    try:
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS c FROM Customer")
        customers = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Equipment WHERE Status='Available'")
        available = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Rental WHERE Rental_Status='Active'")
        active = cur.fetchone()['c']
        cur.execute("SELECT SUM(Amount) AS t FROM Payment WHERE Payment_Status='Completed'")
        revenue = cur.fetchone()['t'] or 0
        db.close()
        return render_template('index.html', customers=customers, available=available, active=active, revenue=revenue)
    except:
        return render_template('index.html', customers=0, available=0, active=0, revenue=0)

# ── Customers ──────────────────────────────────────────────────────────────────
# RUBRIC 3 (showcasing with filters + sort) + RUBRIC 5 (search)
@app.route('/customers')
def customers():
    db = get_db(); cur = db.cursor(dictionary=True)

    search_name  = request.args.get('search_name', '').strip()
    search_email = request.args.get('search_email', '').strip()
    sort_order   = request.args.get('sort', 'ASC')
    if sort_order not in ('ASC', 'DESC'):
        sort_order = 'ASC'

    query  = "SELECT * FROM Customer WHERE 1=1"
    params = []

    if search_name:
        query += " AND (First_Name LIKE %s OR Last_Name LIKE %s)"
        params += [f'%{search_name}%', f'%{search_name}%']
    if search_email:
        query += " AND Email LIKE %s"
        params.append(f'%{search_email}%')

    query += f" ORDER BY Last_Name {sort_order}"

    cur.execute(query, params)
    data = cur.fetchall(); db.close()
    return render_template('customers.html', customers=data,
                           search_name=search_name, search_email=search_email,
                           sort_order=sort_order)

# RUBRIC 1 — register customer, show new Customer_ID after insert
@app.route('/customers/register', methods=['GET', 'POST'])
def register_customer():
    new_id = None
    if request.method == 'POST':
        db = get_db(); cur = db.cursor(dictionary=True)
        try:
            # manual ID: MAX + 1
            cur.execute("SELECT COALESCE(MAX(Customer_ID), 0) + 1 AS nid FROM Customer")
            new_id = cur.fetchone()['nid']
            pwd_hash = generate_password_hash(request.form['password'])
            cur2 = db.cursor()
            cur2.execute(
                """INSERT INTO Customer
                   (Customer_ID, First_Name, Last_Name, Email, Password_Hash, PhNo, Address, DOB)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (new_id, request.form['first_name'], request.form['last_name'],
                 request.form['email'], pwd_hash,
                 request.form['phone'], request.form['address'], request.form['dob'])
            )
            db.commit()
            flash(f'Customer registered! New Customer ID: {new_id}', 'success')
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error'); new_id = None
        finally:
            db.close()
    return render_template('register_customer.html', new_id=new_id)

# RUBRIC 4 — delete customer
@app.route('/customers/delete/<int:cid>', methods=['POST'])
def delete_customer(cid):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("DELETE FROM Customer WHERE Customer_ID = %s", (cid,))
        db.commit(); flash('Customer deleted.', 'success')
    except Exception as e:
        db.rollback(); flash(f'Error: {e}', 'error')
    finally:
        db.close()
    return redirect(url_for('customers'))

# RUBRIC 6 — update customer
@app.route('/customers/edit/<int:cid>', methods=['GET', 'POST'])
def edit_customer(cid):
    db = get_db(); cur = db.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            cur2 = db.cursor()
            cur2.execute(
                """UPDATE Customer
                   SET First_Name=%s, Last_Name=%s, Email=%s, PhNo=%s, Address=%s, DOB=%s
                   WHERE Customer_ID=%s""",
                (request.form['first_name'], request.form['last_name'],
                 request.form['email'], request.form['phone'],
                 request.form['address'], request.form['dob'], cid)
            )
            db.commit(); flash('Customer updated successfully!', 'success')
            db.close(); return redirect(url_for('customers'))
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error')
    cur.execute("SELECT * FROM Customer WHERE Customer_ID = %s", (cid,))
    customer = cur.fetchone(); db.close()
    return render_template('edit_customer.html', customer=customer)

# ── Equipment ──────────────────────────────────────────────────────────────────
# RUBRIC 3 (showcasing with 2 filters + sort) + RUBRIC 5 (search)
@app.route('/equipment')
def equipment():
    db = get_db(); cur = db.cursor(dictionary=True)

    filter_category = request.args.get('category', '').strip()
    filter_status   = request.args.get('status', '').strip()
    sort_order      = request.args.get('sort', 'ASC')
    search_name     = request.args.get('search_name', '').strip()
    if sort_order not in ('ASC', 'DESC'):
        sort_order = 'ASC'

    # fetch distinct categories for dropdown
    cur.execute("SELECT DISTINCT Category FROM Equipment ORDER BY Category")
    categories = [r['Category'] for r in cur.fetchall()]

    query = """SELECT e.*, b.Branch_Name,
                      p.Equip_Name AS Parent_Name
               FROM Equipment e
               LEFT JOIN Branch b ON e.Branch_ID = b.Branch_ID
               LEFT JOIN Equipment p ON e.Parent_Equip_ID = p.Equip_ID
               WHERE 1=1"""
    params = []

    if filter_category:
        query += " AND e.Category = %s"; params.append(filter_category)
    if filter_status:
        query += " AND e.Status = %s"; params.append(filter_status)
    if search_name:
        query += " AND e.Equip_Name LIKE %s"; params.append(f'%{search_name}%')

    query += f" ORDER BY e.Rent_Price_Per_Day {sort_order}"

    cur.execute(query, params)
    data = cur.fetchall(); db.close()
    return render_template('equipment.html', equipment=data, categories=categories,
                           filter_category=filter_category, filter_status=filter_status,
                           sort_order=sort_order, search_name=search_name)

# RUBRIC 1 — add equipment, show new Equip_ID
@app.route('/equipment/add', methods=['GET', 'POST'])
def add_equipment():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT Branch_ID, Branch_Name FROM Branch ORDER BY Branch_Name")
    branches = cur.fetchall()
    cur.execute("SELECT Equip_ID, Equip_Name FROM Equipment ORDER BY Equip_ID")
    equip_list = cur.fetchall()
    new_id = None
    if request.method == 'POST':
        cur2 = db.cursor(dictionary=True)
        try:
            cur2.execute("SELECT COALESCE(MAX(Equip_ID), 0) + 1 AS nid FROM Equipment")
            new_id = cur2.fetchone()['nid']
            parent = request.form['parent_id'] or None
            cur3 = db.cursor()
            cur3.execute(
                """INSERT INTO Equipment
                   (Equip_ID, Equip_Name, Category, Rent_Price_Per_Day, Condition_State, Status, Branch_ID, Parent_Equip_ID)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (new_id, request.form['equip_name'], request.form['category'],
                 request.form['rent_price'], request.form['condition'],
                 request.form['status'], request.form['branch_id'], parent)
            )
            db.commit()
            flash(f'Equipment added! New Equipment ID: {new_id}', 'success')
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error'); new_id = None
    db.close()
    return render_template('add_equipment.html', branches=branches,
                           equip_list=equip_list, new_id=new_id)

# RUBRIC 4 — delete equipment
@app.route('/equipment/delete/<int:eid>', methods=['POST'])
def delete_equipment(eid):
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("DELETE FROM Equipment WHERE Equip_ID = %s", (eid,))
        db.commit(); flash('Equipment deleted.', 'success')
    except Exception as e:
        db.rollback(); flash(f'Error: {e}', 'error')
    finally:
        db.close()
    return redirect(url_for('equipment'))

# RUBRIC 6 — update equipment
@app.route('/equipment/edit/<int:eid>', methods=['GET', 'POST'])
def edit_equipment(eid):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT Branch_ID, Branch_Name FROM Branch ORDER BY Branch_Name")
    branches = cur.fetchall()
    if request.method == 'POST':
        try:
            cur2 = db.cursor()
            cur2.execute(
                """UPDATE Equipment
                   SET Equip_Name=%s, Category=%s, Rent_Price_Per_Day=%s,
                       Condition_State=%s, Status=%s, Branch_ID=%s
                   WHERE Equip_ID=%s""",
                (request.form['equip_name'], request.form['category'],
                 request.form['rent_price'], request.form['condition'],
                 request.form['status'], request.form['branch_id'], eid)
            )
            db.commit(); flash('Equipment updated!', 'success')
            db.close(); return redirect(url_for('equipment'))
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error')
    cur.execute("SELECT * FROM Equipment WHERE Equip_ID = %s", (eid,))
    equip = cur.fetchone(); db.close()
    return render_template('edit_equipment.html', equip=equip, branches=branches)

# ── Rentals ────────────────────────────────────────────────────────────────────
@app.route('/rentals')
def rentals():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT r.*,
                          CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name,
                          e.Equip_Name,
                          s.Staff_Name,
                          b.Branch_Name
                   FROM Rental r
                   LEFT JOIN Customer c ON r.Customer_ID = c.Customer_ID
                   LEFT JOIN Equipment e ON r.Equip_ID = e.Equip_ID
                   LEFT JOIN Staff s ON r.Staff_ID = s.Staff_ID
                   LEFT JOIN Branch b ON r.Branch_ID = b.Branch_ID
                   ORDER BY r.Rental_ID""")
    data = cur.fetchall(); db.close()
    return render_template('rentals.html', rentals=data)

# RUBRIC 1 — book rental, show new Rental_ID
@app.route('/rentals/book', methods=['GET', 'POST'])
def book_rental():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT Customer_ID, CONCAT(First_Name,' ',Last_Name) AS Name FROM Customer ORDER BY First_Name")
    customers = cur.fetchall()
    cur.execute("SELECT Equip_ID, Equip_Name, Rent_Price_Per_Day FROM Equipment WHERE Status='Available' ORDER BY Equip_Name")
    equip = cur.fetchall()
    cur.execute("SELECT Branch_ID, Branch_Name FROM Branch ORDER BY Branch_Name")
    branches = cur.fetchall()
    cur.execute("SELECT Staff_ID, Staff_Name FROM Staff ORDER BY Staff_Name")
    staff = cur.fetchall()
    new_id = None
    if request.method == 'POST':
        cur2 = db.cursor(dictionary=True)
        try:
            cur2.execute("SELECT COALESCE(MAX(Rental_ID), 0) + 1 AS nid FROM Rental")
            new_id = cur2.fetchone()['nid']
            cur3 = db.cursor()
            cur3.execute(
                """INSERT INTO Rental
                   (Rental_ID, Total_Amount, Rental_Status, Start_Date, End_Date, Return_Date,
                    Customer_ID, Equip_ID, Branch_ID, Staff_ID)
                   VALUES (%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s)""",
                (new_id, request.form['total_amount'], request.form['rental_status'],
                 request.form['start_date'], request.form['end_date'],
                 request.form['customer_id'], request.form['equip_id'],
                 request.form['branch_id'], request.form['staff_id'])
            )
            # NOTE: Equipment status is updated by the DB trigger (RUBRIC 2)
            db.commit()
            flash(f'Rental booked! New Rental ID: {new_id}. Please complete the payment.', 'success')
            db.close(); return redirect(url_for('make_payment', rental_id=new_id))
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error')
    db.close()
    return render_template('book_rental.html', customers=customers, equipment=equip,
                           branches=branches, staff=staff, new_id=new_id)

# RUBRIC 6 — update rental status / return date
@app.route('/rentals/edit/<int:rid>', methods=['GET', 'POST'])
def edit_rental(rid):
    db = get_db(); cur = db.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            return_date = request.form['return_date'] or None
            cur2 = db.cursor()
            cur2.execute(
                """UPDATE Rental
                   SET Rental_Status=%s, Return_Date=%s
                   WHERE Rental_ID=%s""",
                (request.form['rental_status'], return_date, rid)
            )
            # if completed, mark equipment available again
            if request.form['rental_status'] == 'Completed':
                cur2.execute("""UPDATE Equipment SET Status='Available'
                                WHERE Equip_ID=(SELECT Equip_ID FROM Rental WHERE Rental_ID=%s)""", (rid,))
            db.commit(); flash('Rental updated!', 'success')
            db.close(); return redirect(url_for('rentals'))
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error')
    cur.execute("""SELECT r.*, CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name, e.Equip_Name
                   FROM Rental r
                   LEFT JOIN Customer c ON r.Customer_ID=c.Customer_ID
                   LEFT JOIN Equipment e ON r.Equip_ID=e.Equip_ID
                   WHERE r.Rental_ID=%s""", (rid,))
    rental = cur.fetchone(); db.close()
    return render_template('edit_rental.html', rental=rental)

# ── Payments ───────────────────────────────────────────────────────────────────
@app.route('/payments')
def payments():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT p.*,
                          CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name,
                          e.Equip_Name,
                          r.Total_Amount AS Rental_Amount
                   FROM Payment p
                   JOIN Rental r ON p.Rental_ID = r.Rental_ID
                   LEFT JOIN Customer c ON r.Customer_ID = c.Customer_ID
                   LEFT JOIN Equipment e ON r.Equip_ID = e.Equip_ID
                   ORDER BY p.Payment_ID""")
    data = cur.fetchall(); db.close()
    return render_template('payments.html', payments=data)

# RUBRIC 1 — make payment, show new Payment_ID
@app.route('/payments/make', methods=['GET', 'POST'])
def make_payment():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT r.Rental_ID,
                          CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name,
                          e.Equip_Name, r.Total_Amount
                   FROM Rental r
                   LEFT JOIN Customer c ON r.Customer_ID = c.Customer_ID
                   LEFT JOIN Equipment e ON r.Equip_ID = e.Equip_ID
                   WHERE r.Rental_ID NOT IN (SELECT Rental_ID FROM Payment WHERE Rental_ID IS NOT NULL)
                   ORDER BY r.Rental_ID""")
    rentals = cur.fetchall()
    selected_rental_id = request.args.get('rental_id')
    new_id = None
    if request.method == 'POST':
        cur2 = db.cursor(dictionary=True)
        try:
            cur2.execute("SELECT COALESCE(MAX(Payment_ID), 0) + 1 AS nid FROM Payment")
            new_id = cur2.fetchone()['nid']
            cur3 = db.cursor()
            cur3.execute(
                """INSERT INTO Payment
                   (Payment_ID, Payment_Date, Amount, Payment_Mode, Payment_Status, Rental_ID)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (new_id, request.form['payment_date'], request.form['amount'],
                 request.form['mode'], request.form['status'],
                 request.form['rental_id'])
            )
            db.commit()
            flash(f'Payment recorded! New Payment ID: {new_id}', 'success')
            db.close(); return redirect(url_for('payments'))
        except Exception as e:
            db.rollback(); flash(f'Error: {e}', 'error')
    db.close()
    return render_template('make_payment.html', rentals=rentals,
                           selected_rental_id=selected_rental_id, new_id=new_id)

# ── Analytics — RUBRIC 7 (GROUP BY + HAVING) ──────────────────────────────────
@app.route('/analytics')
def analytics():
    db = get_db(); cur = db.cursor(dictionary=True)

    # Revenue per branch (GROUP BY)
    cur.execute("""
        SELECT b.Branch_Name,
               COUNT(p.Payment_ID) AS Total_Payments,
               SUM(p.Amount)       AS Total_Revenue,
               AVG(p.Amount)       AS Avg_Payment
        FROM Payment p
        JOIN Rental r  ON p.Rental_ID  = r.Rental_ID
        JOIN Branch b  ON r.Branch_ID  = b.Branch_ID
        WHERE p.Payment_Status = 'Completed'
        GROUP BY b.Branch_ID, b.Branch_Name
        ORDER BY Total_Revenue DESC
    """)
    branch_revenue = cur.fetchall()

    # Branches with revenue > 0 (HAVING)
    cur.execute("""
        SELECT b.Branch_Name,
               SUM(p.Amount) AS Total_Revenue
        FROM Payment p
        JOIN Rental r ON p.Rental_ID = r.Rental_ID
        JOIN Branch b ON r.Branch_ID = b.Branch_ID
        WHERE p.Payment_Status = 'Completed'
        GROUP BY b.Branch_ID, b.Branch_Name
        HAVING SUM(p.Amount) > 0
        ORDER BY Total_Revenue DESC
    """)
    active_branches = cur.fetchall()

    # Equipment category stats (GROUP BY)
    cur.execute("""
        SELECT e.Category,
               COUNT(e.Equip_ID)          AS Total_Items,
               SUM(CASE WHEN e.Status='Available' THEN 1 ELSE 0 END) AS Available,
               AVG(e.Rent_Price_Per_Day)  AS Avg_Price
        FROM Equipment e
        GROUP BY e.Category
        ORDER BY Total_Items DESC
    """)
    category_stats = cur.fetchall()

    # Categories with more than 1 item (HAVING)
    cur.execute("""
        SELECT e.Category,
               COUNT(e.Equip_ID) AS Total_Items
        FROM Equipment e
        GROUP BY e.Category
        HAVING COUNT(e.Equip_ID) > 1
        ORDER BY Total_Items DESC
    """)
    multi_item_categories = cur.fetchall()

    # Customer rental counts (GROUP BY)
    cur.execute("""
        SELECT CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name,
               COUNT(r.Rental_ID)  AS Total_Rentals,
               SUM(r.Total_Amount) AS Total_Spent
        FROM Rental r
        JOIN Customer c ON r.Customer_ID = c.Customer_ID
        GROUP BY c.Customer_ID, c.First_Name, c.Last_Name
        ORDER BY Total_Rentals DESC
    """)
    customer_stats = cur.fetchall()

    # Customers with more than 1 rental (HAVING)
    cur.execute("""
        SELECT CONCAT(c.First_Name,' ',c.Last_Name) AS Customer_Name,
               COUNT(r.Rental_ID) AS Total_Rentals
        FROM Rental r
        JOIN Customer c ON r.Customer_ID = c.Customer_ID
        GROUP BY c.Customer_ID, c.First_Name, c.Last_Name
        HAVING COUNT(r.Rental_ID) > 1
        ORDER BY Total_Rentals DESC
    """)
    repeat_customers = cur.fetchall()

    db.close()
    return render_template('analytics.html',
                           branch_revenue=branch_revenue,
                           active_branches=active_branches,
                           category_stats=category_stats,
                           multi_item_categories=multi_item_categories,
                           customer_stats=customer_stats,
                           repeat_customers=repeat_customers)

# ── Login / Logout ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db(); cur = db.cursor(dictionary=True)
        email    = request.form['email']
        password = request.form['password']
        cur.execute("SELECT * FROM Customer WHERE Email = %s", (email,))
        user = cur.fetchone(); db.close()
        if user and check_password_hash(user['Password_Hash'], password):
            session['customer_id']   = user['Customer_ID']
            session['customer_name'] = f"{user['First_Name']} {user['Last_Name']}"
            flash(f"Welcome back, {user['First_Name']}!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
