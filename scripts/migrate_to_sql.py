"""
migrate_to_sql.py - Migrate data from MongoDB/Cosmos DB to Azure SQL Database
This script helps transition your Executive Orders RAG Chatbot from MongoDB to Azure SQL.
"""

import os
import sys
import json
import logging
import pymongo
import pyodbc
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'eobot')

# Azure SQL connection settings
SQL_SERVER = os.getenv('SQL_SERVER')
SQL_DATABASE = os.getenv('SQL_DATABASE')
SQL_USERNAME = os.getenv('SQL_USERNAME')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')
SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')

def connect_mongodb():
    """Connect to MongoDB/Cosmos DB"""
    try:
        client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
        db = client[MONGODB_DATABASE]
        logger.info(f"Connected to MongoDB database: {MONGODB_DATABASE}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def connect_azure_sql():
    """Connect to Azure SQL Database"""
    try:
        connection_string = (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD}"
        )
        conn = pyodbc.connect(connection_string)
        logger.info(f"Connected to Azure SQL database: {SQL_DATABASE}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Azure SQL: {e}")
        raise

def create_sql_tables(conn):
    """Create the necessary tables in Azure SQL Database"""
    try:
        cursor = conn.cursor()
        
        # Create Users table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
        CREATE TABLE Users (
            UserID VARCHAR(50) PRIMARY KEY,
            Email VARCHAR(255) NOT NULL,
            PasswordHash VARCHAR(255) NOT NULL,
            [Plan] VARCHAR(50) DEFAULT 'free',
            CreatedAt DATETIME NOT NULL,
            LastLogin DATETIME NULL,
            StripeCustomerID VARCHAR(255) NULL,
            SubscriptionID VARCHAR(255) NULL
        )
        """)
        
        # Create ChatMessages table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ChatMessages')
        CREATE TABLE ChatMessages (
            MessageID VARCHAR(50) PRIMARY KEY,
            UserID VARCHAR(50) NOT NULL,
            ConversationID VARCHAR(50) NOT NULL,
            Sender VARCHAR(50) NOT NULL,
            Text NVARCHAR(MAX) NOT NULL,
            Timestamp DATETIME NOT NULL,
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
        """)
        
        # Create UsageStats table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'UsageStats')
        CREATE TABLE UsageStats (
            UsageID VARCHAR(50) PRIMARY KEY,
            UserID VARCHAR(50) NOT NULL,
            Timestamp DATETIME NOT NULL,
            Tokens INT NOT NULL DEFAULT 0,
            Type VARCHAR(50) NOT NULL,
            QueryData NVARCHAR(MAX) NULL,
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
        """)
        
        # Create AdminIPs table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'AdminIPs')
        CREATE TABLE AdminIPs (
            ID VARCHAR(50) PRIMARY KEY,
            IPAddress VARCHAR(50) NOT NULL,
            AddedAt DATETIME NOT NULL
        )
        """)
        
        conn.commit()
        logger.info("SQL tables created successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create SQL tables: {e}")
        raise

def migrate_users(mongo_db, sql_conn):
    """Migrate users from MongoDB to SQL"""
    try:
        cursor = sql_conn.cursor()
        users_collection = mongo_db.users
        users = list(users_collection.find())
        
        logger.info(f"Migrating {len(users)} users...")
        
        for user in users:
            # Extract user data
            user_id = user.get('_id') or str(uuid.uuid4())
            email = user.get('email')
            password_hash = user.get('password_hash')
            
            if not email or not password_hash:
                logger.warning(f"Skipping user with missing data: {user_id}")
                continue
            
            # Handle dates
            created_at = user.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif not created_at:
                created_at = datetime.utcnow()
                
            last_login = user.get('last_login')
            if isinstance(last_login, str):
                last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            
            # Insert into SQL
            cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Users WHERE UserID = ?)
            INSERT INTO Users (
                UserID, Email, PasswordHash, [Plan], CreatedAt, LastLogin, 
                StripeCustomerID, SubscriptionID
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, 
            user_id, user_id, email, password_hash, 
            user.get('plan', 'free'), created_at, last_login,
            user.get('stripe_customer_id'), user.get('subscription_id'))
        
        sql_conn.commit()
        logger.info("Users migration completed successfully")
    except Exception as e:
        sql_conn.rollback()
        logger.error(f"Failed to migrate users: {e}")
        raise

def migrate_chat_messages(mongo_db, sql_conn):
    """Migrate chat messages from MongoDB to SQL"""
    try:
        cursor = sql_conn.cursor()
        messages_collection = mongo_db.chat_messages
        messages = list(messages_collection.find())
        
        logger.info(f"Migrating {len(messages)} chat messages...")
        
        for msg in messages:
            # Extract message data
            message_id = msg.get('_id') or str(uuid.uuid4())
            user_id = msg.get('user_id')
            conversation_id = msg.get('conversation_id')
            sender = msg.get('sender')
            text = msg.get('text')
            
            if not user_id or not conversation_id or not sender or text is None:
                logger.warning(f"Skipping message with missing data: {message_id}")
                continue
            
            # Handle timestamp
            timestamp = msg.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not timestamp:
                timestamp = datetime.utcnow()
            
            # Insert into SQL
            cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM ChatMessages WHERE MessageID = ?)
            INSERT INTO ChatMessages (
                MessageID, UserID, ConversationID, Sender, Text, Timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, 
            message_id, message_id, user_id, conversation_id, sender, text, timestamp)
        
        sql_conn.commit()
        logger.info("Chat messages migration completed successfully")
    except Exception as e:
        sql_conn.rollback()
        logger.error(f"Failed to migrate chat messages: {e}")
        raise

def migrate_usage_stats(mongo_db, sql_conn):
    """Migrate usage statistics from MongoDB to SQL"""
    try:
        cursor = sql_conn.cursor()
        stats_collection = mongo_db.usage_stats
        stats = list(stats_collection.find())
        
        logger.info(f"Migrating {len(stats)} usage statistics...")
        
        for stat in stats:
            # Extract usage data
            usage_id = stat.get('_id') or str(uuid.uuid4())
            user_id = stat.get('user_id')
            
            # Skip IP-based stats if moving to user-based only
            if not user_id:
                logger.info(f"Skipping IP-based usage stat: {usage_id}")
                continue
            
            tokens = stat.get('tokens', 0)
            request_type = stat.get('type', 'prompt')
            
            # Handle timestamp
            timestamp = stat.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not timestamp:
                timestamp = datetime.utcnow()
            
            # Handle data field
            data = stat.get('data')
            if data:
                if isinstance(data, dict):
                    data = json.dumps(data)
            
            # Insert into SQL
            cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM UsageStats WHERE UsageID = ?)
            INSERT INTO UsageStats (
                UsageID, UserID, Timestamp, Tokens, Type, QueryData
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, 
            usage_id, usage_id, user_id, timestamp, tokens, request_type, data)
        
        sql_conn.commit()
        logger.info("Usage statistics migration completed successfully")
    except Exception as e:
        sql_conn.rollback()
        logger.error(f"Failed to migrate usage statistics: {e}")
        raise

def migrate_admin_ips(mongo_db, sql_conn):
    """Migrate admin IPs from MongoDB to SQL"""
    try:
        cursor = sql_conn.cursor()
        admin_collection = mongo_db.admin
        admin_ips = list(admin_collection.find({"type": "admin_ip"}))
        
        logger.info(f"Migrating {len(admin_ips)} admin IPs...")
        
        for ip_doc in admin_ips:
            # Extract IP data
            ip_id = ip_doc.get('_id') or str(uuid.uuid4())
            ip_address = ip_doc.get('ip')
            
            if not ip_address:
                logger.warning(f"Skipping admin IP with missing data: {ip_id}")
                continue
            
            # Handle timestamp
            added_at = ip_doc.get('added_at')
            if isinstance(added_at, str):
                added_at = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
            elif not added_at:
                added_at = datetime.utcnow()
            
            # Insert into SQL
            cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM AdminIPs WHERE IPAddress = ?)
            INSERT INTO AdminIPs (ID, IPAddress, AddedAt) VALUES (?, ?, ?)
            """, 
            ip_address, ip_id, ip_address, added_at)
        
        sql_conn.commit()
        logger.info("Admin IPs migration completed successfully")
    except Exception as e:
        sql_conn.rollback()
        logger.error(f"Failed to migrate admin IPs: {e}")
        raise

def main():
    """Main migration function"""
    logger.info("Starting migration from MongoDB to Azure SQL Database")
    
    try:
        # Connect to databases
        mongo_db = connect_mongodb()
        sql_conn = connect_azure_sql()
        
        # Create SQL tables
        create_sql_tables(sql_conn)
        
        # Migrate data
        migrate_users(mongo_db, sql_conn)
        migrate_chat_messages(mongo_db, sql_conn)
        migrate_usage_stats(mongo_db, sql_conn)
        migrate_admin_ips(mongo_db, sql_conn)
        
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        # Close connections
        if 'sql_conn' in locals():
            sql_conn.close()
        logger.info("Database connections closed")

if __name__ == "__main__":
    main()