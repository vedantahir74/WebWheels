import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import random
import re
from datetime import datetime, timedelta
import os
import smtplib
from price_calculator import calculate_fair_price
from email.message import EmailMessage
from functools import wraps
import groq
GROQ_API_KEY = "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"
app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.secret_key = "vehicle-marketplace-secret-key-2024"


# ==================== DATABASE CLASS ====================
class Database:
    def __init__(self):
        self.db_name = 'WebWheels.db'
        
        if os.path.exists(self.db_name):
            try:
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.execute("PRAGMA busy_timeout = 5000;")
                self.cursor = self.conn.cursor()
                print(f"Connected to existing database: {self.db_name}")
            except:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.db_name = f'vehicle_marketplace_{timestamp}.db'
                print(f"Database locked, creating new: {self.db_name}")
                self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
        else:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print(f"Created new database: {self.db_name}")
        
        self.create_tables()
        self.create_admin()
        
    def create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                address TEXT,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Admin balance table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                balance REAL DEFAULT 10000000.00,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Vehicles table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                variant TEXT,
                fuel_type TEXT NOT NULL,
                year INTEGER NOT NULL,
                price REAL NOT NULL,
                transmission TEXT,
                color TEXT,
                body_type TEXT,
                features TEXT,  
                mileage REAL,
                engine_cc REAL,
                seats INTEGER,
                km_driven INTEGER,
                images TEXT,  
                status TEXT DEFAULT 'PENDING',
                vehicle_type TEXT DEFAULT 'SELL',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users(id)
            )
        ''')
        
        # Rentals table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                renter_id INTEGER,
                owner_id INTEGER,
                daily_rate REAL NOT NULL,
                hourly_rate REAL,
                weekly_rate REAL,
                monthly_rate REAL,
                security_deposit REAL,
                is_available BOOLEAN DEFAULT 1,
                start_date DATE,
                end_date DATE,
                rental_days INTEGER,
                rental_hours INTEGER,
                total_amount REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (renter_id) REFERENCES users(id),
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        ''')
        
        # Transactions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER,
                seller_id INTEGER,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                payment_method TEXT,
                invoice_number TEXT UNIQUE,
                status TEXT DEFAULT 'COMPLETED',
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invoice_data TEXT,
                commission_amount REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (seller_id) REFERENCES users(id)
            )
        ''')
        
        # Purchases table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                seller_id INTEGER,
                vehicle_id INTEGER,
                transaction_id INTEGER,
                purchase_price REAL NOT NULL,
                payment_status TEXT DEFAULT 'COMPLETED',
                delivery_status TEXT DEFAULT 'PENDING',
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivery_address TEXT,
                FOREIGN KEY (buyer_id) REFERENCES users(id),
                FOREIGN KEY (seller_id) REFERENCES users(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        ''')
        
        # Wishlist table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vehicle_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                UNIQUE(user_id, vehicle_id)
            )
        ''')
        
        # AI Chat History
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # OTP verification table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS otp_verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp TEXT NOT NULL,
                purpose TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Custom car requests table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_car_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                body_type TEXT NOT NULL,
                color TEXT NOT NULL,
                fuel_type TEXT NOT NULL,
                engine_cc INTEGER,
                doors INTEGER,
                seats INTEGER,
                transmission TEXT,
                features TEXT,
                additional_requirements TEXT,
                suggested_price REAL,
                status TEXT DEFAULT 'PENDING',
                delivery_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # Feedback table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'APPROVED',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
                
        self.conn.commit()
        print("All tables created successfully!")
    
    def create_admin(self):
        # Check if admin already exists
        self.cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = self.cursor.fetchone()

        if admin:
            return   # Admin already exists

        admin_pass = self.hash_password('Admin@123')

        # Insert admin user
        self.cursor.execute("""
            INSERT INTO users 
            (username, password, email, phone, full_name, role) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'admin',
            admin_pass,
            'webwheels7@gmail.com',
            '7211172096',
            'System Administrator',
            'ADMIN'
        ))

        self.conn.commit()

        # Get admin id safely
        self.cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = self.cursor.fetchone()["id"]

        # Create admin balance record
        self.cursor.execute("""
            INSERT INTO admin_balance (user_id, balance)
            VALUES (?, ?)
        """, (admin_id, 10000000.00))

        self.conn.commit()

        # print("Admin account created (username: admin, password: Admin@123)")
        print("Admin balance initialized with: 1,00,00,000.00")
    
    def hash_password(self, password):
        """Simple password hashing using SHA‑256 (for demonstration)."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    
# =========================================== OTP SYSTEM ============================
    
    # In your Database class:

    def generate_otp(self):
        import random
        return str(random.randint(100000, 999999))

    def save_otp(self, email, otp, purpose):
        from datetime import datetime, timedelta
        
        # Remove old OTP for this email and purpose
        self.cursor.execute("""
            DELETE FROM otp_verification
            WHERE email=? AND purpose=?
        """, (email, purpose))
        
        # Set expiry to 10 minutes from now
        expiry = datetime.now() + timedelta(minutes=10)
        
        # Save new OTP
        self.cursor.execute("""
            INSERT INTO otp_verification
            (email, otp, purpose, expires_at)
            VALUES (?, ?, ?, ?)
        """, (email, otp, purpose, expiry))
        
        self.conn.commit()

    def verify_otp(self, email, otp, purpose):
        from datetime import datetime
        
        # Check if OTP exists and is not expired
        self.cursor.execute("""
            SELECT * FROM otp_verification
            WHERE email=? AND otp=? AND purpose=?
            AND expires_at > ?
        """, (email, otp, purpose, datetime.now()))
        
        row = self.cursor.fetchone()
        
        if row:
            # Delete OTP after successful verification
            self.cursor.execute("""
                DELETE FROM otp_verification
                WHERE email=? AND purpose=?
            """, (email, purpose))
            self.conn.commit()
            return True
        
        return False

    def send_email(self, recipient, subject, body):
        """Send email using Gmail SMTP"""
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            
            sender_email = "webwheels7@gmail.com"
            sender_password = "yfoq lebi idce ipwe"  # Make sure this is correct
            
            # Add this debug line
            print(f"Attempting to send email from {sender_email} to {recipient}")
            
            server.login(sender_email, sender_password)
            print(" SMTP login successful")
            
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient
            
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent to {recipient}")
            return True
        except Exception as e:
            print(f" Error sending email: {e}")
            return False
        
    def hash_password(self, password):
        """Hash password using SHA256"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
# ==================== CUSTOM CAR REQUESTS ====================================
    
    def create_custom_request(self, data):
        """Create custom car request"""
        self.cursor.execute('''
            INSERT INTO custom_car_requests (
                user_id, user_name, user_email, body_type, color, fuel_type,
                engine_cc, doors, seats, transmission, features, 
                additional_requirements, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'], data['user_name'], data['user_email'],
            data['body_type'], data['color'], data['fuel_type'],
            data['engine_cc'], data['doors'], data['seats'], data['transmission'],
            data['features'], data.get('additional_requirements', ''), 'PENDING'
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_custom_requests(self, status='PENDING'):
        """Get custom car requests"""
        if status:
            self.cursor.execute('''
                SELECT * FROM custom_car_requests WHERE status = ? ORDER BY created_at DESC
            ''', (status,))
        else:
            self.cursor.execute('SELECT * FROM custom_car_requests ORDER BY created_at DESC')
        return self.cursor.fetchall()
    
    def update_custom_request_price(self, request_id, price):
        """Update custom request with suggested price"""
        self.cursor.execute('UPDATE custom_car_requests SET suggested_price = ?, status = ? WHERE id = ?',
                          (price, 'PRICE_SET', request_id))
        self.conn.commit()
    
    def update_custom_request_status(self, request_id, status):
        """Update custom request status"""
        self.cursor.execute('UPDATE custom_car_requests SET status = ? WHERE id = ?', (status, request_id))
        self.conn.commit()
    
    def update_custom_request_delivery(self, request_id, address):
        """Update delivery address"""
        self.cursor.execute('UPDATE custom_car_requests SET delivery_address = ? WHERE id = ?', (address, request_id))
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ==================== VALIDATOR CLASS ====================
class EnhancedValidator:
    def __init__(self, db):
        self.db = db
    
    @staticmethod
    def validate_input(prompt, validation_func, error_msg=None):
        """Generic input validation with retry logic"""
        while True:
            value = input(prompt).strip()
            is_valid, message = validation_func(value)
            if is_valid:
                return value
            else:
                print(f"Error: {error_msg if error_msg else message}")
                print("   Please try again.")
    
    def validate_username(self, username):
        """Validate username format and check database availability"""
        if not username:
            return False, "Username cannot be empty"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 20:
            return False, "Username cannot exceed 20 characters"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers and underscores (_)"
        
        if username[0].isdigit():
            return False, "Username cannot start with a number"
        
        # Check database for existing username
        try:
            self.db.cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if self.db.cursor.fetchone():
                return False, "Username already exists! Please choose a different username."
        except:
            pass
        
        return True, "Username is available!"
    
    def validate_email(self, email):
        """Validate email format and check database availability"""
        if not email:
            return False, "Email cannot be empty"
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format (example: user@example.com)"
        
        # Check database for existing email
        try:
            self.db.cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if self.db.cursor.fetchone():
                return False, "Email already registered! Use a different email or try logging in."
        except:
            pass
        
        return True, "Email is valid and available!"
    
    def validate_phone(self, phone):
        """Validate Indian phone number and check database availability"""
        if not phone:
            return False, "Phone number cannot be empty"
        
        # Remove spaces and dashes
        phone_clean = phone.replace(' ', '').replace('-', '')
        
        # Check if only digits
        if not phone_clean.isdigit():
            return False, "Phone number must contain only digits"
        
        # Check length
        if len(phone_clean) != 10:
            return False, "Phone number must be exactly 10 digits"
        
        # Check if starts with valid digit (6-9 for Indian numbers)
        if phone_clean[0] not in ['6', '7', '8', '9']:
            return False, "Indian phone numbers must start with 6, 7, 8, or 9"
        
        # Check database for existing phone
        try:
            self.db.cursor.execute('SELECT id FROM users WHERE phone = ?', (phone_clean,))
            if self.db.cursor.fetchone():
                return False, "Phone number already registered! Use a different number or try logging in."
        except:
            pass
        
        return True, f"Phone number {phone_clean} is valid and available!"
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password:
            return False, "Password cannot be empty"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 50:
            return False, "Password cannot exceed 50 characters"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter (A-Z)"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter (a-z)"
        
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one digit (0-9)"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character (!@#$%^&*...)"
        
        return True, "Strong password!"
    
    @staticmethod
    def validate_full_name(name):
        """Validate full name"""
        if not name:
            return False, "Full name cannot be empty"
        
        if len(name) < 2:
            return False, "Name must be at least 2 characters long"
        
        if len(name) > 50:
            return False, "Name cannot exceed 50 characters"
        
        if not re.match(r'^[a-zA-Z\s.\'-]+$', name):
            return False, "Name can only contain letters, spaces, dots (.), apostrophes (') and hyphens (-)"
        
        return True, "Valid name!"

# ==================== AI HELPER ====================
# ==================== AI HELPER - UPDATED FOR RUPEES AND ACCURATE DATA ====================
class AIHelper:
    def __init__(self, db):
        self.db = db
        self.client = groq.Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
        
        # Updated system prompt with Rupees context
        self.system_prompt = """You are an AI assistant for WebWheels, an Indian vehicle marketplace platform. 
IMPORTANT: Always use Indian Rupees (₹) for all pricing, never use dollars ($).

Your role is to help users with:
1. Buying and selling vehicles in India
2. Renting vehicles in India
3. Vehicle pricing and valuation in Indian Rupees
4. Marketplace policies and procedures
5. Vehicle recommendations based on budget (in lakhs/crores)
6. Custom car building requests
7. Technical questions about vehicles

When providing prices:
- Use ₹ symbol (e.g., ₹5,00,000 for 5 lakhs)
- Use lakhs and crores notation when appropriate (e.g., ₹5.5 lakhs, ₹12 lakhs, ₹1.2 crores)
- Format large numbers with Indian numbering system (lakhs, crores)

Keep responses concise, helpful, and focused on the Indian vehicle marketplace.
Always maintain a professional and friendly tone."""
    
    def get_user_conversation_history(self, user_id, limit=10):
        """Get recent conversation history for context"""
        try:
            self.db.cursor.execute('''
                SELECT query, response, created_at 
                FROM ai_chat_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            history = self.db.cursor.fetchall()
            return list(reversed(history))
        except Exception as e:
            print(f"Error fetching conversation history: {e}")
            return []
    
    def get_detailed_marketplace_context(self):
        """Get comprehensive marketplace statistics with Rupees"""
        try:
            # Basic counts
            self.db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='APPROVED'")
            total_vehicles = self.db.cursor.fetchone()[0] or 0
            
            self.db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type='SELL' AND status='APPROVED'")
            cars_for_sale = self.db.cursor.fetchone()[0] or 0
            
            self.db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type='RENT' AND status='APPROVED'")
            cars_for_rent = self.db.cursor.fetchone()[0] or 0
            
            # Price statistics for cars for sale
            self.db.cursor.execute("""
                SELECT MIN(price), MAX(price), AVG(price) 
                FROM vehicles 
                WHERE status='APPROVED' AND vehicle_type='SELL' AND price > 0
            """)
            price_stats = self.db.cursor.fetchone()
            min_price = price_stats[0] or 0
            max_price = price_stats[1] or 0
            avg_price = price_stats[2] or 0
            
            # Get top brands with counts
            self.db.cursor.execute("""
                SELECT brand, COUNT(*) as count 
                FROM vehicles 
                WHERE status='APPROVED' 
                GROUP BY brand 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_brands = [f"{row[0]} ({row[1]} vehicles)" for row in self.db.cursor.fetchall()]
            
            # Get vehicles by fuel type
            self.db.cursor.execute("""
                SELECT fuel_type, COUNT(*) 
                FROM vehicles 
                WHERE status='APPROVED' 
                GROUP BY fuel_type
            """)
            fuel_types = [f"{row[0]}: {row[1]}" for row in self.db.cursor.fetchall()]
            
            # Get vehicles by body type
            self.db.cursor.execute("""
                SELECT body_type, COUNT(*) 
                FROM vehicles 
                WHERE status='APPROVED' AND body_type IS NOT NULL 
                GROUP BY body_type
            """)
            body_types = [f"{row[0]}: {row[1]}" for row in self.db.cursor.fetchall()]
            
            # Get recent vehicles
            self.db.cursor.execute("""
                SELECT brand, model, year, price 
                FROM vehicles 
                WHERE status='APPROVED' AND vehicle_type='SELL' 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_vehicles = []
            for row in self.db.cursor.fetchall():
                recent_vehicles.append(f"{row[0]} {row[1]} ({row[2]}) - ₹{row[3]:,.0f}")
            
            # Get rental rates
            self.db.cursor.execute("""
                SELECT MIN(daily_rate), MAX(daily_rate), AVG(daily_rate)
                FROM rentals 
                WHERE status='AVAILABLE'
            """)
            rental_stats = self.db.cursor.fetchone()
            min_rental = rental_stats[0] or 0
            max_rental = rental_stats[1] or 0
            avg_rental = rental_stats[2] or 0
            
            # Format the context
            context = f"""
Current marketplace statistics (ALL PRICES IN INDIAN RUPEES ₹):

📊 OVERALL STATISTICS:
- Total available vehicles: {total_vehicles}
- Cars for sale: {cars_for_sale}
- Cars for rent: {cars_for_rent}

💰 PRICE RANGE (Sale Vehicles):
- Minimum price: ₹{min_price:,.0f}
- Maximum price: ₹{max_price:,.0f}
- Average price: ₹{avg_price:,.0f}
- Price in lakhs: ₹{avg_price/100000:.2f} lakhs

🏢 TOP BRANDS AVAILABLE:
{chr(10).join(['  • ' + brand for brand in top_brands]) if top_brands else '  • No brands data'}

⛽ FUEL TYPES:
{chr(10).join(['  • ' + ft for ft in fuel_types]) if fuel_types else '  • No fuel type data'}

🚗 BODY TYPES:
{chr(10).join(['  • ' + bt for bt in body_types]) if body_types else '  • No body type data'}

📅 RENTAL RATES (Per Day):
- Minimum: ₹{min_rental:,.0f}/day
- Maximum: ₹{max_rental:,.0f}/day
- Average: ₹{avg_rental:,.0f}/day

🆕 RECENT LISTINGS:
{chr(10).join(['  • ' + rv for rv in recent_vehicles]) if recent_vehicles else '  • No recent listings'}

Use this data to answer user queries accurately. Always format prices in Indian Rupees (₹).
"""
            return context
            
        except Exception as e:
            print(f"Error getting marketplace context: {e}")
            return "Marketplace data temporarily unavailable."
    
    def get_brand_specific_data(self, brand):
        """Get specific data for a particular brand"""
        try:
            self.db.cursor.execute("""
                SELECT model, year, price, fuel_type, transmission 
                FROM vehicles 
                WHERE status='APPROVED' AND vehicle_type='SELL' AND LOWER(brand) LIKE LOWER(?)
                ORDER BY price
                LIMIT 10
            """, (f'%{brand}%',))
            
            vehicles = self.db.cursor.fetchall()
            
            if not vehicles:
                return None
            
            result = f"\n📊 {brand.upper()} VEHICLES AVAILABLE:\n"
            for v in vehicles:
                result += f"  • {v[0]} ({v[1]}) - {v[3]}, {v[4]} - ₹{v[2]:,.0f}\n"
            
            # Get count and average price
            self.db.cursor.execute("""
                SELECT COUNT(*), AVG(price), MIN(price), MAX(price)
                FROM vehicles 
                WHERE status='APPROVED' AND vehicle_type='SELL' AND LOWER(brand) LIKE LOWER(?)
            """, (f'%{brand}%',))
            stats = self.db.cursor.fetchone()
            
            result += f"\n📈 {brand} STATISTICS:\n"
            result += f"  • Total vehicles: {stats[0]}\n"
            result += f"  • Average price: ₹{stats[1]:,.0f}\n"
            result += f"  • Price range: ₹{stats[2]:,.0f} - ₹{stats[3]:,.0f}\n"
            
            return result
            
        except Exception as e:
            print(f"Error getting brand data: {e}")
            return None
    
    def get_how_to_buy_guide(self):
        """Get step-by-step guide for buying a car"""
        try:
            # Get sample vehicles for reference
            self.db.cursor.execute("""
                SELECT brand, model, price 
                FROM vehicles 
                WHERE status='APPROVED' AND vehicle_type='SELL' 
                ORDER BY RANDOM() 
                LIMIT 3
            """)
            samples = self.db.cursor.fetchall()
            
            sample_text = ""
            if samples:
                sample_text = "\n📌 EXAMPLE VEHICLES CURRENTLY AVAILABLE:\n"
                for s in samples:
                    sample_text += f"  • {s[0]} {s[1]} - ₹{s[2]:,.0f}\n"
            
            guide = f"""
📋 STEP-BY-STEP GUIDE TO BUY A CAR ON WEBWHEELS:

1️⃣ **SEARCH & BROWSE**
   • Use the search bar to find cars by brand, model, or budget
   • Apply filters for price range, fuel type, transmission, etc.
   • Browse through our {self.get_total_sale_vehicles()}+ cars for sale

2️⃣ **VIEW DETAILS**
   • Click on any car to see complete specifications
   • Check photos, features, and vehicle history
   • Compare multiple vehicles side by side

3️⃣ **CONTACT SELLER**
   • Use the "Contact Seller" button to ask questions
   • Request for test drive if interested
   • Negotiate price if needed (sellers may be flexible)

4️⃣ **MAKE PAYMENT**
   • Once decided, click "Buy Now" to proceed to checkout
   • Review the price breakdown:
     - Base Price: Shown on vehicle page
     - Platform Fee: 8% of base price
     - Total: Base Price + Platform Fee
   • Choose payment method (UPI, Credit Card, Net Banking)

5️⃣ **COMPLETE PURCHASE**
   • Enter delivery address
   • Complete payment securely
   • Receive invoice via email
   • Vehicle will be delivered within 7-10 business days

💰 **PRICE EXAMPLE:**
   If you buy a car priced at ₹5,00,000:
   • Base Price: ₹5,00,000
   • Platform Fee (8%): ₹40,000
   • Total You Pay: ₹5,40,000
{sample_text}

Need help finding a specific car? Just ask me about available models or brands!
"""
            return guide
            
        except Exception as e:
            print(f"Error generating guide: {e}")
            return self.get_fallback_guide()
    
    def get_total_sale_vehicles(self):
        """Get total number of vehicles for sale"""
        try:
            self.db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='APPROVED' AND vehicle_type='SELL'")
            return self.db.cursor.fetchone()[0]
        except:
            return "many"
    
    def get_fallback_guide(self):
        """Fallback guide if database query fails"""
        return """
📋 STEP-BY-STEP GUIDE TO BUY A CAR ON WEBWHEELS:

1️⃣ **SEARCH & BROWSE**
   • Use the search bar to find cars by brand, model, or budget
   • Apply filters for price range, fuel type, transmission, etc.

2️⃣ **VIEW DETAILS**
   • Click on any car to see complete specifications
   • Check photos, features, and vehicle history

3️⃣ **CONTACT SELLER**
   • Use the "Contact Seller" button to ask questions
   • Request for test drive if interested

4️⃣ **MAKE PAYMENT**
   • Click "Buy Now" to proceed to checkout
   • Review price breakdown (Base Price + 8% platform fee)
   • Choose payment method

5️⃣ **COMPLETE PURCHASE**
   • Enter delivery address
   • Complete payment
   • Receive invoice via email

Need help finding a specific car? Just ask me about available models or brands!
"""
    
    def detect_query_type(self, query):
        """Detect what type of information user is asking for"""
        query_lower = query.lower()
        
        # Check for brand-specific queries
        brands = ['maruti', 'suzuki', 'hyundai', 'tata', 'mahindra', 'kia', 'honda', 
                  'toyota', 'mg', 'renault', 'nissan', 'ford', 'volkswagen', 'skoda']
        for brand in brands:
            if brand in query_lower:
                return f"brand_{brand}"
        
        # Check for how-to queries
        if any(word in query_lower for word in ['how to', 'guide', 'steps', 'process']):
            if 'buy' in query_lower:
                return "how_to_buy"
            elif 'sell' in query_lower:
                return "how_to_sell"
            elif 'rent' in query_lower:
                return "how_to_rent"
        
        # Check for statistics queries
        if any(word in query_lower for word in ['how many', 'count', 'available', 'total']):
            return "statistics"
        
        # Check for price queries
        if any(word in query_lower for word in ['price', 'cost', '₹', 'rupee', 'lakh', 'crore']):
            return "pricing"
        
        return "general"
    
    def get_response(self, query, user_id=None):
        """Get AI response using Groq API with accurate Indian Rupees data"""
        try:
            # Detect query type
            query_type = self.detect_query_type(query)
            
            # Handle specific query types without calling Groq API
            if query_type == "how_to_buy":
                return self.get_how_to_buy_guide()
            
            elif query_type.startswith("brand_"):
                brand = query_type.replace("brand_", "")
                brand_data = self.get_brand_specific_data(brand)
                if brand_data:
                    return brand_data
            
            elif query_type == "statistics":
                return self.get_detailed_marketplace_context()
            
            # For other queries, use Groq API with enhanced context
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add marketplace context for all queries
            marketplace_context = self.get_detailed_marketplace_context()
            messages.append({"role": "system", "content": marketplace_context})
            
            # Add user context if logged in
            if user_id:
                try:
                    self.db.cursor.execute('''
                        SELECT full_name, role FROM users WHERE id = ?
                    ''', (user_id,))
                    user = self.db.cursor.fetchone()
                    if user:
                        user_context = f"The user is {user[0]} with role: {user[1]}. "
                        messages.append({"role": "system", "content": f"User context: {user_context}"})
                except Exception as e:
                    print(f"Error getting user context: {e}")
            
            # Add conversation history
            if user_id:
                history = self.get_user_conversation_history(user_id, limit=5)
                for hist_item in history:
                    messages.append({"role": "user", "content": hist_item[0]})
                    messages.append({"role": "assistant", "content": hist_item[1]})
            
            # Add current query with type hint
            messages.append({"role": "user", "content": query})
            
            # Get response from Groq
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=2048,
                top_p=1,
                stream=False,
            )
            
            response = chat_completion.choices[0].message.content
            
            # Save to database
            if user_id:
                try:
                    self.db.cursor.execute('''
                        INSERT INTO ai_chat_history (user_id, query, response)
                        VALUES (?, ?, ?)
                    ''', (user_id, query, response))
                    self.db.conn.commit()
                except Exception as e:
                    print(f"Error saving chat history: {e}")
            
            return response
            
        except Exception as e:
            print(f"Groq API Error: {e}")
            return self.get_fallback_response(query)
    
    def get_fallback_response(self, query):
        """Enhanced fallback response with Rupees"""
        query_lower = query.lower()
        
        if 'buy' in query_lower:
            return self.get_how_to_buy_guide()
        elif any(brand in query_lower for brand in ['maruti', 'hyundai', 'tata', 'mahindra']):
            return "I can help you check available vehicles! Please try asking specifically like 'Show me Maruti cars' or use the search feature above."
        else:
            return """I apologize, but I'm having trouble connecting to my AI service right now. 

In the meantime, you can:
1. Browse our available vehicles using the search feature
2. Check the 'Buy Cars' section for detailed listings
3. Use the filters to find cars by brand, price, or fuel type

All prices on our platform are in Indian Rupees (₹). For example, you'll find cars ranging from ₹3 lakhs to ₹25 lakhs.

Please try again in a few moments!"""


# ======================================= FLASK ROUTES =============================================
db = Database()
validator = EnhancedValidator(db)
ai_helper = AIHelper(db)

def auto_release_expired_rentals():
    today = datetime.now().strftime("%Y-%m-%d")
    db.cursor.execute("""
        UPDATE rentals
        SET status='AVAILABLE',
            is_available=1
        WHERE status='RENTED'
          AND end_date < ?
    """, (today,))
    db.conn.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'ADMIN':
            flash('Admin access required', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

#====================================== Home page route ====================================
@app.route('/')
def index():
    """Home page"""
  
    db.cursor.execute('SELECT * FROM vehicles WHERE status = "APPROVED" ORDER BY RANDOM() LIMIT 4')
    featured_vehicles = db.cursor.fetchall()

    db.cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = db.cursor.fetchone()[0]

    db.cursor.execute("SELECT COUNT(*) FROM users")
    total_users = db.cursor.fetchone()[0]

    db.cursor.execute('''
        SELECT f.*, u.username, u.full_name,
               strftime('%d %b %Y', f.created_at) as formatted_date
        FROM feedback f
        JOIN users u ON f.user_id = u.id
        WHERE f.status = 'APPROVED'
        ORDER BY f.created_at DESC
        LIMIT 10
    ''')
    feedbacks = db.cursor.fetchall()

    return render_template('index.html',
                         featured_vehicles=featured_vehicles,
                         total_vehicles=total_vehicles,
                         total_users=total_users,
                         feedbacks=feedbacks)
    
    
#====================================== Registration Route =================================
@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'GET' and not request.args.get('error'):
        session.pop('form_data', None)
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']
        email = request.form['email']
        phone = request.form['phone']
        full_name = request.form['full_name']
        address = request.form.get('address', '')

        session['form_data'] = {
            'username': username,
            'email': email,
            'phone': phone,
            'full_name': full_name,
            'address': address,
            'password': password,
            'confirm_password': confirm
        }

        validator = EnhancedValidator(db)

        # Validate username
        is_valid, message = validator.validate_username(username)
        if not is_valid:
            flash(message, "danger")

            session['form_data']['username'] = ''
            return redirect(url_for("register", error="username"))

        # Validate email
        is_valid, message = validator.validate_email(email)
        if not is_valid:
            flash(message, "danger")
            session['form_data']['email'] = ''
            return redirect(url_for("register", error="email"))

        # Validate phone
        is_valid, message = validator.validate_phone(phone)
        if not is_valid:
            flash(message, "danger")
            session['form_data']['phone'] = ''  # Sirf phone empty hoga
            return redirect(url_for("register", error="phone"))

        # Validate password
        is_valid, message = validator.validate_password(password)
        if not is_valid:
            flash(message, "danger")
            session['form_data']['password'] = ''
            session['form_data']['confirm_password'] = ''
            return redirect(url_for("register", error="password"))

        # Validate full name
        is_valid, message = validator.validate_full_name(full_name)
        if not is_valid:
            flash(message, "danger")
            session['form_data']['full_name'] = ''
            return redirect(url_for("register", error="full_name"))

        # Check password match
        if password != confirm:
            flash("Passwords do not match", "danger")
            session['form_data']['password'] = ''
            session['form_data']['confirm_password'] = ''
            return redirect(url_for("register", error="confirm_password"))

        # Success - clear form data
        phone_clean = phone.replace(' ', '').replace('-', '')
        session.pop('form_data', None)
        
        session['registration_data'] = {
            "username": username,
            "password": password,
            "email": email,
            "phone": phone_clean,
            "full_name": full_name,
            "address": address
        }
        return redirect(url_for("send_register_otp"))

    # GET request
    form_data = session.get('form_data', {})
    error_field = request.args.get('error', '')
    
    return render_template("register.html", 
                         show_otp=False,
                         form_data=form_data,
                         error_field=error_field)
    
#------------------------------------register OTP routes--------------------------------------
@app.route('/send-register-otp')
def send_register_otp():
    if 'registration_data' not in session:
        flash("Fill form first","danger")
        return redirect(url_for("register"))
    
    email = session['registration_data']['email']
    
    # Generate and save OTP
    otp = db.generate_otp()
    db.save_otp(email, otp, "REGISTRATION")
    
    
    db.send_email(
        email,
        "WebWheels OTP Verification",  
        f"""Dear Customer,

    Thank you for choosing WebWheels! To complete your verification, please use the following One-Time Password (OTP):

    🔐 Your OTP: {otp}

    This code is valid for the next 10 minutes. Please do not share this OTP with anyone for security reasons.

    If you didn't request this code, please ignore this email.

Happy Driving!
Team WebWheels"""
    )
    
    flash("OTP sent to your email", "success")
    return render_template(
        "register.html",
        show_otp=True,
        email=email
    )

#------------------------------------register OTP verification route--------------------------------------
@app.route('/verify-register-otp', methods=['POST'])
def verify_register_otp():
    if 'registration_data' not in session:
        flash("Session expired","danger")
        return redirect(url_for("register"))
    
    email = request.form['email']
    otp = request.form['otp']
    
    data = session['registration_data']
    
    if db.verify_otp(email, otp, "REGISTRATION"):
       
        db.cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if db.cursor.fetchone():
            flash("Email already registered! Please use a different email or login.", "danger")
            session.pop("registration_data", None)
            return redirect(url_for("register"))
        
       
        db.cursor.execute("SELECT id FROM users WHERE phone = ?", (data['phone'],))
        if db.cursor.fetchone():
            flash("Phone number already registered! Please use a different phone number.", "danger")
            session.pop("registration_data", None)
            return redirect(url_for("register"))
        
      
        db.cursor.execute("SELECT id FROM users WHERE username = ?", (data['username'],))
        if db.cursor.fetchone():
            flash("Username already taken! Please choose a different username.", "danger")
            session.pop("registration_data", None)
            return redirect(url_for("register"))
        
        hashed = db.hash_password(data['password'])
        
        try:
            db.cursor.execute("""
                INSERT INTO users
                (username,password,email,phone,full_name,address,role)
                VALUES (?,?,?,?,?,?,?)
            """,(
                data['username'],
                hashed,
                email,
                data['phone'],
                data['full_name'],
                data['address'],
                "USER"
            ))
            
            db.conn.commit()
            session.pop("registration_data", None)
            
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: users.email" in str(e):
                flash("Email already registered! Please use a different email.", "danger")
            elif "UNIQUE constraint failed: users.phone" in str(e):
                flash("Phone number already registered! Please use a different phone number.", "danger")
            elif "UNIQUE constraint failed: users.username" in str(e):
                flash("Username already taken! Please choose a different username.", "danger")
            else:
                flash(f"Registration error: {str(e)}", "danger")
            return redirect(url_for("register"))
    
    flash("Invalid or expired OTP","danger")
    return render_template(
        "register.html",
        show_otp=True,
        email=email
    )

#======================================login route ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        
        if '@' in identifier:
            db.cursor.execute('SELECT id, username, email, phone, full_name, address, role, password FROM users WHERE email = ?', (identifier,))
        elif identifier.isdigit() and len(identifier) == 10:
            db.cursor.execute('SELECT id, username, email, phone, full_name, address, role, password FROM users WHERE phone = ?', (identifier,))
        else:
            db.cursor.execute('SELECT id, username, email, phone, full_name, address, role, password FROM users WHERE username = ?', (identifier,))
        
        user = db.cursor.fetchone()
        
        if user:
            # Verify password
            hashed_pass = db.hash_password(password)
            if hashed_pass == user[7]:
                
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['email'] = user[2]
                session['phone'] = user[3]
                session['full_name'] = user[4]
                session['address'] = user[5]
                session['role'] = user[6]
                
                if user[6] != 'ADMIN':  
                    try:
                        db.cursor.execute('''
                            SELECT COUNT(*) FROM custom_car_requests 
                            WHERE user_id = ? AND status IN ("PENDING", "PRICE_SET")
                        ''', (user[0],))
                        pending_count_result = db.cursor.fetchone()
                        session['pending_custom_count'] = pending_count_result[0] if pending_count_result else 0
                    except Exception as e:
                        print(f"Error getting pending count: {e}")
                        session['pending_custom_count'] = 0
                else:
                    
                    session['pending_custom_count'] = 0
                
                flash(f'Welcome back, {user[4]}!', 'success')
                
                if user[6] == 'ADMIN':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('Incorrect password!', 'danger')
        else:
            flash('Account not found!', 'danger')
    
    return render_template('login.html')

#--------------------------- forgot password routes --------------------------------------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password - send OTP"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        db.cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = db.cursor.fetchone()
        
        if user:
            otp = db.generate_otp()
            db.save_otp(email, otp, 'FORGOT_PASSWORD')
            
            subject = 'WebWheels - Password Reset OTP'
            body = f"""Dear Customer,

    Thank you for choosing WebWheels! To complete your password reset, please use the following One-Time Password (OTP):

    🔐 Your OTP: {otp}

    This code is valid for the next 10 minutes. Please do not share this OTP with anyone for security reasons.

    If you didn't request this code, please ignore this email.

Happy Driving!
Team WebWheels"""
            db.send_email(email, subject, body)
            
            flash('OTP sent to your email', 'success')  
            return render_template('login.html', show_forgot_step=2, email=email)
        else:
            flash('Email not registered', 'danger')
            return render_template('login.html', show_forgot_step=1)  
    
    return render_template('login.html', show_forgot_step=1)

#--------------------------- forgot password OTP verification route --------------------------------------
@app.route('/verify-forgot-otp', methods=['POST'])
def verify_forgot_otp():
    """Verify forgot password OTP"""
    email = request.form.get('email')
    otp = request.form.get('otp')
    
    if db.verify_otp(email, otp, 'FORGOT_PASSWORD'):
        flash('OTP verified successfully', 'success') 
        return render_template('login.html', show_forgot_step=3, email=email)
    
    flash('Invalid or expired OTP', 'danger')
    return render_template('login.html', show_forgot_step=2, email=email)

#---------------------------- reset password route --------------------------------------
@app.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password"""
    email = request.form.get('email')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        flash('Passwords do not match', 'danger')
        return render_template('login.html', show_forgot_step=3, email=email)
    
    hashed_pass = db.hash_password(new_password)
    db.cursor.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_pass, email))
    db.conn.commit()
    
    flash('Password reset successfully! Please login.', 'success')
    return redirect(url_for('login'))

#================================== Browse Vehicles Route ==============================
@app.route('/browse/vehicles')
def browse_vehicles():
    """Browse vehicles with rental availability and wishlist status"""
    vehicle_type = request.args.get('type', 'all')
    search = request.args.get('search', '')

    query = """
        SELECT v.*, u.username, r.is_available as rental_available
        FROM vehicles v
        JOIN users u ON v.seller_id = u.id
        LEFT JOIN rentals r ON v.id = r.vehicle_id
        WHERE v.status = 'APPROVED'
    """
    params = []

    if vehicle_type == 'sale':
        query += " AND v.vehicle_type = 'SELL'"
    elif vehicle_type == 'rent':
        query += " AND v.vehicle_type = 'RENT'"

    if search:
        query += " AND (v.brand LIKE ? OR v.model LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    query += " ORDER BY v.created_at DESC"

    db.cursor.execute(query, params)
    rows = db.cursor.fetchall()

    
    column_names = [description[0] for description in db.cursor.description]
    vehicles = [dict(zip(column_names, row)) for row in rows]

    
    wishlisted_ids = []
    if 'user_id' in session:
   
        db.cursor.execute("SELECT vehicle_id FROM wishlist WHERE user_id = ?", (session['user_id'],))
        wishlist_rows = db.cursor.fetchall()
        wishlisted_ids = [row[0] for row in wishlist_rows]

    return render_template('browse.html',
                           vehicles=vehicles,
                           vehicle_type=vehicle_type,
                           search=search,
                           wishlisted_ids=wishlisted_ids)

#================================== AI Assistant Route ==================================
@app.route('/ai/assistant', methods=['GET', 'POST'])
def ai_assistant():
    """AI Assistant with Groq integration"""
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            user_id = session.get('user_id')
            response = ai_helper.get_response(query, user_id)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'response': response})
            
            return render_template('ai_assistant.html', response=response)
    
    return render_template('ai_assistant.html')

#================================== Logout Route ==================================
@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard redirect"""
    if session.get('role') == 'ADMIN':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))

#================================================== User Dashboard Routes ======================================================
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """User dashboard"""
    user_id = session['user_id']
    
    db.cursor.execute('SELECT COUNT(*) FROM vehicles WHERE seller_id = ?', (user_id,))
    my_listings = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM wishlist WHERE user_id = ?', (user_id,))
    my_wishlist = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
    my_transactions = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM custom_car_requests WHERE user_id = ?', (user_id,))
    custom_requests_count = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM custom_car_requests WHERE user_id = ? AND status IN ("PENDING", "PRICE_SET")', (user_id,))
    pending_custom_count = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT * FROM custom_car_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 3', (user_id,))
    recent_custom_requests = []
    for row in db.cursor.fetchall():
        recent_custom_requests.append(dict(row))
    
    db.cursor.execute('SELECT * FROM vehicles WHERE seller_id = ? ORDER BY created_at DESC LIMIT 5', (user_id,))
    my_vehicles = db.cursor.fetchall()
    
    db.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = dict(db.cursor.fetchone())
    
    return render_template('user_dashboard.html',
                         user=user,
                         listings_count=my_listings,
                         transactions_count=my_transactions,
                         wishlist_count=my_wishlist,
                         custom_requests_count=custom_requests_count,
                         pending_custom_count=pending_custom_count,
                         recent_custom_requests=recent_custom_requests,
                         my_vehicles=my_vehicles,
                         ai_queries_count=0)

#==================================== User Listings Route ============================
@app.route('/my/listings')
@login_required
def my_listings():
    """View user's listings"""
    db.cursor.execute("""
        SELECT *
        FROM vehicles
        WHERE seller_id = ?
        ORDER BY created_at DESC
    """, (session['user_id'],))
    listings = db.cursor.fetchall()
    return render_template('my_listings.html', listings=listings)

#==================================== User Wishlist Route ============================
@app.route('/my/wishlist')
@login_required
def my_wishlist():
    query = '''
        SELECT v.*, u.username,
               r.daily_rate, r.hourly_rate, r.weekly_rate, r.monthly_rate,
               r.security_deposit
        FROM wishlist w
        JOIN vehicles v ON w.vehicle_id = v.id
        JOIN users u ON v.seller_id = u.id
        LEFT JOIN rentals r ON v.id = r.vehicle_id
        WHERE w.user_id = ?
    '''
    db.cursor.execute(query, (session['user_id'],))
    rows = db.cursor.fetchall()
    
    wishlist_items = []
    for row in rows:
        item = dict(row)
        if item['vehicle_type'] == 'RENT':
            
            item['display_price'] = item.get('daily_rate') or 0
        else:
           
            base_price = item.get('price') or 0
            commission = base_price * 0.08
            item['display_price'] = base_price + commission
        wishlist_items.append(item)
    
    return render_template("my_wishlist.html", wishlist_items=wishlist_items)

#---------------------------- Add Wishlist Routes -----------------------------
@app.route('/api/add-to-wishlist/<int:vehicle_id>', methods=['POST'])
@login_required
def add_to_wishlist(vehicle_id):
    """Add vehicle to wishlist"""
    try:
        db.cursor.execute('''
            INSERT OR IGNORE INTO wishlist (user_id, vehicle_id)
            VALUES (?, ?)
        ''', (session['user_id'], vehicle_id))
        db.conn.commit()
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#----------------------------- Remove Wishlist Routes -----------------------------
@app.route('/api/remove-from-wishlist/<int:vehicle_id>', methods=['POST'])
@login_required
def remove_from_wishlist(vehicle_id):
    """Remove vehicle from wishlist"""
    try:
        db.cursor.execute('DELETE FROM wishlist WHERE user_id = ? AND vehicle_id = ?', 
                         (session['user_id'], vehicle_id))
        db.conn.commit()
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

#============================== User Transactions Route ============================
@app.route('/my/transactions')
@login_required
def my_transactions():
    """View user's transactions"""
    db.cursor.execute('''
        SELECT t.*, v.brand, v.model 
        FROM transactions t
        JOIN vehicles v ON t.vehicle_id = v.id
        WHERE t.user_id = ?
        ORDER BY t.transaction_date DESC
    ''', (session['user_id'],))
    transactions = db.cursor.fetchall()
    return render_template('my_transactions.html', transactions=transactions)

#============================== Submit Feedback Route ============================
@app.route('/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    if not rating or not comment:
        flash('Please provide both rating and comment', 'danger')
        return redirect(url_for('index'))
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        flash('Rating must be between 1 and 5', 'danger')
        return redirect(url_for('index'))
    
    db.cursor.execute('''
        INSERT INTO feedback (user_id, rating, comment)
        VALUES (?, ?, ?)
    ''', (session['user_id'], rating, comment))
    db.conn.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('index'))


# ================================= SELL VEHICLE ==============================
@app.route('/sell/vehicle', methods=['GET', 'POST'])
@login_required
def sell_vehicle():

    if request.method == 'POST':
        try:
           
            brand = request.form.get('brand')
            model = request.form.get('model')
            variant = request.form.get('variant')
            year = int(request.form.get('year'))
            fuel_type = request.form.get('fuel_type')
            transmission = request.form.get('transmission')

            color = request.form.get('color')
            body_type = request.form.get('body_type')

            km_driven = int(request.form.get('km_driven', 0))
            mileage = float(request.form.get('mileage', 15))

            engine_cc = int(request.form.get('engine_cc') or 1200)
            seats = int(request.form.get('seats') or 5)

            features_raw = request.form.get('features', '')

           
            if model == 'other' and request.form.get('model_other'):
                model = request.form.get('model_other')
            if variant == 'other' and request.form.get('variant_other'):
                variant = request.form.get('variant_other')

           
            features_list = [
                f.strip() for f in features_raw.split(',')
                if f.strip()
            ]

           
            vehicle_data = {
                "brand": brand,
                "model": model,
                "variant": variant,
                "manufacturing_year": year,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "color": color,
                "body_type": body_type,
                "kilometers_driven": km_driven,
                "engine_capacity": engine_cc,
                "number_of_seats": seats,
                "mileage": mileage,
                "features": features_list
            }

            pricing_result = calculate_fair_price(vehicle_data)

            if not pricing_result.get("success", True):
                flash("Price calculation failed", "danger")
                return redirect(url_for("sell_vehicle"))

            price = round(pricing_result["final_price"] / 1000) * 1000

            #
            images = request.files.getlist("vehicle_images")
            image_names = []

            
            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

            import time
            import random
            import string

            for img in images:
                if img and img.filename:  
                    
                    
                    if '.' in img.filename:
                        file_ext = img.filename.rsplit('.', 1)[1].lower()
                    else:
                        file_ext = 'jpg'  
                    
                    
                    if file_ext not in ALLOWED_EXTENSIONS:
                        flash(f"File type .{file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}", "warning")
                        continue
                    
                    img.seek(0, 2)  
                    file_size = img.tell()  
                    img.seek(0)  
                    
                    if file_size > 5 * 1024 * 1024:  
                        flash(f"File {img.filename} is too large. Maximum size is 5MB.", "warning")
                        continue
                    
                    timestamp = str(int(time.time() * 1000))  
                    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                    unique_filename = f"vehicle_{timestamp}_{random_str}.{file_ext}"
                    
                    save_path = os.path.join(upload_folder, unique_filename)
                    
                   
                    img.save(save_path)
                    
                
                    image_names.append(unique_filename)

            
            if not image_names:
                flash("Please upload at least one valid image.", "danger")
                return redirect(url_for("sell_vehicle"))

           
            images_string = ",".join(image_names)

            # ================= MODEL + VARIANT =================
            full_model = f"{model}-{variant}" if variant else model

           
            query = """
                INSERT INTO vehicles (
                    seller_id,
                    brand,
                    model,
                    fuel_type,
                    year,
                    price,
                    transmission,
                    color,
                    body_type,
                    features,
                    mileage,
                    engine_cc,
                    seats,
                    status,
                    vehicle_type,
                    km_driven,
                    images
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            values = (
                session["user_id"],
                brand,
                full_model,
                fuel_type,
                year,
                price,
                transmission,
                color,
                body_type,
                ",".join(features_list),
                mileage,
                engine_cc,
                seats,
                "PENDING",
                "SELL",
                km_driven,
                images_string
            )

            db.cursor.execute(query, values)
            db.conn.commit()

            flash(
                f"Vehicle listed successfully! Price ₹{price:,}",
                "success"
            )

            return redirect(url_for("my_listings"))

        except Exception as e:
            print("SELL ERROR:", e)
            import traceback
            traceback.print_exc()
            flash(f"Error: {str(e)}", "danger")

    return render_template("sell_vehicle.html")


#==================================== Price Calculation API Route ============================
@app.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    try:
       
        brand = request.form.get('brand')
        model = request.form.get('model')
        year_str = request.form.get('year')
        fuel_type = request.form.get('fuel_type')
        transmission = request.form.get('transmission')
        color = request.form.get('color', '')
        body_type = request.form.get('body_type', '')
        features_raw = request.form.get('features', '')
        km_driven_str = request.form.get('km_driven', '0')
        engine_cc_str = request.form.get('engine_cc', '1200')
        seats_str = request.form.get('seats', '5')
        mileage_str = request.form.get('mileage', '15')

        
        if not all([brand, model, year_str, fuel_type, transmission]):
            return jsonify({'error': 'Missing required fields (Brand, Model, Year, Fuel Type, Transmission)'}), 400

       
        try:
            year = int(year_str)
            km_driven = float(km_driven_str) if km_driven_str else 0
            engine_cc = float(engine_cc_str) if engine_cc_str else 1200
            seats = int(seats_str) if seats_str else 5
            mileage = float(mileage_str) if mileage_str else 15
        except ValueError as ve:
            return jsonify({'error': f'Invalid input format: {str(ve)}'}), 400

       
        if isinstance(features_raw, str):
            features_list = [f.strip() for f in features_raw.split(',') if f.strip()]
        else:
            features_list = []

      
        vehicle_data = {
            'brand': brand,
            'model': model,
            'manufacturing_year': year,
            'fuel_type': fuel_type,
            'transmission': transmission,
            'color': color,
            'body_type': body_type,
            'kilometers_driven': int(km_driven),
            'engine_capacity': int(engine_cc),
            'number_of_seats': seats,
            'mileage': mileage,
            'features': features_list,
        }

       
        pricing_result = calculate_fair_price(vehicle_data)

       
        if not pricing_result.get('success', True):
            return jsonify({
                'error': pricing_result.get('error', 'Price calculation failed')
            }), 400

        
        calculated_price = pricing_result['final_price']
        price = round(calculated_price / 1000) * 1000

        
        return jsonify({
            'price': price,
            'condition': 'Fair Price (Rule-Based)',
            'base_price': pricing_result.get('base_price'),
            'vehicle_age': pricing_result.get('vehicle_age'),
        }), 200

    except ValueError as ve:
        return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
    except Exception as e:
        print(f"Endpoint error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    

#===================================== user Profile Route ============================
@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    
    db.cursor.execute("""
        SELECT id, username, email, phone, full_name, address, role, created_at
        FROM users WHERE id = ?
    """, (user_id,))
    row = db.cursor.fetchone()
    user = {
        "id": row[0], "username": row[1], "email": row[2], "phone": row[3],
        "full_name": row[4], "address": row[5], "role": row[6], "created_at": row[7]
    }
    
    db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE seller_id = ?", (user_id,))
    listings_count = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
    transactions_count = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM wishlist WHERE user_id = ?", (user_id,))
    wishlist_count = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM ai_chat_history WHERE user_id = ?", (user_id,))
    ai_queries_count = db.cursor.fetchone()[0]
    
    return render_template("profile.html", user=user, listings_count=listings_count,
                         transactions_count=transactions_count, wishlist_count=wishlist_count,
                         ai_queries_count=ai_queries_count)

# =================================== BUY CAR ROUTES ===============================
@app.route('/buy/vehicle/<int:vehicle_id>')
@login_required
def buy_vehicle_detail(vehicle_id):
    db.cursor.execute("SELECT * FROM vehicles WHERE id=? AND status='APPROVED'", (vehicle_id,))
    vehicle = db.cursor.fetchone()
    if not vehicle:
        flash("Vehicle not found", "danger")
        return redirect(url_for("browse_vehicles"))
    return render_template("vehicle_detail.html", vehicle=vehicle)

# ------------------------- CHECKOUT ----------------
@app.route('/buy/checkout/<int:vehicle_id>', methods=["GET","POST"])
@login_required
def checkout(vehicle_id):
    db.cursor.execute("SELECT * FROM vehicles WHERE id=? AND status='APPROVED'", (vehicle_id,))
    vehicle = db.cursor.fetchone()
    if not vehicle:
        flash("Vehicle unavailable", "danger")
        return redirect(url_for("browse_vehicles"))
    
    base_price = vehicle["price"]
   
    commission = base_price * 0.08
    total = base_price + commission

    if request.method == "POST":
        payment_method = request.form.get("payment_method")
        address = request.form.get("delivery_address")
        return redirect(url_for("process_payment", vehicle_id=vehicle_id,
                              payment_method=payment_method, address=address))

    return render_template("checkout.html", vehicle=vehicle, base_price=base_price,
                         commission=commission, total=total)

# ---------------------------- PAYMENT ----------------------
@app.route('/buy/payment/<int:vehicle_id>')
@login_required
def process_payment(vehicle_id):
    """Process payment only - NO EMAIL HERE"""
    payment_method = request.args.get("payment_method")
    address = request.args.get("address")
    
    db.cursor.execute("SELECT * FROM vehicles WHERE id=? AND status='APPROVED'", (vehicle_id,))
    vehicle = db.cursor.fetchone()
    
    base_price = vehicle["price"]
    commission = base_price * 0.08
    total = base_price + commission
    
    
    db.cursor.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
    admin = db.cursor.fetchone()
    admin_id = admin["id"] if admin else None

    transaction_id = random.randint(100000, 999999)
    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    
    db.cursor.execute("""
        INSERT INTO transactions
        (id, user_id, vehicle_id, seller_id, amount, transaction_type, 
         payment_method, status, commission_amount, invoice_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (transaction_id, session["user_id"], vehicle_id, vehicle["seller_id"],
          total, "PURCHASE", payment_method, "COMPLETED", commission, invoice_no))

   
    db.cursor.execute("""
        INSERT INTO purchases
        (buyer_id, seller_id, vehicle_id, purchase_price, delivery_address)
        VALUES (?, ?, ?, ?, ?)
    """, (session["user_id"], vehicle["seller_id"], vehicle_id, base_price, address))

    
    db.cursor.execute("UPDATE vehicles SET status='SOLD' WHERE id=?", (vehicle_id,))
    
    if admin_id:
        db.cursor.execute("""
            UPDATE admin_balance SET balance = balance + ? WHERE user_id = ?
        """, (total, admin_id))

    db.conn.commit()
    
    session['last_transaction'] = {
        'id': transaction_id,
        'invoice_no': invoice_no
    }
    
    flash('Payment successful! Your invoice is ready.', 'success')
    return redirect(url_for("invoice", tid=transaction_id, invoice_no=invoice_no))

#------------------------------ INVOICE ----------------------
@app.route('/invoice/<int:tid>/<invoice_no>')
@login_required
def invoice(tid, invoice_no):
    """Display invoice and handle email sending"""
    
    db.cursor.execute("""
        SELECT t.*, v.brand, v.model, v.year, v.fuel_type, v.transmission, 
               v.color, v.body_type, v.price, u.full_name AS seller_name,
               u2.full_name AS buyer_name, u2.email AS buyer_email, 
               u2.phone AS buyer_phone
        FROM transactions t
        JOIN vehicles v ON t.vehicle_id=v.id
        JOIN users u ON v.seller_id=u.id
        JOIN users u2 ON t.user_id = u2.id
        WHERE t.id=?
    """, (tid,))
    transaction = db.cursor.fetchone()
    
    if not transaction:
        flash('Invoice not found', 'danger')
        return redirect(url_for('dashboard'))
    
    trans_dict = dict(transaction)
    
    base_price = trans_dict['price']
    commission = base_price * 0.08
    total = trans_dict['amount']
    
   
    email_sent = request.args.get('email_sent', 'false')
    

    send_email = request.args.get('send_email', 'false')
    
    if send_email == 'true':
       
        try:
            subject = f"Invoice {invoice_no} - WebWheels"
            body = f"""
{'='*60}
🏢   WEBWHEELS  🏢
{'='*60}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 INVOICE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔢 Invoice No: {invoice_no}
📅 Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 BUYER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Name: {trans_dict['buyer_name']}
📧 Email: {trans_dict['buyer_email']}
📞 Phone: {trans_dict['buyer_phone']}

👤 SELLER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Name: {trans_dict['seller_name']}

🚘 VEHICLE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ Model: {trans_dict['brand']} {trans_dict['model']} ({trans_dict['year']})
🎨 Color: {trans_dict['color']}
⛽ Fuel: {trans_dict['fuel_type']}
⚙️ Transmission: {trans_dict['transmission']}

💰 PAYMENT BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Base Price:              ₹ {base_price:>12,.2f}
📊 Platform Fee (8%):       ₹ {commission:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 TOTAL AMOUNT:            ₹ {total:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔤 Amount in Words: 
✨ Rupees {number_to_words(total)} Only ✨

💳 Payment Method: {trans_dict['payment_method']}
🆔 Transaction ID: {tid}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ This is a system generated invoice
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 CONTACT US
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: webwheels7@gmail.com
📱 Phone: +91-7211172096

🙏 Thank you for choosing WebWheels! 🚗✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            success = db.send_email(trans_dict['buyer_email'], subject, body)
            
            if success:
                flash(f'Invoice sent to {trans_dict["buyer_email"]}', 'success')
                email_sent = 'true'
            else:
                flash('Failed to send email. Please try again.', 'warning')
                
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'danger')
            print(f"Email error: {e}")
    
    return render_template("invoice.html", 
                         invoice_no=invoice_no,
                         transaction=trans_dict,
                         base_price=base_price,
                         commission=commission,
                         total=total,
                         date=datetime.now().strftime("%d-%m-%Y %H:%M"),
                         email_sent=email_sent)
def number_to_words(num):
    """Convert number to words in Indian Rupees format"""
    if num is None:
        return "Zero"
    
    num = int(round(num))
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
   
    if num == 0:
        return "Zero"
    
    def convert_less_than_thousand(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else:
            return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 != 0 else "")
    
    def convert_less_than_lakh(n):
        if n < 1000:
            return convert_less_than_thousand(n)
        elif n < 100000:  
            return convert_less_than_thousand(n // 1000) + " Thousand" + (" " + convert_less_than_thousand(n % 1000) if n % 1000 != 0 else "")
        else: 
            return convert_less_than_thousand(n // 100000) + " Lakh" + (" " + convert_less_than_lakh(n % 100000) if n % 100000 != 0 else "")
    
    if num < 10000000:  
        return convert_less_than_lakh(num)
    else:
        crores = num // 10000000
        remainder = num % 10000000
        return convert_less_than_thousand(crores) + " Crore" + (" " + convert_less_than_lakh(remainder) if remainder != 0 else "")

# =================================== RENT VEHICLE ROUTES =============================
@app.route("/rent/vehicle/<int:vehicle_id>")
@login_required
def rent_vehicle_detail(vehicle_id):
    auto_release_expired_rentals()
    db.cursor.execute("""
        SELECT v.id, v.brand, v.model, v.year, v.color, v.transmission,
               v.mileage, v.seats, v.features, v.body_type, v.engine_cc,
               v.images,                                     -- ← added images
               r.id, r.daily_rate, r.hourly_rate, r.weekly_rate,
               r.monthly_rate, r.security_deposit,
               u.username, u.phone, u.email
        FROM vehicles v
        JOIN rentals r ON v.id = r.vehicle_id
        JOIN users u ON r.owner_id = u.id
        WHERE v.id = ?
        AND (r.status='AVAILABLE' OR (r.status='RENTED' AND r.end_date < DATE('now')))
    """, (vehicle_id,))
    row = db.cursor.fetchone()
    if row is None:
        flash("Vehicle not available", "danger")
        return redirect(url_for("browse_vehicles"))
    
    rental = {
        "vehicle_id": row[0],
        "brand": row[1],
        "model": row[2],
        "year": row[3],
        "color": row[4],
        "transmission": row[5],
        "mileage": row[6],
        "seats": row[7],
        "features": row[8],
        "body_type": row[9],
        "engine_cc": row[10],
        "images": row[11],           
        "rental_id": row[12],
        "daily_rate": row[13],
        "hourly_rate": row[14],
        "weekly_rate": row[15],
        "monthly_rate": row[16],
        "security_deposit": row[17],
        "owner_name": row[18],
        "owner_phone": row[19],
        "owner_email": row[20]
    }
    return render_template("rent_detail.html", rental=rental)

# ------------------------- RENT CHECKOUT ----------------
@app.route("/rent/checkout/<int:rental_id>", methods=["GET","POST"])
@login_required
def rent_checkout(rental_id):
    db.cursor.execute("""
        SELECT v.id, v.brand, v.model, r.id, r.daily_rate,
               r.hourly_rate, r.weekly_rate, r.monthly_rate, r.security_deposit
        FROM vehicles v
        JOIN rentals r ON v.id=r.vehicle_id
        WHERE r.id=? AND (r.status='AVAILABLE' OR (r.status='RENTED' AND r.end_date < DATE('now')))
    """,(rental_id,))
    r = db.cursor.fetchone()
    if r is None:
        flash("Rental not available", "danger")
        return redirect(url_for("browse_vehicles"))
    
    rental = {
        "vehicle_id": r[0], "brand": r[1], "model": r[2], "rental_id": r[3],
        "daily_rate": r[4], "hourly_rate": r[5], "weekly_rate": r[6],
        "monthly_rate": r[7], "security_deposit": r[8]
    }

    if request.method == "POST":
        return rent_payment_process(rental_id)

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("rent_checkout.html", rental=rental, today=today)

# ---------------------------- RENT PAYMENT  ----------------------
@app.route("/rent/payment/process/<int:rental_id>", methods=["POST"])
@login_required
def rent_payment_process(rental_id):
    rental_type = request.form.get("rental_type")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    payment_method = request.form.get("payment_method")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    duration = (end - start).days

    if duration <= 0:
        flash("Invalid date selection", "danger")
        return redirect(url_for("rent_checkout", rental_id=rental_id))

    db.cursor.execute("""
        SELECT r.*, v.brand, v.model, v.seller_id, v.year, v.color, 
               v.transmission, v.seats, v.fuel_type, v.body_type,
               u.full_name as owner_name, u.email as owner_email, u.phone as owner_phone
        FROM rentals r
        JOIN vehicles v ON r.vehicle_id=v.id
        JOIN users u ON r.owner_id = u.id
        WHERE r.id=? AND r.is_available=1
    """,(rental_id,))
    rental = db.cursor.fetchone()
    
    if not rental:
        flash("Rental not available", "danger")
        return redirect(url_for("browse_vehicles"))

    daily = rental[4]
    hourly = rental[5] or 0
    weekly = rental[6] or 0
    monthly = rental[7] or 0
    deposit = rental[8]
    
    db.cursor.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
    admin = db.cursor.fetchone()
    admin_id = admin["id"] if admin else None


    if rental_type == "hourly":
        rent_amount = hourly * duration * 24
    elif rental_type == "weekly":
        weeks = max(1, duration // 7)
        rent_amount = weekly * weeks
    elif rental_type == "monthly":
        months = max(1, duration // 30)
        rent_amount = monthly * months
    else:
        rent_amount = daily * duration
    
    commission_amount = rent_amount * 0.05 
    total= rent_amount + commission_amount + deposit
    total_admin=rent_amount + commission_amount
    # owner_payout = deposit 

    invoice = f"RENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    
    transaction_id = random.randint(100000, 999999)
    

    brand = rental[10]
    model = rental[11]
    year = rental[14]  
    color = rental[15]  
    transmission = rental[16]  
    seats = rental[17]  
    fuel_type = rental[18]  
    body_type = rental[19]  
    owner_name = rental[20]  
    owner_email = rental[21] 
    owner_phone = rental[22]  
    db.cursor.execute("""
        INSERT INTO transactions
        (id, user_id, vehicle_id, seller_id, amount, transaction_type,
         payment_method, invoice_number, status, commission_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(transaction_id, session["user_id"], rental[1], rental[3], total, "RENTAL",
        payment_method, invoice, "COMPLETED",  commission_amount))

   
    db.cursor.execute("""
        UPDATE rentals SET
            renter_id=?, start_date=?, end_date=?,
            rental_days=?, total_amount=?, status='RENTED', is_available=0
        WHERE id=?
    """,(session["user_id"], start_date, end_date, duration, total, rental_id))
    
    
    if admin_id:
        db.cursor.execute("UPDATE admin_balance SET balance = balance + ? WHERE user_id = ?", (total_admin, admin_id))
        # db.cursor.execute("UPDATE admin_balance SET balance = balance - ? WHERE user_id = ?", (owner_payout, admin_id))
    db.conn.commit()
    
    session['last_rental_transaction'] = {
        'transaction_id': transaction_id,
        'invoice_no': invoice,
        'rental_id': rental_id,
        'brand': brand,
        'model': model,
        'year': year,
        'color': color,
        'transmission': transmission,
        'seats': seats,
        'fuel_type': fuel_type,
        'body_type': body_type,
        'rent_amount': rent_amount,
        'deposit': deposit,
        'commission': commission_amount ,
        'total': total,
        'payment_method': payment_method,
        'start_date': start_date,
        'end_date': end_date,
        'duration': duration,
        'rental_type': rental_type
    }
    
    # ================ FIXED EMAIL SENDING CODE ================
    try:
        # Get renter details from database instead of session
        db.cursor.execute('SELECT full_name, email, phone FROM users WHERE id = ?', (session['user_id'],))
        renter = db.cursor.fetchone()
        
        if renter:
            renter_name = renter[0]
            renter_email = renter[1]
            renter_phone = renter[2]
            
            print(f"📧 Attempting to send rental invoice to: {renter_email}")
            
            # Create email subject
            subject = f"🧾 Rental Invoice {invoice} - WebWheels 🚗"
            
            # Create email body with emojis
            body = f"""
{'='*60}
🏢   WEBWHEELS RENTAL INVOICE  🏢
{'='*60}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 INVOICE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔢 Invoice No: {invoice}
📅 Date: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 RENTER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Name: {renter_name}
📧 Email: {renter_email}
📞 Phone: {renter_phone}

👤 OWNER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Name: {owner_name}
📧 Email: {owner_email}
📞 Phone: {owner_phone}

🚘 VEHICLE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ Model: {brand} {model} ({year})
🎨 Color: {color}
⛽ Fuel: {fuel_type}
⚙️ Transmission: {transmission}
🪑 Seats: {seats}

📅 RENTAL DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📆 Start Date: {start_date}
📆 End Date: {end_date}
⏱️ Duration: {duration} days
🔄 Rental Type: {rental_type.capitalize()}

💰 PAYMENT BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Rent Amount:              ₹ {rent_amount:>12,.2f}
🔒 Security Deposit:         ₹ {deposit:>12,.2f}
📊 Platform Fee (8%):        ₹ {commission_amount:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 TOTAL AMOUNT:             ₹ {total:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔤 Amount in Words: 
✨ Rupees {number_to_words(total)} Only ✨

💳 Payment Method: {payment_method}
🆔 Transaction ID: {transaction_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ This is a system generated invoice
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 CONTACT US
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: webwheels7@gmail.com
📱 Phone: +91-7211172096

🙏 Thank you for renting with WebWheels! 🚗✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Send the email to renter
            success = db.send_email(renter_email, subject, body)
            
            if success:
                print(f" Rental invoice email sent successfully to {renter_email}")
                flash('Rental invoice sent to your email!', 'success')
            else:
                print(f" Failed to send rental invoice email to {renter_email}")
                flash('Payment successful but email could not be sent. Please check your email settings.', 'warning')
        else:
            print(f" Could not fetch renter details for user ID: {session['user_id']}")
            flash('Payment successful but could not send email due to missing user details.', 'warning')
            
    except Exception as e:
        print(f" Error sending rental invoice email: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Payment successful but email sending failed. Please contact support.', 'warning')
    # ================ END OF FIXED EMAIL SENDING CODE ================
    
    flash('Rental payment successful!', 'success')
    return redirect(url_for("rent_invoice", tid=transaction_id, invoice_no=invoice))

def number_to_words(num):
    """Convert number to words in Indian Rupees format"""
    if num is None:
        return "Zero"
    
    # Convert to integer (paise not needed for words)
    num = int(round(num))
    
    # Define word mappings
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    # Indian numbering system (lakhs, crores)
    if num == 0:
        return "Zero"
    
    def convert_less_than_thousand(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else:
            return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 != 0 else "")
    
    def convert_less_than_lakh(n):
        if n < 1000:
            return convert_less_than_thousand(n)
        elif n < 100000:  # Less than 1 lakh (100,000)
            return convert_less_than_thousand(n // 1000) + " Thousand" + (" " + convert_less_than_thousand(n % 1000) if n % 1000 != 0 else "")
        else:  # Less than 1 crore (10,000,000)
            return convert_less_than_thousand(n // 100000) + " Lakh" + (" " + convert_less_than_lakh(n % 100000) if n % 100000 != 0 else "")
    
    if num < 10000000:  # Less than 1 crore
        return convert_less_than_lakh(num)
    else:
        crores = num // 10000000
        remainder = num % 10000000
        return convert_less_than_thousand(crores) + " Crore" + (" " + convert_less_than_lakh(remainder) if remainder != 0 else "")

#------------------------------ RENT INVOICE----------------------

@app.route('/rent/invoice/<tid>/<invoice_no>')
@login_required
def rent_invoice(tid, invoice_no):
    rental_data = session.get('last_rental_transaction', {})
    
    db.cursor.execute('SELECT username, email, phone FROM users WHERE id = ?', (session.get('user_id'),))
    user = db.cursor.fetchone()
    
    renter_name = user['username'] if user else session.get('username', 'User')
    renter_email = user['email'] if user else session.get('email', 'N/A')
    renter_phone = user['phone'] if user else 'N/A'
    
    from datetime import datetime
    date = datetime.now().strftime('%d %b %Y')
    
    return render_template('rent_invoice.html',
                           invoice_number=invoice_no,
                           transaction_id=tid,
                           date=date,
                           renter_name=renter_name,
                           renter_email=renter_email,
                           renter_phone=renter_phone,
                           owner_name='Vehicle Owner',
                           brand=rental_data.get('brand', 'Brand'),
                           model=rental_data.get('model', 'Model'),
                           year=rental_data.get('year', 'Year'),
                           fuel_type=rental_data.get('fuel_type', 'Fuel'),
                           transmission=rental_data.get('transmission', 'Transmission'),
                           rent_amount=rental_data.get('rent_amount', 0),
                           deposit=rental_data.get('deposit', 0),
                           total_amount=rental_data.get('total', 0),
                           payment_method=rental_data.get('payment_method', 'N/A'),
                           email_sent=request.args.get('send_email', 'false'))


# ================================= MY RENTALS ROUTE ====================
@app.route("/my/rentals")
@login_required
def my_rentals():
    db.cursor.execute("""
        SELECT 
            v.brand,
            v.model,
            r.rental_days,
            r.total_amount,
            r.status,
            r.created_at
        FROM rentals r
        JOIN vehicles v ON r.vehicle_id = v.id
        WHERE r.renter_id = ?
        ORDER BY r.created_at DESC
    """, (session["user_id"],))

    rows = db.cursor.fetchall()

    rentals = []
    for r in rows:
        rentals.append({
            "brand": r[0],
            "model": r[1],
            "rental_days": r[2],
            "total_amount": r[3],
            "status": r[4],
            "created_at": r[5]
        })

    return render_template("my_rentals.html", rentals=rentals)

# ============================= USER PROFILE UPDATE ROUTE ====================
@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    
    try:
        db.cursor.execute('''
            UPDATE users SET full_name = ?, phone = ?, address = ? WHERE id = ?
        ''', (full_name, phone, address, session['user_id']))
        db.conn.commit()
       
        session['full_name'] = full_name
        session['phone'] = phone
        session['address'] = address
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'danger')
    return redirect(url_for('profile'))

# ================================================== Admin Dashboard Routes ================================================
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard"""

    # Total users
    db.cursor.execute("SELECT COUNT(*) FROM users")
    total_users = db.cursor.fetchone()[0]

    # Total vehicles
    db.cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = db.cursor.fetchone()[0]

    # Pending vehicles
    db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status='PENDING'")
    pending_vehicles = db.cursor.fetchone()[0]

    # Total transactions
    db.cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = db.cursor.fetchone()[0]

    # Admin balance
    db.cursor.execute(
        "SELECT balance FROM admin_balance WHERE user_id=?",
        (session['user_id'],)
    )
    row = db.cursor.fetchone()
    admin_balance = row[0] if row else 0

    
    db.cursor.execute("""
        SELECT v.*, u.username
        FROM vehicles v
        JOIN users u ON v.seller_id = u.id
        WHERE v.status='PENDING'
        ORDER BY v.created_at DESC
        LIMIT 5
    """)
    recent_pending = db.cursor.fetchall()
    try:
        db.cursor.execute("SELECT * FROM custom_requests ORDER BY created_at DESC")
        custom_requests = db.cursor.fetchall()
    except:
        custom_requests = []

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_vehicles=total_vehicles,
        pending_vehicles=pending_vehicles,
        total_transactions=total_transactions,
        admin_balance=admin_balance,
        recent_pending=recent_pending,
        custom_requests=custom_requests
    )


#========================== Admin Pending Vehicles Route ============================
@app.route('/admin/pending-vehicles')
@admin_required
def admin_pending_vehicles():
    """Approve pending vehicles"""
    db.cursor.execute('''
        SELECT v.*, u.username FROM vehicles v
        JOIN users u ON v.seller_id = u.id
        WHERE v.status = 'PENDING'
        ORDER BY v.created_at DESC
    ''')
    
    rows = db.cursor.fetchall()
    
    vehicles = []
    for row in rows:
        vehicle_dict = {
            'id': row[0],
            'seller_id': row[1],
            'brand': row[2],
            'model': row[3],
            'variant': row[4],
            'fuel_type': row[5],
            'year': row[6],
            'price': row[7],
            'transmission': row[8],
            'color': row[9],
            'body_type': row[10],
            'features': row[11],
            'mileage': row[12],
            'engine_cc': row[13],
            'seats': row[14],
            'km_driven': row[15],
            'images': row[16],  
            'status': row[17],
            'vehicle_type': row[18],
            'created_at': row[19],
            'username': row[20]  
        }
        vehicles.append(vehicle_dict)
    
    return render_template('admin_pending_vehicles.html', vehicles=vehicles)

#========================= Admin Approve Vehicle Route ============================
@app.route('/admin/approve/<int:vehicle_id>')
@admin_required
def approve_vehicle(vehicle_id):
    """Approve a vehicle"""
    try:
       
        db.cursor.execute('SELECT price, vehicle_type, seller_id FROM vehicles WHERE id = ?', (vehicle_id,))
        vehicle = db.cursor.fetchone()
        
        if vehicle:
            price = vehicle[0]
            vehicle_type = vehicle[1]
            seller_id = vehicle[2]
            
            
            db.cursor.execute('UPDATE vehicles SET status = "APPROVED" WHERE id = ?', (vehicle_id,))
            
            # For sale vehicles, deduct price +  from admin balance
            if vehicle_type == 'SELL':
                total_amount = price
                
             
                db.cursor.execute('SELECT balance FROM admin_balance WHERE user_id = ?', (session['user_id'],))
                balance_result = db.cursor.fetchone()
                balance = balance_result[0] if balance_result else 0
                
              
                if seller_id != session['user_id']:
                    if balance >= total_amount:
                        new_balance = balance - total_amount
                        db.cursor.execute('UPDATE admin_balance SET balance = ? WHERE user_id = ?',
                                        (new_balance, session['user_id']))
                        flash(f'Vehicle approved and ₹{total_amount:,.2f} deducted from admin balance', 'success')
                    else:
                        flash(f'Insufficient admin balance. Required: ₹{total_amount:,.2f}, Available: ₹{balance:,.2f}', 'danger')
                    
                        db.cursor.execute('UPDATE vehicles SET status = "PENDING" WHERE id = ?', (vehicle_id,))
                        db.conn.commit()
                        return redirect(url_for('admin_pending_vehicles'))
                else:
                    flash('Vehicle approved (admin\'s own listing, no balance deduction)', 'info')
            
            
            elif vehicle_type == 'RENT':
                flash('Rental vehicle approved', 'success')
            
            db.conn.commit()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_pending_vehicles'))

#========================= Admin All Vehicles Route ============================
@app.route('/admin/all-vehicles')
@admin_required
def admin_all_vehicles():
    db.cursor.execute('''
        SELECT v.*, u.username 
        FROM vehicles v
        JOIN users u ON v.seller_id = u.id
        ORDER BY v.created_at DESC
    ''')
    rows = db.cursor.fetchall()

    vehicles = []
    for r in rows:
        vehicle = {
            'id': r[0],
            'brand': r[2],
            'model': r[3],
            'variant': r[4],
            'fuel_type': r[5],
            'year': r[6],
            'price': float(r[7]) if r[7] is not None else 0.0,
            'transmission': r[8],
            'color': r[9],
            'body_type': r[10],
            'features': r[11],
            'mileage': r[12],
            'engine_cc': r[13],
            'seats': r[14],
            'km_driven': r[15],
            'images': r[16],
            'status': r[17],
            'vehicle_type': r[18],
            'created_at': r[19],
            'username': r[20]
        }
        vehicles.append(vehicle)

    return render_template('admin_all_vehicles.html', vehicles=vehicles)

#========================= Admin All Users Route ============================
@app.route('/admin/all-users')
@admin_required
def admin_all_users():
    db.cursor.execute("""
        SELECT id, username, email, phone, full_name, role, created_at
        FROM users ORDER BY created_at DESC
    """)
    rows = db.cursor.fetchall()
    users = []
    for r in rows:
        users.append({
            "id": r[0], "username": r[1], "email": r[2], "phone": r[3],
            "full_name": r[4], "role": r[5], "created_at": r[6]
        })
    return render_template("admin_all_users.html", users=users)

#========================= Admin All Transactions Route ============================
@app.route('/admin/all-transactions')
@admin_required
def admin_all_transactions():
    db.cursor.execute("""
        SELECT t.id, u.username, v.brand, v.model, t.amount,
               t.transaction_type, t.commission_amount, t.transaction_date
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        JOIN vehicles v ON t.vehicle_id = v.id
        ORDER BY t.transaction_date DESC
    """)
    rows = db.cursor.fetchall()
    transactions = []
    for r in rows:
        transactions.append({
            "id": r[0], "username": r[1], "brand": r[2], "model": r[3],
            "amount": float(r[4]), "transaction_type": r[5],
            "commission_amount": float(r[6]) if r[6] else 0,
            "transaction_date": r[7]
        })
    return render_template("admin_all_transactions.html", transactions=transactions)

#==================== Admin Add Vehicle Route ============================
@app.route('/admin/add-vehicle', methods=['GET', 'POST'])
@admin_required
def admin_add_vehicle():
    """Admin add vehicle with image upload (works for both SELL and RENT)"""
    if request.method == 'POST':
        try:
           
            brand = request.form.get('brand')
            model = request.form.get('model')
            variant = request.form.get('variant', '')
            year = int(request.form.get('year'))
            fuel_type = request.form.get('fuel_type')
            transmission = request.form.get('transmission')
            color = request.form.get('color')
            body_type = request.form.get('body_type')
            features = request.form.get('features', '')
            mileage = float(request.form.get('mileage') or 0)
            engine_cc = float(request.form.get('engine_cc') or 0)
            seats = int(request.form.get('seats') or 5)
            km_driven = int(request.form.get('km_driven') or 0)
            vehicle_type = request.form.get('vehicle_type')  

            
            if model == 'other' and request.form.get('model_other'):
                model = request.form.get('model_other')
            if variant == 'other' and request.form.get('variant_other'):
                variant = request.form.get('variant_other')

           
            price = float(request.form.get('price') or 0) if vehicle_type == 'SELL' else 0

            
            images = request.files.getlist('vehicle_images')
            image_names = []

           
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

           
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

            import time
            import random
            import string

            for img in images:
                if img and img.filename:
                    
                    if '.' in img.filename:
                        file_ext = img.filename.rsplit('.', 1)[1].lower()
                    else:
                        file_ext = 'jpg'

                    
                    if file_ext not in ALLOWED_EXTENSIONS:
                        flash(f"File type .{file_ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "warning")
                        continue

                  
                    img.seek(0, 2)
                    file_size = img.tell()
                    img.seek(0)
                    if file_size > 5 * 1024 * 1024:  
                        flash(f"File {img.filename} is too large (max 5MB)", "warning")
                        continue

                    
                    timestamp = str(int(time.time() * 1000))
                    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                    unique_filename = f"vehicle_{timestamp}_{random_str}.{file_ext}"
                    save_path = os.path.join(upload_folder, unique_filename)

                    
                    img.save(save_path)
                    image_names.append(unique_filename)

           
            if not image_names:
                flash('Please upload at least one valid image.', 'danger')
                return redirect(url_for('admin_add_vehicle'))

            images_string = ",".join(image_names)

          
            db.cursor.execute('''
                INSERT INTO vehicles 
                (seller_id, brand, model, variant, fuel_type, year, price, transmission,
                 color, body_type, features, mileage, engine_cc, seats, km_driven,
                 images, status, vehicle_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['user_id'],          # seller_id = admin
                brand,
                model,
                variant,
                fuel_type,
                year,
                price,
                transmission,
                color,
                body_type,
                features,
                mileage,
                engine_cc,
                seats,
                km_driven,
                images_string,
                'APPROVED',                  
                vehicle_type
            ))

            vehicle_id = db.cursor.lastrowid

           
            if vehicle_type == 'RENT':
                daily_rate = float(request.form.get('daily_rate') or 0)
                weekly_rate = float(request.form.get('weekly_rate') or 0)
                monthly_rate = float(request.form.get('monthly_rate') or 0)
                security_deposit = float(request.form.get('security_deposit') or 0)

                db.cursor.execute('''
                    INSERT INTO rentals 
                    (vehicle_id, owner_id, daily_rate, weekly_rate, monthly_rate,
                     security_deposit, is_available, status)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 'AVAILABLE')
                ''', (vehicle_id, session['user_id'], daily_rate, weekly_rate,
                      monthly_rate, security_deposit))

            db.conn.commit()
            flash('Vehicle added successfully with images!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            db.conn.rollback()
            flash(f'Error adding vehicle: {str(e)}', 'danger')
            print("Admin add vehicle error:", e)
            import traceback
            traceback.print_exc()

    return render_template('admin_add_vehicle.html')

#===================== Statistics Route =====================
@app.route('/statistics')
def statistics():
    """System statistics"""
    db.cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type = 'SELL'")
    sale_vehicles = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type = 'RENT'")
    rent_vehicles = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM users")
    total_users = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = db.cursor.fetchone()[0]
    db.cursor.execute("SELECT brand, COUNT(*) FROM vehicles GROUP BY brand ORDER BY COUNT(*) DESC")
    top_brands = db.cursor.fetchall()
    
    return render_template('statistics.html', total_vehicles=total_vehicles,
                         sale_vehicles=sale_vehicles, rent_vehicles=rent_vehicles,
                         total_users=total_users, total_transactions=total_transactions,
                         top_brands=top_brands)


@app.route('/admin/reports')
@admin_required
def admin_reports():
    """Admin reports page"""
    # Get basic stats for reports
    db.cursor.execute("SELECT COUNT(*) FROM users")
    total_users = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = db.cursor.fetchone()[0]
    
    db.cursor.execute("SELECT SUM(amount) FROM transactions")
    total_revenue = db.cursor.fetchone()[0] or 0
    
    return render_template(
        'admin_reports.html',
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_transactions=total_transactions,
        total_revenue=total_revenue
    )


@app.route('/admin/settings')
@admin_required
def admin_settings():
    """Admin settings page"""
    return render_template('admin_settings.html')



# ==================== CUSTOM CAR BUILDER ROUTES ====================

#---------------- user submits custom request ----------------
@app.route('/custom-car-builder', methods=['GET', 'POST'])
@login_required
def custom_car_builder():
    """Build custom car request"""
    if request.method == 'POST':
        try:
            user_id = session['user_id']
            user_name = session.get('full_name', session['username'])
            user_email = session['email']
            
            data = {
                'user_id': user_id,
                'user_name': user_name,
                'user_email': user_email,
                'body_type': request.form.get('body_type'),
                'color': request.form.get('color'),
                'fuel_type': request.form.get('fuel_type'),
                'engine_cc': int(request.form.get('engine_cc') or 0),
                'doors': int(request.form.get('doors') or 4),
                'seats': int(request.form.get('seats') or 5),
                'transmission': request.form.get('transmission'),
                'features': request.form.get('features', ''),
                'additional_requirements': request.form.get('additional_requirements', '')
            }
            
            request_id = db.create_custom_request(data)
            
            
            if 'pending_custom_count' in session:
                session['pending_custom_count'] += 1
            else:
               
                db.cursor.execute('''
                    SELECT COUNT(*) FROM custom_car_requests 
                    WHERE user_id = ? AND status IN ("PENDING", "PRICE_SET")
                ''', (user_id,))
                session['pending_custom_count'] = db.cursor.fetchone()[0]
            
            flash('Custom car request submitted successfully! Admin will review and set price.', 'success')
            return redirect(url_for('my_custom_requests'))
        except Exception as e:
            flash(f'Error submitting request: {str(e)}', 'danger')
    
    return render_template('custom_car_builder.html')

#---------------- user views their custom requests ----------------
@app.route('/my/custom-requests')
@login_required
def my_custom_requests():
    """View user's custom car requests"""
    user_id = session['user_id']
    
    
    db.cursor.execute('SELECT * FROM custom_car_requests WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    rows = db.cursor.fetchall()
    
    requests = []
    if rows:
        columns = [desc[0] for desc in db.cursor.description]
        requests = [dict(zip(columns, row)) for row in rows]
    
    
    db.cursor.execute('''
        SELECT COUNT(*) FROM custom_car_requests 
        WHERE user_id = ? AND status IN ("PENDING", "PRICE_SET")
    ''', (user_id,))
    session['pending_custom_count'] = db.cursor.fetchone()[0]
    
    return render_template('my_custom_requests.html', requests=requests)

#---------------- admin views all custom requests ----------------
@app.route('/admin/custom-requests')
@admin_required
def admin_custom_requests():
    """Admin custom requests page"""
    try:
        db.cursor.execute('''
            SELECT ccr.*, u.username, u.phone 
            FROM custom_car_requests ccr
            LEFT JOIN users u ON ccr.user_id = u.id
            ORDER BY ccr.created_at DESC
        ''')
        
        rows = db.cursor.fetchall()
        
        custom_requests = []
        if rows:
            columns = [desc[0] for desc in db.cursor.description]
            for row in rows:
                custom_requests.append(dict(zip(columns, row)))
                
    except Exception as e:
        print(f"Error fetching custom requests: {e}")
        custom_requests = []
    
   
    status_counts = {
        'PENDING': 0,
        'PRICE_SET': 0,
        'ACCEPTED': 0,
        'REJECTED': 0,
        'PROCESSING': 0,
        'COMPLETED': 0,
        'APPROVED': 0
    }
    
    for req in custom_requests:
        status = req.get('status', 'PENDING')
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts['PENDING'] += 1
    
    return render_template(
        "admin_custom_requests.html",
        custom_requests=custom_requests,
        status_counts=status_counts,
        total_requests=len(custom_requests)
    )

#---------------- admin sets price ----------------------------
@app.route('/admin/set-price/<int:request_id>', methods=['POST'])
@admin_required
def set_custom_price(request_id):
    """Admin sets price for custom request"""
 
    price = request.form.get('price')
    notes = request.form.get('notes', '')
    
    if not price or float(price) <= 0:
        flash('Please enter a valid price', 'danger')
        return redirect(url_for('admin_custom_requests'))
    
    try:
      
        db.cursor.execute('''
            UPDATE custom_car_requests 
            SET suggested_price = ?, 
                status = 'PRICE_SET',
                additional_requirements = COALESCE(additional_requirements, '') || ?
            WHERE id = ?
        ''', (float(price), f"\n\nAdmin Notes: {notes}", request_id))
        db.conn.commit()
        
       
        db.cursor.execute('SELECT user_email FROM custom_car_requests WHERE id = ?', (request_id,))
        user_email = db.cursor.fetchone()[0]
        
        
        subject = "Custom Car Price Set - WebWheels"
        body = f"""
Your custom car request has been reviewed!

The admin has set a price for your custom car: ₹{float(price):,.2f}

Please log in to your account to:
1. View the price details
2. Accept or reject the offer
3. If accepted, proceed to payment


Thank you,
WebWheels Team
        """
        db.send_email(user_email, subject, body)
        
        flash(f'Price set to ₹{float(price):,.2f}. User notified via email.', 'success')
    except Exception as e:
        flash(f'Error setting price: {str(e)}', 'danger')
    
    return redirect(url_for('admin_custom_requests'))

#---------------- admin approves after user accepts ----------------
@app.route('/admin/approve-custom/<int:request_id>')
@admin_required
def approve_custom_request(request_id):
    """Admin approves custom request"""
    db.update_custom_request_status(request_id, 'APPROVED')
    flash('Request approved.', 'success')
    return redirect(url_for('admin_custom_requests'))

#-------------------custom invoice route----------------------------
@app.route('/custom-invoice/<int:transaction_id>')
@login_required
def custom_invoice(transaction_id):
    """Invoice for custom car payment"""
    
    db.cursor.execute('''
        SELECT t.*, ccr.*, u.full_name, u.email, u.phone
        FROM transactions t
        JOIN custom_car_requests ccr ON t.id = ?
        JOIN users u ON t.user_id = u.id
        WHERE t.id = ? AND t.user_id = ?
    ''', (transaction_id, transaction_id, session['user_id']))
    
    row = db.cursor.fetchone()
    
    if not row:
        flash('Invoice not found', 'danger')
        return redirect(url_for('my_custom_requests'))

    columns = [desc[0] for desc in db.cursor.description]
    invoice_data = dict(zip(columns, row))
    
    return render_template('custom_invoice.html', invoice=invoice_data)

#---------------- user accepts custom price ----------------
@app.route('/accept-custom-price/<int:request_id>', methods=['GET', 'POST'])
@login_required
def accept_custom_price(request_id):
    """User accepts custom car price and proceeds to payment"""
    
    db.cursor.execute('SELECT * FROM custom_car_requests WHERE id = ? AND user_id = ?', 
                     (request_id, session['user_id']))
    req_row = db.cursor.fetchone()
    
    if not req_row:
        flash('Request not found', 'danger')
        return redirect(url_for('my_custom_requests'))
    
   
    columns = ['id', 'user_id', 'user_name', 'user_email', 'body_type', 'color', 
               'fuel_type', 'engine_cc', 'doors', 'seats', 'transmission', 
               'features', 'additional_requirements', 'suggested_price', 
               'status', 'delivery_address', 'created_at']
    req = dict(zip(columns, req_row))
    
    
    if req['status'] != 'PRICE_SET':
        flash('Price not yet set by admin or already processed', 'warning')
        return redirect(url_for('my_custom_requests'))
    
    if request.method == 'POST':
       
        address = request.form.get('delivery_address', '').strip()
        if not address:
            flash('Please provide a delivery address', 'danger')
            return render_template('accept_custom_price.html', request=req)
        
        
        db.cursor.execute('''
            UPDATE custom_car_requests 
            SET delivery_address = ?, status = 'ACCEPTED' 
            WHERE id = ?
        ''', (address, request_id))
        
        
        base_price = float(req['suggested_price'])
        commission = 0.0          
        total = base_price + commission
        
        
        transaction_id = random.randint(100000, 999999)
        invoice_no = f"CUSTOM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        
        db.cursor.execute('''
            INSERT INTO transactions
            (id, user_id, amount, transaction_type, 
             payment_method, invoice_number, status, commission_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, session['user_id'], total, 'CUSTOM_CAR',
              'PENDING', invoice_no, 'PENDING', commission))
        
       
        db.cursor.execute('''
            UPDATE custom_car_requests 
            SET status = 'PROCESSING' 
            WHERE id = ?
        ''', (request_id,))
        
        db.conn.commit()
        
        
        if 'pending_custom_count' in session and session['pending_custom_count'] > 0:
            session['pending_custom_count'] -= 1
        
        
        session['custom_payment_data'] = {
            'transaction_id': transaction_id,
            'invoice_no': invoice_no,
            'request_id': request_id,
            'base_price': base_price,
            'commission': commission,
            'total': total,
            'delivery_address': address
        }
        
        flash('Please complete the payment to finalize your custom car order.', 'success')
        return redirect(url_for('custom_payment', transaction_id=transaction_id))
    
    return render_template('accept_custom_price.html', request=req)

#---------------- user rejects custom price ----------------
@app.route('/reject-custom-price/<int:request_id>', methods=['GET', 'POST'])
@login_required
def reject_custom_price(request_id):
    """User rejects custom car price"""
   
    db.cursor.execute('SELECT * FROM custom_car_requests WHERE id = ? AND user_id = ?', 
                     (request_id, session['user_id']))
    row = db.cursor.fetchone()
    
    if not row:
        flash('Request not found', 'danger')
        return redirect(url_for('my_custom_requests'))
    
    
    columns = ['id', 'user_id', 'user_name', 'user_email', 'body_type', 'color', 
               'fuel_type', 'engine_cc', 'doors', 'seats', 'transmission', 
               'features', 'additional_requirements', 'suggested_price', 
               'status', 'delivery_address', 'created_at']
    req = dict(zip(columns, row))
    
    if req['status'] != 'PRICE_SET':
        flash('Cannot reject request in current status', 'warning')
        return redirect(url_for('my_custom_requests'))
    
    if request.method == 'POST':
        reason = request.form.get('reason', '')
        
        
        db.update_custom_request_status(request_id, 'REJECTED')
        
        
        if 'pending_custom_count' in session and session['pending_custom_count'] > 0:
            session['pending_custom_count'] -= 1
        
        flash('Custom request rejected successfully.', 'info')
        return redirect(url_for('my_custom_requests'))
  
  
   
    return render_template('reject_custom_price.html', request=req)


def send_invoice_email(self, recipient_email, invoice_data):
        """Send invoice email with complete invoice details"""
        subject = f"Invoice {invoice_data['invoice_number']} - WebWheels"
        
        body = f"""
===========================================
          INVOICE - WebWheels
===========================================

Invoice Number: {invoice_data['invoice_number']}
Date: {invoice_data['date']}

-------------------------------------------
BUYER INFORMATION
-------------------------------------------
Name: {invoice_data['buyer_name']}
Email: {recipient_email}
Phone: {invoice_data['buyer_phone']}
Address: {invoice_data['buyer_address']}

-------------------------------------------
VEHICLE DETAILS
-------------------------------------------
Vehicle: {invoice_data['brand']} {invoice_data['model']}
Year: {invoice_data['year']}
Fuel Type: {invoice_data['fuel_type']}
Transmission: {invoice_data['transmission']}
Color: {invoice_data['color']}
Body Type: {invoice_data['body_type']}

-------------------------------------------
PRICING BREAKDOWN
-------------------------------------------
Base Price: ₹ {invoice_data['base_price']:,.2f}
 (18%): ₹ {invoice_data['']:,.2f}
Commission (8%): ₹ {invoice_data['commission']:,.2f}

-------------------------------------------
TOTAL AMOUNT PAID: ₹ {invoice_data['total_amount']:,.2f}
-------------------------------------------

Payment Method: {invoice_data['payment_method']}
Transaction ID: {invoice_data['transaction_id']}

-------------------------------------------
SELLER INFORMATION
-------------------------------------------
Seller Name: {invoice_data['seller_name']}

-------------------------------------------
DELIVERY ADDRESS
-------------------------------------------
{invoice_data['delivery_address']}

===========================================
Thank you for your purchase!

For any queries, contact us at:
Email: support@vehiclemart.com
Phone: 1800-123-4567
===========================================
        """
        return self.send_email(recipient_email, subject, body)



def send_rental_invoice_email(self, recipient_email, invoice_data):
        """Send rental invoice email with complete details"""
        subject = f"Rental Invoice {invoice_data['invoice_number']} - WebWheels"
        
        body = f"""
===========================================
      RENTAL INVOICE - WebWheels
===========================================

Invoice Number: {invoice_data['invoice_number']}
Date: {invoice_data['date']}

-------------------------------------------
RENTER INFORMATION
-------------------------------------------
Name: {invoice_data['renter_name']}
Email: {recipient_email}
Phone: {invoice_data['renter_phone']}

-------------------------------------------
VEHICLE DETAILS
-------------------------------------------
Vehicle: {invoice_data['brand']} {invoice_data['model']}
Year: {invoice_data['year']}
Transmission: {invoice_data['transmission']}

-------------------------------------------
RENTAL DETAILS
-------------------------------------------
Rental Period: {invoice_data['start_date']} to {invoice_data['end_date']}
Duration: {invoice_data['rental_days']} days

-------------------------------------------
PRICING BREAKDOWN
-------------------------------------------
Rental Amount: ₹ {invoice_data['rent_amount']:,.2f}
 (18%): ₹ {invoice_data['']:,.2f}
Security Deposit: ₹ {invoice_data['deposit']:,.2f}
Commission (8%): ₹ {invoice_data['commission']:,.2f}

-------------------------------------------
TOTAL AMOUNT PAID: ₹ {invoice_data['total_amount']:,.2f}
-------------------------------------------

Payment Method: {invoice_data['payment_method']}
Transaction ID: {invoice_data['transaction_id']}

-------------------------------------------
OWNER INFORMATION
-------------------------------------------
Owner Name: {invoice_data['owner_name']}

===========================================
Thank you for renting with us!

For any queries, contact us at:
Email: support@vehiclemart.com
Phone: 1800-123-4567
===========================================
        """
        return self.send_email(recipient_email, subject, body)

 
def hash_password(self, password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


@app.route('/custom-payment/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def custom_payment(transaction_id):
    """Payment page for custom car – updates admin balance on success"""

    payment_data = session.get('custom_payment_data', {})
    
    if not payment_data or payment_data.get('transaction_id') != transaction_id:
        flash('Payment session expired or invalid', 'danger')
        return redirect(url_for('my_custom_requests'))
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        
        db.cursor.execute('''
            UPDATE transactions 
            SET payment_method = ?, status = 'COMPLETED'
            WHERE id = ?
        ''', (payment_method, transaction_id))
        
        db.cursor.execute('''
            UPDATE custom_car_requests 
            SET status = 'PAID' 
            WHERE id = ?
        ''', (payment_data['request_id'],))
        
        # 👇 **ADD THE PAYMENT TO ADMIN BALANCE** (admin earns money)
        # First, get the admin user ID (the one with role='ADMIN')
        db.cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
        admin_row = db.cursor.fetchone()
        if not admin_row:
            flash('Admin account not found! Please contact support.', 'danger')
            return redirect(url_for('my_custom_requests'))
        
        admin_id = admin_row[0]
        total_amount = payment_data['total']
        
        
        db.cursor.execute('''
            UPDATE admin_balance 
            SET balance = balance + ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (total_amount, admin_id))
        
       
        db.conn.commit()
        
       
        session.pop('custom_payment_data', None)
        
        flash('Payment successful! Your custom car is now in production.', 'success')
        return redirect(url_for('custom_invoice', transaction_id=transaction_id))
    
    return render_template('custom_payment.html', 
                         payment_data=payment_data,
                         transaction_id=transaction_id)
    
# ==================================== ADDITIONAL ROUTES ========================
@app.route('/advanced-search')
def advanced_search():
    """Advanced search for vehicles with multiple filters"""
    
    db.cursor.execute('SELECT DISTINCT brand FROM vehicles WHERE status = ? AND vehicle_type = ?', ('APPROVED', 'SELL'))
    brands = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT model FROM vehicles WHERE status = ? AND vehicle_type = ?', ('APPROVED', 'SELL'))
    all_models = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT body_type FROM vehicles WHERE status = ? AND body_type IS NOT NULL', ('APPROVED',))
    body_types = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT fuel_type FROM vehicles WHERE status = ? AND fuel_type IS NOT NULL', ('APPROVED',))
    fuel_types = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT transmission FROM vehicles WHERE status = ? AND transmission IS NOT NULL', ('APPROVED',))
    transmissions = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT color FROM vehicles WHERE status = ? AND color IS NOT NULL', ('APPROVED',))
    colors = [row[0] for row in db.cursor.fetchall()]
    
    db.cursor.execute('SELECT DISTINCT year FROM vehicles WHERE status = ? ORDER BY year DESC', ('APPROVED',))
    years = [str(row[0]) for row in db.cursor.fetchall()]
    
    
    search_query = request.args.get('search', '')
    brand_filter = request.args.get('brand', '')
    model_filter = request.args.get('model', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    min_year = request.args.get('min_year', '')
    max_year = request.args.get('max_year', '')
    body_type = request.args.get('body_type', '')
    fuel_type = request.args.get('fuel_type', '')
    transmission = request.args.get('transmission', '')
    color = request.args.get('color', '')
    min_mileage = request.args.get('min_mileage', '')
    max_mileage = request.args.get('max_mileage', '')
    min_engine = request.args.get('min_engine', '')
    max_engine = request.args.get('max_engine', '')
    seats = request.args.get('seats', '')
    sort_by = request.args.get('sort', 'newest')
    vehicle_type_filter = request.args.get('vehicle_type', 'all')
    
    
    query = 'SELECT v.*, u.username FROM vehicles v JOIN users u ON v.seller_id = u.id WHERE v.status = ?'
    params = ['APPROVED']
    
    
    if vehicle_type_filter == 'sale':
        query += ' AND v.vehicle_type = ?'
        params.append('SELL')
    elif vehicle_type_filter == 'rent':
        query += ' AND v.vehicle_type = ?'
        params.append('RENT')
    
   
    if search_query:
        query += ' AND (v.brand LIKE ? OR v.model LIKE ? OR v.color LIKE ? OR v.body_type LIKE ? OR v.fuel_type LIKE ? OR v.transmission LIKE ?)'
        search_term = f'%{search_query}%'
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term])
    
    
    if brand_filter:
        query += ' AND v.brand = ?'
        params.append(brand_filter)
    
   
    if model_filter:
        query += ' AND v.model = ?'
        params.append(model_filter)
    
    
    if min_price:
        query += ' AND v.price >= ?'
        params.append(float(min_price))
    
    if max_price:
        query += ' AND v.price <= ?'
        params.append(float(max_price))
    
    
    if min_year:
        query += ' AND v.year >= ?'
        params.append(int(min_year))
    
    if max_year:
        query += ' AND v.year <= ?'
        params.append(int(max_year))
    
    
    if body_type:
        query += ' AND v.body_type = ?'
        params.append(body_type)
    
    
    if fuel_type:
        query += ' AND v.fuel_type = ?'
        params.append(fuel_type)
    
    
    if transmission:
        query += ' AND v.transmission = ?'
        params.append(transmission)
    
    
    if color:
        query += ' AND v.color = ?'
        params.append(color)
    
   
    if min_mileage:
        query += ' AND v.mileage >= ?'
        params.append(float(min_mileage))
    
    if max_mileage:
        query += ' AND v.mileage <= ?'
        params.append(float(max_mileage))
    
   
    if min_engine:
        query += ' AND v.engine_cc >= ?'
        params.append(float(min_engine))
    
    if max_engine:
        query += ' AND v.engine_cc <= ?'
        params.append(float(max_engine))
    
    
    if seats:
        query += ' AND v.seats = ?'
        params.append(int(seats))
    
    
    if sort_by == 'price_low':
        query += ' ORDER BY v.price ASC'
    elif sort_by == 'price_high':
        query += ' ORDER BY v.price DESC'
    elif sort_by == 'year_new':
        query += ' ORDER BY v.year DESC'
    elif sort_by == 'year_old':
        query += ' ORDER BY v.year ASC'
    elif sort_by == 'mileage_low':
        query += ' ORDER BY v.mileage ASC'
    elif sort_by == 'mileage_high':
        query += ' ORDER BY v.mileage DESC'
    elif sort_by == 'oldest':
        query += ' ORDER BY v.created_at ASC'
    else:
        query += ' ORDER BY v.created_at DESC'
    
    db.cursor.execute(query, params)
    vehicles = db.cursor.fetchall()
    
   
    filtered_models = []
    if brand_filter:
        db.cursor.execute('SELECT DISTINCT model FROM vehicles WHERE brand = ? AND status = ?', (brand_filter, 'APPROVED'))
        filtered_models = [row[0] for row in db.cursor.fetchall()]
    
    return render_template('advanced_search.html', 
                         vehicles=vehicles, 
                         brands=brands,
                         all_models=all_models,
                         filtered_models=filtered_models,
                         body_types=body_types,
                         fuel_types=fuel_types,
                         transmissions=transmissions,
                         colors=colors,
                         years=years,
                         search_query=search_query,
                         selected_brand=brand_filter,
                         selected_model=model_filter,
                         min_price=min_price,
                         max_price=max_price,
                         min_year=min_year,
                         max_year=max_year,
                         selected_body_type=body_type,
                         selected_fuel=fuel_type,
                         selected_transmission=transmission,
                         selected_color=color,
                         min_mileage=min_mileage,
                         max_mileage=max_mileage,
                         min_engine=min_engine,
                         max_engine=max_engine,
                         selected_seats=seats,
                         sort_by=sort_by,
                         vehicle_type_filter=vehicle_type_filter)

#=================== Buy Cars Route with Advanced Search ==============================
@app.route('/buy-cars')
def buy_cars():
    """Browse cars for sale with advanced search"""
   
    db.cursor.execute('SELECT DISTINCT brand FROM vehicles WHERE status = ? AND vehicle_type = ?', ('APPROVED', 'SELL'))
    brands = [row[0] for row in db.cursor.fetchall()]
    
    
    db.cursor.execute('SELECT DISTINCT brand, model FROM vehicles WHERE status = ? AND vehicle_type = ?', ('APPROVED', 'SELL'))
    models_data = db.cursor.fetchall()
    
    
    search_query = request.args.get('search', '')
    brand_filter = request.args.get('brand', '')
    model_filter = request.args.get('model', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    body_type = request.args.get('body_type', '')
    fuel_type = request.args.get('fuel_type', '')
    transmission = request.args.get('transmission', '')
    sort_by = request.args.get('sort', 'newest')
    
    
    query = 'SELECT * FROM vehicles WHERE status = ? AND vehicle_type = ?'
    params = ['APPROVED', 'SELL']
    
    if search_query:
        query += ' AND (brand LIKE ? OR model LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if brand_filter:
        query += ' AND brand = ?'
        params.append(brand_filter)
    
    if model_filter:
        query += ' AND model = ?'
        params.append(model_filter)
    
    if min_price:
        query += ' AND price >= ?'
        params.append(float(min_price))
    
    if max_price:
        query += ' AND price <= ?'
        params.append(float(max_price))
    
    if body_type:
        query += ' AND body_type = ?'
        params.append(body_type)
    
    if fuel_type:
        query += ' AND fuel_type = ?'
        params.append(fuel_type)
    
    if transmission:
        query += ' AND transmission = ?'
        params.append(transmission)
    
    
    if sort_by == 'price_low':
        query += ' ORDER BY price ASC'
    elif sort_by == 'price_high':
        query += ' ORDER BY price DESC'
    elif sort_by == 'oldest':
        query += ' ORDER BY created_at ASC'
    else:
        query += ' ORDER BY created_at DESC'
    
    db.cursor.execute(query, params)
    vehicles = db.cursor.fetchall()
    
    
    models_by_brand = {}
    for row in models_data:
        if row[0] not in models_by_brand:
            models_by_brand[row[0]] = []
        models_by_brand[row[0]].append(row[1])
    
    return render_template('buy_cars.html', vehicles=vehicles, brands=brands,
                         models_by_brand=models_by_brand, search_query=search_query,
                         selected_brand=brand_filter, selected_model=model_filter,
                         min_price=min_price, max_price=max_price,
                         selected_body_type=body_type, selected_fuel=fuel_type,
                         selected_transmission=transmission, sort_by=sort_by)
    
#=================== Rent Cars Route with Auto-Release of Expired Rentals ==============================
@app.route('/rent-cars')
def rent_cars():
    """Browse cars for rent"""
    from datetime import datetime
    
    
    db.cursor.execute('''
        UPDATE rentals SET is_available = 1, renter_id = NULL, 
        start_date = NULL, end_date = NULL, status = 'AVAILABLE'
        WHERE status = 'RENTED' AND end_date < ?
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    db.conn.commit()
    
    
    db.cursor.execute('''
        SELECT v.*, r.id as rental_id, r.daily_rate, r.hourly_rate, 
               r.weekly_rate, r.monthly_rate, r.security_deposit,
               r.is_available, r.end_date, u.username as owner_name
        FROM vehicles v
        JOIN rentals r ON v.id = r.vehicle_id
        JOIN users u ON r.owner_id = u.id
        WHERE v.status = 'APPROVED'
        ORDER BY r.is_available DESC, v.created_at DESC
    ''')
    
    rentals = []
    for row in db.cursor.fetchall():
        rentals.append(dict(row))
    
    return render_template('rent_cars.html', rentals=rentals)

#=================== Search Route with Multiple Field Search ==============================
@app.route('/search')
def search():
    """Search vehicles"""
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('buy_cars'))
    
    
    db.cursor.execute('''
        SELECT * FROM vehicles 
        WHERE status = 'APPROVED'
        AND (brand LIKE ? OR model LIKE ? OR body_type LIKE ? OR fuel_type LIKE ?)
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    
    vehicles = db.cursor.fetchall()
    
    
    db.cursor.execute('SELECT DISTINCT brand FROM vehicles WHERE status = ?', ('APPROVED',))
    brands = [row[0] for row in db.cursor.fetchall()]
    
    return render_template('buy_cars.html', vehicles=vehicles,
                         brands=brands, search_query=query)


@app.route('/view-invoice/<int:tid>')
@login_required
def view_invoice(tid):
    """View invoice"""
    db.cursor.execute('''
        SELECT t.*, v.brand, v.model, v.year, v.vehicle_type,
               u.username, u.email, u.full_name, u.phone, u.address as user_address
        FROM transactions t
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN users u ON t.user_id = u.id
        WHERE t.id = ?
    ''', (tid,))
    
    transaction = db.cursor.fetchone()
    
    if transaction:
        transaction = dict(transaction)
        
        if transaction['transaction_type'] == 'SALE':
            base_price = transaction['amount'] - (transaction['commission_amount'] or 0)
        else:
            base_price = transaction['amount'] - (transaction['commission_amount'] or 0)
        
        total = base_price + (transaction['commission_amount'] or 0)
        
        return render_template('invoice.html', transaction=transaction, base_price=base_price)
    
    flash('Transaction not found', 'danger')
    return redirect(url_for('index'))

@app.route('/car/<int:car_id>')
def car_details(car_id):
    """View car details"""
    db.cursor.execute('SELECT * FROM vehicles WHERE id = ?', (car_id,))
    car = db.cursor.fetchone()
    
    if not car:
        flash('Car not found', 'danger')
        return redirect(url_for('buy_cars'))
    
    return render_template('car_details.html', car=car)

@app.route('/rent/<int:car_id>')
def rent_details(car_id):
    """View rental car details"""
    from datetime import datetime
    
    # Auto-release expired rentals
    db.cursor.execute('''
        UPDATE rentals SET is_available = 1, renter_id = NULL, 
        start_date = NULL, end_date = NULL, status = 'AVAILABLE'
        WHERE status = 'RENTED' AND end_date < ?
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    db.conn.commit()
    
    db.cursor.execute('''
        SELECT v.*, r.*, u.username as owner_name
        FROM vehicles v
        JOIN rentals r ON v.id = r.vehicle_id
        JOIN users u ON r.owner_id = u.id
        WHERE v.id = ?
    ''', (car_id,))
    
    car = db.cursor.fetchone()
    
    if not car:
        flash('Car not found', 'danger')
        return redirect(url_for('rent_cars'))
    
    return render_template('rent_details.html', car=dict(car), datetime=datetime)

@app.route('/rent/<int:car_id>/book', methods=['GET', 'POST'])
@login_required
def book_rental(car_id):
    """Book a rental car"""
    from datetime import datetime
    
    db.cursor.execute('''
        SELECT v.*, r.* FROM vehicles v
        JOIN rentals r ON v.id = r.vehicle_id
        WHERE v.id = ? AND r.is_available = 1
    ''', (car_id,))
    
    rental = db.cursor.fetchone()
    
    if not rental:
        flash('Car not available for rental', 'danger')
        return redirect(url_for('rent_cars'))
    
    if request.method == 'POST':
        rental_type = request.form.get('rental_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        payment_method = request.form.get('payment_method')
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        duration = (end - start).days
        
        if duration <= 0:
            flash('Invalid date selection', 'danger')
            return redirect(url_for('book_rental', car_id=car_id))
        
        rates = {
            'hourly': rental['hourly_rate'] or 0,
            'daily': rental['daily_rate'],
            'weekly': rental['weekly_rate'] or 0,
            'monthly': rental['monthly_rate'] or 0
        }
        
        rent_amount = rates.get(rental_type, rates['daily']) * duration
        commission = rent_amount * 0.08
        deposit = rental['security_deposit']
        total = rent_amount + commission + deposit
        
        
        transaction_id = random.randint(100000, 999999)
        invoice = f"RENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        db.cursor.execute('''
            INSERT INTO transactions
            (user_id, vehicle_id, seller_id, amount, transaction_type,
             payment_method, invoice_number, status, commission_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], rental['vehicle_id'], rental['owner_id'],
              total, 'RENTAL', payment_method, invoice, 'COMPLETED', commission))
        
        
        db.cursor.execute('''
            UPDATE rentals SET
                renter_id = ?, start_date = ?, end_date = ?,
                rental_days = ?, total_amount = ?, status = 'RENTED', is_available = 0
            WHERE id = ?
        ''', (session['user_id'], start_date, end_date, duration, total, rental['rental_id']))
        
        db.conn.commit()
        
        return redirect(url_for('view_invoice', tid=transaction_id))
    
    return render_template('book_rental.html', rental=rental)

if __name__ == "__main__":
    app.run(debug=True)
