from flask import Flask, request, jsonify, send_file
import os
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import json

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# --- MongoDB Connection ---
# Replace the connection string with your own if it's different.
# By default, MongoDB runs on port 27017 on localhost.
try:
    client = MongoClient(os.environ.get("mongodb+srv://abhilasha-108:108108@cluster0.owce1kn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"))
    db = client['library_db']  # Use or create a database named 'library_db'
    books_collection = db['books']  # Collection for books
    users_collection = db['users']  # Collection for users
    borrowed_collection = db['borrowed']  # Collection for borrowed transactions
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Function to serve the main HTML file
@app.route('/')
def serve_html():
    """Serves the main HTML file."""
    try:
        return send_file('library_website.html')
    except Exception as e:
        return jsonify({"message": f"Error serving file: {e}", "status": "error"}), 500

# Function to get dashboard counts from MongoDB
@app.route('/dashboard_counts', methods=['GET'])
def get_dashboard_counts():
    """Returns counts for the dashboard from MongoDB."""
    total_books = books_collection.count_documents({})
    total_users = users_collection.count_documents({})
    borrowed_books_count = borrowed_collection.count_documents({"return_date": None})
    
    return jsonify({
        "total_books": total_books,
        "total_users": total_users,
        "borrowed_books": borrowed_books_count
    })

# Function to add a book to the database
@app.route('/add_book', methods=['POST'])
def add_book():
    """Adds a new book to the library in MongoDB."""
    data = request.json
    title = data.get('title')
    author = data.get('author')
    isbn = data.get('isbn')
    
    if not all([title, author, isbn]):
        return jsonify({"message": "All fields are required.", "status": "error"}), 400
    
    # Check if a book with this ISBN already exists
    if books_collection.find_one({"isbn": isbn}):
        return jsonify({"message": "A book with this ISBN already exists.", "status": "error"}), 409
    
    new_book = {"title": title, "author": author, "isbn": isbn, "is_borrowed": False}
    books_collection.insert_one(new_book)
    return jsonify({"message": "Book added successfully.", "status": "success"})

# Function to add a user to the database
@app.route('/add_user', methods=['POST'])
def add_user():
    """Adds a new user to the system in MongoDB."""
    data = request.json
    name = data.get('name')
    user_id = data.get('user_id')
    
    if not all([name, user_id]):
        return jsonify({"message": "All fields are required.", "status": "error"}), 400
    
    # Check if a user with this ID already exists
    if users_collection.find_one({"user_id": user_id}):
        return jsonify({"message": "A user with this ID already exists.", "status": "error"}), 409
    
    new_user = {"name": name, "user_id": user_id}
    users_collection.insert_one(new_user)
    return jsonify({"message": "User added successfully.", "status": "success"})

# Function to handle borrowing a book in the database
@app.route('/borrow_book', methods=['POST'])
def borrow_book():
    """Handles the borrowing of a book, updating MongoDB."""
    data = request.json
    user_id = data.get('user_id')
    isbn = data.get('isbn')

    book = books_collection.find_one({"isbn": isbn})
    user = users_collection.find_one({"user_id": user_id})

    if not book:
        return jsonify({"message": "Book not found.", "status": "error"}), 404
    
    if book.get('is_borrowed', False):
        return jsonify({"message": "Book is already borrowed.", "status": "error"}), 409
        
    if not user:
        return jsonify({"message": "User not found.", "status": "error"}), 404

    # Update the book's status and add a new borrowed transaction
    books_collection.update_one({"isbn": isbn}, {"$set": {"is_borrowed": True}})
    
    new_borrowed = {
        "user_id": user_id, 
        "isbn": isbn, 
        "borrow_date": "2023-01-15",
        "book_title": book.get('title'),
        "user_name": user.get('name')
    }
    borrowed_collection.insert_one(new_borrowed)
    
    return jsonify({"message": "Book borrowed successfully.", "status": "success"})

# Function to handle returning a book in the database
@app.route('/return_book', methods=['POST'])
def return_book():
    """Handles the return of a book, updating MongoDB."""
    data = request.json
    user_id = data.get('user_id')
    isbn = data.get('isbn')

    book = books_collection.find_one({"isbn": isbn})
    if not book:
        return jsonify({"message": "Book not found.", "status": "error"}), 404

    if not book.get('is_borrowed', False):
        return jsonify({"message": "This book is not currently borrowed.", "status": "error"}), 409

    borrow_record = borrowed_collection.find_one({"isbn": isbn, "user_id": user_id, "return_date": None})
    if not borrow_record:
        return jsonify({"message": "This book was not borrowed by this user.", "status": "error"}), 404
    
    # Update the book's status and the borrowed transaction's return date
    books_collection.update_one({"isbn": isbn}, {"$set": {"is_borrowed": False}})
    borrowed_collection.update_one(
        {"isbn": isbn, "user_id": user_id, "return_date": None},
        {"$set": {"return_date": "2023-01-16"}} # Using a placeholder date
    )
    
    return jsonify({"message": "Book returned successfully.", "status": "success"})

# Function to get all books from the database
@app.route('/all_books', methods=['GET'])
def get_all_books():
    """Returns a list of all books from MongoDB."""
    all_books = list(books_collection.find({}, {'_id': 0}))
    return jsonify(all_books)

# Function to get all users from the database
@app.route('/all_users', methods=['GET'])
def get_all_users():
    """Returns a list of all users from MongoDB."""
    all_users = list(users_collection.find({}, {'_id': 0}))
    return jsonify(all_users)

# Function to get all currently borrowed books from the database
@app.route('/borrowed_books', methods=['GET'])
def get_borrowed_books():
    """Returns a list of all currently borrowed books from MongoDB."""
    borrowed_books = list(borrowed_collection.find({"return_date": None}, {'_id': 0}))
    return jsonify(borrowed_books)

# Function to delete a book from the database
@app.route('/delete_book/<isbn>', methods=['DELETE'])
def delete_book(isbn):
    """Deletes a book by ISBN from MongoDB."""
    book_to_delete = books_collection.find_one({"isbn": isbn})
    if not book_to_delete:
        return jsonify({"message": "Book not found.", "status": "error"}), 404
        
    if book_to_delete.get('is_borrowed', False):
        return jsonify({"message": "Cannot delete a book that is currently borrowed.", "status": "error"}), 409
    
    books_collection.delete_one({"isbn": isbn})
    return jsonify({"message": "Book deleted successfully.", "status": "success"})

# Function to delete a user from the database
@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Deletes a user by user ID from MongoDB."""
    user_to_delete = users_collection.find_one({"user_id": user_id})
    if not user_to_delete:
        return jsonify({"message": "User not found.", "status": "error"}), 404

    # Check if the user has any borrowed books
    if borrowed_collection.find_one({"user_id": user_id, "return_date": None}):
        return jsonify({"message": "Cannot delete a user with borrowed books.", "status": "error"}), 409
    
    users_collection.delete_one({"user_id": user_id})
    return jsonify({"message": "User deleted successfully.", "status": "success"})


